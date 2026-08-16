"""Consultation, waiting list and referral endpoints for the mobile client.

Routing and authorization rules come from `consultations.services`, shared with
the web views.
"""
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.clinical_notes import clerking_schema

from ..models import (
    Consultation, ConsultationNote, ConsultingRoom, Referral, SOAPNote,
    WaitingList,
)
from ..services import (
    ConsultationActionError, call_in_patient, complete_waiting_entry,
    update_consultation_status, update_referral_status, waiting_queue,
)
from .serializers import (
    ConsultationNoteSerializer, ConsultationSerializer,
    ConsultingRoomSerializer, ReferralSerializer, SOAPNoteSerializer,
    WaitingListSerializer,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class ConsultationPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


class ConsultationViewSet(viewsets.ModelViewSet):
    """The doctor's consultations."""

    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = ConsultationPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # These actions carry their own authorisation (see services); DRF's
        # model permissions would answer the wrong question here — a doctor
        # moving their own consultation is not "may add a consultation".
        if self.action in ('set_status', 'notes'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Consultation.objects
            .select_related('patient', 'doctor', 'consulting_room')
            .prefetch_related('notes__created_by')
            .order_by('-consultation_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('mine') == 'true':
            queryset = queryset.filter(doctor=self.request.user)
        if params.get('search'):
            queryset = queryset.filter(
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search']) |
                Q(diagnosis__icontains=params['search'])
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user, status='in_progress')

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        consultation = self.get_object()
        try:
            update_consultation_status(
                consultation, request.user, request.data.get('status')
            )
        except ConsultationActionError as e:
            return _error(e, status.HTTP_403_FORBIDDEN if 'permission' in str(e)
                          else status.HTTP_400_BAD_REQUEST)
        return Response(ConsultationSerializer(consultation).data)

    @action(detail=True, methods=['post'])
    def notes(self, request, pk=None):
        """Append a timestamped note to the consultation."""
        consultation = self.get_object()
        text = (request.data.get('note') or '').strip()
        if not text:
            return _error('The note is empty.')
        note = ConsultationNote.objects.create(
            consultation=consultation, note=text, created_by=request.user
        )
        return Response(
            ConsultationNoteSerializer(note).data, status=status.HTTP_201_CREATED
        )


class WaitingListViewSet(viewsets.ModelViewSet):
    """The clinic queue: check in, call in, complete."""

    queryset = WaitingList.objects.all()
    serializer_class = WaitingListSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = ConsultationPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # These actions carry their own authorisation (see services); DRF's
        # model permissions would answer the wrong question here — a doctor
        # moving their own consultation is not "may add a consultation".
        if self.action in ('call_in', 'complete'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        params = self.request.query_params
        if params.get('all') == 'true':
            queryset = WaitingList.objects.select_related(
                'patient', 'consulting_room', 'doctor'
            )
        else:
            queryset = waiting_queue(
                consulting_room=params.get('room') or None,
                doctor=self.request.user if params.get('mine') == 'true' else None,
                today_only=params.get('today', 'true') == 'true',
            )
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        # Urgent first, then whoever has been waiting longest.
        return queryset.order_by('priority', 'check_in_time')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='call-in')
    def call_in(self, request, pk=None):
        """Start a consultation for the next patient."""
        entry = self.get_object()
        try:
            consultation = call_in_patient(entry, request.user)
        except ConsultationActionError as e:
            return _error(e)
        return Response({
            'waiting_entry': WaitingListSerializer(entry).data,
            'consultation': ConsultationSerializer(consultation).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        entry = self.get_object()
        try:
            complete_waiting_entry(entry)
        except ConsultationActionError as e:
            return _error(e)
        return Response(WaitingListSerializer(entry).data)


class ReferralViewSet(viewsets.ModelViewSet):
    """Referrals in and out, with the routing rules enforced on accept."""

    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = ConsultationPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # These actions carry their own authorisation (see services); DRF's
        # model permissions would answer the wrong question here — a doctor
        # moving their own consultation is not "may add a consultation".
        if self.action in ('set_status',):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Referral.objects
            .select_related('patient', 'referring_doctor', 'assigned_doctor',
                            'referred_to_department')
            .order_by('-referral_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('outgoing') == 'true':
            queryset = queryset.filter(referring_doctor=self.request.user)
        if params.get('incoming') == 'true':
            # Addressed to this user directly, to their department, or already
            # assigned to them.
            department = getattr(
                getattr(self.request.user, 'profile', None), 'department', None
            )
            incoming = Q(referred_to_doctor=self.request.user) | Q(
                assigned_doctor=self.request.user
            )
            if department:
                incoming |= Q(referred_to_department=department)
            queryset = queryset.filter(incoming)
        return queryset

    def perform_create(self, serializer):
        serializer.save(referring_doctor=self.request.user, status='pending')

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        referral = self.get_object()
        try:
            update_referral_status(
                referral,
                request.user,
                request.data.get('status'),
                request.data.get('notes', ''),
            )
        except ConsultationActionError as e:
            return _error(e, status.HTTP_403_FORBIDDEN if 'permission' in str(e)
                          else status.HTTP_400_BAD_REQUEST)
        return Response(
            ReferralSerializer(referral, context={'request': request}).data
        )


class SOAPNoteViewSet(viewsets.ModelViewSet):
    """Clerking notes against a consultation."""

    queryset = SOAPNote.objects.all()
    serializer_class = SOAPNoteSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = ConsultationPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            SOAPNote.objects
            .select_related('consultation__patient', 'created_by')
            .order_by('-created_at')
        )
        params = self.request.query_params
        if params.get('consultation'):
            queryset = queryset.filter(consultation_id=params['consultation'])
        if params.get('patient'):
            queryset = queryset.filter(
                consultation__patient_id=params['patient']
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def schema(self, request):
        """The proforma's sections, so the app renders the same 13 fields in
        the same order without keeping its own copy of the labels."""
        return Response(clerking_schema())


class ConsultingRoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConsultingRoom.objects.filter(is_active=True)
    serializer_class = ConsultingRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ConsultingRoom.objects.select_related('department').filter(
            is_active=True
        ).order_by('room_number')
        if self.request.query_params.get('department'):
            queryset = queryset.filter(
                department_id=self.request.query_params['department']
            )
        return queryset
