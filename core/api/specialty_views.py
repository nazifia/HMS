"""The specialty record endpoints, one set of views for eighteen modules.

`/api/specialty/modules/` lists them; `/api/specialty/<kind>/schema/` says what
fields a module has; `/api/specialty/<kind>/records/` reads and writes them.
The app renders any module from the schema, so adding a nineteenth specialty
means adding one line to `SPECIALTY_MODULES`.
"""
from accounts.permissions import is_tenant_admin
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.clinical_notes import CLERKING_FIELDS, clerking_schema
from core.specialty_api import (
    HIDDEN_FIELDS, UnknownSpecialty, model_for, module_summary,
    note_model_for, record_schema,
)


class IsClinicalStaff(permissions.BasePermission):
    """Specialty records are clinical notes about a patient.

    The HTML pages are restricted to clinical cadres by
    `StrictAccessControlMiddleware.SPECIALTY_CLINICAL_NAMESPACES`; that rule
    keys off the URL namespace, which these endpoints do not share, so the
    same rule is applied here rather than left off.
    """

    message = 'Specialty records are restricted to clinical staff.'

    def has_permission(self, request, view):
        from accounts.permissions import get_user_roles
        from accounts.strict_access_control import StrictAccessControlMiddleware

        if not request.user.is_authenticated:
            return False
        if is_tenant_admin(request.user):
            return True
        roles = {role.lower() for role in get_user_roles(request.user)}
        return bool(roles & StrictAccessControlMiddleware.CLINICAL_ALLOWED_ROLES)


class SpecialtyPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


def record_serializer_for(model):
    """A serializer built from the model, so no module needs one written."""
    doctor_field = 'dentist' if hasattr(model, 'dentist') else 'doctor'

    class _RecordSerializer(serializers.ModelSerializer):
        patient_name = serializers.CharField(
            source='patient.get_full_name', read_only=True
        )
        patient_number = serializers.CharField(
            source='patient.patient_id', read_only=True
        )
        doctor_name = serializers.SerializerMethodField()

        class Meta:
            exclude = tuple(
                name for name in HIDDEN_FIELDS
                if name not in ('id',) and _has_field(model, name)
            )

        def get_doctor_name(self, record):
            doctor = getattr(record, doctor_field, None)
            return str(doctor) if doctor else ''

    _RecordSerializer.Meta.model = model
    return _RecordSerializer


def _has_field(model, name):
    return any(field.name == name for field in model._meta.fields)


@api_view(['GET'])
@permission_classes([IsClinicalStaff])
def modules(request):
    """Every specialty module the app can open."""
    return Response(module_summary())


@api_view(['GET'])
@permission_classes([IsClinicalStaff])
def schema(request, kind):
    """This module's fields, plus the clerking proforma if it takes notes."""
    try:
        note_model, _ = note_model_for(kind)
        return Response({
            'kind': kind,
            'fields': record_schema(kind),
            'clinical_note_fields': clerking_schema() if note_model else [],
        })
    except UnknownSpecialty as e:
        return _error(e, status.HTTP_404_NOT_FOUND)


class SpecialtyRecordList(APIView):
    """List and create records for one specialty module."""

    permission_classes = [IsClinicalStaff]

    def get(self, request, kind):
        try:
            model = model_for(kind)
        except UnknownSpecialty as e:
            return _error(e, status.HTTP_404_NOT_FOUND)

        queryset = model.objects.select_related('patient').order_by('-id')
        patient = request.query_params.get('patient')
        if patient:
            queryset = queryset.filter(patient_id=patient)
        search = request.query_params.get('search')
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__patient_id__icontains=search)
            )

        paginator = SpecialtyPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = record_serializer_for(model)(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, kind):
        try:
            model = model_for(kind)
        except UnknownSpecialty as e:
            return _error(e, status.HTTP_404_NOT_FOUND)

        # Writing a clinical record is a clinical act, not a read.
        if not (
            request.user.is_superuser
            or request.user.has_perm(
                f'{model._meta.app_label}.add_{model._meta.model_name}'
            )
        ):
            return _error(
                f'You do not have permission to add {kind} records.',
                status.HTTP_403_FORBIDDEN,
            )

        serializer = record_serializer_for(model)(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SpecialtyRecordDetail(APIView):
    """One record, and its clinical notes."""

    permission_classes = [IsClinicalStaff]

    def get_record(self, kind, pk):
        return get_object_or_404(model_for(kind), pk=pk)

    def get(self, request, kind, pk):
        try:
            record = self.get_record(kind, pk)
        except UnknownSpecialty as e:
            return _error(e, status.HTTP_404_NOT_FOUND)
        serializer = record_serializer_for(type(record))(record)
        return Response(serializer.data)

    def patch(self, request, kind, pk):
        try:
            record = self.get_record(kind, pk)
        except UnknownSpecialty as e:
            return _error(e, status.HTTP_404_NOT_FOUND)
        serializer = record_serializer_for(type(record))(
            record, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SpecialtyClinicalNotes(APIView):
    """The clerking proforma against one specialty record."""

    permission_classes = [IsClinicalStaff]

    def get(self, request, kind, pk):
        try:
            note_model, record_field = note_model_for(kind)
        except UnknownSpecialty as e:
            return _error(e, status.HTTP_404_NOT_FOUND)
        if note_model is None:
            return _error(f'{kind} records do not take clinical notes.')

        notes = note_model.objects.filter(**{record_field: pk}).order_by('-id')
        return Response([_note_payload(note) for note in notes])

    def post(self, request, kind, pk):
        try:
            note_model, record_field = note_model_for(kind)
            record = get_object_or_404(model_for(kind), pk=pk)
        except UnknownSpecialty as e:
            return _error(e, status.HTTP_404_NOT_FOUND)
        if note_model is None:
            return _error(f'{kind} records do not take clinical notes.')

        # Blank means "not recorded": only write what was sent.
        values = {
            name: request.data[name]
            for name in CLERKING_FIELDS
            if str(request.data.get(name, '')).strip()
        }
        if not values:
            return _error('Write at least one section of the clerking note.')

        note = note_model.objects.create(
            created_by=request.user, **{record_field: record}, **values,
        )
        return Response(_note_payload(note), status=status.HTTP_201_CREATED)


def _note_payload(note):
    return {
        'id': note.id,
        'created_by_name': (
            note.created_by.get_full_name() if note.created_by else ''
        ),
        'created_at': note.created_at,
        **{name: getattr(note, name, '') for name in CLERKING_FIELDS},
    }
