from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from decimal import Decimal
import csv
from .models import Invoice, InvoiceItem, Payment, Service
from .forms import InvoiceForm, InvoiceItemForm, PaymentForm, ServiceForm, InvoiceSearchForm
from patients.models import Patient
from appointments.models import Appointment
from laboratory.models import TestRequest
from pharmacy.models import Prescription
from inpatient.models import Admission
from core.audit_utils import log_audit_action
from core.models import InternalNotification, send_notification_email

@login_required
def invoice_list(request):
    """View for listing all invoices with search and filter functionality"""
    search_form = InvoiceSearchForm(request.GET)
    invoices = Invoice.objects.all().order_by('-created_at')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search_query) |
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query)
            )

        if status:
            invoices = invoices.filter(status=status)

        if date_from:
            invoices = invoices.filter(created_at__date__gte=date_from)

        if date_to:
            invoices = invoices.filter(created_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(invoices, 10)  # Show 10 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts for different statuses
    pending_count = Invoice.objects.filter(status='pending').count()
    paid_count = Invoice.objects.filter(status='paid').count()
    partially_paid_count = Invoice.objects.filter(status='partially_paid').count()
    overdue_count = Invoice.objects.filter(status='overdue').count()
    cancelled_count = Invoice.objects.filter(status='cancelled').count()

    # Get total amounts
    total_amount = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    paid_amount = Invoice.objects.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    pending_amount = Invoice.objects.filter(status='pending').aggregate(total=Sum('total_amount'))['total'] or 0
    overdue_amount = Invoice.objects.filter(status='overdue').aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_invoices': invoices.count(),
        'pending_count': pending_count,
        'paid_count': paid_count,
        'partially_paid_count': partially_paid_count,
        'overdue_count': overdue_count,
        'cancelled_count': cancelled_count,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'overdue_amount': overdue_amount,
    }

    return render(request, 'billing/invoice_list.html', context)

@login_required
def create_invoice(request):
    """View for creating a new invoice"""
    # Pre-fill patient_id if provided in GET parameters
    patient_id = request.GET.get('patient_id')
    initial_data = {}

    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
            initial_data['patient'] = patient
        except Patient.DoesNotExist:
            pass

    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            # Audit log
            log_audit_action(request.user, 'create', invoice, f"Created invoice {invoice.invoice_number}")
            # Notification to billing/admin
            if invoice.created_by:
                InternalNotification.objects.create(
                    user=invoice.created_by,
                    message=f"Invoice {invoice.invoice_number} created for {invoice.patient.get_full_name()}"
                )
            # Send email notification if user has email
            if invoice.created_by and hasattr(invoice.created_by, 'email') and invoice.created_by.email:
                send_notification_email(
                    subject="New Invoice Created",
                    message=f"Invoice {invoice.invoice_number} has been created for {invoice.patient.get_full_name()}.",
                    recipient_list=[invoice.created_by.email]
                )
            messages.success(request, f'Invoice {invoice.invoice_number} has been created successfully.')
            return redirect('billing:detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm(initial=initial_data)

    context = {
        'form': form,
        'title': 'Create New Invoice'
    }

    return render(request, 'billing/invoice_form.html', context)

@login_required
def invoice_detail(request, invoice_id):
    """View for displaying invoice details"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice_items = invoice.items.all()
    payments = invoice.payments.all().order_by('-payment_date')

    # Handle adding new invoice item
    if request.method == 'POST' and 'add_item' in request.POST:
        item_form = InvoiceItemForm(request.POST)
        if item_form.is_valid():
            item = item_form.save(commit=False)
            item.invoice = invoice
            # Calculate total price and save
            item.save()

            # Update invoice total amount
            subtotal = invoice.items.aggregate(total=Sum('total_amount'))['total'] or 0
            invoice.subtotal = subtotal
            invoice.total_amount = subtotal + invoice.tax_amount - invoice.discount_amount
            invoice.save()

            messages.success(request, f'Item {item.description} added to invoice.')
            return redirect('billing:detail', invoice_id=invoice.id)
    else:
        item_form = InvoiceItemForm()

    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'payments': payments,
        'item_form': item_form,
    }

    return render(request, 'billing/invoice_detail.html', context)

@login_required
def edit_invoice(request, invoice_id):
    """View for editing an invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Don't allow editing of paid or cancelled invoices
    if invoice.status in ['paid', 'cancelled']:
        messages.error(request, f'Cannot edit invoice with status: {invoice.get_status_display()}')
        return redirect('billing:detail', invoice_id=invoice.id)

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, f'Invoice {invoice.invoice_number} has been updated successfully.')
            return redirect('billing:detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm(instance=invoice)

    context = {
        'form': form,
        'invoice': invoice,
        'title': f'Edit Invoice: {invoice.invoice_number}'
    }

    return render(request, 'billing/invoice_form.html', context)

@login_required
def delete_invoice(request, invoice_id):
    """View for deleting an invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Don't allow deleting of paid invoices
    if invoice.status == 'paid':
        messages.error(request, 'Cannot delete a paid invoice.')
        return redirect('billing:detail', invoice_id=invoice.id)

    # Check if there are payments associated with this invoice
    if invoice.payments.exists():
        messages.error(request, 'Cannot delete an invoice with payments. Cancel it instead.')
        return redirect('billing:detail', invoice_id=invoice.id)

    if request.method == 'POST':
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f'Invoice {invoice_number} has been deleted.')
        return redirect('billing:list')

    context = {
        'invoice': invoice
    }

    return render(request, 'billing/delete_invoice.html', context)

@login_required
def print_invoice(request, invoice_id):
    """View for printing an invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice_items = invoice.items.all()
    payments = invoice.payments.all().order_by('-payment_date')

    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'payments': payments,
        'print_view': True
    }

    return render(request, 'billing/print_invoice.html', context)

