"""Payment view for billing module.
Provides a robust record_payment view fixing context errors.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from billing.models import Invoice
from billing.forms import PaymentForm
from core.billing_office_integration import BillingOfficePaymentProcessor

@login_required
def record_payment(request, invoice_id):
    """Handle payment recording for a given invoice.
    Ensures context is always defined to avoid UnboundLocalError.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    patient = invoice.patient
    patient_wallet = getattr(patient, 'wallet', None)

    # Calculate remaining amount
    remaining_amount = invoice.get_balance()

    if request.method == 'POST':
        form = PaymentForm(request.POST, invoice=invoice, patient_wallet=patient_wallet)
        if form.is_valid():
            # Process payment using billing office integration
            payment_data = form.cleaned_data
            success, message, payment = BillingOfficePaymentProcessor.process_payment(
                request=request,
                invoice=invoice,
                amount=payment_data['amount'],
                payment_source=payment_data.get('payment_source', 'billing_office'),
                payment_method=payment_data.get('payment_method', 'cash'),
                transaction_id=payment_data.get('transaction_id', ''),
                notes=payment_data.get('notes', ''),
                module_name='Billing'
            )

            if success:
                messages.success(request, message)
                return redirect('billing:detail', invoice_id=invoice.id)
            else:
                messages.error(request, message)
    else:
        # Set initial amount to remaining balance
        initial_data = {'amount': remaining_amount}
        form = PaymentForm(initial=initial_data, invoice=invoice, patient_wallet=patient_wallet)

    context = {
        'title': f'Record Payment - Invoice #{invoice.invoice_number}',
        'invoice': invoice,
        'patient': patient,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'form': form,
    }

    return render(request, 'billing/payment_form.html', context)
