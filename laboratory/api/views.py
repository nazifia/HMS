"""Laboratory endpoints for the mobile client.

Thin JSON skin over `laboratory.services` — the workflow rules are shared with
the HTML views, not restated here.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..models import Test, TestCategory, TestRequest, TestResult
from ..services import (
    LabActionError, create_result, update_status, verify_result,
)
from .serializers import (
    TestCategorySerializer, TestRequestSerializer, TestResultSerializer,
    TestSerializer,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class LabPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(exc):
    return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TestViewSet(viewsets.ReadOnlyModelViewSet):
    """The test catalogue, with each test's parameters."""

    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LabPagination

    def get_queryset(self):
        queryset = (
            Test.objects
            .select_related('category')
            .prefetch_related('parameters')
            .order_by('name')
        )
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


class TestCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TestCategory.objects.order_by('name')
    serializer_class = TestCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class TestRequestViewSet(viewsets.ModelViewSet):
    """Test requests: raise them, move them along, read their results."""

    queryset = TestRequest.objects.all()
    serializer_class = TestRequestSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = LabPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            TestRequest.objects
            .select_related('patient', 'doctor', 'invoice')
            .prefetch_related('tests__parameters', 'results__parameters__parameter')
            .order_by('-request_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('priority'):
            queryset = queryset.filter(priority=params['priority'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search'])
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        test_request = self.get_object()
        try:
            update_status(test_request, request.data.get('status'))
        except LabActionError as e:
            return _error(e)
        return Response(TestRequestSerializer(test_request).data)

    @action(detail=True, methods=['post'], url_path='enter-result')
    def enter_result(self, request, pk=None):
        """Record one test's result.

        `parameters` maps TestParameter id -> {value, is_normal, notes}.
        """
        test_request = self.get_object()
        test = get_object_or_404(Test, id=request.data.get('test'))
        try:
            result = create_result(
                test_request,
                test,
                request.user,
                notes=request.data.get('notes', ''),
                parameters=request.data.get('parameters') or {},
            )
        except LabActionError as e:
            return _error(e)
        test_request.refresh_from_db()
        return Response(
            {
                'result': TestResultSerializer(result).data,
                'test_request': TestRequestSerializer(test_request).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TestResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Results, plus sign-off."""

    queryset = TestResult.objects.all()
    serializer_class = TestResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LabPagination

    def get_queryset(self):
        queryset = (
            TestResult.objects
            .select_related('test', 'test_request__patient', 'performed_by',
                            'verified_by')
            .prefetch_related('parameters__parameter')
            .order_by('-result_date')
        )
        params = self.request.query_params
        if params.get('test_request'):
            queryset = queryset.filter(test_request_id=params['test_request'])
        if params.get('patient'):
            queryset = queryset.filter(test_request__patient_id=params['patient'])
        if params.get('unverified') == 'true':
            queryset = queryset.filter(verified_by__isnull=True)
        return queryset

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Sign off a result. Needs the lab's own result permission, not just
        whatever allows reading."""
        if not (
            request.user.is_superuser
            or request.user.has_perm('laboratory.enter_testresults')
        ):
            return Response(
                {'error': 'You do not have permission to verify results.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            result = verify_result(self.get_object(), request.user)
        except LabActionError as e:
            return _error(e)
        return Response(TestResultSerializer(result).data)
