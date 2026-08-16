"""Cart + dispensing endpoints for the mobile client.

Thin JSON skin over `pharmacy.cart_services` — no cart rules live here.
"""
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..cart_models import PrescriptionCart, PrescriptionCartItem
from ..cart_services import (
    CartActionError,
    CartExistsError,
    create_cart_for_prescription,
    dispense_cart,
    generate_cart_invoice,
    pay_cart_from_wallet,
    remove_cart_item,
    set_cart_dispensary,
    set_cart_item_quantity,
    substitute_cart_item,
    undo_substitution,
)
from ..models import (
    ActiveStoreInventory, Dispensary, Medication, Prescription,
)
from .serializers import CartItemSerializer, CartSerializer
from .views import PharmacyPagination


def _error(exc, **extra):
    return Response({'error': str(exc), **extra}, status=status.HTTP_400_BAD_REQUEST)


class CartViewSet(viewsets.ReadOnlyModelViewSet):
    """Carts, plus the actions that move one through the workflow."""

    queryset = PrescriptionCart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            PrescriptionCart.objects
            .select_related('prescription__patient', 'dispensary', 'invoice')
            .prefetch_related('items__prescription_item__medication')
            .order_by('-created_at')
        )
        cart_status = self.request.query_params.get('status')
        prescription = self.request.query_params.get('prescription')
        if cart_status:
            queryset = queryset.filter(status=cart_status)
        if prescription:
            queryset = queryset.filter(prescription_id=prescription)
        return queryset

    def create(self, request):
        """Create a cart from a prescription, optionally for selected items."""
        prescription = get_object_or_404(
            Prescription, id=request.data.get('prescription')
        )
        selected = request.data.get('items') or []
        try:
            cart, notes = create_cart_for_prescription(
                prescription, request.user, selected, request
            )
        except CartExistsError as e:
            # Not an error the user can fix — hand them the cart that exists.
            return Response(
                {'error': str(e), 'cart': CartSerializer(e.cart).data},
                status=status.HTTP_409_CONFLICT,
            )
        except CartActionError as e:
            return _error(e)
        return Response(
            {'cart': CartSerializer(cart).data, 'notes': notes},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def dispensary(self, request, pk=None):
        """Set (or clear, with a null id) the cart's dispensary."""
        cart = self.get_object()
        dispensary_id = request.data.get('dispensary')
        dispensary = (
            get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
            if dispensary_id
            else None
        )
        try:
            set_cart_dispensary(cart, dispensary, request.user)
        except CartActionError as e:
            return _error(e)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=['post'])
    def invoice(self, request, pk=None):
        """Bill the cart. Payment itself still happens at the billing office."""
        cart = self.get_object()
        try:
            generate_cart_invoice(cart, request.user, request)
        except CartActionError as e:
            return _error(e)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=['post'], url_path='pay-from-wallet')
    def pay_from_wallet(self, request, pk=None):
        """Settle the cart's invoice from the patient's wallet.

        Pass `allow_negative: true` to overdraw the wallet deliberately.
        """
        cart = self.get_object()
        try:
            payment, amount = pay_cart_from_wallet(
                cart,
                request.user,
                allow_negative=request.data.get('allow_negative') is True,
                request=request,
            )
        except CartActionError as e:
            return _error(e)
        cart.refresh_from_db()
        return Response({
            'cart': CartSerializer(cart).data,
            'paid': payment is not None,
            'amount': str(amount),
            'notes': [] if payment else ['Nothing to pay on this invoice.'],
        })

    @action(detail=True, methods=['get'])
    def wallet(self, request, pk=None):
        """Patient wallet balance and what this cart still needs."""
        from patients.models import PatientWallet

        cart = self.get_object()
        wallet = PatientWallet.objects.filter(
            patient=cart.prescription.patient
        ).first()
        due = (
            cart.invoice.get_balance() if cart.invoice else cart.get_patient_payable()
        )
        return Response({
            'balance': str(wallet.balance if wallet else '0.00'),
            'due': str(due),
        })

    @action(detail=True, methods=['post'])
    def dispense(self, request, pk=None):
        """Dispense the cart. `quantities` maps cart item id -> quantity."""
        cart = self.get_object()
        quantities = {
            int(k): v for k, v in (request.data.get('quantities') or {}).items()
        }
        try:
            result = dispense_cart(cart, request.user, quantities)
        except CartActionError as e:
            return _error(e)
        return Response({
            'cart': CartSerializer(result['cart']).data,
            'completed': result['completed'],
            'dispensed': result['dispensed'],
            'partial': result['partial'],
            'skipped': result['skipped'],
            'notes': result['notes'],
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        cart = self.get_object()
        if cart.status in ('completed', 'cancelled'):
            return _error(CartActionError(
                f'Cart is already {cart.get_status_display()}.'
            ))
        cart.status = 'cancelled'
        cart.save(update_fields=['status'])
        return Response(CartSerializer(cart).data)


class CartItemViewSet(viewsets.GenericViewSet):
    """Quantity edits and removals for a single cart item."""

    queryset = PrescriptionCartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def partial_update(self, request, pk=None):
        item = self.get_object()
        try:
            quantity = int(request.data.get('quantity'))
        except (TypeError, ValueError):
            return _error(CartActionError('Quantity must be a number'))
        try:
            set_cart_item_quantity(item, quantity)
        except CartActionError as e:
            return _error(e)
        return Response(CartSerializer(item.cart).data)

    def destroy(self, request, pk=None):
        item = self.get_object()
        try:
            cart = remove_cart_item(item)
        except CartActionError as e:
            return _error(e)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=['post'])
    def substitute(self, request, pk=None):
        """Dispense an alternative medication instead of the prescribed one."""
        item = self.get_object()
        medication = get_object_or_404(
            Medication, id=request.data.get('medication'), is_active=True
        )
        try:
            note = substitute_cart_item(
                item, medication, (request.data.get('reason') or '').strip(),
                request.user,
            )
        except CartActionError as e:
            return _error(e)
        return Response({'cart': CartSerializer(item.cart).data, 'notes': [note]})

    @action(detail=True, methods=['post'], url_path='remove-substitution')
    def remove_substitution(self, request, pk=None):
        item = self.get_object()
        try:
            note = undo_substitution(item, request.user)
        except CartActionError as e:
            return _error(e)
        return Response({'cart': CartSerializer(item.cart).data, 'notes': [note]})

    @action(detail=True, methods=['get'])
    def alternatives(self, request, pk=None):
        """Medications in stock at the cart's dispensary, for substitution."""
        from django.db.models import Sum

        item = self.get_object()
        active_store = getattr(item.cart.dispensary, 'active_store', None)
        if active_store is None:
            return Response([])

        rows = (
            ActiveStoreInventory.objects
            .filter(active_store=active_store, stock_quantity__gt=0)
            .exclude(medication=item.prescription_item.medication)
            .values('medication__id', 'medication__name', 'medication__strength',
                    'medication__dosage_form', 'medication__price')
            .annotate(stock=Sum('stock_quantity'))
            .order_by('medication__name')
        )
        return Response([
            {
                'id': row['medication__id'],
                'name': row['medication__name'],
                'strength': row['medication__strength'],
                'dosage_form': row['medication__dosage_form'],
                'price': str(row['medication__price']),
                'stock': row['stock'],
            }
            for row in rows
        ])