@login_required
def record_payment(request, invoice_id):
    """Enhanced view for recording payments with dual payment method support"""
    from patients.models import PatientWallet
    from django.db import transaction
    
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Calculate remaining amount
    remaining_amount = invoice.get_balance()

    if remaining_amount <= 0 and invoice.status == 'paid':
        messages.info(request, 'This invoice has already been fully paid.')
        return redirect('billing:detail', invoice_id=invoice.id)

    # Get or create patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=invoice.patient)
    except PatientWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        patient_wallet = PatientWallet.objects.create(
            patient=invoice.patient,
            balance=0
        )

    if request.method == 'POST':
        form = PaymentForm(
            request.POST,
            invoice=invoice,
            patient_wallet=patient_wallet
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.received_by = request.user

                    payment_source = form.cleaned_data['payment_source']

                    if payment_source == 'patient_wallet':
                        # Force wallet payment method
                        payment.payment_method = 'wallet'

                    payment.save()

                    # Audit log
                    log_audit_action(
                        request.user, 
                        'create', 
                        payment, 
                        f"Recorded {payment_source} payment of ₦{payment.amount:.2f} for invoice {invoice.invoice_number}"
                    )
                    
                    # Notification to billing/admin
                    if invoice.created_by:
                        InternalNotification.objects.create(
                            user=invoice.created_by,
                            message=f"Payment of ₦{payment.amount:.2f} recorded for invoice {invoice.invoice_number} via {payment_source}"
                        )
                    
                    # Send email notification if user has email
                    if invoice.created_by and hasattr(invoice.created_by, 'email') and invoice.created_by.email:
                        send_notification_email(
                            subject="Payment Recorded",
                            message=f"A payment of ₦{payment.amount:.2f} was recorded for invoice {invoice.invoice_number} via {payment_source.replace('_', ' ').title()}.",
                            recipient_list=[invoice.created_by.email]
                        )
                    
                    messages.success(request, f'Payment of ₦{payment.amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')
                    return redirect('billing:detail', invoice_id=invoice.id)
                    
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
    else:
        # Pre-fill the amount with the remaining balance
        form = PaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet,
            initial={
                'amount': remaining_amount,
                'payment_date': timezone.now().date(),
                'payment_method': 'cash'
            }
        )

    context = {
        'form': form,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'title': f'Record Payment for Invoice #{invoice.invoice_number}'
    }

    return render(request, 'billing/payment_form.html', context)

@login_required
def service_list(request):
    """View for listing all services"""
    services = Service.objects.all().order_by('name')

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service {service.name} has been added successfully.')
            return redirect('billing:services')
    else:
        form = ServiceForm()

    context = {
        'services': services,
        'form': form,
        'title': 'Manage Services'
    }

    return render(request, 'billing/service_list.html', context)

