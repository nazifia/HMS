"""Cart actions shared by the HTML views and the mobile REST API.

The cart is a money path (invoice totals, stock deduction, dispensing logs), so
it gets exactly one implementation. `cart_views` renders it with messages and
redirects; `api/cart_views` returns JSON. Neither owns the rules.
"""
from accounts.permissions import is_tenant_admin
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.audit_utils import log_audit_action

from .billing_utils import create_pharmacy_invoice
from .cart_models import PrescriptionCart, PrescriptionCartItem
from .models import ActiveStoreInventory, DispensingLog

logger = logging.getLogger(__name__)


class CartActionError(Exception):
    """A cart action the user is not allowed to take right now."""


class CartExistsError(CartActionError):
    """A usable cart already exists; send the caller there instead."""

    def __init__(self, cart, message):
        super().__init__(message)
        self.cart = cart


def cart_invoice_editable(cart):
    """True when the cart's linked invoice (if any) has no payment yet."""
    inv = cart.invoice
    return not inv or not inv.amount_paid or inv.amount_paid == 0


def sync_cart_invoice(cart):
    """
    Re-sync the cart's unpaid invoice to the current patient-payable total after
    the cart items change (manual qty edit, item removal, recost). If nothing is
    left to bill, void the invoice and reopen the cart. No-op if there is no
    invoice or it already has a payment.
    """
    inv = cart.invoice
    if not inv or (inv.amount_paid and inv.amount_paid > 0):
        return
    new_payable = cart.get_patient_payable()
    if new_payable <= 0:
        inv.status = "cancelled"
        inv.save()
        cart.invoice = None
        cart.status = "active"
        cart.save(update_fields=["invoice", "status"])
    else:
        inv.subtotal = new_payable
        inv.save()  # save() recomputes total_amount + status


def set_cart_item_quantity(item, quantity):
    """Change a cart item's quantity and keep the unpaid invoice in step."""
    cart = item.cart

    if cart.status not in ("active", "invoiced") or not cart_invoice_editable(cart):
        raise CartActionError(
            "Quantities can only be edited before the invoice is paid."
        )

    if quantity <= 0:
        raise CartActionError("Quantity must be greater than zero")

    item.update_available_stock()  # Refresh stock info
    if quantity > item.available_stock:
        raise CartActionError(
            f"Quantity exceeds available stock. Only {item.available_stock} "
            f"available in selected dispensary."
        )

    with transaction.atomic():
        item.quantity = quantity
        item.save()
        sync_cart_invoice(cart)

    cart.refresh_from_db()
    return item


def remove_cart_item(item):
    """Drop an item from the cart and re-sync the unpaid invoice."""
    cart = item.cart
    if cart.status not in ("active", "invoiced") or not cart_invoice_editable(cart):
        raise CartActionError("Items can only be removed before the invoice is paid.")
    item.delete()
    sync_cart_invoice(cart)
    return cart


def set_cart_dispensary(cart, dispensary, user):
    """Point the cart at a dispensary and refresh every item's stock figure."""
    if dispensary is not None and not is_tenant_admin(user):
        if hasattr(user, "can_access_dispensary") and not user.can_access_dispensary(
            dispensary
        ):
            raise CartActionError(
                f"You don't have permission to access '{dispensary.name}'. "
                f"Please select a dispensary you are assigned to."
            )

    cart.dispensary = dispensary
    cart.save()

    for item in cart.items.all():
        item.update_available_stock()
        item.save()
    return cart


