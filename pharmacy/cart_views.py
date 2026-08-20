"""
Prescription Cart Views for HMS Pharmacy Module

Handles cart operations: create, view, update, checkout, and complete dispensing.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.permissions import permission_required
from django.db import transaction
from django.db.models import Sum, Count
from django.http import JsonResponse
from decimal import Decimal
from django.utils import timezone
import json

from .cart_models import PrescriptionCart, PrescriptionCartItem
from .models import Prescription, PrescriptionItem, Dispensary, DispensingLog
from .models import ActiveStoreInventory
from billing.models import Invoice as PharmacyInvoice
from pharmacy.billing_utils import create_pharmacy_invoice
from core.audit_utils import log_audit_action

# Cart rules live in cart_services so the HTML views and the mobile API share
# one implementation of the money path.
from .cart_services import (
    CartActionError,
    CartExistsError,
    cart_invoice_editable as _cart_invoice_editable,
    create_cart_for_prescription,
    dispense_cart,
    generate_cart_invoice,
    pay_cart_from_wallet as pay_cart_from_wallet_service,
    set_cart_dispensary,
    set_cart_item_quantity,
    substitute_cart_item as substitute_cart_item_service,
    sync_cart_invoice,
    undo_substitution,
)


@login_required
@permission_required("pharmacy.create")
def create_cart_from_prescription(request, prescription_id):
    """
    Create a new cart from prescription.
    Adds selected prescription items to cart with prescribed quantities.
    """
    prescription = get_object_or_404(Prescription, id=prescription_id)

    selected_item_ids = []
    if request.method == "POST":
        selected_item_ids = [
            int(item_id)
            for item_id in request.POST.getlist("selected_items")
            if item_id.isdigit()
        ]

    try:
        cart, notes = create_cart_for_prescription(
            prescription, request.user, selected_item_ids, request
        )
    except CartExistsError as e:
        messages.info(request, f"{e} Redirecting to existing cart.")
        return redirect("pharmacy:view_cart", cart_id=e.cart.id)
    except CartActionError as e:
        messages.error(request, str(e))
        return redirect("pharmacy:prescription_detail", prescription_id=prescription.id)
    except Exception as e:
        messages.error(request, f"Error creating cart: {str(e)}")
        return redirect("pharmacy:prescription_detail", prescription_id=prescription.id)

    messages.success(request, f"Cart created with {cart.items.count()} items.")
    for note in notes:
        messages.info(request, note)

    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.view")
def view_cart(request, cart_id):
    """
    View cart details with all items.
    Allows selecting dispensary and reviewing items before checkout.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    # Validate pharmacist access to cart's dispensary
    if not request.user.is_superuser and cart.dispensary:
        if hasattr(request.user, "can_access_dispensary"):
            if not request.user.can_access_dispensary(cart.dispensary):
                messages.error(
                    request,
                    f"You don't have permission to access this cart. "
                    f"The cart is assigned to '{cart.dispensary.name}', "
                    f"which you are not authorized to access.",
                )
                return redirect("pharmacy:cart_list")

    # Heal dangling invoice FK: if the linked Invoice row was deleted outside
    # Django (raw SQL/admin bulk delete), invoice_id stays set and any access
    # raises Invoice.DoesNotExist. Null it once so the rest of the view is safe.
    try:
        cart.invoice
    except PharmacyInvoice.DoesNotExist:
        cart.invoice = None
        cart.save(update_fields=["invoice"])

    # Auto-update cart status if invoice is paid (handles billing office payments)
    if (
        cart.invoice
        and cart.invoice.status == "paid"
        and cart.status in ["invoiced", "active"]
    ):
        cart.status = "paid"
        cart.save(update_fields=["status"])
        messages.info(
            request,
            '💳 Cart status updated to "Paid" - payment processed via billing office',
        )
    elif not cart.invoice and cart.status in ["invoiced", "active"]:
        # NOTE: We no longer auto-mark cart as paid based on prescription's billing invoice
        # This is because for partial dispensing, each cart should have its own invoice
        # and payment status. The cart's payment status should only be determined by
        # its own invoice (cart.invoice), not by other invoices for the same prescription.
        pass

    # Get all dispensaries - filter for pharmacists
    if request.user.is_superuser:
        dispensaries = Dispensary.objects.filter(is_active=True)
    else:
        if hasattr(request.user, "get_all_assigned_dispensaries"):
            assigned_dispensaries = request.user.get_all_assigned_dispensaries()
            dispensaries = Dispensary.objects.filter(
                id__in=[d.id for d in assigned_dispensaries], is_active=True
            )
        else:
            dispensaries = Dispensary.objects.none()

    # Calculate totals
    subtotal = cart.get_subtotal()
    patient_payable = cart.get_patient_payable()
    nhia_coverage = cart.get_nhia_coverage()

    # Check if cart can generate invoice
    can_checkout, checkout_message = cart.can_generate_invoice()

    # Get pricing breakdown
    is_nhia_patient = cart.prescription.patient.is_nhia_patient()

    # Get payment details for billing office payments
    payment_details = None
    if cart.invoice and cart.invoice.payments.exists():
        payment_details = cart.invoice.payments.all().order_by("-payment_date")

    # Get patient wallet (for wallet payment option)
    from patients.models import PatientWallet

    patient_wallet, _ = PatientWallet.objects.get_or_create(
        patient=cart.prescription.patient, defaults={"balance": Decimal("0.00")}
    )

    # Amount needed to pay this cart's invoice (balance if invoiced, else payable estimate)
    if cart.invoice:
        cart_payable_now = cart.invoice.get_balance()
    else:
        cart_payable_now = patient_payable

    # Can wallet pay be offered? (cart has unpaid invoice, or is active+ready to invoice)
    can_pay_with_wallet = False
    if cart.invoice and cart.invoice.status != "paid":
        can_pay_with_wallet = True
    elif not cart.invoice and can_checkout:
        can_pay_with_wallet = True

    # Get all available medications in the dispensary for substitution
    available_medications = []
    if cart.dispensary and cart.status == "active":
        from pharmacy.models import ActiveStoreInventory, Medication

        # Check if dispensary has an active_store (OneToOne relationship)
        # Using hasattr is safer for OneToOne fields to avoid DoesNotExist exceptions
        if hasattr(cart.dispensary, "active_store"):
            try:
                active_store = cart.dispensary.active_store
                # Get all medications with stock in this dispensary
                med_stock = (
                    ActiveStoreInventory.objects.filter(
                        active_store=active_store, stock_quantity__gt=0
                    )
                    .select_related("medication")
                    .values(
                        "medication__id",
                        "medication__name",
                        "medication__strength",
                        "medication__dosage_form",
                        "medication__generic_name",
                        "medication__price",
                    )
                    .annotate(total_stock=Sum("stock_quantity"))
                    .order_by("medication__name")
                )

                for med in med_stock:
                    # Build full medication name
                    name_parts = [med["medication__name"]]
                    if med["medication__strength"]:
                        name_parts.append(med["medication__strength"])
                    if med["medication__dosage_form"]:
                        name_parts.append(med["medication__dosage_form"])
                    full_name = " ".join(name_parts)

                    available_medications.append(
                        {
                            "id": med["medication__id"],
                            "name": med["medication__name"],
                            "full_name": full_name,
                            "strength": med["medication__strength"] or "",
                            "dosage_form": med["medication__dosage_form"] or "",
                            "generic_name": med["medication__generic_name"] or "",
                            "stock": med["total_stock"],
                            "price": float(med["medication__price"])
                            if med["medication__price"]
                            else 0,
                        }
                    )
            except Exception as e:
                # Log error but continue - cart will work without substitution feature
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Error loading available medications for cart {cart.id}: {e}"
                )

    context = {
        "cart": cart,
        "dispensaries": dispensaries,
        "subtotal": subtotal,
        "patient_payable": patient_payable,
        "nhia_coverage": nhia_coverage,
        "can_checkout": can_checkout,
        "checkout_message": checkout_message,
        "is_nhia_patient": is_nhia_patient,
        "payment_details": payment_details,
        "patient_wallet": patient_wallet,
        "cart_payable_now": cart_payable_now,
        "can_pay_with_wallet": can_pay_with_wallet,
        "wallet_balance_sufficient": patient_wallet.balance >= cart_payable_now,
        "can_edit_quantities": cart.status in ("active", "invoiced")
        and _cart_invoice_editable(cart),
        "available_medications": json.dumps(available_medications),
        "page_title": f"Prescription Cart #{cart.id}",
        "active_nav": "pharmacy",
    }

    return render(request, "pharmacy/cart/view_cart.html", context)


