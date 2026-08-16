"""Theatre endpoints for the mobile client.

A thin JSON skin over `theatre.services` — double-booking, the NHIA rule and
the surgery invoice are shared with the surgery form and its view, not restated
here. Medical packs stay where they are: `PackOrder` already links to a
surgery, so this exposes the link rather than a second pack workflow.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date, parse_datetime, parse_duration
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from patients.models import Patient

from ..models import (
    OperationTheatre, Surgery, SurgeryType, SurgicalEquipment,
)
from ..services import (
    TheatreActionError, add_post_op_note, assign_team_member,
    record_equipment_usage, save_checklist, schedule_surgery, theatre_conflicts,
    theatre_day, update_status,
)
from .serializers import (
    EquipmentUsageSerializer, OperationTheatreSerializer,
    PostOperativeNoteSerializer, PreOperativeChecklistSerializer,
    SurgerySerializer, SurgeryTypeSerializer, SurgicalEquipmentSerializer,
    SurgicalTeamSerializer,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class TheatrePagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


class OperationTheatreViewSet(viewsets.ReadOnlyModelViewSet):
    """The theatres themselves, and what each is doing today."""

    queryset = OperationTheatre.objects.all()
    serializer_class = OperationTheatreSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TheatrePagination

    def get_queryset(self):
        queryset = OperationTheatre.objects.order_by('theatre_number')
        if self.request.query_params.get('available') == 'true':
            queryset = queryset.filter(is_available=True)
        return queryset

    @action(detail=False, methods=['get'])
    def today(self, request):
        """The day's list, per theatre — what the board on the wall shows."""
        date = parse_date(request.query_params.get('date', '')) or None
        theatre = None
        if request.query_params.get('theatre'):
            theatre = get_object_or_404(
                OperationTheatre, id=request.query_params['theatre']
            )
        surgeries = theatre_day(theatre=theatre, date=date)
        return Response({
            'count': surgeries.count(),
            'results': SurgerySerializer(surgeries, many=True).data,
        })


class SurgeryTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SurgeryType.objects.all()
    serializer_class = SurgeryTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TheatrePagination

    def get_queryset(self):
        queryset = SurgeryType.objects.order_by('name')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class SurgicalEquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SurgicalEquipment.objects.all()
    serializer_class = SurgicalEquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TheatrePagination

    def get_queryset(self):
        queryset = SurgicalEquipment.objects.order_by('name')
        params = self.request.query_params
        if params.get('search'):
            queryset = queryset.filter(name__icontains=params['search'])
        if params.get('equipment_type'):
            queryset = queryset.filter(equipment_type=params['equipment_type'])
        if params.get('available') == 'true':
            queryset = queryset.filter(is_available=True)
        return queryset