@login_required
def add_service(request):
    """Redirect to service_list view which handles both listing and adding"""
    # The request parameter is required by the decorator but not used
    return redirect('billing:services')

@login_required
def edit_service(request, service_id):
    """View for editing a service"""
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f'Service {service.name} has been updated successfully.')
            return redirect('billing:services')
    else:
        form = ServiceForm(instance=service)

    context = {
        'form': form,
        'service': service,
        'title': f'Edit Service: {service.name}'
    }

    return render(request, 'billing/service_form.html', context)

@login_required
def delete_service(request, service_id):
    """View for deleting a service"""
    service = get_object_or_404(Service, id=service_id)

    # Check if service is used in any invoice items
    if InvoiceItem.objects.filter(service=service).exists():
        messages.error(request, f'Cannot delete service {service.name} because it is used in invoices.')
        return redirect('billing:services')

    if request.method == 'POST':
        service.delete()
        messages.success(request, f'Service {service.name} has been deleted.')
        return redirect('billing:services')

    context = {
        'service': service
    }

    return render(request, 'billing/delete_service.html', context)

@login_required
def patient_invoices(request, patient_id):
    """View for displaying invoices for a specific patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    invoices = Invoice.objects.filter(patient=patient).order_by('-created_at')

    # Get total amounts
    total_amount = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    paid_amount = invoices.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    pending_amount = invoices.filter(status__in=['pending', 'partially_paid', 'overdue']).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'patient': patient,
        'invoices': invoices,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
    }

    return render(request, 'billing/patient_invoices.html', context)

@login_required
def admission_invoices(request):
    """View for listing all admissions with their billing status"""
    admissions = Admission.objects.all().order_by('-admission_date')

    for admission in admissions:
        admission.balance_due = admission.billed_amount - admission.amount_paid
        if admission.balance_due <= 0:
            admission.payment_status_display = 'Paid'
            admission.status_badge_class = 'success'
        elif admission.amount_paid > 0:
            admission.payment_status_display = 'Partially Paid'
            admission.status_badge_class = 'warning'
        else:
            admission.payment_status_display = 'Pending'
            admission.status_badge_class = 'danger'

    context = {
        'admissions': admissions,
        'title': 'Admission Invoices'
    }

    return render(request, 'admissions/admission_invoices.html', context)

@login_required
def billing_reports(request):
    """View for billing summary and reporting"""
    # Revenue by month (last 12 months)
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    months = []
    revenue_data = []
    for i in range(11, -1, -1):
        month = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
        next_month = (month + timedelta(days=32)).replace(day=1)
        total = Invoice.objects.filter(
            invoice_date__gte=month,
            invoice_date__lt=next_month,
            status__in=['paid', 'partially_paid']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        months.append(month.strftime('%b %Y'))
        revenue_data.append(float(total))
    # Outstanding balances
    outstanding = Invoice.objects.filter(status__in=['pending', 'partially_paid', 'overdue']).aggregate(total=Sum('total_amount'))['total'] or 0
    # Invoice count by status
    status_counts = Invoice.objects.values('status').annotate(count=Count('id'))
    # Revenue by department (ServiceCategory)
    from billing.models import ServiceCategory
    dept_revenue = (
        InvoiceItem.objects
        .values('service__category__name')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')
    )
    # Revenue by service
    service_revenue = (
        InvoiceItem.objects
        .values('service__name')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')
    )
    # Revenue by provider (created_by)
    provider_revenue = (
        Invoice.objects
        .values('created_by__username')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')
    )
    context = {
        'months': months,
        'revenue_data': revenue_data,
        'outstanding': outstanding,
        'status_counts': status_counts,
        'dept_revenue': dept_revenue,
        'service_revenue': service_revenue,
        'provider_revenue': provider_revenue,
        'page_title': 'Billing Reports',
    }
    return render(request, 'billing/billing_reports.html', context)

@login_required
def export_billing_report_csv(request):
    """Export billing report as CSV (by department, service, provider)"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="billing_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Type', 'Name', 'Total'])
    # Department
    for row in InvoiceItem.objects.values('service__category__name').annotate(total=Sum('total_amount')).order_by('-total'):
        writer.writerow(['Department', row['service__category__name'] or 'Uncategorized', row['total']])
    # Service
    for row in InvoiceItem.objects.values('service__name').annotate(total=Sum('total_amount')).order_by('-total'):
        writer.writerow(['Service', row['service__name'] or 'Custom/Other', row['total']])
    # Provider
    for row in Invoice.objects.values('created_by__username').annotate(total=Sum('total_amount')).order_by('-total'):
        writer.writerow(['Provider', row['created_by__username'] or 'Unknown', row['total']])
    return response