def create_cart_for_prescription(
    prescription, user, selected_item_ids=None, request=None
):
    """Create a cart for the prescription's undispensed items.

    Returns (cart, notes). `notes` are informational lines for the caller to
    surface. Raises CartActionError when no cart should be created, and
    CartExistsError when the caller should be sent to an existing cart instead.
    """
    notes = []

    if prescription.status in ["cancelled", "completed"]:
        raise CartActionError(
            f"Cannot create cart for prescription with status: "
            f"{prescription.get_status_display()}"
        )

    if not any(
        item.remaining_quantity_to_dispense > 0 for item in prescription.items.all()
    ):
        raise CartActionError(
            "No items remaining to dispense. All items have been fully dispensed."
        )

    existing = PrescriptionCart.objects.filter(
        prescription=prescription, status__in=["active", "invoiced", "paid"]
    ).first()
    if existing:
        raise CartExistsError(
            existing,
            f"A {existing.status} cart already exists for this prescription.",
        )

    # A partially dispensed cart does not block a new cart, but only for items
    # it does not already hold.
    partial = PrescriptionCart.objects.filter(
        prescription=prescription, status="partially_dispensed"
    ).first()

    # Items already claimed by any live cart must not be added twice.
    claimed = set()
    for cart in PrescriptionCart.objects.filter(
        prescription=prescription,
        status__in=["active", "invoiced", "paid", "partially_dispensed"],
    ):
        claimed.update(cart.items.values_list("prescription_item_id", flat=True))

    candidates = prescription.items.all()
    if selected_item_ids:
        candidates = candidates.filter(id__in=selected_item_ids)
    to_add = [
        p_item
        for p_item in candidates
        if p_item.id not in claimed and p_item.remaining_quantity_to_dispense > 0
    ]

    if not to_add:
        if partial:
            raise CartExistsError(
                partial,
                "A partially dispensed cart already holds the remaining items.",
            )
        raise CartActionError(
            "No items to add to cart. All items have been fully dispensed."
        )

    with transaction.atomic():
        cart = PrescriptionCart.objects.create(
            prescription=prescription, created_by=user
        )
        for p_item in to_add:
            PrescriptionCartItem.objects.create(
                cart=cart,
                prescription_item=p_item,
                quantity=p_item.remaining_quantity_to_dispense,
                unit_price=p_item.medication.price or Decimal("0.00"),
            )

        log_audit_action(
            user,
            "create",
            cart,
            f"Created prescription cart with {len(to_add)} items",
        )

    # Auto-generate the pharmacy invoice; a failure here leaves a usable cart.
    try:
        can_checkout, message = cart.can_generate_invoice()
        if can_checkout:
            invoice = create_pharmacy_invoice(
                request, cart.prescription, cart.get_patient_payable(), force_new=False
            )
            if invoice:
                cart.invoice = invoice
                cart.status = "invoiced"
                cart.save()
                log_audit_action(
                    user, "update", cart, f"Generated pharmacy invoice #{invoice.id} from cart"
                )
                notes.append(
                    f"Invoice #{invoice.id} created. "
                    f"Total: ₦{cart.get_patient_payable():.2f}"
                )
            else:
                notes.append("Cart created but failed to generate invoice.")
        else:
            notes.append(f"Cart created. {message}")
    except Exception as e:  # noqa: BLE001 - cart must survive a billing failure
        logger.error("Error auto-generating invoice: %s", e)
        notes.append(f"Cart created but failed to auto-generate invoice: {e}")

    return cart, notes


def generate_cart_invoice(cart, user, request=None):
    """Bill the cart: create the pharmacy invoice and mark the cart invoiced."""
    can_checkout, message = cart.can_generate_invoice()
    if not can_checkout:
        raise CartActionError(message)

    auth_ok, auth_message = cart.prescription.check_nhia_authorization()
    if not auth_ok:
        raise CartActionError(auth_message)

    with transaction.atomic():
        invoice = create_pharmacy_invoice(
            request, cart.prescription, cart.get_patient_payable()
        )
        if not invoice:
            raise CartActionError("Failed to create invoice")

        cart.invoice = invoice
        cart.status = "invoiced"
        cart.save()

        log_audit_action(
            user,
            "create",
            cart,
            f"Generated invoice from cart with {cart.items.count()} items",
        )
    return invoice


