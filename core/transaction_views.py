from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from patients.models import Patient, PatientWallet, WalletTransaction
from billing.models import Payment as BillingPayment, Invoice
# from pharmacy_billing.models import Payment as PharmacyPayment
from inpatient.models import Admission
from consultations.models import Consultation
from theatre.models import Surgery


@login_required
def comprehensive_transaction_history(request, patient_id=None):
    """
    Comprehensive view showing all monetary transactions for a patient or system-wide
    """
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
    
    # Date filtering
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    transaction_type = request.GET.get('transaction_type', 'all')
    
    # Default to last 365 days if no dates provided (show full year of data)
    if not date_from:
        date_from = (timezone.now() - timedelta(days=365)).date()
    else:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    
    if not date_to:
        date_to = timezone.now().date()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    transactions = []
    
    # 1. Wallet Transactions
    wallet_transactions = WalletTransaction.objects.filter(
        created_at__date__range=[date_from, date_to]
    )
    if patient:
        wallet_transactions = wallet_transactions.filter(wallet__patient=patient)
    
    for wt in wallet_transactions:
        transactions.append({
            'date': wt.created_at,
            'type': 'Wallet Transaction',
            'subtype': wt.get_transaction_type_display(),
            'amount': wt.amount,
            'balance_after': wt.balance_after,
            'description': wt.description,
            'reference': wt.reference_number,
            'patient': wt.wallet.patient,
            'created_by': wt.created_by,
            'status': wt.get_status_display(),
            'source': 'wallet',
            'related_object': wt,
            'invoice': wt.invoice,
        })
    
    # 2. Billing Payments
    billing_payments = BillingPayment.objects.filter(
        created_at__date__range=[date_from, date_to]
    ).select_related('invoice', 'invoice__patient', 'received_by')
    if patient:
        billing_payments = billing_payments.filter(invoice__patient=patient)
    
    for bp in billing_payments:
        transactions.append({
            'date': bp.created_at,
            'type': 'Billing Payment',
            'subtype': bp.get_payment_method_display(),
            'amount': bp.amount,
            'balance_after': None,
            'description': f"Payment for Invoice #{bp.invoice.invoice_number}",
            'reference': bp.transaction_id or f"PAY-{bp.id}",
            'patient': bp.invoice.patient,
            'created_by': bp.received_by,
            'status': 'Completed',
            'source': 'billing',
            'related_object': bp,
            'invoice': bp.invoice,
        })
    
    # 3. Pharmacy Payments - Temporarily disabled
    # pharmacy_payments = PharmacyPayment.objects.filter(
    #     created_at__date__range=[date_from, date_to]
    # ).select_related('invoice', 'invoice__patient', 'received_by')
    # if patient:
    #     pharmacy_payments = pharmacy_payments.filter(invoice__patient=patient)
    # 
    # for pp in pharmacy_payments:
    #     transactions.append({
    #         'date': pp.created_at,
    #         'type': 'Pharmacy Payment',
    #         'subtype': pp.get_payment_method_display(),
    #         'amount': pp.amount,
    #         'balance_after': None,
    #         'description': f"Pharmacy payment for Invoice #{pp.invoice.id}",
    #         'reference': pp.transaction_id or f"PHARM-{pp.id}",
    #         'patient': pp.invoice.patient,
    #         'created_by': pp.received_by,
    #         'status': 'Completed',
    #         'source': 'pharmacy',
    #         'related_object': pp,
    #         'invoice': pp.invoice,
    #     })
    
    # 4. Admission Payments (from invoices)
    admission_invoices = Invoice.objects.filter(
        created_at__date__range=[date_from, date_to],
        source_app='inpatient'
    ).select_related('patient', 'admission')
    if patient:
        admission_invoices = admission_invoices.filter(patient=patient)
    
    for invoice in admission_invoices:
        for payment in invoice.payments.all():
            transactions.append({
                'date': payment.created_at,
                'type': 'Admission Payment',
                'subtype': payment.get_payment_method_display(),
                'amount': payment.amount,
                'balance_after': None,
                'description': f"Admission payment for {invoice.admission.patient.get_full_name() if invoice.admission else 'Unknown'}",
                'reference': payment.transaction_id or f"ADM-{payment.id}",
                'patient': invoice.patient,
                'created_by': payment.received_by,
                'status': 'Completed',
                'source': 'admission',
                'related_object': payment,
                'invoice': invoice,
            })
    
    # Filter by transaction type
    if transaction_type != 'all':
        transactions = [t for t in transactions if t['source'] == transaction_type]
    
    # Sort by date (newest first)
    transactions.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate summary statistics
    total_amount = sum(t['amount'] for t in transactions)
    total_transactions = len(transactions)
    
    # Group by type for summary
    summary_by_type = {}
    for t in transactions:
        # Use subtype as the primary grouping, fallback to source if no subtype
        display_type = t['subtype'] if t['subtype'] else t['source']
        if display_type not in summary_by_type:
            summary_by_type[display_type] = {'count': 0, 'amount': Decimal('0.00'), 'source': t['source']}
        summary_by_type[display_type]['count'] += 1
        summary_by_type[display_type]['amount'] += t['amount']
    
    # Check if there are no transactions and add helpful debug info
    if not transactions:
        # Try to find any transactions without date filtering for debugging
        all_wallet_transactions = WalletTransaction.objects.all()
        all_billing_payments = BillingPayment.objects.all()
        total_wallet = all_wallet_transactions.count()
        total_billing = all_billing_payments.count()
        
        context = {
            'patient': patient,
            'transactions': transactions,
            'total_amount': total_amount,
            'total_transactions': total_transactions,
            'summary_by_type': summary_by_type,
            'date_from': date_from,
            'date_to': date_to,
            'transaction_type': transaction_type,
            'title': f'Transaction History - {patient.get_full_name()}' if patient else 'System Transaction History',
            'debug_info': f"Total wallet transactions in DB: {total_wallet}, Total billing payments in DB: {total_billing}"
        }
    else:
        context = {
            'patient': patient,
            'transactions': transactions,
            'total_amount': total_amount,
            'total_transactions': total_transactions,
            'summary_by_type': summary_by_type,
            'date_from': date_from,
            'date_to': date_to,
            'transaction_type': transaction_type,
            'title': f'Transaction History - {patient.get_full_name()}' if patient else 'System Transaction History'
        }
    
    return render(request, 'core/comprehensive_transaction_history.html', context)


