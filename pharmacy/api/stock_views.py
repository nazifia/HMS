"""Inventory, stock transfers and dispensing history for the mobile client.

Transfer rules already live on the models (`can_approve`, `approve_transfer`,
`execute_transfer`), so these viewsets only translate them to JSON.
"""
from datetime import timedelta

from django.db.models import F, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    ActiveStoreInventory, DispensingLog, InterDispensaryTransfer,
    MedicationTransfer,
)
from .serializers import (
    ActiveStoreInventorySerializer, DispensingLogSerializer,
    InterDispensaryTransferSerializer, MedicationTransferSerializer,
)
from .views import PharmacyPagination


def _error(message):
    return Response({'error': str(message)}, status=status.HTTP_400_BAD_REQUEST)


class ActiveStoreInventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """What is on the shelf, per dispensary."""

    queryset = ActiveStoreInventory.objects.all()
    serializer_class = ActiveStoreInventorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            ActiveStoreInventory.objects
            .select_related('medication__category', 'active_store__dispensary')
            .order_by('medication__name')
        )
        params = self.request.query_params
        dispensary = params.get('dispensary')
        search = params.get('search')

        if dispensary:
            queryset = queryset.filter(active_store__dispensary_id=dispensary)
        if search:
            queryset = queryset.filter(
                Q(medication__name__icontains=search) |
                Q(medication__generic_name__icontains=search) |
                Q(medication__manufacturer__icontains=search)
            )
        if params.get('low_stock') == 'true':
            # reorder_level is a column, so this filters in SQL rather than
            # walking every row through is_low_stock().
            queryset = queryset.filter(stock_quantity__lte=F('reorder_level'))
        if params.get('expiring') == 'true':
            queryset = queryset.filter(
                expiry_date__lte=timezone.now().date() + timedelta(days=90)
            )
        return queryset


class TransferActionsMixin:
    """approve / reject / execute, driven by the model's own guards."""

    def _run(self, method_name, *args):
        transfer = self.get_object()
        try:
            getattr(transfer, method_name)(*args)
        except ValueError as e:
            return _error(e)
        transfer.refresh_from_db()
        return Response(self.get_serializer(transfer).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._run('approve_transfer', request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        return self._run('execute_transfer', request.user)


class InterDispensaryTransferViewSet(
    TransferActionsMixin, viewsets.ModelViewSet
):
    """Stock moved between dispensaries."""

    queryset = InterDispensaryTransfer.objects.all()
    serializer_class = InterDispensaryTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = (
            InterDispensaryTransfer.objects
            .select_related('medication', 'from_dispensary', 'to_dispensary',
                            'requested_by')
            .order_by('-created_at')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('dispensary'):
            queryset = queryset.filter(
                Q(from_dispensary_id=params['dispensary']) |
                Q(to_dispensary_id=params['dispensary'])
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Tell the requester straight away whether the source has the stock.
        transfer = InterDispensaryTransfer.objects.get(id=response.data['id'])
        available, message = transfer.check_availability()
        response.data['available'] = available
        response.data['availability_message'] = message
        return response

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._run(
            'reject_transfer', request.user, request.data.get('reason')
        )


class MedicationTransferViewSet(TransferActionsMixin, viewsets.ModelViewSet):
    """Stock moved from the bulk store into a dispensary's active store."""

    queryset = MedicationTransfer.objects.all()
    serializer_class = MedicationTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = (
            MedicationTransfer.objects
            .select_related('medication', 'from_bulk_store',
                            'to_active_store__dispensary', 'requested_by')
            .order_by('-created_at')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('dispensary'):
            queryset = queryset.filter(
                to_active_store__dispensary_id=params['dispensary']
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class DispensingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Who dispensed what, when."""

    queryset = DispensingLog.objects.all()
    serializer_class = DispensingLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            DispensingLog.objects
            .select_related('prescription_item__medication',
                            'prescription_item__prescription__patient',
                            'dispensed_by', 'dispensary')
            .order_by('-dispensed_date')
        )
        params = self.request.query_params
        if params.get('dispensary'):
            queryset = queryset.filter(dispensary_id=params['dispensary'])
        if params.get('mine') == 'true':
            queryset = queryset.filter(dispensed_by=self.request.user)
        if params.get('date_from'):
            queryset = queryset.filter(dispensed_date__date__gte=params['date_from'])
        if params.get('date_to'):
            queryset = queryset.filter(dispensed_date__date__lte=params['date_to'])
        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Totals for the current filter — what the top of the screen shows."""
        totals = self.filter_queryset(self.get_queryset()).aggregate(
            quantity=Sum('dispensed_quantity'),
            value=Sum('total_price_for_this_log'),
        )
        return Response({
            'entries': self.filter_queryset(self.get_queryset()).count(),
            'quantity': totals['quantity'] or 0,
            'value': str(totals['value'] or '0.00'),
        })