def pay_cart_from_wallet(cart, user, allow_negative=False, request=None):
    """Settle the cart's invoice from the patient's wallet.

    Bills the cart first if it is ready but not yet invoiced. Returns
    (payment, amount); payment is None when there was nothing left to pay.
    """
    from billing.models import Payment as PharmacyPayment
    from core.models import InternalNotification
    from patients.models import PatientWallet

    if not is_tenant_admin(user) and cart.dispensary:
        if hasattr(user, "can_access_dispensary") and not user.can_access_dispensary(
            cart.dispensary
        ):
            raise CartActionError(
                f"You don't have permission to process payment for "
                f"'{cart.dispensary.name}'."
            )

    with transaction.atomic():
        invoice = cart.invoice
        if invoice is None:
            invoice = generate_cart_invoice(cart, user, request)

        if invoice.status == "paid":
            if cart.status in ["active", "invoiced"]:
                cart.status = "paid"
                cart.save(update_fields=["status"])
            return None, Decimal("0.00")

        amount = invoice.get_balance()
        if amount <= 0:
            return None, Decimal("0.00")

        patient = cart.prescription.patient
        wallet, _ = PatientWallet.objects.get_or_create(
            patient=patient, defaults={"balance": Decimal("0.00")}
        )
        if wallet.balance < amount and not allow_negative:
            raise CartActionError(
                f"Insufficient wallet balance. Available: ₦{wallet.balance:.2f}, "
                f"required: ₦{amount:.2f}. Top up the wallet or allow an overdraft."
            )

        # Record payment. billing signals handle the rest: a wallet-method
        # payment debits the patient wallet once, and invoice.amount_paid +
        # status are recomputed from the sum of payments. Doing those here too
        # would double-debit the wallet.
        payment = PharmacyPayment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method="wallet",
            received_by=user,
            notes=(
                f"Payment for prescription #{cart.prescription.id} "
                f"(Cart #{cart.id})"
            ),
        )
        invoice.refresh_from_db()

        cart.status = "paid"
        cart.save(update_fields=["status"])

        prescription = cart.prescription
        if hasattr(prescription, "payment_status"):
            prescription.payment_status = "paid"
            prescription.save(update_fields=["payment_status"])

        log_audit_action(
            user,
            "create",
            payment,
            f"Wallet payment of ₦{amount:.2f} for cart #{cart.id} "
            f"(prescription #{prescription.id})",
        )

        if prescription.doctor:
            InternalNotification.objects.create(
                user=prescription.doctor,
                message=(
                    f"Wallet payment of ₦{amount:.2f} recorded for "
                    f"prescription #{prescription.id}"
                ),
            )

    return payment, amount


def substitute_cart_item(item, medication, reason, user):
    """Swap an item's medication for an alternative. Returns a note."""
    if not is_tenant_admin(user) and item.cart.dispensary:
        if hasattr(user, "can_access_dispensary") and not user.can_access_dispensary(
            item.cart.dispensary
        ):
            raise CartActionError(
                f"You don't have permission to substitute items for "
                f"'{item.cart.dispensary.name}'."
            )

    can_sub, message = item.can_substitute()
    if not can_sub:
        raise CartActionError(message)

    if not reason:
        raise CartActionError("Please provide a reason for substitution")

    original = item.prescription_item.medication
    try:
        with transaction.atomic():
            item.substitute_with(medication, reason, user)
            log_audit_action(
                user,
                "update",
                item,
                f"Substituted {original.name} with {medication.name}. "
                f"Reason: {reason}",
            )
    except ValidationError as e:
        raise CartActionError(str(e))

    item.update_available_stock()
    if item.available_stock >= item.quantity:
        return (
            f"{medication.name} has sufficient stock "
            f"({item.available_stock} units available)"
        )
    return (
        f"Only {item.available_stock} units of {medication.name} available "
        f"(need {item.quantity})"
    )


def undo_substitution(item, user):
    """Revert an item to its prescribed medication. Returns a note."""
    if not item.is_substituted():
        raise CartActionError("This item is not substituted")

    original = item.prescription_item.medication
    substitute = item.substitute_medication
    with transaction.atomic():
        item.remove_substitution()
        log_audit_action(
            user,
            "update",
            item,
            f"Removed substitution of {substitute.name}, reverted to {original.name}",
        )
    return f"Reverted to original medication: {original.name}"