class SurgeryViewSet(viewsets.ModelViewSet):
    """Surgeries and everything the theatre does to one."""

    queryset = Surgery.objects.all()
    serializer_class = SurgerySerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = TheatrePagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # Workflow actions are not "may this user add a surgery".
        if self.action in (
            'set_status', 'team', 'checklist', 'post_op_note', 'equipment',
        ):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Surgery.objects
            .select_related('patient', 'surgery_type', 'theatre',
                            'primary_surgeon', 'anesthetist',
                            'authorization_code', 'pre_op_checklist')
            .prefetch_related('team_members__staff', 'equipment_used__equipment',
                              'pack_orders__pack')
            .order_by('-scheduled_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('theatre'):
            queryset = queryset.filter(theatre_id=params['theatre'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('surgeon'):
            queryset = queryset.filter(primary_surgeon_id=params['surgeon'])
        if params.get('date'):
            queryset = queryset.filter(scheduled_date__date=params['date'])
        if params.get('upcoming') == 'true':
            queryset = queryset.filter(status__in=['scheduled', 'pending'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search']) |
                Q(surgery_type__name__icontains=params['search'])
            )
        return queryset

    def create(self, request, *args, **kwargs):
        """Book a theatre slot: refuses a clash, then raises the invoice."""
        data = request.data
        patient = get_object_or_404(Patient, id=data.get('patient'))
        surgery_type = get_object_or_404(SurgeryType, id=data.get('surgery_type'))
        theatre = get_object_or_404(OperationTheatre, id=data.get('theatre'))

        scheduled_date = parse_datetime(str(data.get('scheduled_date', '')))
        if scheduled_date is None:
            return _error('A valid scheduled_date is required.')

        duration = data.get('expected_duration')
        expected_duration = (
            parse_duration(str(duration)) if duration else surgery_type.average_duration
        )
        if expected_duration is None:
            return _error('expected_duration must look like "HH:MM:SS".')

        user_model = get_user_model()
        surgeon = (
            get_object_or_404(user_model, id=data['primary_surgeon'])
            if data.get('primary_surgeon') else request.user
        )
        anesthetist = (
            get_object_or_404(user_model, id=data['anesthetist'])
            if data.get('anesthetist') else None
        )

        code = None
        if data.get('authorization_code'):
            from nhia.models import AuthorizationCode

            code = get_object_or_404(
                AuthorizationCode, id=data['authorization_code']
            )

        try:
            surgery, invoice = schedule_surgery(
                patient=patient,
                surgery_type=surgery_type,
                theatre=theatre,
                scheduled_date=scheduled_date,
                expected_duration=expected_duration,
                user=request.user,
                primary_surgeon=surgeon,
                anesthetist=anesthetist,
                pre_surgery_notes=data.get('pre_surgery_notes', ''),
                authorization_code=code,
            )
        except TheatreActionError as e:
            return _error(e)

        payload = self.get_serializer(surgery).data
        payload['invoice'] = invoice.id
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='check-slot')
    def check_slot(self, request):
        """Is this theatre free? Asked before the booking form is submitted."""
        theatre = get_object_or_404(
            OperationTheatre, id=request.query_params.get('theatre')
        )
        # An unencoded "+" in a timezone offset arrives as a space.
        raw = str(request.query_params.get('scheduled_date', '')).replace(' ', '+')
        scheduled_date = parse_datetime(raw)
        if scheduled_date is None:
            return _error('A valid scheduled_date is required.')
        duration = parse_duration(
            str(request.query_params.get('expected_duration', ''))
        ) or timedelta(hours=1)

        clashes = theatre_conflicts(theatre, scheduled_date, duration)
        return Response({'free': not clashes, 'conflicts': clashes})

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        surgery = self.get_object()
        try:
            update_status(surgery, request.data.get('status'))
        except TheatreActionError as e:
            return _error(e)
        return Response(self.get_serializer(surgery).data)

    @action(detail=True, methods=['post'])
    def team(self, request, pk=None):
        """Put someone on the team."""
        surgery = self.get_object()
        staff = get_object_or_404(get_user_model(), id=request.data.get('staff'))
        try:
            member = assign_team_member(
                surgery, staff, request.data.get('role'),
                usage_notes=request.data.get('usage_notes', ''),
            )
        except TheatreActionError as e:
            return _error(e)
        return Response(
            SurgicalTeamSerializer(member).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get', 'post'])
    def checklist(self, request, pk=None):
        """The pre-op checklist: a real checklist, not a text field."""
        surgery = self.get_object()
        if request.method == 'GET':
            checklist = getattr(surgery, 'pre_op_checklist', None)
            if checklist is None:
                return Response({'detail': 'No checklist yet.'},
                                status=status.HTTP_404_NOT_FOUND)
            return Response(PreOperativeChecklistSerializer(checklist).data)

        try:
            checklist = save_checklist(surgery, request.user, request.data)
        except TheatreActionError as e:
            return _error(e)
        return Response(PreOperativeChecklistSerializer(checklist).data)

    @action(detail=True, methods=['post'], url_path='post-op-note')
    def post_op_note(self, request, pk=None):
        surgery = self.get_object()
        try:
            note = add_post_op_note(
                surgery, request.user,
                notes=request.data.get('notes', ''),
                complications=request.data.get('complications', ''),
                follow_up_instructions=request.data.get(
                    'follow_up_instructions', ''
                ),
            )
        except TheatreActionError as e:
            return _error(e)
        return Response(
            PostOperativeNoteSerializer(note).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], url_path='post-op-notes')
    def post_op_notes(self, request, pk=None):
        surgery = self.get_object()
        notes = surgery.post_op_notes.select_related('created_by')
        return Response(PostOperativeNoteSerializer(notes, many=True).data)

    @action(detail=True, methods=['post'])
    def equipment(self, request, pk=None):
        """Note equipment against the surgery."""
        surgery = self.get_object()
        equipment = get_object_or_404(
            SurgicalEquipment, id=request.data.get('equipment')
        )
        try:
            usage = record_equipment_usage(
                surgery, equipment,
                quantity_used=int(request.data.get('quantity_used', 1)),
                notes=request.data.get('notes', ''),
            )
        except (TheatreActionError, ValueError) as e:
            return _error(e)
        return Response(
            EquipmentUsageSerializer(usage).data, status=status.HTTP_201_CREATED
        )
