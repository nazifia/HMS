"""Radiology endpoints for the mobile client.

Structurally the twin of `/laboratory/api/`: a catalogue, orders that move
through statuses, and reports that get signed off. The difference is that a
report carries a study image and a report file, so these endpoints accept
multipart as well as JSON.
"""
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ..models import (
    RadiologyCategory, RadiologyOrder, RadiologyResult, RadiologyTest,
)
from ..services import (
    RadiologyActionError, finalize_result, save_result, update_status,
    verify_result,
)
from .serializers import (
    RadiologyCategorySerializer, RadiologyOrderSerializer,
    RadiologyResultSerializer, RadiologyTestSerializer,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class RadiologyPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


class RadiologyTestViewSet(viewsets.ReadOnlyModelViewSet):
    """The imaging catalogue."""

    queryset = RadiologyTest.objects.all()
    serializer_class = RadiologyTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RadiologyPagination

    def get_queryset(self):
        queryset = RadiologyTest.objects.select_related('category').order_by('name')
        params = self.request.query_params
        if params.get('search'):
            queryset = queryset.filter(
                Q(name__icontains=params['search']) |
                Q(category__name__icontains=params['search'])
            )
        if params.get('category'):
            queryset = queryset.filter(category_id=params['category'])
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset


class RadiologyCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RadiologyCategory.objects.order_by('name')
    serializer_class = RadiologyCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class RadiologyOrderViewSet(viewsets.ModelViewSet):
    """Orders: raise them, move them along, write the report."""

    queryset = RadiologyOrder.objects.all()
    serializer_class = RadiologyOrderSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = RadiologyPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            RadiologyOrder.objects
            .select_related('patient', 'test', 'test__category',
                            'referring_doctor', 'invoice', 'result',
                            'result__performed_by', 'result__verified_by',
                            'authorization_code')
            .order_by('-order_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('priority'):
            queryset = queryset.filter(priority=params['priority'])
        if params.get('unreported') == 'true':
            queryset = queryset.filter(result__isnull=True)
        if params.get('search'):
            queryset = queryset.filter(
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search']) |
                Q(test__name__icontains=params['search'])
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(referring_doctor=self.request.user)

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        order = self.get_object()
        try:
            update_status(order, request.data.get('status'))
        except RadiologyActionError as e:
            return _error(e)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'], url_path='enter-result')
    def enter_result(self, request, pk=None):
        """Write the report. Send multipart to attach the study or a report file."""
        order = self.get_object()
        try:
            result = save_result(
                order,
                request.user,
                fields={k: v for k, v in request.data.items()},
                files={
                    name: request.FILES[name]
                    for name in ('image_file', 'images', 'report_file')
                    if name in request.FILES
                },
            )
        except RadiologyActionError as e:
            return _error(e)

        order.refresh_from_db()
        return Response(
            {
                'result': RadiologyResultSerializer(
                    result, context=self.get_serializer_context()
                ).data,
                'order': self.get_serializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RadiologyResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Reports, plus sign-off and finalising."""

    queryset = RadiologyResult.objects.all()
    serializer_class = RadiologyResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RadiologyPagination

    def get_queryset(self):
        queryset = (
            RadiologyResult.objects
            .select_related('order', 'order__test', 'order__patient',
                            'performed_by', 'verified_by')
            .order_by('-result_date')
        )
        params = self.request.query_params
        if params.get('order'):
            queryset = queryset.filter(order_id=params['order'])
        if params.get('patient'):
            queryset = queryset.filter(order__patient_id=params['patient'])
        if params.get('result_status'):
            queryset = queryset.filter(result_status=params['result_status'])
        if params.get('unverified') == 'true':
            queryset = queryset.filter(result_status__in=['draft', 'submitted'])
        return queryset

    def _may_sign_off(self, user):
        return user.is_superuser or user.has_perm('radiology.change_radiologyresult')

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Sign off a report. Needs the radiology result permission, not just
        whatever allows reading."""
        if not self._may_sign_off(request.user):
            return _error(
                'You do not have permission to verify radiology reports.',
                status.HTTP_403_FORBIDDEN,
            )
        try:
            result = verify_result(
                self.get_object(), request.user,
                notes=request.data.get('notes', ''),
            )
        except RadiologyActionError as e:
            return _error(e)
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        if not self._may_sign_off(request.user):
            return _error(
                'You do not have permission to finalize radiology reports.',
                status.HTTP_403_FORBIDDEN,
            )
        try:
            result = finalize_result(self.get_object(), request.user)
        except RadiologyActionError as e:
            return _error(e)
        return Response(self.get_serializer(result).data)
