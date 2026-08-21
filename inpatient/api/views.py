"""Inpatient endpoints for the mobile client.

A thin JSON skin over `inpatient.services` — admitting, discharging,
transferring and the daily charge rule are shared with the HTML views, not
restated here.
"""
from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from billing.models import Service
from patients.models import Patient, PatientWallet

from ..models import (
    Admission, Bed, ClinicalRecord, DailyRound, InpatientMedication,
    NursingNote, Ward,
)
from ..services import (
    InpatientActionError, admit_patient, discharge_patient, transfer_patient,
)
from .serializers import (
    AdmissionChargesSerializer, AdmissionSerializer, BedSerializer,
    ClinicalRecordSerializer, DailyRoundSerializer,
    InpatientMedicationSerializer, NursingNoteSerializer, WardSerializer,
)
from saas.api import TenantScopedQuerysetMixin

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class InpatientPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


class WardViewSet(viewsets.ReadOnlyModelViewSet):
    """The ward board: every ward with its live bed counts."""

    queryset = Ward.objects.all()
    serializer_class = WardSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InpatientPagination

    def get_queryset(self):
        queryset = Ward.objects.prefetch_related('beds').order_by('name')
        params = self.request.query_params
        if params.get('search'):
            queryset = queryset.filter(
                Q(name__icontains=params['search']) |
                Q(floor__icontains=params['search'])
            )
        if params.get('ward_type'):
            queryset = queryset.filter(ward_type=params['ward_type'])
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset


class BedViewSet(viewsets.ReadOnlyModelViewSet):
    """Beds, filtered the way a bed map asks for them."""

    queryset = Bed.objects.all()
    serializer_class = BedSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InpatientPagination

    def get_queryset(self):
        queryset = (
            Bed.objects
            .select_related('ward')
            .prefetch_related(Prefetch(
                'admissions',
                queryset=Admission.objects.filter(
                    status='admitted').select_related('patient'),
                to_attr='current_admissions_list',
            ))
            .order_by('ward__name', 'bed_number')
        )
        params = self.request.query_params
        if params.get('ward'):
            queryset = queryset.filter(ward_id=params['ward'])
        if params.get('free') == 'true':
            queryset = queryset.filter(is_occupied=False, is_active=True)
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset


class AdmissionViewSet(viewsets.ModelViewSet):
    """Admissions and everything the ward does to one."""

    queryset = Admission.objects.all()
    serializer_class = AdmissionSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = InpatientPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # Discharge is its own right (Admission.discharge_patient), and the
        # workflow actions are not "may this user add an admission".
        if self.action in ('discharge', 'transfer', 'charges'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Admission.objects
            .select_related('patient', 'patient__wallet', 'bed', 'bed__ward',
                            'attending_doctor')
            .order_by('-admission_date')
        )
        params = self.request.query_params
        # Wards care about who is in a bed now; everything else is history.
        status_filter = params.get('status') or 'admitted'
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('ward'):
            queryset = queryset.filter(bed__ward_id=params['ward'])
        if params.get('doctor'):
            queryset = queryset.filter(attending_doctor_id=params['doctor'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search']) |
                Q(diagnosis__icontains=params['search'])
            )
        return queryset

    def get_object(self):
        # The list defaults to current inpatients; a detail route addresses one
        # admission by id and must still find a discharged one.
        admission = get_object_or_404(Admission, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, admission)
        return admission

    def create(self, request, *args, **kwargs):
        """Admit a patient: takes the bed, raises the invoice, charges the wallet."""
        data = request.data
        patient = get_object_or_404(Patient, id=data.get('patient'))
        bed = get_object_or_404(Bed, id=data.get('bed'))
        doctor_id = data.get('attending_doctor') or request.user.id
        doctor = get_object_or_404(get_user_model(), id=doctor_id, is_active=True)

        service = None
        if data.get('admission_service'):
            service = get_object_or_404(Service, id=data['admission_service'])

        code = None
        if data.get('authorization_code'):
            from nhia.models import AuthorizationCode
            code = get_object_or_404(
                AuthorizationCode, id=data['authorization_code']
            )

        try:
            admission, invoice = admit_patient(
                patient=patient,
                bed=bed,
                attending_doctor=doctor,
                diagnosis=data.get('diagnosis', ''),
                reason_for_admission=data.get('reason_for_admission', ''),
                user=request.user,
                admission_notes=data.get('admission_notes', ''),
                admission_service=service,
                authorization_code=code,
            )
        except InpatientActionError as e:
            return _error(e)

        payload = AdmissionSerializer(admission).data
        payload['invoice'] = invoice.id if invoice else None
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def discharge(self, request, pk=None):
        if not (
            request.user.is_superuser
            or request.user.has_perm('inpatient.discharge_patient')
        ):
            return _error(
                'You do not have permission to discharge patients.',
                status.HTTP_403_FORBIDDEN,
            )
        admission = self.get_object()
        try:
            discharge_patient(
                admission,
                user=request.user,
                status=request.data.get('status', 'discharged'),
                discharge_notes=request.data.get('discharge_notes', ''),
            )
        except InpatientActionError as e:
            return _error(e)
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        """Move the patient to another bed — a ward move is the same call."""
        admission = self.get_object()
        to_bed = get_object_or_404(Bed, id=request.data.get('bed'))
        try:
            transfer_patient(
                admission, to_bed,
                user=request.user,
                notes=request.data.get('notes', ''),
            )
        except InpatientActionError as e:
            return _error(e)
        admission.refresh_from_db()
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=['get'])
    def charges(self, request, pk=None):
        """Billed, paid, outstanding and what it does to the wallet."""
        admission = self.get_object()
        wallet, _ = PatientWallet.objects.get_or_create(patient=admission.patient)
        billed = admission.get_total_cost()
        paid = admission.get_actual_charges_from_wallet()
        data = {
            'billed': billed,
            'paid': paid,
            'outstanding': admission.get_outstanding_admission_cost(),
            'wallet_balance': wallet.balance,
            'wallet_impact': admission.get_total_wallet_impact(),
            'daily_charge': (
                admission.bed.ward.charge_per_day if admission.bed else 0
            ),
            'duration_days': admission.get_duration(),
        }
        return Response(AdmissionChargesSerializer(data).data)


class _AdmissionChildViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Rows that hang off one admission: rounds, notes, records, medications."""

    permission_classes = WRITE_PERMISSIONS
    pagination_class = InpatientPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    author_field = None

    def get_queryset(self):
        queryset = self.queryset.select_related('admission__patient')
        admission = self.request.query_params.get('admission')
        if admission:
            queryset = queryset.filter(admission_id=admission)
        return queryset

    def perform_create(self, serializer):
        serializer.save(**{self.author_field: self.request.user})


class DailyRoundViewSet(_AdmissionChildViewSet):
    queryset = DailyRound.objects.select_related('doctor').all()
    serializer_class = DailyRoundSerializer
    author_field = 'doctor'


class NursingNoteViewSet(_AdmissionChildViewSet):
    queryset = NursingNote.objects.select_related('nurse').all()
    serializer_class = NursingNoteSerializer
    author_field = 'nurse'


class ClinicalRecordViewSet(_AdmissionChildViewSet):
    queryset = ClinicalRecord.objects.select_related('recorded_by').all()
    serializer_class = ClinicalRecordSerializer
    author_field = 'recorded_by'

    def get_queryset(self):
        queryset = super().get_queryset()
        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)
        return queryset


class InpatientMedicationViewSet(_AdmissionChildViewSet):
    queryset = InpatientMedication.objects.select_related(
        'ordered_by', 'prescription'
    ).all()
    serializer_class = InpatientMedicationSerializer
    author_field = 'ordered_by'