@login_required
def create_invoice_for_prescription(request, prescription_id):
    """Create an invoice for a prescription if not already created."""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    if hasattr(prescription, 'invoice') and prescription.invoice:
        messages.info(request, 'Invoice already exists for this prescription.')
        return redirect('billing:invoice_detail', invoice_id=prescription.invoice.id)

    # You may want to select a Service for dispensing medication
    service = Service.objects.filter(name__icontains='Medication Dispensing').first()
    if not service:
        messages.error(request, 'Medication Dispensing service not found. Please create it in Billing > Services.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Calculate total from prescription items
    items = prescription.items.all()
    subtotal = sum(item.medication.price * item.quantity for item in items)
    tax_amount = (subtotal * service.tax_percentage) / 100
    total = subtotal + tax_amount

    invoice = Invoice.objects.create(
        patient=prescription.patient,
        status='pending',
        total_amount=total,
        subtotal=subtotal,
        tax_amount=tax_amount,
        created_by=request.user,
        prescription=prescription
    )
    # Link invoice to prescription if not already linked
    prescription.invoice = invoice
    prescription.save()

    # Add invoice items
    for item in items:
        InvoiceItem.objects.create(
            invoice=invoice,
            service=service,
            description=f"{item.medication.name} x {item.quantity}",
            quantity=item.quantity,
            unit_price=item.medication.price,
            tax_percentage=service.tax_percentage,
            tax_amount=(item.medication.price * item.quantity * service.tax_percentage) / 100,
            total_amount=(item.medication.price * item.quantity) + ((item.medication.price * item.quantity * service.tax_percentage) / 100)
        )

    messages.success(request, f'Invoice created for prescription #{prescription.id}.')
    return redirect('billing:invoice_detail', invoice_id=invoice.id)


@login_required
def medication_billing_dashboard(request):
    """Dashboard for medication billing management"""
    from pharmacy.models import Prescription
    from pharmacy_billing.models import Invoice as PharmacyInvoice

    # Get prescriptions with pending payments
    pending_prescriptions = Prescription.objects.filter(
        payment_status='unpaid'
    ).select_related('patient', 'doctor').order_by('-prescription_date')

    # Get pharmacy invoices
    pharmacy_invoices = PharmacyInvoice.objects.filter(
        status__in=['pending', 'partially_paid']
    ).select_related('patient', 'prescription').order_by('-invoice_date')

    # Statistics
    total_pending_amount = sum(inv.get_balance() for inv in pharmacy_invoices)
    total_prescriptions = pending_prescriptions.count()
    total_invoices = pharmacy_invoices.count()

    context = {
        'pending_prescriptions': pending_prescriptions[:10],  # Show latest 10
        'pharmacy_invoices': pharmacy_invoices[:10],  # Show latest 10
        'total_pending_amount': total_pending_amount,
        'total_prescriptions': total_prescriptions,
        'total_invoices': total_invoices,
        'title': 'Medication Billing Dashboard'
    }

    return render(request, 'billing/medication_billing_dashboard.html', context)


@login_required
def prescription_billing_detail(request, prescription_id):
    """Detailed view for prescription billing with individual item breakdown"""
    from pharmacy.models import Prescription
    from pharmacy_billing.models import Invoice as PharmacyInvoice, Payment as PharmacyPayment

    prescription = get_object_or_404(Prescription, id=prescription_id)
    prescription_items = prescription.items.all().select_related('medication')

    # Get pricing breakdown
    pricing_breakdown = prescription.get_pricing_breakdown()

    # Get or create pharmacy invoice
    pharmacy_invoice = None
    try:
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        pass

    # Get payments if invoice exists
    payments = []
    if pharmacy_invoice:
        payments = PharmacyPayment.objects.filter(invoice=pharmacy_invoice).order_by('-payment_date')

    # Calculate item-level pricing
    items_with_pricing = []
    for item in prescription_items:
        item_total = item.medication.price * item.quantity
        if pricing_breakdown['is_nhia_patient']:
            patient_pays = item_total * Decimal('0.10')
            nhia_covers = item_total * Decimal('0.90')
        else:
            patient_pays = item_total
            nhia_covers = Decimal('0.00')

        items_with_pricing.append({
            'item': item,
            'total_cost': item_total,
            'patient_pays': patient_pays,
            'nhia_covers': nhia_covers
        })

    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'items_with_pricing': items_with_pricing,
        'pricing_breakdown': pricing_breakdown,
        'pharmacy_invoice': pharmacy_invoice,
        'payments': payments,
        'title': f'Prescription Billing - #{prescription.id}'
    }

    return render(request, 'billing/prescription_billing_detail.html', context)


