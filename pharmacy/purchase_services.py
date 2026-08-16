"""Purchase workflow shared by the HTML views and the mobile REST API.

Procurement is a money path (approval, goods receipt into bulk stock, supplier
payments), so it gets one implementation. Each function locks the purchase row
and re-checks the model's own guard before mutating.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import Purchase, PurchaseApproval, PurchasePayment


class PurchaseActionError(Exception):
    """A purchase action the user is not allowed to take right now."""


def _can_approve_purchases(user):
    return user.is_superuser or user.has_perm("pharmacy.can_approve_purchases")


def _can_process_payments(user):
    return user.is_superuser or user.has_perm("pharmacy.can_process_payments")


def submit_for_approval(
    purchase, user, notes="", priority_level="normal", expected_delivery_date=None
):
    """Move a draft purchase into the approval queue."""
    if purchase.approval_status != "draft":
        raise PurchaseActionError(
            "This purchase has already been submitted or processed."
        )
    if not purchase.items.exists():
        raise PurchaseActionError("Cannot submit purchase without items.")
    if purchase.total_amount <= 0:
        raise PurchaseActionError("Cannot submit purchase with zero total amount.")

    purchase.approval_status = "pending"
    purchase.approval_updated_at = timezone.now()
    purchase.submitted_for_approval_at = timezone.now()
    purchase.approval_notes = notes
    purchase.priority_level = priority_level
    if expected_delivery_date:
        purchase.expected_delivery_date = expected_delivery_date
    purchase.save()
    return purchase


def approve_purchase(purchase, user, notes=""):
    """Approve a pending purchase. Stock arrives later, at delivery."""
    if not _can_approve_purchases(user):
        raise PurchaseActionError("You do not have permission to approve purchases.")

    with transaction.atomic():
        # Lock the row and re-check status so two concurrent approvers cannot
        # both approve the same purchase.
        purchase = Purchase.objects.select_for_update().get(id=purchase.id)
        if not purchase.can_be_approved():
            raise PurchaseActionError(
                "This purchase cannot be approved in its current status."
            )

        purchase.approval_status = "approved"
        purchase.current_approver = user
        purchase.approval_notes = notes
        purchase.approval_updated_at = timezone.now()
        purchase.save()

        PurchaseApproval.objects.create(
            purchase=purchase,
            approver=user,
            status="approved",
            comments=notes,
            decided_at=timezone.now(),
            step_order=1,
        )
    return purchase


def reject_purchase(purchase, user, reason):
    if not _can_approve_purchases(user):
        raise PurchaseActionError("You do not have permission to reject purchases.")
    if purchase.approval_status not in ["pending", "draft"]:
        raise PurchaseActionError(
            "This purchase cannot be rejected in its current status."
        )
    if not reason:
        raise PurchaseActionError("Please provide a reason for rejection.")

    with transaction.atomic():
        purchase.approval_status = "rejected"
        purchase.current_approver = user
        purchase.approval_notes = reason
        purchase.approval_updated_at = timezone.now()
        purchase.save()

        PurchaseApproval.objects.create(
            purchase=purchase,
            approver=user,
            status="rejected",
            comments=reason,
            decided_at=timezone.now(),
            step_order=1,
        )
    return purchase


def receive_delivery(purchase, quantities):
    """Book received goods into the bulk store.

    `quantities` maps PurchaseItem id -> quantity received in this delivery.
    """
    if not purchase.can_receive_delivery():
        raise PurchaseActionError(
            "Deliveries can only be received for approved purchases that are "
            "not yet fully received."
        )

    cleaned = {}
    for item_id, raw in quantities.items():
        if raw is None or raw == "":
            continue
        try:
            cleaned[int(item_id)] = int(raw)
        except (TypeError, ValueError):
            raise PurchaseActionError(f"Invalid quantity '{raw}'.")

    if not any(qty > 0 for qty in cleaned.values()):
        raise PurchaseActionError("Enter a received quantity for at least one item.")

    with transaction.atomic():
        # Lock the row so concurrent receipts can't double-add stock.
        purchase = Purchase.objects.select_for_update().get(id=purchase.id)
        if not purchase.can_receive_delivery():
            raise PurchaseActionError(
                "This purchase can no longer receive deliveries."
            )
        try:
            purchase.receive_items(cleaned)
        except ValueError as e:
            raise PurchaseActionError(str(e))
    return purchase


def record_payment(
    purchase, user, amount, payment_method, reference="", notes=""
):
    """Record a supplier payment against the purchase."""
    if not _can_process_payments(user):
        raise PurchaseActionError("You do not have permission to process payments.")
    if purchase.approval_status != "approved":
        raise PurchaseActionError("Only approved purchases can be paid.")
    if purchase.payment_status == "paid":
        raise PurchaseActionError("This purchase has already been paid.")
    if purchase.delivery_status == "pending":
        raise PurchaseActionError(
            "Payment is only allowed after goods have been received. "
            "Record a delivery for this purchase first."
        )

    try:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise PurchaseActionError("Invalid payment amount.")
    if amount <= 0:
        raise PurchaseActionError("Payment amount must be greater than zero.")

    with transaction.atomic():
        # Lock the row so concurrent payments can't both pass the
        # outstanding-balance check and overpay.
        purchase = Purchase.objects.select_for_update().get(id=purchase.id)
        if purchase.payment_status == "paid":
            raise PurchaseActionError("This purchase has already been paid.")

        outstanding = purchase.get_outstanding_amount()
        if amount > outstanding:
            raise PurchaseActionError(
                f"Payment amount exceeds outstanding balance (₦{outstanding})."
            )

        payment = PurchasePayment.objects.create(
            purchase=purchase,
            amount=amount,
            payment_method=payment_method,
            transaction_id=reference,
            notes=notes,
            received_by=user,
            payment_date=timezone.now(),
        )

        if amount >= outstanding:
            purchase.payment_status = "paid"
            purchase.payment_date = timezone.now()
        else:
            purchase.payment_status = "partial"
        purchase.save(update_fields=["payment_status", "payment_date"])

    return payment, purchase
