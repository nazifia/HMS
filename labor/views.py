from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from decimal import Decimal
from .models import LaborRecord, LaborClinicalNote
from .forms import LaborRecordForm, LaborRecordSearchForm, LaborClinicalNoteForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from pharmacy.models import Prescription, PrescriptionItem, MedicalPack, PackOrder
from pharmacy.forms import PackOrderForm
from billing.models import Invoice, InvoiceItem, Service, ServiceCategory
from core.decorators import department_access_required
from core.department_dashboard_utils import (
    get_user_department,
    build_department_dashboard_context,
    build_enhanced_dashboard_context,
    categorize_referrals,
    get_daily_trend_data,
    get_status_distribution,
    calculate_completion_rate,
    get_active_staff
)
from django.utils import timezone
import json


@login_required
@department_access_required('Labor')
def labor_dashboard(request):
    """Enhanced Dashboard for Labor department with charts and delivery metrics"""
    from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
    from datetime import timedelta

    user_department = get_user_department(request.user)

    # Superusers can access all departments without assignment
    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=LaborRecord,
        record_queryset=LaborRecord.objects.all(),
        priority_field=None,
        status_field=None,
        completed_status=None
    )

    # Labor-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Deliveries today
    deliveries_today = LaborRecord.objects.filter(
        visit_date__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()

    # Follow-ups due this week
    followups_due = LaborRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Mode of delivery distribution
    svd_count = LaborRecord.objects.filter(mode_of_delivery__icontains='SVD').count()
    csection_count = LaborRecord.objects.filter(mode_of_delivery__icontains='C-Section').count()
    assisted_count = LaborRecord.objects.filter(mode_of_delivery__icontains='Assisted').count()
    vbac_count = LaborRecord.objects.filter(mode_of_delivery__icontains='VBAC').count()

    # Cervical dilation tracking (patients in active labor, dilation < 10cm)
    active_labor = LaborRecord.objects.filter(
        cervical_dilation__lt=10,
        cervical_dilation__gte=4,
        visit_date__gte=today - timedelta(days=1)
    ).count()

    # Ruptured membranes count (today)
    ruptured_membranes = LaborRecord.objects.filter(
        rupture_of_membranes=True,
        visit_date__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()

    # Common diagnoses (top 5)
    diagnosis_data = LaborRecord.objects.filter(
        diagnosis__isnull=False
    ).exclude(diagnosis='').values('diagnosis').annotate(count=Count('id')).order_by('-count')[:5]
    diagnosis_labels = [item['diagnosis'][:30] for item in diagnosis_data]
    diagnosis_counts = [item['count'] for item in diagnosis_data]

    # Delivery mode distribution for chart
    delivery_labels = ['SVD', 'C-Section', 'Assisted', 'VBAC']
    delivery_counts = [svd_count, csection_count, assisted_count, vbac_count]

    # Get recent records with patient info
    recent_records = LaborRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'deliveries_today': deliveries_today,
        'followups_due': followups_due,
        'svd_count': svd_count,
        'csection_count': csection_count,
        'assisted_count': assisted_count,
        'active_labor': active_labor,
        'ruptured_membranes': ruptured_membranes,
        'diagnosis_labels': json.dumps(diagnosis_labels),
        'diagnosis_counts': json.dumps(diagnosis_counts),
        'delivery_labels': json.dumps(delivery_labels),
        'delivery_counts': json.dumps(delivery_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'labor/dashboard.html', context)


@login_required
def labor_records_list(request):
    """View to list all labor records with search and pagination"""
    records = LaborRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = LaborRecordSearchForm(request.GET)
    search_query = None
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if search_query:
            records = records.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(diagnosis__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(visit_date__gte=date_from)
            
        if date_to:
            records = records.filter(visit_date__lte=date_to)
    
    # Get counts for stats
    total_records = records.count()
    follow_up_count = records.filter(follow_up_required=True).count()
    
    # Pagination
    paginator = Paginator(records, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': total_records,
        'follow_up_count': follow_up_count,
    }
    return render(request, 'labor/labor_records_list.html', context)

@login_required
def create_labor_record(request):
    """View to create a new labor record"""
    if request.method == 'POST':
        form = LaborRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Labor record created successfully.')
            return redirect('labor:labor_record_detail', record_id=record.id)
    else:
        form = LaborRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Labor Record'
    }
    return render(request, 'labor/labor_record_form.html', context)

@login_required
def labor_record_detail(request, record_id):
    """View to display details of a specific labor record"""
    record = get_object_or_404(
        LaborRecord.objects.select_related('patient', 'doctor'),
        id=record_id
    )

    # **NHIA AUTHORIZATION CHECK**
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    authorization_message = None
    authorization_request_pending = False

    if is_nhia_patient:
        if record.authorization_code:
            authorization_message = f"Authorized - Code: {record.authorization_code}"
        else:
            authorization_message = "NHIA Authorization Required"

            # Check for pending authorization request
            from core.models import InternalNotification
            authorization_request_pending = InternalNotification.objects.filter(
                message__contains=f"Record ID: {record.id}",
                is_read=False
            ).filter(
                message__contains="Labor"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for labor services."
                )

    context = {
        'record': record,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'labor/labor_record_detail.html', context)

@login_required
def edit_labor_record(request, record_id):
    """View to edit an existing labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)

    if request.method == 'POST':
        form = LaborRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Labor record updated successfully.')
            return redirect('labor:labor_record_detail', record_id=record.id)
    else:
        form = LaborRecordForm(instance=record)

    # **NHIA AUTHORIZATION CHECK**
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    authorization_message = None
    authorization_request_pending = False

    if is_nhia_patient:
        if record.authorization_code:
            authorization_message = f"Authorized - Code: {record.authorization_code}"
        else:
            authorization_message = "NHIA Authorization Required"

            # Check for pending authorization request
            from core.models import InternalNotification
            authorization_request_pending = InternalNotification.objects.filter(
                message__contains=f"Record ID: {record.id}",
                is_read=False
            ).filter(
                message__contains="Labor"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for labor services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit Labor Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'labor/labor_record_form.html', context)

@login_required
def delete_labor_record(request, record_id):
    """View to delete a labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Labor record deleted successfully.')
        return redirect('labor:labor_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'labor/labor_record_confirm_delete.html', context)

@login_required
def search_labor_patients(request):
    """AJAX view for searching patients in Labor module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_labor(request, record_id):
    """Create a prescription for a labor patient"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        prescription_form = MedicalModulePrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        
        if prescription_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Create the prescription
                    diagnosis = prescription_form.cleaned_data['diagnosis']
                    notes = prescription_form.cleaned_data['notes']
                    prescription_type = prescription_form.cleaned_data['prescription_type']
                    
                    prescription = Prescription.objects.create(
                        patient=record.patient,
                        doctor=request.user,
                        diagnosis=diagnosis,
                        notes=notes,
                        prescription_type=prescription_type
                    )
                    
                    # Add prescription items
                    for form in formset.cleaned_data:
                        if form and not form.get('DELETE', False):
                            medication = form['medication']
                            dosage = form['dosage']
                            frequency = form['frequency']
                            duration = form['duration']
                            quantity = form['quantity']
                            instructions = form.get('instructions', '')
                            
                            PrescriptionItem.objects.create(
                                prescription=prescription,
                                medication=medication,
                                dosage=dosage,
                                frequency=frequency,
                                duration=duration,
                                quantity=quantity,
                                instructions=instructions
                            )
                    
                    messages.success(request, 'Prescription created successfully!')
                    return redirect('labor:labor_record_detail', record_id=record.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating prescription: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        prescription_form = MedicalModulePrescriptionForm()
        formset = PrescriptionItemFormSet()
    
    context = {
        'record': record,
        'prescription_form': prescription_form,
        'formset': formset,
        'title': 'Create Prescription'
    }
    return render(request, 'labor/create_prescription.html', context)


@login_required
def order_medical_pack_for_labor(request, record_id):
    """Order a medical pack for a specific labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    # Get labor-specific packs
    available_packs = MedicalPack.objects.filter(
        is_active=True,
        pack_type='labor'
    )
    
    # Filter by labor type if available
    if record.mode_of_delivery:
        delivery_type_packs = available_packs.filter(
            labor_type__icontains=record.mode_of_delivery.lower()
        )
        if delivery_type_packs.exists():
            available_packs = delivery_type_packs
    
    if request.method == 'POST':
        form = PackOrderForm(request.POST, labor_record=record, preselected_patient=record.patient)

        if form.is_valid():
            try:
                with transaction.atomic():
                    pack_order = form.save(commit=False)
                    pack_order.patient = record.patient
                    pack_order.labor_record = record
                    pack_order.ordered_by = request.user
                    
                    # Set scheduled date to labor visit date if not provided
                    if not pack_order.scheduled_date:
                        pack_order.scheduled_date = record.visit_date
                    
                    pack_order.save()
                    
                    # Automatically create prescription from pack items
                    try:
                        prescription = pack_order.create_prescription()
                        
                        # Add pack costs to patient billing
                        _add_pack_to_patient_billing(record.patient, pack_order, 'labor')
                        
                        messages.success(
                            request, 
                            f'Medical pack "{pack_order.pack.name}" ordered successfully for labor record. '
                            f'Prescription #{prescription.id} has been automatically created with {prescription.items.count()} medications. '
                            f'Pack cost (₦{pack_order.pack.get_total_cost():.2f}) has been added to patient billing.'
                        )
                    except Exception as e:
                        # Pack order was created but prescription failed
                        messages.warning(
                            request,
                            f'Medical pack "{pack_order.pack.name}" ordered successfully, but prescription creation failed: {str(e)}. '
                            f'Please create the prescription manually if needed.'
                        )
                    return redirect('labor:labor_record_detail', record_id=record.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating pack order: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        # Pre-populate form with labor context
        initial_data = {
            'scheduled_date': record.visit_date,
            'order_notes': f'Pack order for labor record: {record.diagnosis or "Labor/Delivery"}'
        }
        form = PackOrderForm(initial=initial_data, labor_record=record, preselected_patient=record.patient)
        
        # Filter pack choices to labor-specific packs
        form.fields['pack'].queryset = available_packs
        form.fields['patient'].initial = record.patient
        form.fields['patient'].widget.attrs['readonly'] = True
    
    context = {
        'record': record,
        'form': form,
        'available_packs': available_packs,
        'page_title': 'Order Medical Pack for Labor',
        'pack': None  # Will be set if pack_id is in GET params
    }
    
    # Handle pack preview
    pack_id = request.GET.get('pack_id')
    if pack_id:
        try:
            pack = get_object_or_404(MedicalPack, id=pack_id, is_active=True)
            context['pack'] = pack
            context['form'].fields['pack'].initial = pack
        except:
            pass
    
    return render(request, 'labor/order_medical_pack.html', context)


def _add_pack_to_patient_billing(patient, pack_order, source_context='general'):
    """Helper function to add pack costs to patient billing"""
    from django.utils import timezone
    
    # Create or get invoice for patient
    invoice, created = Invoice.objects.get_or_create(
        patient=patient,
        status='pending',
        source_app='pharmacy',  # Using pharmacy as the source for pack orders
        defaults={
            'invoice_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=7),
            'subtotal': Decimal('0.00'),
            'tax_amount': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'created_by': pack_order.ordered_by,
        }
    )
    
    # Create or get medical pack service category
    pack_service_category, _ = ServiceCategory.objects.get_or_create(
        name="Medical Packs",
        defaults={'description': 'Pre-packaged medical supplies and medications'}
    )
    
    # Create or get service for this specific pack
    service, _ = Service.objects.get_or_create(
        name=f"Medical Pack: {pack_order.pack.name}",
        category=pack_service_category,
        defaults={
            'price': pack_order.pack.get_total_cost(),
            'description': f"Medical pack for {pack_order.pack.get_pack_type_display()}: {pack_order.pack.name}",
            'tax_percentage': Decimal('0.00')  # Assuming no tax on medical packs
        }
    )
    
    # Add invoice item for the pack
    pack_cost = pack_order.pack.get_total_cost()
    invoice_item = InvoiceItem.objects.create(
        invoice=invoice,
        service=service,
        description=f"Medical Pack: {pack_order.pack.name} (Order #{pack_order.id}) - {source_context.title()}",
        quantity=1,
        unit_price=pack_cost,
        tax_percentage=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        total_amount=pack_cost
    )
    
    # Update invoice totals
    from django.db import models
    invoice.subtotal = invoice.items.aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0.00')
    invoice.tax_amount = invoice.items.aggregate(
        total=models.Sum('tax_amount')
    )['total'] or Decimal('0.00')
    invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount_amount
    invoice.save()
    
    return invoice_item

# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to a labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)

    if request.method == 'POST':
        form = LaborClinicalNoteForm(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.labor_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('labor:record_detail', record_id=record.pk)
    else:
        form = LaborClinicalNoteForm()

    context = {
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }
    return render(request, 'labor/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404(LaborClinicalNote, id=note_id)
    record = note.labor_record

    if request.method == 'POST':
        form = LaborClinicalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('labor:record_detail', record_id=record.pk)
    else:
        form = LaborClinicalNoteForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }
    return render(request, 'labor/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404(LaborClinicalNote, id=note_id)
    record_id = note.labor_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('labor:record_detail', record_id=record_id)

    context = {
        'note': note
    }
    return render(request, 'labor/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404(LaborClinicalNote, id=note_id)

    context = {
        'note': note,
        'record': note.labor_record
    }
    return render(request, 'labor/clinical_note_detail.html', context)
