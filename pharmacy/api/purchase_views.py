"""Procurement endpoints for the mobile client.

Thin JSON skin over `pharmacy.purchase_services` — no workflow rules here.
"""
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Purchase, PurchaseItem
from ..purchase_services import (
    PurchaseActionError,
    approve_purchase,
    receive_delivery,
    record_payment,
    reject_purchase,
    submit_for_approval,
)
from .serializers import (
    PurchaseItemSerializer, PurchasePaymentSerializer, PurchaseSerializer,
)
from .views import PharmacyPagination


def _error(exc):
    return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseViewSet(viewsets.ModelViewSet):
    """Purchase orders, from draft through approval, delivery and payment."""

    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            Purchase.objects
            .select_related('supplier', 'dispensary')
            .prefetch_related('items__medication', 'payments__received_by')
            .order_by('-created_at')
        )
        params = self.request.query_params
        for field in ('approval_status', 'payment_status', 'delivery_status'):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get('supplier'):
            queryset = queryset.filter(supplier_id=params['supplier'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(invoice_number__icontains=params['search']) |
                Q(supplier__name__icontains=params['search'])
            )
        return queryset

    def perform_create(self, serializer):
        # total_amount is recomputed from items; a new order starts at zero.
        serializer.save(created_by=self.request.user, total_amount=0)

    def _run(self, service, *args, **kwargs):
        try:
            service(*args, **kwargs)
        except PurchaseActionError as e:
            return _error(e)
        purchase = self.get_object()
        purchase.refresh_from_db()
        return Response(PurchaseSerializer(purchase).data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        return self._run(
            submit_for_approval,
            self.get_object(),
            request.user,
            notes=request.data.get('notes', ''),
            priority_level=request.data.get('priority_level', 'normal'),
            expected_delivery_date=request.data.get('expected_delivery_date'),
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._run(
            approve_purchase, self.get_object(), request.user,
            request.data.get('notes', ''),
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._run(
            reject_purchase, self.get_object(), request.user,
            request.data.get('reason', ''),
        )

    @action(detail=True, methods=['post'], url_path='receive-delivery')
    def receive_delivery(self, request, pk=None):
        """`quantities` maps purchase item id -> quantity received now."""
        return self._run(
            receive_delivery,
            self.get_object(),
            request.data.get('quantities') or {},
        )

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        purchase = self.get_object()
        try:
            payment, purchase = record_payment(
                purchase,
                request.user,
                request.data.get('amount'),
                request.data.get('payment_method'),
                reference=request.data.get('reference', ''),
                notes=request.data.get('notes', ''),
            )
        except PurchaseActionError as e:
            return _error(e)
        return Response({
            'purchase': PurchaseSerializer(purchase).data,
            'payment': PurchasePaymentSerializer(payment).data,
        })


class PurchaseItemViewSet(viewsets.ModelViewSet):
    """Lines on a purchase order. Editable only while it is still a draft."""

    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = PurchaseItem.objects.select_related('medication', 'purchase')
        if self.request.query_params.get('purchase'):
            queryset = queryset.filter(
                purchase_id=self.request.query_params['purchase']
            )
        return queryset

    def _reject_if_locked(self, purchase):
        if purchase.approval_status != 'draft':
            return _error(PurchaseActionError(
                f'Items can only be changed while the purchase is a draft '
                f'(this one is {purchase.get_approval_status_display()}).'
            ))
        return None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blocked = self._reject_if_locked(serializer.validated_data['purchase'])
        return blocked or super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        blocked = self._reject_if_locked(self.get_object().purchase)
        return blocked or super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        blocked = self._reject_if_locked(self.get_object().purchase)
        return blocked or super().destroy(request, *args, **kwargs)