@login_required
def process_medication_payment(request, prescription_id):
    """Process payment for medication prescription from billing office"""
    from pharmacy.models import Prescription
    from pharmacy_billing.models import Invoice as PharmacyInvoice, Payment as PharmacyPayment
    from pharmacy_billing.utils import create_pharmacy_invoice
    from django.db import transaction

    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Get or create pharmacy invoice
    pharmacy_invoice = None
    try:
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        # Create invoice using the utility function
        total_price = prescription.get_total_prescribed_price()
        pharmacy_invoice = create_pharmacy_invoice(request, prescription, total_price)
        if not pharmacy_invoice:
            messages.error(request, 'Failed to create invoice for this prescription.')
            return redirect('billing:prescription_billing_detail', prescription_id=prescription.id)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')

        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, 'Payment amount must be greater than zero.')
                return redirect('billing:prescription_billing_detail', prescription_id=prescription.id)

            if amount > pharmacy_invoice.get_balance():
                messages.error(request, f'Payment amount cannot exceed the remaining balance of ₦{pharmacy_invoice.get_balance():.2f}.')
                return redirect('billing:prescription_billing_detail', prescription_id=prescription.id)

            with transaction.atomic():
                # Create payment record
                payment = PharmacyPayment.objects.create(
                    invoice=pharmacy_invoice,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    notes=notes,
                    received_by=request.user
                )

                # Update invoice
                pharmacy_invoice.amount_paid += amount
                if pharmacy_invoice.amount_paid >= pharmacy_invoice.total_amount:
                    pharmacy_invoice.status = 'paid'
                    # Mark that this is a manual payment processed by billing staff
                    pharmacy_invoice._manual_payment_processed = True
                    prescription.payment_status = 'paid'
                    prescription.save(update_fields=['payment_status'])
                else:
                    pharmacy_invoice.status = 'partially_paid'

                pharmacy_invoice.save()

                messages.success(request, f'Payment of ₦{amount:.2f} recorded successfully.')
                return redirect('billing:prescription_billing_detail', prescription_id=prescription.id)

        except (ValueError, TypeError):
            messages.error(request, 'Invalid payment amount.')
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')

    return redirect('billing:prescription_billing_detail', prescription_id=prescription.id)

@login_required
def create_invoice_for_admission(request, admission_id):
    """Create an invoice for an admission if not already created."""
    admission = get_object_or_404(Admission, id=admission_id)

    # Check if patient is NHIA - NHIA patients are exempt from admission fees
    is_nhia_patient = hasattr(admission.patient, 'nhia_info') and admission.patient.nhia_info.is_active

    if is_nhia_patient:
        messages.info(request,
            f'Patient {admission.patient.get_full_name()} is an NHIA patient and is exempt from admission fees. '
            'No invoice will be created.'
        )
        return redirect('inpatient:admission_detail', pk=admission.id)

    # Check if an invoice already exists for this admission
    if hasattr(admission, 'invoices') and admission.invoices.exists():
        messages.info(request, 'Invoice already exists for this admission.')
        return redirect('billing:admission_payment', admission_id=admission.id)

    # Calculate total from admission cost
    total_cost = admission.get_total_cost()

    # You may want to select a Service for admission charges
    # For simplicity, let's assume a generic 'Admission Charges' service exists
    service = Service.objects.filter(name__icontains='Admission Charges').first()
    if not service:
        messages.error(request, 'Admission Charges service not found. Please create it in Billing > Services.')
        return redirect('inpatient:admission_detail', admission_id=admission.id)

    # Create the invoice
    invoice = Invoice.objects.create(
        patient=admission.patient,
        status='pending',
        total_amount=total_cost,
        subtotal=total_cost, # Assuming no separate tax/discount for simplicity here
        tax_amount=0,
        discount_amount=0,
        created_by=request.user,
        admission=admission, # Link the invoice to the admission
        source_app='inpatient'
    )

    # Add invoice item for admission charges
    InvoiceItem.objects.create(
        invoice=invoice,
        service=service,
        description=f"Admission Charges for {admission.get_duration()} days",
        quantity=1,
        unit_price=total_cost,
        tax_percentage=0,
        tax_amount=0,
        discount_amount=0,
        total_amount=total_cost
    )

    messages.success(request, f'Invoice created for admission #{admission.id}.')
    return redirect('billing:admission_payment', admission_id=admission.id)


