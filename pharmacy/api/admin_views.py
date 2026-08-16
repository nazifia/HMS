"""Medical packs, expenses and dispensary administration for the mobile client.

Writes are gated by `DjangoModelPermissions`, which maps POST/PATCH/DELETE onto
the model's add/change/delete permissions. Reading stays open to any
authenticated user the pharmacy access middleware already let through — so
holding `pharmacy.view` no longer implies being able to create records.
"""
from django.db.models import Q, Sum
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    Dispensary, MedicalPack, MedicalPackItem, PackOrder,
    PharmacistDispensaryAssignment, PharmacyExpense,
)
from .serializers import (
    DispensaryWriteSerializer, MedicalPackItemSerializer, MedicalPackSerializer,
    PackOrderSerializer, PharmacistAssignmentSerializer,
    PharmacyExpenseSerializer,
)
from .views import PharmacyPagination

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


def _error(message):
    return Response({'error': str(message)}, status=status.HTTP_400_BAD_REQUEST)


class MedicalPackViewSet(viewsets.ModelViewSet):
    """Predefined packs for surgery, labour and emergency use."""

    queryset = MedicalPack.objects.all()
    serializer_class = MedicalPackSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            MedicalPack.objects
            .prefetch_related('items__medication')
            .order_by('name')
        )
        params = self.request.query_params
        if params.get('pack_type'):
            queryset = queryset.filter(pack_type=params['pack_type'])
        if params.get('search'):
            queryset = queryset.filter(name__icontains=params['search'])
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Whether every item in the pack is currently in stock."""
        can_order, message = self.get_object().can_be_ordered()
        return Response({'can_order': can_order, 'message': message})


class MedicalPackItemViewSet(viewsets.ModelViewSet):
    queryset = MedicalPackItem.objects.all()
    serializer_class = MedicalPackItemSerializer
    permission_classes = WRITE_PERMISSIONS

    def get_queryset(self):
        queryset = MedicalPackItem.objects.select_related('medication', 'pack')
        if self.request.query_params.get('pack'):
            queryset = queryset.filter(pack_id=self.request.query_params['pack'])
        return queryset.order_by('order', 'id')


class PackOrderViewSet(viewsets.ModelViewSet):
    """Orders for a pack, with the model's own workflow guards."""

    queryset = PackOrder.objects.all()
    serializer_class = PackOrderSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = PharmacyPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            PackOrder.objects
            .select_related('pack', 'patient', 'ordered_by')
            .order_by('-ordered_at')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        return queryset

    def perform_create(self, serializer):
        serializer.save(ordered_by=self.request.user)

    def _run(self, method_name, user):
        order = self.get_object()
        try:
            getattr(order, method_name)(user)
        except ValueError as e:
            return _error(e)
        order.refresh_from_db()
        return Response(PackOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        return self._run('process_order', request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._run('approve_order', request.user)

    @action(detail=True, methods=['post'])
    def dispense(self, request, pk=None):
        return self._run('dispense_order', request.user)


class PharmacyExpenseViewSet(viewsets.ModelViewSet):
    """Pharmacy running costs beyond medication purchases."""

    queryset = PharmacyExpense.objects.all()
    serializer_class = PharmacyExpenseSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            PharmacyExpense.objects
            .select_related('supplier', 'created_by')
            .order_by('-expense_date', '-created_at')
        )
        params = self.request.query_params
        if params.get('expense_type'):
            queryset = queryset.filter(expense_type=params['expense_type'])
        if params.get('payment_status'):
            queryset = queryset.filter(payment_status=params['payment_status'])
        if params.get('date_from'):
            queryset = queryset.filter(expense_date__gte=params['date_from'])
        if params.get('date_to'):
            queryset = queryset.filter(expense_date__lte=params['date_to'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(description__icontains=params['search']) |
                Q(reference_number__icontains=params['search'])
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Totals for the current filter, split by payment status."""
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.aggregate(total=Sum('amount'))['total'] or 0
        pending = queryset.filter(payment_status='pending').aggregate(
            total=Sum('amount')
        )['total'] or 0
        return Response({
            'entries': queryset.count(),
            'total': str(total),
            'pending': str(pending),
        })


class DispensaryAdminViewSet(viewsets.ModelViewSet):
    """Create and edit dispensaries. Read-only listing lives at
    `/pharmacy/api/dispensaries/`; this one accepts writes."""

    queryset = Dispensary.objects.all()
    serializer_class = DispensaryWriteSerializer
    permission_classes = WRITE_PERMISSIONS
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = Dispensary.objects.select_related('manager').order_by('name')
        if self.request.query_params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=['get'])
    def pharmacists(self, request, pk=None):
        assignments = (
            self.get_object().pharmacist_assignments
            .select_related('pharmacist')
            .filter(is_active=True)
        )
        return Response(PharmacistAssignmentSerializer(assignments, many=True).data)


class PharmacistAssignmentViewSet(viewsets.ModelViewSet):
    """Which pharmacist works at which dispensary."""

    queryset = PharmacistDispensaryAssignment.objects.all()
    serializer_class = PharmacistAssignmentSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            PharmacistDispensaryAssignment.objects
            .select_related('pharmacist', 'dispensary')
            .order_by('-start_date')
        )
        params = self.request.query_params
        if params.get('dispensary'):
            queryset = queryset.filter(dispensary_id=params['dispensary'])
        if params.get('active') != 'all':
            queryset = queryset.filter(is_active=True)
        return queryset
