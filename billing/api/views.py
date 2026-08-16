"""Billing endpoints for the mobile client.

Payments go through `BillingOfficePaymentProcessor`, the same processor the
billing office pages use — it owns balance checks, the wallet debit and the
invoice status update.
"""
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.billing_office_integration import BillingOfficePaymentProcessor

from ..models import Invoice, InvoiceItem, Payment, Service, ServiceCategory
from .serializers import (
    InvoiceItemSerializer, InvoiceSerializer, PaymentSerializer,
    ServiceCategorySerializer, ServiceSerializer,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class BillingPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': str(message)}, status=code)


class InvoiceViewSet(viewsets.ModelViewSet):
    """Invoices, and taking payment against them."""

    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = BillingPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        # Taking payment is its own right, checked in the action itself.
        if self.action in ('pay', 'summary'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Invoice.objects
            .select_related('patient', 'patient__wallet', 'created_by')
            .prefetch_related('items__service', 'payments__received_by')
            .order_by('-invoice_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('source_app'):
            queryset = queryset.filter(source_app=params['source_app'])
        if params.get('unpaid') == 'true':
            queryset = queryset.filter(status__in=['pending', 'partially_paid'])
        if params.get('search'):
            queryset = queryset.filter(
                Q(invoice_number__icontains=params['search']) |
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search'])
            )
        return queryset

    def perform_create(self, serializer):
        # A new invoice starts empty and pending; adding items recomputes the
        # totals through Invoice.save().
        serializer.save(
            created_by=self.request.user,
            status='pending',
            subtotal=Decimal('0.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('0.00'),
            source_app=serializer.validated_data.get('source_app') or 'billing',
        )

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Record a payment: billing office, patient wallet, insurance…"""
        if not (
            request.user.is_superuser
            or request.user.has_perm('billing.process_payment')
        ):
            return _error(
                'You do not have permission to record payments.',
                status.HTTP_403_FORBIDDEN,
            )

        invoice = self.get_object()
        try:
            amount = Decimal(str(request.data.get('amount'))).quantize(
                Decimal('0.01')
            )
        except (InvalidOperation, TypeError):
            return _error('Invalid amount.')

        success, message, payment = BillingOfficePaymentProcessor.process_payment(
            request=request,
            invoice=invoice,
            amount=amount,
            payment_source=request.data.get('payment_source', 'billing_office'),
            payment_method=request.data.get('payment_method', 'cash'),
            transaction_id=request.data.get('transaction_id', ''),
            notes=request.data.get('notes', ''),
            module_name='Mobile',
        )
        if not success:
            return _error(message)

        invoice.refresh_from_db()
        return Response({
            'invoice': InvoiceSerializer(invoice).data,
            'payment': PaymentSerializer(payment).data,
            'message': message,
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """What is owed, and what was collected today — the cashier's header."""
        queryset = self.filter_queryset(self.get_queryset())
        outstanding = queryset.filter(
            status__in=['pending', 'partially_paid']
        ).aggregate(
            total=Sum('total_amount'), paid=Sum('amount_paid'),
        )
        collected_today = Payment.objects.filter(
            payment_date__date=timezone.now().date()
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        owed = (outstanding['total'] or Decimal('0.00')) - (
            outstanding['paid'] or Decimal('0.00')
        )
        return Response({
            'invoices': queryset.count(),
            'outstanding': str(owed),
            'collected_today': str(collected_today),
        })


class InvoiceItemViewSet(viewsets.ModelViewSet):
    """Lines on an invoice. Locked once the invoice has been paid."""

    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = WRITE_PERMISSIONS

    def get_queryset(self):
        queryset = InvoiceItem.objects.select_related('service', 'invoice')
        if self.request.query_params.get('invoice'):
            queryset = queryset.filter(
                invoice_id=self.request.query_params['invoice']
            )
        return queryset

    def _reject_if_paid(self, invoice):
        if invoice.amount_paid and invoice.amount_paid > 0:
            return _error(
                'Items cannot be changed once the invoice has been paid against.'
            )
        return None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.validated_data['invoice']
        blocked = self._reject_if_paid(invoice)
        if blocked:
            return blocked
        response = super().create(request, *args, **kwargs)
        invoice.recalculate_from_items()
        return response

    def update(self, request, *args, **kwargs):
        invoice = self.get_object().invoice
        blocked = self._reject_if_paid(invoice)
        if blocked:
            return blocked
        response = super().update(request, *args, **kwargs)
        invoice.recalculate_from_items()
        return response

    def destroy(self, request, *args, **kwargs):
        invoice = self.get_object().invoice
        blocked = self._reject_if_paid(invoice)
        if blocked:
            return blocked
        response = super().destroy(request, *args, **kwargs)
        invoice.recalculate_from_items()
        return response


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment history — recording one goes through the invoice's pay action."""

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = BillingPagination

    def get_queryset(self):
        queryset = (
            Payment.objects
            .select_related('invoice__patient', 'received_by')
            .order_by('-payment_date')
        )
        params = self.request.query_params
        if params.get('invoice'):
            queryset = queryset.filter(invoice_id=params['invoice'])
        if params.get('patient'):
            queryset = queryset.filter(invoice__patient_id=params['patient'])
        if params.get('mine') == 'true':
            queryset = queryset.filter(received_by=self.request.user)
        if params.get('date_from'):
            queryset = queryset.filter(payment_date__date__gte=params['date_from'])
        if params.get('date_to'):
            queryset = queryset.filter(payment_date__date__lte=params['date_to'])
        return queryset


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """The service catalogue invoice lines are built from."""

    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = BillingPagination

    def get_queryset(self):
        queryset = Service.objects.select_related('category').order_by('name')
        params = self.request.query_params
        if params.get('search'):
            queryset = queryset.filter(name__icontains=params['search'])
        if params.get('category'):
            queryset = queryset.filter(category_id=params['category'])
        return queryset


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCategory.objects.order_by('name')
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