@login_required
@permission_required("pharmacy.edit")
def update_cart_dispensary(request, cart_id):
    """
    Update the dispensary for the cart.
    This triggers stock availability update for all items.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    if request.method == "POST":
        dispensary_id = request.POST.get("dispensary_id")

        if dispensary_id:
            try:
                dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
                set_cart_dispensary(cart, dispensary, request.user)
                messages.success(request, f"Dispensary updated to {dispensary.name}")
            except Dispensary.DoesNotExist:
                messages.error(request, "Invalid dispensary selected")
            except CartActionError as e:
                messages.error(request, str(e))
        else:
            set_cart_dispensary(cart, None, request.user)
            messages.info(request, "Dispensary cleared")

    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.edit")
def update_cart_item_quantity(request, item_id):
    """
    Update quantity for a cart item.
    AJAX endpoint.
    """
    if request.method == "POST":
        import json

        try:
            data = json.loads(request.body)
            quantity = int(data.get("quantity", 0))

            item = get_object_or_404(PrescriptionCartItem, id=item_id)
            cart = item.cart

            try:
                set_cart_item_quantity(item, quantity)
            except CartActionError as e:
                return JsonResponse({"success": False, "error": str(e)}, status=400)

            cart.refresh_from_db()
            invoice_balance = (
                float(cart.invoice.get_balance()) if cart.invoice else None
            )

            return JsonResponse(
                {
                    "success": True,
                    "item_subtotal": float(item.get_subtotal()),
                    "item_patient_pays": float(item.get_patient_pays()),
                    "item_nhia_covers": float(item.get_nhia_covers()),
                    "cart_subtotal": float(cart.get_subtotal()),
                    "cart_patient_payable": float(cart.get_patient_payable()),
                    "cart_nhia_coverage": float(cart.get_nhia_coverage()),
                    "invoice_balance": invoice_balance,
                    "stock_status": item.get_stock_status(),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


@login_required
@permission_required("pharmacy.edit")
def recost_cart(request, cart_id):
    """
    Recost an active cart so the patient-payable total fits the amount the
    patient actually has. Defaults to the patient's wallet balance; an explicit
    `target` (POST) overrides it. Scales/removes items via cart.recost_to_amount.
    """
    from patients.models import PatientWallet

    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    if request.method != "POST":
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    raw_target = request.POST.get("target", "").strip()
    if raw_target:
        try:
            target = Decimal(raw_target)
        except Exception:
            messages.error(request, "Invalid target amount.")
            return redirect("pharmacy:view_cart", cart_id=cart.id)
    else:
        wallet, _ = PatientWallet.objects.get_or_create(
            patient=cart.prescription.patient, defaults={"balance": Decimal("0.00")}
        )
        target = wallet.balance

    try:
        with transaction.atomic():
            result = cart.recost_to_amount(target)
            # Keep any existing unpaid invoice in step with the new total.
            sync_cart_invoice(cart)
    except Exception as e:
        messages.error(request, f"Cannot recost cart: {e}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    log_audit_action(
        request.user,
        "update",
        cart,
        f"Recosted cart #{cart.id} to ₦{result['target']:.2f} "
        f"(payable ₦{result['old_payable']:.2f} → ₦{result['new_payable']:.2f})",
    )

    msg = (
        f"✅ Recosted to fit ₦{result['target']:.2f}. "
        f"Patient payable now ₦{result['new_payable']:.2f} "
        f"(was ₦{result['old_payable']:.2f})."
    )
    if result["removed"]:
        msg += f" Removed (unaffordable): {', '.join(result['removed'])}."
    messages.success(request, msg)

    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.edit")
def remove_cart_item(request, item_id):
    """
    Remove an item from cart.
    """
    item = get_object_or_404(PrescriptionCartItem, id=item_id)
    cart = item.cart

    if cart.status not in ("active", "invoiced") or not _cart_invoice_editable(cart):
        messages.error(
            request, "Items can only be removed before the invoice is paid."
        )
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    with transaction.atomic():
        item.delete()
        # Keep the linked unpaid invoice in step with the new total.
        sync_cart_invoice(cart)
    messages.success(request, "Item removed from cart")

    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.create")
def generate_invoice_from_cart(request, cart_id):
    """
    Generate invoice from cart.
    Creates billing invoice and updates cart status.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    # Validate pharmacist access to cart's dispensary
    if not request.user.is_superuser and cart.dispensary:
        if hasattr(request.user, "can_access_dispensary"):
            if not request.user.can_access_dispensary(cart.dispensary):
                messages.error(
                    request,
                    f"You don't have permission to generate an invoice for "
                    f"'{cart.dispensary.name}'.",
                )
                return redirect("pharmacy:cart_list")

    selected_items = request.POST.getlist("selected_item")
    if not selected_items:
        messages.warning(
            request,
            "⚠️ No specific items were selected in the UI. All items with "
            "sufficient stock will be included in the invoice.",
        )
    else:
        messages.info(
            request,
            f"✓ Generating invoice for {len(selected_items)} selected medication(s).",
        )

    try:
        generate_cart_invoice(cart, request.user, request)
    except CartActionError as e:
        messages.error(request, f"Cannot generate invoice: {e}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)
    except Exception as e:
        messages.error(request, f"Error generating invoice: {str(e)}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    messages.success(request, f"Invoice generated with {cart.items.count()} items.")
    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.edit")
def pay_cart_from_wallet(request, cart_id):
    """
    Pay a cart's invoice directly from the patient's wallet.
    Auto-generates the invoice first if the cart is active and ready.
    On success the cart is marked 'paid' and ready for dispensing.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    if request.method != "POST":
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    try:
        payment, amount = pay_cart_from_wallet_service(
            cart,
            request.user,
            allow_negative=request.POST.get("allow_negative") == "true",
            request=request,
        )
    except CartActionError as e:
        messages.error(request, f"Cannot process payment: {e}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)
    except Exception as e:
        messages.error(request, f"Error processing wallet payment: {str(e)}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    if payment is None:
        messages.info(request, "Nothing to pay on this invoice.")
    else:
        messages.success(
            request,
            f"✅ Paid ₦{amount:.2f} from patient wallet. "
            f"Cart is ready for dispensing.",
        )
    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.dispense")
def complete_dispensing_from_cart(request, cart_id):
    """
    Complete dispensing after payment.
    Supports partial dispensing - dispenses available items and keeps cart active for pending items.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    # Per-item quantities the pharmacist typed on the cart page.
    quantities = {}
    for key, value in request.POST.items():
        if key.startswith("dispense_qty_") and value:
            item_id = key.removeprefix("dispense_qty_")
            if item_id.isdigit():
                quantities[int(item_id)] = value

    try:
        result = dispense_cart(cart, request.user, quantities)
    except CartActionError as e:
        messages.error(request, f"Cannot complete dispensing: {e}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)
    except Exception as e:
        messages.error(request, f"Error completing dispensing: {str(e)}")
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    for note in result["notes"]:
        messages.info(request, note)

    if result["completed"]:
        messages.success(request, "✅ Successfully dispensed all items! Cart completed.")
        return redirect(
            "pharmacy:prescription_detail", prescription_id=cart.prescription_id
        )

    progress = result["progress"]
    messages.success(
        request,
        f"✅ Dispensed {result['dispensed'] + result['partial']} items. "
        f"Progress: {progress['percentage']}% complete. "
        f"{progress['remaining_quantity']} items still pending.",
    )
    messages.info(
        request,
        "ℹ️ Cart remains active for pending items. You can dispense remaining "
        "items when stock becomes available.",
    )
    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.edit")
def cancel_cart(request, cart_id):
    """Cancel a cart"""
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    # Validate pharmacist access to cart's dispensary
    if not request.user.is_superuser and cart.dispensary:
        if hasattr(request.user, "can_access_dispensary"):
            if not request.user.can_access_dispensary(cart.dispensary):
                messages.error(
                    request,
                    f"You don't have permission to cancel this cart. "
                    f"The cart is assigned to '{cart.dispensary.name}' which you're not authorized to access.",
                )
                return redirect("pharmacy:cart_list")

    if cart.status in ["completed", "paid"]:
        messages.error(request, "Cannot cancel cart that is paid or completed")
        return redirect("pharmacy:view_cart", cart_id=cart.id)

    cart.cancel_cart()
    messages.success(request, "Cart cancelled")

    return redirect(
        "pharmacy:prescription_detail", prescription_id=cart.prescription.id
    )


@login_required
@permission_required("pharmacy.view")
def cart_list(request):
    """
    List all prescription carts with filtering options.
    Pharmacists only see carts for their assigned dispensary.
    """
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    status_filter = request.GET.get("status", "")
    dispensary_filter = request.GET.get("dispensary", "")
    search_query = request.GET.get("search", "")

    # Base queryset
    carts = PrescriptionCart.objects.select_related(
        "prescription__patient", "created_by", "dispensary", "invoice"
    ).order_by("-created_at")

    # Apply dispensary filter based on user role
    if not request.user.is_superuser:
        pharmacist_dispensary_id = request.session.get("selected_dispensary_id")
        if pharmacist_dispensary_id:
            # Pharmacist: Only show carts for their assigned dispensary
            carts = carts.filter(dispensary_id=pharmacist_dispensary_id)
        # If no dispensary selected but user is pharmacist, show empty list
        elif request.user.is_pharmacist():
            carts = carts.none()

    # Apply additional filters
    if status_filter:
        carts = carts.filter(status=status_filter)

    if dispensary_filter:
        carts = carts.filter(dispensary_id=dispensary_filter)

    if search_query:
        carts = carts.filter(
            Q(prescription__patient__first_name__icontains=search_query)
            | Q(prescription__patient__last_name__icontains=search_query)
            | Q(prescription__id__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(carts, 20)  # 20 carts per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get all dispensaries for filter dropdown
    dispensaries = Dispensary.objects.filter(is_active=True)

    # Get selected dispensary for display context
    selected_dispensary = None
    if not request.user.is_superuser:
        selected_dispensary_id = request.session.get("selected_dispensary_id")
        if selected_dispensary_id:
            try:
                selected_dispensary = Dispensary.objects.get(id=selected_dispensary_id)
            except Dispensary.DoesNotExist:
                selected_dispensary = None

    context = {
        "carts": page_obj,
        "dispensaries": dispensaries,
        "selected_dispensary": selected_dispensary,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "page_title": "Prescription Carts",
        "active_nav": "pharmacy",
    }

    return render(request, "pharmacy/cart/cart_list.html", context)


@login_required
@permission_required("pharmacy.view")
def cart_receipt(request, cart_id):
    """
    Display printable cart receipt.

    Supports three output formats via ?format=:
      - (default)  full A4-style HTML receipt, browser print
      - thermal    80mm/58mm thermal-roll HTML, browser print
      - pdf        downloadable A4 PDF generated with ReportLab
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    # Validate pharmacist access to cart's dispensary
    if not request.user.is_superuser and cart.dispensary:
        if hasattr(request.user, "can_access_dispensary"):
            if not request.user.can_access_dispensary(cart.dispensary):
                messages.error(
                    request,
                    f"You don't have permission to view receipt for '{cart.dispensary.name}'. "
                    f"This cart is assigned to a dispensary you're not authorized to access.",
                )
                return redirect("pharmacy:cart_list")

    # Per-tenant letterhead (falls back to settings on the bare host).
    from saas.context_processors import hospital_details

    details = hospital_details(request)

    output = (request.GET.get("format") or "").lower()

    if output == "pdf":
        hospital = getattr(request, "hospital", None)
        return _cart_receipt_pdf(
            cart,
            details["hospital_name"],
            details["hospital_address"],
            details["hospital_phone"],
            hospital.logo if hospital and hospital.logo else None,
        )

    if output == "thermal":
        return _cart_receipt_thermal(request, cart)

    context = {
        "cart": cart,
        "now": timezone.now(),
        "page_title": f"Cart Receipt #{cart.id}",
    }

    return render(request, "pharmacy/cart/cart_receipt.html", context)


def _cart_receipt_thermal(request, cart):
    """80mm/58mm roll version of the cart receipt (?format=thermal[&width=58])."""
    from core.receipts import render_thermal, fmt_dt

    patient = cart.prescription.patient
    is_nhia = patient.is_nhia_patient()

    items = []
    for item in cart.items.all():
        med = item.prescription_item.medication
        items.append(
            {
                "name": f"{med.name} {med.strength}",
                "qty": item.quantity,
                "unit": item.unit_price,
                "amount": item.get_subtotal(),
                "note": (
                    f"Pt 10%: {item.get_patient_pays():,.2f} / "
                    f"NHIA: {item.get_nhia_covers():,.2f}"
                )
                if is_nhia
                else "",
            }
        )

    totals = [("Subtotal", cart.get_subtotal(), False)]
    if is_nhia:
        totals.append(("NHIA 90%", cart.get_nhia_coverage(), False))
    totals.append(
        ("Pt Pays" if is_nhia else "TOTAL", cart.get_patient_payable(), True)
    )

    return render_thermal(
        request,
        title="CART RECEIPT",
        meta=[
            ("Cart", f"#{cart.id}"),
            ("Date", fmt_dt(cart.created_at)),
            ("By", cart.created_by.get_full_name()),
            ("Disp", cart.dispensary.name if cart.dispensary else ""),
            ("Patient", patient.get_full_name()),
            ("Patient ID", patient.patient_id),
            ("Rx", f"#{cart.prescription.id}"),
            ("NHIA", "patient 10% / NHIA 90%" if is_nhia else ""),
            (
                "Invoice",
                f"#{cart.invoice.id} ({cart.invoice.get_status_display()})"
                if cart.invoice
                else "",
            ),
        ],
        items=items,
        totals=totals,
    )


def _cart_receipt_pdf(cart, hospital_name, hospital_address, hospital_phone, logo=None):
    """Render an A4 PDF of the cart receipt using ReportLab.

    Helvetica has no Naira (NGN) glyph, so amounts are prefixed "NGN " to
    avoid tofu boxes in the PDF output.
    """
    from io import BytesIO
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Image,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    def money(value):
        try:
            return f"NGN {float(value or 0):,.2f}"
        except (TypeError, ValueError):
            return "NGN 0.00"

    patient = cart.prescription.patient
    is_nhia = bool(getattr(patient, "is_nhia_patient", False))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Cart Receipt #{cart.id}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "rcptTitle", parent=styles["Title"], fontSize=16, spaceAfter=2
    )
    sub_style = ParagraphStyle(
        "rcptSub", parent=styles["Normal"], alignment=1, textColor=colors.grey
    )
    h_style = ParagraphStyle(
        "rcptH", parent=styles["Heading4"], spaceBefore=10, spaceAfter=4
    )
    small = ParagraphStyle(
        "rcptSmall", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )

    elements = []
    if logo:
        # A bad/missing upload must not take the whole receipt down with it.
        try:
            with logo.open("rb") as fh:
                img = Image(BytesIO(fh.read()))
            img.drawWidth = img.imageWidth * (18 * mm) / img.imageHeight
            img.drawHeight = 18 * mm
            img.hAlign = "CENTER"
            elements.append(img)
        except Exception:
            pass
    elements.append(Paragraph(hospital_name or "Hospital Management System", title_style))
    if hospital_address:
        elements.append(Paragraph(hospital_address, sub_style))
    if hospital_phone:
        elements.append(Paragraph(hospital_phone, sub_style))
    elements.append(Paragraph("PRESCRIPTION CART RECEIPT", sub_style))
    elements.append(Spacer(1, 8))

    # Cart + patient info side by side
    created_by = cart.created_by.get_full_name() if cart.created_by else ""
    info_left = [
        ["Cart ID:", f"#{cart.id}"],
        ["Status:", cart.get_status_display()],
        ["Created:", cart.created_at.strftime("%b %d, %Y %H:%M")],
        ["Created By:", created_by],
    ]
    if cart.dispensary:
        info_left.append(["Dispensary:", cart.dispensary.name])

    info_right = [
        ["Patient:", patient.get_full_name()],
        ["Patient ID:", patient.patient_id],
        ["Prescription:", f"#{cart.prescription.id}"],
    ]
    if is_nhia:
        info_right.append(["NHIA No:", getattr(patient, "nhia_number", "") or ""])

    rows = max(len(info_left), len(info_right))
    info_left += [["", ""]] * (rows - len(info_left))
    info_right += [["", ""]] * (rows - len(info_right))
    info_data = [
        [l[0], l[1], r[0], r[1]] for l, r in zip(info_left, info_right)
    ]
    info_table = Table(info_data, colWidths=[28 * mm, 50 * mm, 28 * mm, 48 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(info_table)

    if is_nhia:
        elements.append(Spacer(1, 6))
        elements.append(
            Paragraph(
                "<b>NHIA Patient:</b> Patient pays 10%, NHIA covers 90% of medication costs.",
                small,
            )
        )

    elements.append(Paragraph("Items", h_style))

    if is_nhia:
        header = ["Medication", "Qty", "Unit Price", "Subtotal", "Patient 10%", "NHIA 90%"]
        col_widths = [50 * mm, 13 * mm, 25 * mm, 27 * mm, 27 * mm, 27 * mm]
    else:
        header = ["Medication", "Qty", "Unit Price", "Subtotal"]
        col_widths = [78 * mm, 18 * mm, 35 * mm, 35 * mm]

    item_data = [header]
    for item in cart.items.all():
        med = item.prescription_item.medication
        name = med.name + (f" {med.strength}" if med.strength else "")
        row = [
            Paragraph(name, styles["Normal"]),
            str(item.quantity),
            money(item.unit_price),
            money(item.get_subtotal()),
        ]
        if is_nhia:
            row += [money(item.get_patient_pays()), money(item.get_nhia_covers())]
        item_data.append(row)

    item_table = Table(item_data, colWidths=col_widths, repeatRows=1)
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(item_table)

    # Summary
    summary_data = [["Subtotal:", money(cart.get_subtotal())]]
    if is_nhia:
        summary_data.append(["NHIA Coverage (90%):", money(cart.get_nhia_coverage())])
        summary_data.append(["Patient Pays (10%):", money(cart.get_patient_payable())])
    else:
        summary_data.append(["Total Amount:", money(cart.get_patient_payable())])

    summary_table = Table(summary_data, colWidths=[60 * mm, 40 * mm], hAlign="RIGHT")
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#333333")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(Spacer(1, 10))
    elements.append(summary_table)

    if cart.invoice:
        elements.append(Paragraph("Invoice Information", h_style))
        elements.append(
            Paragraph(
                f"Invoice #{cart.invoice.id} &mdash; {cart.invoice.get_status_display()}",
                styles["Normal"],
            )
        )

    elements.append(Spacer(1, 30))
    elements.append(
        Paragraph(
            "This is a computer-generated receipt. "
            f"Printed on {timezone.now().strftime('%b %d, %Y %H:%M')}.",
            small,
        )
    )

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="cart_receipt_{cart.id}.pdf"'
    )
    return response


@login_required
@permission_required("pharmacy.edit")
def substitute_cart_item(request, item_id):
    """
    Substitute a cart item with an alternative medication.
    Requires pharmacist approval and reason.
    """
    cart_item = get_object_or_404(PrescriptionCartItem, id=item_id)
    cart = cart_item.cart

    if request.method == "POST":
        substitute_med_id = request.POST.get("substitute_medication_id")
        reason = request.POST.get("reason", "").strip()

        if not substitute_med_id:
            messages.error(request, "Please select a substitute medication")
            return redirect("pharmacy:view_cart", cart_id=cart.id)

        try:
            from pharmacy.models import Medication

            substitute_med = Medication.objects.get(id=substitute_med_id)
            note = substitute_cart_item_service(
                cart_item, substitute_med, reason, request.user
            )
        except Medication.DoesNotExist:
            messages.error(request, "Invalid substitute medication selected")
            return redirect("pharmacy:view_cart", cart_id=cart.id)
        except CartActionError as e:
            messages.error(request, f"Cannot substitute: {e}")
            return redirect("pharmacy:view_cart", cart_id=cart.id)
        except Exception as e:
            messages.error(request, f"Error during substitution: {str(e)}")
            return redirect("pharmacy:view_cart", cart_id=cart.id)

        messages.success(
            request,
            f"✅ Successfully substituted "
            f"{cart_item.prescription_item.medication.name} with {substitute_med.name}",
        )
        messages.info(request, note)

    return redirect("pharmacy:view_cart", cart_id=cart.id)


@login_required
@permission_required("pharmacy.edit")
def remove_substitution(request, item_id):
    """
    Remove substitution and revert to original prescribed medication.
    """
    cart_item = get_object_or_404(PrescriptionCartItem, id=item_id)
    cart = cart_item.cart

    try:
        messages.success(request, undo_substitution(cart_item, request.user))
    except CartActionError as e:
        messages.warning(request, str(e))
    except Exception as e:
        messages.error(request, f"Error removing substitution: {str(e)}")

    return redirect("pharmacy:view_cart", cart_id=cart.id)

