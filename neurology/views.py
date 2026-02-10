from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import NeurologyRecord, NeurologyService, NeurologyTest, NeurologyClinicalNote
from .forms import NeurologyRecordForm, NeurologyRecordSearchForm, NeurologyServiceForm, NeurologyTestForm, NeurologyClinicalNoteForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from pharmacy.models import Prescription, PrescriptionItem
from billing.models import Invoice, InvoiceItem
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
import json


@login_required
@department_access_required('Neurology')
def neurology_dashboard(request):
    """Enhanced Dashboard for Neurology department with charts and metrics"""
    from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
    from datetime import timedelta

    user_department = get_user_department(request.user)

    # Superusers can access all departments without assignment
    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    # For superusers without department, pass None (function should handle it)
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=NeurologyRecord,
        record_queryset=NeurologyRecord.objects.all(),
        priority_field=None,  # Neurology records don't have priority field
        status_field='treatment_status',
        completed_status='completed'
    )

    # Add neurology-specific statistics
    today = timezone.now().date()

    # Treatment status statistics
    planned_treatments = NeurologyRecord.objects.filter(treatment_status='planned').count()
    in_progress_treatments = NeurologyRecord.objects.filter(treatment_status='in_progress').count()
    completed_treatments = NeurologyRecord.objects.filter(treatment_status='completed').count()
    completed_today = NeurologyRecord.objects.filter(
        treatment_status='completed',
        updated_at__date=today
    ).count()

    # Appointments today
    appointments_today = NeurologyRecord.objects.filter(
        appointment_date__date=today
    ).count()

    # Follow-ups due this week
    week_end = today + timedelta(days=7)
    followups_due = NeurologyRecord.objects.filter(
        next_appointment_date__date__gte=today,
        next_appointment_date__date__lte=week_end
    ).count()

    # Common conditions (top 5)
    condition_data = NeurologyRecord.objects.filter(
        condition_type__isnull=False
    ).exclude(condition_type='').values('condition_type').annotate(count=Count('id')).order_by('-count')[:5]
    condition_labels = [dict(NeurologyRecord.CONDITION_TYPE_CHOICES).get(item['condition_type'], item['condition_type']) for item in condition_data]  # type: ignore
    condition_counts = [item['count'] for item in condition_data]

    # Emergency neurology cases (records created today with urgent notes)
    emergency_cases = NeurologyRecord.objects.filter(
        created_at__date=today,
        diagnosis__icontains='emergency'
    ).count() + NeurologyRecord.objects.filter(
        created_at__date=today,
        diagnosis__icontains='urgent'
    ).count()

    # Get recent records with patient info
    recent_records = NeurologyRecord.objects.select_related('patient', 'service', 'neurologist').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Get chart data from build_enhanced_dashboard_context
    # Ensure we have the chart data needed by template
    if 'daily_trend' not in context:
        context['daily_trend'] = {
            'labels': json.dumps(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
            'data': json.dumps([0, 0, 0, 0, 0, 0, 0])
        }
    
    if 'status_distribution' not in context:
        context['status_distribution'] = {
            'labels': json.dumps(['Planned', 'In Progress', 'Completed']),
            'data': json.dumps([planned_treatments, in_progress_treatments, completed_treatments]),
            'colors': json.dumps(['#6c757d', '#17a2b8', '#28a745'])
        }

    # Add to context
    context.update({
        'total_records': NeurologyRecord.objects.count(),
        'records_today': NeurologyRecord.objects.filter(created_at__date=today).count(),
        'records_this_week': NeurologyRecord.objects.filter(created_at__date__gte=today - timedelta(days=7)).count(),
        'pending_treatments': planned_treatments,
        'in_progress_treatments': in_progress_treatments,
        'completed_treatments': completed_treatments,
        'completed_today': completed_today,
        'appointments_today': appointments_today,
        'followups_due': followups_due,
        'emergency_cases': emergency_cases,
        'condition_labels': json.dumps(condition_labels),
        'condition_counts': json.dumps(condition_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
        'pending_referrals': categorized_referrals['ready_to_accept'] + categorized_referrals['awaiting_authorization'],
        'pending_referrals_count': len(categorized_referrals['ready_to_accept'] + categorized_referrals['awaiting_authorization']),
        'pending_authorizations': len(categorized_referrals['awaiting_authorization']),
    })

    return render(request, 'neurology/dashboard.html', context)


@login_required
def neurology_records(request):
    """View to list all neurology records with search and pagination"""
    records = NeurologyRecord.objects.select_related('patient', 'service', 'neurologist').all()
    
    # Add search functionality
    search_form = NeurologyRecordSearchForm(request.GET)
    search_query = request.GET.get('search', '')
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search', search_query)
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        condition_type = search_form.cleaned_data.get('condition_type')
        treatment_status = search_form.cleaned_data.get('treatment_status')
        
        if search_query:
            records = records.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(diagnosis__icontains=search_query) |
                Q(treatment_procedure__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(created_at__date__gte=date_from)
            
        if date_to:
            records = records.filter(created_at__date__lte=date_to)
            
        if condition_type:
            records = records.filter(condition_type=condition_type)
            
        if treatment_status:
            records = records.filter(treatment_status=treatment_status)
    
    # Pagination
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': records.count(),
    }
    return render(request, 'neurology/neurology_records.html', context)

@login_required
def create_neurology_record(request):
    """View to create a new neurology record"""
    if request.method == 'POST':
        form = NeurologyRecordForm(request.POST)
        if form.is_valid():
            # Extract patient from form field directly
            patient = form.cleaned_data.get('patient')

            # **AUTHORIZATION CHECK**: Check if patient has pending referrals requiring authorization
            if patient:
                from consultations.models import Referral
                # Get user's department
                user_department = None
                if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.department:
                    user_department = request.user.profile.department

                if user_department:
                    # Check for unauthorized referrals to this department
                    unauthorized_referrals = Referral.objects.filter(
                        patient=patient,
                        referred_to_department=user_department,
                        status='pending',
                        requires_authorization=True,
                        authorization_status__in=['required', 'pending']
                    )

                    if unauthorized_referrals.exists():
                        referral = unauthorized_referrals.first()
                        messages.error(
                            request,
                            f"Cannot create neurology record for {patient.get_full_name()}. "
                            f"This patient has a pending referral (ID: {referral.id}) that requires desk office authorization. "
                            f"Please wait for authorization before proceeding with treatment."
                        )
                        return redirect('neurology:create_neurology_record')

            # Set default values for created_at and updated_at
            record = form.save(commit=False)
            if not record.created_at:
                record.created_at = timezone.now()
            if not record.updated_at:
                record.updated_at = timezone.now()
            record.save()
            messages.success(request, 'Neurology record created successfully.')
            return redirect('neurology:neurology_record_detail', record_id=record.id)
    else:
        form = NeurologyRecordForm()

    context = {
        'form': form,
        'title': 'Create Neurology Record',
        'all_patients': Patient.objects.all().order_by('first_name', 'last_name'),
    }
    return render(request, 'neurology/neurology_record_form.html', context)

@login_required
def neurology_record_detail(request, record_id):
    """View to display details of a specific neurology record"""
    record = get_object_or_404(NeurologyRecord.objects.select_related('patient', 'service', 'neurologist'), id=record_id)

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

    # Get tests for this record
    tests = NeurologyTest.objects.filter(neurology_record=record).order_by('-performed_at')

    # Get clinical notes for this record
    clinical_notes = NeurologyClinicalNote.objects.filter(neurology_record=record).select_related('created_by').order_by('-created_at')

    # **NHIA AUTHORIZATION CHECK**
    from core.models import InternalNotification
    
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    authorization_message = None
    authorization_amount = None
    has_pending_request = False

    # Check for existing pending authorization request
    if is_nhia_patient and requires_authorization:
        from django.db.models import Q
        has_pending_request = InternalNotification.objects.filter(
            Q(message__icontains=f"Patient: {record.patient.get_full_name()} (ID: {record.patient.patient_id})") &
            Q(message__icontains="Module: neurology") &
            Q(is_read=False)
        ).exists()

    if is_nhia_patient:
        if record.authorization_code:
            authorization_message = f"Authorized - Code: {record.authorization_code}"
            # Calculate authorization amount based on service price
            if record.service:
                authorization_amount = record.service.price
            elif hasattr(record, 'get_service_price'):
                authorization_amount = record.get_service_price
        else:
            authorization_message = "NHIA Authorization Required"
            messages.warning(
                request,
                f"This is an NHIA patient. An authorization code from desk office is required before proceeding with treatment or billing. "
                f"Please contact the desk office to obtain authorization for neurology services."
            )

    context = {
        'record': record,
        'prescriptions': prescriptions,
        'tests': tests,
        'clinical_notes': clinical_notes,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_amount': authorization_amount,
        'has_pending_request': has_pending_request,
    }
    return render(request, 'neurology/neurology_record_detail.html', context)

@login_required
def edit_neurology_record(request, record_id):
    """View to edit an existing neurology record"""
    record = get_object_or_404(NeurologyRecord, id=record_id)

    if request.method == 'POST':
        form = NeurologyRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Neurology record updated successfully.')
            return redirect('neurology:neurology_record_detail', record_id=record.id)
    else:
        form = NeurologyRecordForm(instance=record)

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
                message__contains="Neurology"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for neurology services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit Neurology Record',
        'all_patients': Patient.objects.all().order_by('first_name', 'last_name'),
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'neurology/neurology_record_form.html', context)

@login_required
def delete_neurology_record(request, record_id):
    """View to delete a neurology record"""
    record = get_object_or_404(NeurologyRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Neurology record deleted successfully.')
        return redirect('neurology:neurology_records')
    
    context = {
        'record': record
    }
    return render(request, 'neurology/neurology_record_confirm_delete.html', context)

@login_required
def search_neurology_patients(request):
    """AJAX view for searching patients in neurology module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_neurology(request, record_id):
    """Create a prescription for a neurology patient"""
    record = get_object_or_404(NeurologyRecord, id=record_id)
    
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
                    return redirect('neurology:neurology_record_detail', record_id=record.pk)
                    
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
    return render(request, 'neurology/create_prescription.html', context)

@login_required
def neurology_services(request):
    """View to list and manage neurology services"""
    services = NeurologyService.objects.all().order_by('name')
    
    if request.method == 'POST':
        form = NeurologyServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Neurology service created successfully.')
            return redirect('neurology:neurology_services')
    else:
        form = NeurologyServiceForm()
    
    context = {
        'services': services,
        'form': form,
    }
    return render(request, 'neurology/neurology_services.html', context)

@login_required
def edit_neurology_service(request, service_id):
    """View to edit a neurology service"""
    service = get_object_or_404(NeurologyService, id=service_id)
    
    if request.method == 'POST':
        form = NeurologyServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Neurology service updated successfully.')
            return redirect('neurology:neurology_services')
    else:
        form = NeurologyServiceForm(instance=service)
    
    context = {
        'form': form,
        'service': service,
        'title': 'Edit Neurology Service'
    }
    return render(request, 'neurology/neurology_service_form.html', context)

@login_required
def delete_neurology_service(request, service_id):
    """View to delete a neurology service"""
    service = get_object_or_404(NeurologyService, id=service_id)
    
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Neurology service deleted successfully.')
        return redirect('neurology:neurology_services')
    
    context = {
        'service': service
    }
    return render(request, 'neurology/neurology_service_confirm_delete.html', context)

@login_required
def add_test_to_neurology_record(request, record_id):
    """Add a test to a neurology record"""
    record = get_object_or_404(NeurologyRecord, id=record_id)
    
    if request.method == 'POST':
        form = NeurologyTestForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.neurology_record = record
            test.performed_by = request.user
            test.save()
            messages.success(request, 'Test added successfully.')
            return redirect('neurology:neurology_record_detail', record_id=record.pk)
    else:
        form = NeurologyTestForm()
    
    context = {
        'form': form,
        'record': record,
        'title': 'Add Test'
    }
    return render(request, 'neurology/add_test.html', context)

@login_required
def delete_test(request, test_id):
    """Delete a neurology test"""
    test = get_object_or_404(NeurologyTest, id=test_id)
    record_id = test.neurology_record.pk
    
    if request.method == 'POST':
        test.delete()
        messages.success(request, 'Test deleted successfully.')
        return redirect('neurology:neurology_record_detail', record_id=record_id)
    
    context = {
        'test': test
    }
    return render(request, 'neurology/test_confirm_delete.html', context)

@login_required
def generate_invoice_for_neurology(request, record_id):
    """Generate an invoice for a neurology record"""
    record = get_object_or_404(NeurologyRecord, id=record_id)

    # Check if invoice already exists
    if record.invoice:
        messages.info(request, 'An invoice already exists for this neurology record.')
        return redirect('neurology:neurology_record_detail', record_id=record.pk)

    # **NHIA AUTHORIZATION CHECK**: Prevent invoice generation without authorization
    if record.patient.patient_type == 'nhia':
        if not record.authorization_code:
            messages.error(
                request,
                f"Cannot generate invoice for NHIA patient {record.patient.get_full_name()}. "
                f"An authorization code from the desk office is required before generating an invoice. "
                f"Please contact the desk office to obtain the authorization code."
            )
            return redirect('neurology:neurology_record_detail', record_id=record.pk)

        # Check if authorization is valid
        if not record.authorization_code.is_valid():
            messages.error(
                request,
                f"Cannot generate invoice. The authorization code for this neurology record is expired or invalid. "
                f"Please contact the desk office for a new authorization code."
            )
            return redirect('neurology:neurology_record_detail', record_id=record.pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Calculate amounts
                service_price = record.get_service_price()
                subtotal = service_price
                tax_amount = Decimal('0.00')  # No tax for neurology services
                discount_amount = Decimal('0.00')
                total_amount = subtotal + tax_amount - discount_amount

                # Set due date (7 days from now)
                due_date = timezone.now().date() + timezone.timedelta(days=7)

                # Create the invoice
                invoice = Invoice.objects.create(
                    patient=record.patient,
                    created_by=request.user,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    discount_amount=discount_amount,
                    total_amount=total_amount,
                    due_date=due_date,
                    status='pending',
                    source_app='other'  # Neurology doesn't have a specific source_app choice
                )

                # Link invoice to neurology record
                record.invoice = invoice  # type: ignore
                record.save()

                messages.success(request, f'Invoice #{invoice.invoice_number} generated successfully.')
                return redirect('neurology:neurology_record_detail', record_id=record.pk)

        except Exception as e:
            messages.error(request, f'Error generating invoice: {str(e)}')
    
    context = {
        'record': record,
        'title': 'Generate Invoice'
    }
    return render(request, 'neurology/generate_invoice.html', context)


# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to a neurology record"""
    record = get_object_or_404(NeurologyRecord, id=record_id)

    if request.method == 'POST':
        form = NeurologyClinicalNoteForm(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.neurology_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('neurology:neurology_record_detail', record_id=record.pk)
    else:
        form = NeurologyClinicalNoteForm()

    context = {
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }
    return render(request, 'neurology/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404(NeurologyClinicalNote, id=note_id)
    record = note.neurology_record

    if request.method == 'POST':
        form = NeurologyClinicalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('neurology:neurology_record_detail', record_id=record.pk)
    else:
        form = NeurologyClinicalNoteForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }
    return render(request, 'neurology/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404(NeurologyClinicalNote, id=note_id)
    record_id = note.neurology_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('neurology:neurology_record_detail', record_id=record_id)

    context = {
        'note': note
    }
    return render(request, 'neurology/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404(NeurologyClinicalNote, id=note_id)

    context = {
        'note': note,
        'record': note.neurology_record
    }
    return render(request, 'neurology/clinical_note_detail.html', context)