def dispense_cart(cart, user, quantities=None):
    """Dispense a paid cart, in full or in part.

    `quantities` maps cart item id -> quantity to dispense now; items left out
    dispense whatever stock allows. Returns a summary dict.
    """
    quantities = quantities or {}

    if not is_tenant_admin(user) and cart.dispensary:
        if hasattr(user, "can_access_dispensary") and not user.can_access_dispensary(
            cart.dispensary
        ):
            raise CartActionError(
                f"You don't have permission to dispense from "
                f"'{cart.dispensary.name}'."
            )

    can_complete, message = cart.can_complete_dispensing()
    if not can_complete:
        raise CartActionError(message)

    auth_ok, auth_message = cart.prescription.check_nhia_authorization()
    if not auth_ok:
        raise CartActionError(auth_message)

    notes = []
    dispensed_count = 0
    partial_count = 0
    skipped_count = 0

    with transaction.atomic():
        # Lock the cart row so a double-submit (or two pharmacists on the same
        # cart) serialize: the second txn blocks here, then re-reads the updated
        # quantity_dispensed below and skips already-dispensed items.
        cart = PrescriptionCart.objects.select_for_update().get(id=cart.id)

        for cart_item in cart.items.all():
            p_item = cart_item.prescription_item
            medication = cart_item.get_effective_medication()
            remaining_qty = cart_item.get_remaining_quantity()
            if remaining_qty <= 0:
                continue

            available_to_dispense = cart_item.get_available_to_dispense_now()

            if cart_item.id in quantities:
                try:
                    quantity_to_dispense = int(quantities[cart_item.id])
                except (ValueError, TypeError):
                    raise CartActionError(f"Invalid quantity for {medication.name}.")
                if quantity_to_dispense <= 0:
                    continue
                if quantity_to_dispense > available_to_dispense:
                    raise CartActionError(
                        f"Cannot dispense {quantity_to_dispense} of "
                        f"{medication.name}. Only {available_to_dispense} available."
                    )
            else:
                if available_to_dispense <= 0:
                    notes.append(
                        f"No stock available for {medication.name}. "
                        f"Will dispense when stock arrives."
                    )
                    skipped_count += 1
                    continue
                quantity_to_dispense = available_to_dispense

            unit_price = cart_item.unit_price
            DispensingLog.objects.create(
                prescription_item=p_item,
                dispensed_by=user,
                dispensed_quantity=quantity_to_dispense,
                unit_price_at_dispense=unit_price,
                total_price_for_this_log=Decimal(str(quantity_to_dispense)) * unit_price,
                dispensary=cart.dispensary,
            )

            _deduct_stock(cart.dispensary, medication, quantity_to_dispense)

            p_item.quantity_dispensed_so_far += quantity_to_dispense
            if p_item.quantity_dispensed_so_far >= p_item.quantity:
                p_item.is_dispensed = True
                p_item.dispensed_at = timezone.now()
            p_item.save()

            cart_item.quantity_dispensed += quantity_to_dispense
            cart_item.save()

            if quantity_to_dispense < remaining_qty:
                partial_count += 1
                notes.append(
                    f"Partially dispensed {medication.name}: "
                    f"{quantity_to_dispense} of {remaining_qty} remaining"
                )
            else:
                dispensed_count += 1

        prescription = cart.prescription
        total_items = prescription.items.count()
        fully_dispensed = prescription.items.filter(is_dispensed=True).count()
        if fully_dispensed == total_items:
            prescription.status = "dispensed"
        elif fully_dispensed > 0:
            prescription.status = "partially_dispensed"
        prescription.save()

        if cart.is_fully_dispensed():
            cart.status = "completed"
            cart.save()
            log_audit_action(
                user, "update", cart, "Completed full dispensing of all items from cart"
            )
        else:
            cart.status = "partially_dispensed"
            cart.save()
            log_audit_action(
                user,
                "update",
                cart,
                f"Partial dispensing: {dispensed_count} fully dispensed, "
                f"{partial_count} partially dispensed, {skipped_count} skipped",
            )

    return {
        "cart": cart,
        "completed": cart.status == "completed",
        "dispensed": dispensed_count,
        "partial": partial_count,
        "skipped": skipped_count,
        "progress": cart.get_dispensing_progress(),
        "notes": notes,
    }


def _deduct_stock(dispensary, medication, quantity):
    """Take `quantity` off the dispensary's active store, oldest batch first."""
    active_store = getattr(dispensary, "active_store", None)
    if active_store is None:
        return

    try:
        # select_for_update locks the rows for the txn so a concurrent dispense
        # of the same stock can't oversell (lost update).
        remaining = quantity
        for inv_item in (
            ActiveStoreInventory.objects.select_for_update()
            .filter(
                medication=medication,
                active_store=active_store,
                stock_quantity__gt=0,
            )
            .order_by("id")  # FIFO - oldest batch first
        ):
            if remaining <= 0:
                break
            take = min(inv_item.stock_quantity, remaining)
            inv_item.stock_quantity -= take
            inv_item.save()
            remaining -= take
    except Exception as e:  # noqa: BLE001 - matches the previous view behaviour
        logger.warning("Error updating active store inventory: %s", e)
