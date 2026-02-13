from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from billing.models import Invoice, Payment
from patients.models import PatientWallet
from .payment_forms import TheatrePaymentForm
from .models import Surgery
from core.billing_office_integration import BillingOfficePaymentProcessor
from .views import theatre_access_required


@login_required
@theatre_access_required
@require_http_methods(["GET", "POST"])
def theatre_payment(request, surgery_id):
    """Handle theatre service payment processing with dual payment methods"""
    surgery = get_object_or_404(Surgery, id=surgery_id)

    # Get or create invoice for surgery
    try:
        invoice = Invoice.objects.get(
            patient=surgery.patient, source_app="theatre", object_id=surgery.id
        )
    except Invoice.DoesNotExist:
        # Create invoice if it doesn't exist
        invoice = Invoice.objects.create(
            patient=surgery.patient,
            source_app="theatre",
            object_id=surgery.id,
            total_amount=surgery.estimated_cost or Decimal("0.00"),
            description=f"Theatre services for {surgery.procedure_name}",
        )

    # Get or create patient wallet
    patient_wallet, created = PatientWallet.objects.get_or_create(
        patient=surgery.patient, defaults={"balance": Decimal("0.00")}
    )

    if request.method == "POST":
        form = TheatrePaymentForm(
            request.POST, invoice=invoice, patient_wallet=patient_wallet
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.created_by = request.user

                    # Set payment method based on payment source
                    payment_source = form.cleaned_data["payment_source"]
                    if payment_source == "patient_wallet":
                        payment.payment_method = "wallet"
                        # Deduct from wallet
                        patient_wallet.balance -= payment.amount
                        patient_wallet.save()

                    payment.save()

                    # Update invoice status if fully paid
                    if invoice.get_balance() <= 0:
                        invoice.status = "paid"
                        invoice.save()
                        # Update surgery status if needed
                        if hasattr(surgery, "status"):
                            surgery.status = "payment_confirmed"
                            surgery.save()

                    # Log the payment
                    payment_method_display = (
                        "Wallet"
                        if payment_source == "patient_wallet"
                        else payment.get_payment_method_display()
                    )
                    messages.success(
                        request,
                        f"Payment of ₦{payment.amount:.2f} recorded successfully via {payment_method_display}.",
                    )

                    return redirect("theatre:surgery_detail", surgery_id=surgery.id)

            except Exception as e:
                messages.error(request, f"Payment processing failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TheatrePaymentForm(invoice=invoice, patient_wallet=patient_wallet)

    context = {
        "form": form,
        "surgery": surgery,
        "invoice": invoice,
        "patient_wallet": patient_wallet,
        "remaining_balance": invoice.get_balance(),
        "payments": Payment.objects.filter(invoice=invoice).order_by("-created_at"),
    }

    return render(request, "theatre/payment.html", context)


@login_required
@theatre_access_required
def theatre_payment_history(request, surgery_id):
    """View payment history for a theatre service"""
    surgery = get_object_or_404(Surgery, id=surgery_id)

    try:
        invoice = Invoice.objects.get(
            patient=surgery.patient, source_app="theatre", object_id=surgery.id
        )
        payments = Payment.objects.filter(invoice=invoice).order_by("-created_at")
    except Invoice.DoesNotExist:
        invoice = None
        payments = []

    context = {
        "surgery": surgery,
        "invoice": invoice,
        "payments": payments,
    }

    return render(request, "theatre/payment_history.html", context)


@login_required
@theatre_access_required
def confirm_theatre_payment(request, surgery_id):
    """Confirm theatre payment and update surgery status"""
    surgery = get_object_or_404(Surgery, id=surgery_id)

    try:
        invoice = Invoice.objects.get(
            patient=surgery.patient, source_app="theatre", object_id=surgery.id
        )
        if invoice.get_balance() <= 0:
            if hasattr(surgery, "status"):
                surgery.status = "payment_confirmed"
                surgery.save()
            messages.success(
                request, "Theatre service payment confirmed. Surgery can now proceed."
            )
        else:
            messages.warning(
                request,
                "Payment is not complete. Please complete payment before confirming.",
            )
    except Invoice.DoesNotExist:
        messages.error(request, "No invoice found for this surgery.")

    return redirect("theatre:surgery_detail", surgery_id=surgery.id)