@login_required
def admission_payment(request, admission_id):
    """Enhanced view for processing admission payments from billing office or patient wallet"""
    from inpatient.models import Admission
    from patients.models import PatientWallet
    from .forms import AdmissionPaymentForm

    admission = get_object_or_404(Admission, id=admission_id)

    # Check if patient is NHIA - NHIA patients are exempt from admission fees
    is_nhia_patient = hasattr(admission.patient, 'nhia_info') and admission.patient.nhia_info.is_active

    if is_nhia_patient:
        messages.info(request,
            f'Patient {admission.patient.get_full_name()} is an NHIA patient and is exempt from admission fees. '
            'No payment is required.'
        )
        return redirect('inpatient:admission_detail', pk=admission.id)

    # Get or create invoice for this admission
    invoice = None
    if hasattr(admission, 'invoices') and admission.invoices.exists():
        invoice = admission.invoices.first()
    else:
        # Create invoice if it doesn't exist
        from billing.models import Service
        try:
            service = Service.objects.get(name__iexact="Admission")
        except Service.DoesNotExist:
            messages.error(request, 'Admission service not found. Please contact administrator.')
            return redirect('inpatient:admission_detail', pk=admission.id)

        total_cost = service.price
        invoice = Invoice.objects.create(
            patient=admission.patient,
            status='pending',
            total_amount=total_cost,
            subtotal=total_cost,
            tax_amount=0,
            discount_amount=0,
            created_by=request.user,
            admission=admission,
            source_app='inpatient'
        )

        InvoiceItem.objects.create(
            invoice=invoice,
            service=service,
            description=f"Admission Charges",
            quantity=1,
            unit_price=total_cost,
            tax_percentage=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=total_cost
        )

    # Get patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=admission.patient)
    except PatientWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        patient_wallet = PatientWallet.objects.create(
            patient=admission.patient,
            balance=0
        )

    remaining_amount = invoice.get_balance()

    if remaining_amount <= 0:
        messages.info(request, 'This admission has already been fully paid.')
        return redirect('inpatient:admission_detail', pk=admission.id)

    if request.method == 'POST':
        form = AdmissionPaymentForm(
            request.POST,
            invoice=invoice,
            patient_wallet=patient_wallet
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.received_by = request.user

                    payment_source = form.cleaned_data['payment_source']

                    if payment_source == 'patient_wallet':
                        # Force wallet payment method
                        payment.payment_method = 'wallet'

                    payment.save()

                    # Audit log
                    log_audit_action(
                        request.user,
                        'create',
                        payment,
                        f"Recorded {payment_source} payment of ₦{payment.amount:.2f} for admission {admission.id}"
                    )

                    # Notification
                    notification_user = request.user
                    if hasattr(admission.patient, 'primary_doctor') and admission.patient.primary_doctor:
                        notification_user = admission.patient.primary_doctor
                    elif hasattr(admission, 'attending_doctor') and admission.attending_doctor:
                        notification_user = admission.attending_doctor

                    InternalNotification.objects.create(
                        user=notification_user,
                        message=f"Payment of ₦{payment.amount:.2f} recorded for admission {admission.id} via {payment_source}"
                    )

                    messages.success(request, f'Payment of ₦{payment.amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')
                    return redirect('inpatient:admission_detail', pk=admission.id)

            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
    else:
        form = AdmissionPaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet,
            initial={
                'amount': remaining_amount,
                'payment_date': timezone.now().date(),
                'payment_method': 'cash'
            }
        )

    context = {
        'form': form,
        'admission': admission,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'title': f'Payment for Admission #{admission.id}'
    }

    return render(request, 'billing/admission_payment.html', context)
