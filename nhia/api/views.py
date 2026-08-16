"""NHIA / desk-office endpoints for the mobile client.

Three modules already refuse work when an authorization code is missing
(consultations, laboratory, appointments) and until now the only way to issue
one was the desk-office web page. The rules live in `nhia.services`, shared
with those pages.
"""
from datetime import datetime, timezone as dt_timezone

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from patients.models import Patient

from ..authorization_utils import validate_authorization_code
from ..models import AuthorizationCode, NHIAPatient
from ..services import (
    AUTHORIZABLE, AuthorizationError, authorize, cancel_code,
    expire_stale_codes, issue_code, model_for, pending_counts,
    pending_queryset,
)
from .serializers import (
    AuthorizationCodeSerializer, NHIAPatientSerializer, PendingItemSerializer,
    pending_row,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

OLDEST = datetime.min.replace(tzinfo=dt_timezone.utc)


class NhiaPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


class AuthorizationCodeViewSet(viewsets.ModelViewSet):
    """Issue, list, look up and cancel authorization codes."""

    queryset = AuthorizationCode.objects.all()
    serializer_class = AuthorizationCodeSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = NhiaPagination
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        # Verifying a code is what the wards do before starting work; it is a
        # read, not "may this user add a code".
        if self.action == 'verify':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        # Cheap, and it keeps an expired code from looking active in the app.
        expire_stale_codes()
        queryset = (
            AuthorizationCode.objects
            .select_related('patient', 'patient__nhia_info', 'generated_by')
            .order_by('-generated_at')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('service_type'):
            queryset = queryset.filter(service_type=params['service_type'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(code__icontains=params['search']) |
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search'])
            )
        return queryset

    def create(self, request, *args, **kwargs):
        """Issue a code for a patient, standalone (not tied to a request)."""
        patient = get_object_or_404(Patient, id=request.data.get('patient'))
        try:
            auth_code = issue_code(
                patient,
                amount=request.data.get('amount'),
                service_type=request.data.get('service_type', 'general'),
                expiry_days=request.data.get('expiry_days', 30),
                user=request.user,
                notes=request.data.get('notes', ''),
                code=request.data.get('code'),
            )
        except AuthorizationError as e:
            return _error(e)
        return Response(
            AuthorizationCodeSerializer(auth_code).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            auth_code = cancel_code(self.get_object())
        except AuthorizationError as e:
            return _error(e)
        return Response(AuthorizationCodeSerializer(auth_code).data)

    @action(detail=False, methods=['get'])
    def verify(self, request):
        """Look a code up by its printed value and say whether it may be used."""
        code = (request.query_params.get('code') or '').strip()
        if not code:
            return _error('Enter a code to verify.')

        expire_stale_codes()
        auth_code = AuthorizationCode.objects.filter(code__iexact=code).first()
        if auth_code is None:
            return Response(
                {'valid': False, 'message': 'No such authorization code.',
                 'code': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        valid, message = validate_authorization_code(
            auth_code, request.query_params.get('service_type')
        )
        return Response({
            'valid': valid,
            'message': message,
            'code': AuthorizationCodeSerializer(auth_code).data,
        })


class NHIAPatientViewSet(viewsets.ReadOnlyModelViewSet):
    """NHIA registrations, for looking a patient up by scheme number."""

    queryset = NHIAPatient.objects.all()
    serializer_class = NHIAPatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = NhiaPagination

    def get_queryset(self):
        queryset = (
            NHIAPatient.objects
            .select_related('patient')
            .order_by('patient__first_name', 'patient__last_name')
        )
        params = self.request.query_params
        if params.get('search'):
            queryset = queryset.filter(
                Q(nhia_reg_number__icontains=params['search']) |
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search'])
            )
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset


class PendingAuthorizationView(APIView):
    """The desk-office queue: everything across the hospital waiting on a code.

    `?kind=` narrows it to one module; without it the six are merged and sorted
    newest first, which is how the desk office works through them.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        kinds = [request.query_params['kind']] if request.query_params.get('kind') \
            else list(AUTHORIZABLE)
        patient = request.query_params.get('patient')

        rows = []
        for kind in kinds:
            try:
                queryset = pending_queryset(kind)
            except AuthorizationError as e:
                return _error(e)
            if patient:
                queryset = queryset.filter(patient_id=patient)
            rows.extend(pending_row(kind, item) for item in queryset[:100])

        # Undated rows sort last rather than blowing up the comparison.
        rows.sort(key=lambda row: row['requested_on'] or OLDEST, reverse=True)
        return Response({
            'counts': pending_counts(),
            'results': PendingItemSerializer(rows, many=True).data,
        })


class AuthorizeItemView(APIView):
    """Issue a code for one waiting item and attach it, in a single call."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, kind, item_id):
        if not (
            request.user.is_superuser
            or request.user.has_perm('nhia.add_authorizationcode')
        ):
            return _error(
                'You do not have permission to issue authorization codes.',
                status.HTTP_403_FORBIDDEN,
            )
        try:
            model = model_for(kind)
        except AuthorizationError as e:
            return _error(e)

        item = get_object_or_404(model, pk=item_id)
        try:
            auth_code = authorize(
                kind, item, request.user,
                amount=request.data.get('amount'),
                expiry_days=request.data.get('expiry_days', 30),
                notes=request.data.get('notes', ''),
                code=request.data.get('code'),
            )
        except AuthorizationError as e:
            return _error(e)

        return Response(
            AuthorizationCodeSerializer(auth_code).data,
            status=status.HTTP_201_CREATED,
        )