@login_required
def patient_financial_summary(request, patient_id):
    """
    Financial summary for a specific patient showing all monetary activities
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get wallet information
    try:
        wallet = PatientWallet.objects.get(patient=patient)
        wallet_balance = wallet.balance
        total_credits = wallet.get_total_credits()
        total_debits = wallet.get_total_debits()
    except PatientWallet.DoesNotExist:
        wallet = None
        wallet_balance = Decimal('0.00')
        total_credits = Decimal('0.00')
        total_debits = Decimal('0.00')
    
    # Get all invoices for the patient
    invoices = Invoice.objects.filter(patient=patient).order_by('-created_at')
    total_invoiced = sum(invoice.total_amount for invoice in invoices)
    total_paid = sum(invoice.amount_paid for invoice in invoices)
    outstanding_balance = total_invoiced - total_paid
    
    # Recent transactions (last 10)
    recent_transactions = []
    if wallet:
        recent_wallet_transactions = wallet.get_transaction_history(limit=10)
        for wt in recent_wallet_transactions:
            recent_transactions.append({
                'date': wt.created_at,
                'type': 'Wallet',
                'description': wt.description,
                'amount': wt.amount,
                'reference': wt.reference_number,
            })
    
    # Recent payments
    recent_payments = BillingPayment.objects.filter(
        invoice__patient=patient
    ).order_by('-created_at')[:5]
    
    for payment in recent_payments:
        recent_transactions.append({
            'date': payment.created_at,
            'type': 'Payment',
            'description': f"Payment for Invoice #{payment.invoice.invoice_number}",
            'amount': payment.amount,
            'reference': payment.transaction_id or f"PAY-{payment.id}",
        })
    
    # Sort recent transactions by date
    recent_transactions.sort(key=lambda x: x['date'], reverse=True)
    recent_transactions = recent_transactions[:10]  # Keep only 10 most recent
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'wallet_balance': wallet_balance,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'outstanding_balance': outstanding_balance,
        'recent_transactions': recent_transactions,
        'invoices_count': invoices.count(),
        'title': f'Financial Summary - {patient.get_full_name()}'
    }
    
    return render(request, 'core/patient_financial_summary.html', context)
