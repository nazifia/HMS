"""Patient records, vitals, history and wallet for the mobile client.

Writes are gated by `DjangoModelPermissions` (add_*/change_* on the model);
wallet funding is gated separately because it moves money and is not the same
right as editing a patient record.
"""
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..models import MedicalHistory, Patient, PatientWallet, Vitals
from ..outstanding import patient_outstanding
from .serializers import (
    MedicalHistorySerializer, PatientSerializer, VitalsSerializer,
    WalletSerializer, WalletTransactionSerializer,
)
from saas.api import TenantScopedQuerysetMixin

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class PatientPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message):
    return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)


class PatientViewSet(viewsets.ModelViewSet):
    """Patient register: search, view, register, update."""

    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = PatientPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # DjangoModelPermissions maps any POST on this viewset to add_patient,
        # which is the wrong question for the wallet actions — they carry their
        # own checks below.
        if self.action in ('wallet', 'transactions', 'fund'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Patient.objects
            .select_related('wallet', 'primary_doctor')
            .order_by('-registration_date')
        )
        params = self.request.query_params
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(patient_id__icontains=search) |
                Q(phone_number__icontains=search)
            )
        if params.get('patient_type'):
            queryset = queryset.filter(patient_type=params['patient_type'])
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=['get'])
    def wallet(self, request, pk=None):
        """Balance plus what the patient still owes."""
        patient = self.get_object()
        wallet, _ = PatientWallet.objects.get_or_create(patient=patient)
        outstanding = patient_outstanding(patient)
        return Response({
            'wallet': WalletSerializer(wallet).data,
            'outstanding': {
                'admissions': str(outstanding['admissions']),
                'invoices': str(outstanding['invoices']),
                'total': str(outstanding['total']),
            },
        })

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        wallet, _ = PatientWallet.objects.get_or_create(patient=self.get_object())
        queryset = wallet.transactions.select_related('created_by').order_by(
            '-created_at'
        )
        page = self.paginate_queryset(queryset)
        serializer = WalletTransactionSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def fund(self, request, pk=None):
        """Credit the patient's wallet.

        Moving money is a different right from editing a patient record, so
        this asks for the wallet-transaction permission explicitly rather than
        riding on whatever let the caller PATCH the patient.
        """
        if not (
            request.user.is_superuser
            or request.user.has_perm('patients.add_wallettransaction')
        ):
            return Response(
                {'error': 'You do not have permission to fund wallets.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            amount = Decimal(str(request.data.get('amount'))).quantize(
                Decimal('0.01')
            )
        except (InvalidOperation, TypeError):
            return _error('Invalid amount.')
        if amount <= 0:
            return _error('Amount must be greater than zero.')

        patient = self.get_object()
        wallet, _ = PatientWallet.objects.get_or_create(patient=patient)
        description = request.data.get('description') or 'Funds added to wallet'
        payment_method = request.data.get('payment_method')
        if payment_method:
            description = f"{description} (Payment method: {payment_method})"

        # wallet.credit() owns the money path: it locks the row, writes the
        # transaction record and optionally settles outstanding charges.
        transaction = wallet.credit(
            amount=amount,
            description=description,
            transaction_type='deposit',
            user=request.user,
            apply_to_outstanding=request.data.get('apply_to_outstanding') is True,
        )
        wallet.refresh_from_db()
        return Response({
            'wallet': WalletSerializer(wallet).data,
            'transaction': WalletTransactionSerializer(transaction).data,
            'outstanding': str(patient_outstanding(patient)['total']),
        })


class PatientChildViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Records that hang off a patient and are always read per patient."""

    permission_classes = WRITE_PERMISSIONS
    pagination_class = PatientPagination

    def get_queryset(self):
        queryset = super().get_queryset().select_related('patient')
        patient = self.request.query_params.get('patient')
        if patient:
            queryset = queryset.filter(patient_id=patient)
        return queryset


class VitalsViewSet(PatientChildViewSet):
    queryset = Vitals.objects.all()
    serializer_class = VitalsSerializer

    def perform_create(self, serializer):
        # recorded_by is a free-text name on this model; default it to whoever
        # is signed in rather than making the app supply it.
        serializer.save(
            recorded_by=serializer.validated_data.get('recorded_by')
            or self.request.user.get_full_name()
            or self.request.user.username
        )


class MedicalHistoryViewSet(PatientChildViewSet):
    queryset = MedicalHistory.objects.all()
    serializer_class = MedicalHistorySerializer

    def perform_create(self, serializer):
        serializer.save(
            doctor_name=serializer.validated_data.get('doctor_name')
            or self.request.user.get_full_name()
            or self.request.user.username
        )
