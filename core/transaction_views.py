from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from patients.models import Patient, PatientWallet, WalletTransaction
from billing.models import Payment as BillingPayment, Invoice
from core.decorators import role_required


def _parse_date(value, default):
    """Parse YYYY-MM-DD, falling back to default on bad/missing input."""
    if value:
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            pass
    return default


@login_required
@role_required(['admin', 'accountant', 'receptionist'])
def comprehensive_transaction_history(request, patient_id=None):
    """
    Comprehensive view showing all monetary transactions for a patient or system-wide
    """
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)

    # Date filtering (default: last 365 days)
    today = timezone.now().date()
    date_from = _parse_date(request.GET.get('date_from'), today - timedelta(days=365))
    date_to = _parse_date(request.GET.get('date_to'), today)
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    transaction_type = request.GET.get('transaction_type', 'all')

    transactions = []

    # 1. Wallet Transactions
    wallet_transactions = WalletTransaction.objects.filter(
        created_at__date__range=[date_from, date_to]
    ).select_related(
        'patient', 'patient_wallet__patient', 'created_by', 'invoice'
    )
    if patient:
        # Shared-wallet transactions always record the acting patient directly.
        wallet_transactions = wallet_transactions.filter(
            Q(patient=patient) | Q(patient_wallet__patient=patient)
        )

    for wt in wallet_transactions:
        transaction_patient = wt.patient
        if transaction_patient is None and wt.patient_wallet:
            transaction_patient = wt.patient_wallet.patient

        transactions.append({
            'date': wt.created_at,
            'type': 'Wallet Transaction',
            'subtype': wt.get_transaction_type_display(),
            'amount': wt.amount,
            'is_credit': wt.is_credit_transaction(),
            'balance_after': wt.balance_after,
            'description': wt.description,
            'reference': wt.reference_number,
            'patient': transaction_patient,
            'created_by': wt.created_by,
            'status': wt.get_status_display(),
            'source': 'wallet',
            'invoice': wt.invoice,
        })

    # 2. Billing Payments (covers all invoice sources: billing, pharmacy, inpatient, ...)
    billing_payments = BillingPayment.objects.filter(
        created_at__date__range=[date_from, date_to]
    ).select_related('invoice', 'invoice__patient', 'received_by')
    if patient:
        billing_payments = billing_payments.filter(invoice__patient=patient)

    SOURCE_BY_APP = {'pharmacy': 'pharmacy', 'inpatient': 'admission'}
    TYPE_BY_SOURCE = {'pharmacy': 'Pharmacy Payment', 'admission': 'Admission Payment'}

    for bp in billing_payments:
        source = SOURCE_BY_APP.get(bp.invoice.source_app, 'billing')
        transactions.append({
            'date': bp.created_at,
            'type': TYPE_BY_SOURCE.get(source, 'Billing Payment'),
            'subtype': bp.get_payment_method_display(),
            'amount': bp.amount,
            'is_credit': True,
            'balance_after': None,
            'description': f"Payment for Invoice #{bp.invoice.invoice_number}",
            'reference': bp.transaction_id or f"PAY-{bp.id}",
            'patient': bp.invoice.patient,
            'created_by': bp.received_by,
            'status': 'Completed',
            'source': source,
            'invoice': bp.invoice,
        })

    # Filter by transaction type
    if transaction_type != 'all':
        transactions = [t for t in transactions if t['source'] == transaction_type]

    # Sort by date (newest first)
    transactions.sort(key=lambda x: x['date'], reverse=True)

    # Summary statistics
    total_amount = sum(t['amount'] for t in transactions)
    total_credits = sum(t['amount'] for t in transactions if t['is_credit'])
    total_debits = total_amount - total_credits

    # Group by type for summary
    summary_by_type = {}
    for t in transactions:
        display_type = t['subtype'] or t['source']
        entry = summary_by_type.setdefault(
            display_type, {'count': 0, 'amount': Decimal('0.00'), 'source': t['source']}
        )
        entry['count'] += 1
        entry['amount'] += t['amount']

    context = {
        'patient': patient,
        'transactions': transactions,
        'total_amount': total_amount,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'total_transactions': len(transactions),
        'summary_by_type': summary_by_type,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_type': transaction_type,
        'title': f'Transaction History - {patient.get_full_name()}' if patient else 'System Transaction History',
    }

    return render(request, 'core/comprehensive_transaction_history.html', context)


@login_required
@role_required(['admin', 'accountant', 'receptionist'])
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

    # Invoice totals (cancelled invoices excluded so they don't inflate outstanding)
    invoices = Invoice.objects.filter(patient=patient).exclude(status='cancelled')
    invoice_totals = invoices.aggregate(
        total_invoiced=Sum('total_amount'), total_paid=Sum('amount_paid'), count=Count('id')
    )
    total_invoiced = invoice_totals['total_invoiced'] or Decimal('0.00')
    total_paid = invoice_totals['total_paid'] or Decimal('0.00')
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
                'is_credit': wt.is_credit_transaction(),
                'reference': wt.reference_number,
            })

    # Recent payments
    recent_payments = BillingPayment.objects.filter(
        invoice__patient=patient
    ).select_related('invoice').order_by('-created_at')[:10]

    for payment in recent_payments:
        recent_transactions.append({
            'date': payment.created_at,
            'type': 'Payment',
            'description': f"Payment for Invoice #{payment.invoice.invoice_number}",
            'amount': payment.amount,
            'is_credit': True,
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
        'invoices_count': invoice_totals['count'],
        'title': f'Financial Summary - {patient.get_full_name()}'
    }

    return render(request, 'core/patient_financial_summary.html', context)
