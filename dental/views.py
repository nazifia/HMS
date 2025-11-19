from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from .models import DentalRecord, DentalService, DentalXRay
from .forms import DentalRecordForm, DentalRecordSearchForm, DentalServiceForm, DentalXRayForm
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
@department_access_required('Dental')
def dental_dashboard(request):
    """Enhanced Dashboard for Dental department with charts and metrics"""
    from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=DentalRecord,
        record_queryset=DentalRecord.objects.all(),
        priority_field=None,  # Dental records don't have priority field
        status_field='treatment_status',
        completed_status='completed'
    )

    # Add dental-specific statistics
    today = timezone.now().date()

    # Treatment status statistics
    planned_treatments = DentalRecord.objects.filter(treatment_status='planned').count()
    in_progress_treatments = DentalRecord.objects.filter(treatment_status='in_progress').count()
    completed_treatments = DentalRecord.objects.filter(treatment_status='completed').count()
    completed_today = DentalRecord.objects.filter(
        treatment_status='completed',
        updated_at__date=today
    ).count()

    # Appointments today
    appointments_today = DentalRecord.objects.filter(
        appointment_date__date=today
    ).count()

    # Follow-ups due this week
    week_end = today + timedelta(days=7)
    followups_due = DentalRecord.objects.filter(
        next_appointment_date__date__gte=today,
        next_appointment_date__date__lte=week_end
    ).count()

    # Common procedures (top 5)
    procedure_data = DentalRecord.objects.filter(
        service__isnull=False
    ).values('service__name').annotate(count=Count('id')).order_by('-count')[:5]
    procedure_labels = [item['service__name'] for item in procedure_data]
    procedure_counts = [item['count'] for item in procedure_data]

    # Emergency dental cases (records created today with urgent notes)
    emergency_cases = DentalRecord.objects.filter(
        created_at__date=today,
        diagnosis__icontains='emergency'
    ).count() + DentalRecord.objects.filter(
        created_at__date=today,
        diagnosis__icontains='pain'
    ).count()

    # Get recent records with patient info
    recent_records = DentalRecord.objects.select_related('patient', 'service', 'dentist').order_by('-created_at')[:10]

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
        'total_records': DentalRecord.objects.count(),
        'records_today': DentalRecord.objects.filter(created_at__date=today).count(),
        'records_this_week': DentalRecord.objects.filter(created_at__date__gte=today - timedelta(days=7)).count(),
        'pending_treatments': planned_treatments,
        'in_progress_treatments': in_progress_treatments,
        'completed_treatments': completed_treatments,
        'completed_today': completed_today,
        'appointments_today': appointments_today,
        'followups_due': followups_due,
        'emergency_cases': emergency_cases,
        'procedure_labels': json.dumps(procedure_labels),
        'procedure_counts': json.dumps(procedure_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
        'pending_referrals': categorized_referrals['ready_to_accept'] + categorized_referrals['awaiting_authorization'],
        'pending_referrals_count': len(categorized_referrals['ready_to_accept'] + categorized_referrals['awaiting_authorization']),
        'pending_authorizations': len(categorized_referrals['awaiting_authorization']),
    })

    return render(request, 'dental/dashboard.html', context)


@login_required
def dental_records(request):
    """View to list all dental records with search and pagination"""
    records = DentalRecord.objects.select_related('patient', 'service', 'dentist').all()
    
    # Add search functionality
    search_form = DentalRecordSearchForm(request.GET)
    search_query = request.GET.get('search', '')
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search', search_query)
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        service = search_form.cleaned_data.get('service')
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
            
        if service:
            records = records.filter(service=service)
            
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
    return render(request, 'dental/dental_records.html', context)

@login_required
def create_dental_record(request):
    """View to create a new dental record"""
    if request.method == 'POST':
        form = DentalRecordForm(request.POST)
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
                            f"Cannot create dental record for {patient.get_full_name()}. "
                            f"This patient has a pending referral (ID: {referral.id}) that requires desk office authorization. "
                            f"Please wait for authorization before proceeding with treatment."
                        )
                        return redirect('dental:create_dental_record')

            # Set default values for created_at and updated_at
            record = form.save(commit=False)
            if not record.created_at:
                record.created_at = timezone.now()
            if not record.updated_at:
                record.updated_at = timezone.now()
            record.save()
            messages.success(request, 'Dental record created successfully.')
            return redirect('dental:dental_record_detail', record_id=record.id)
    else:
        form = DentalRecordForm()

    context = {
        'form': form,
        'title': 'Create Dental Record'
    }
    return render(request, 'dental/dental_record_form.html', context)

@login_required
def dental_record_detail(request, record_id):
    """View to display details of a specific dental record"""
    record = get_object_or_404(DentalRecord.objects.select_related('patient', 'service', 'dentist'), id=record_id)

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

    # Get X-rays for this record
    xrays = DentalXRay.objects.filter(dental_record=record).order_by('-taken_at')

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
            Q(message__icontains="Module: dental") &
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
                f"Please contact the desk office to obtain authorization for dental services."
            )

    context = {
        'record': record,
        'prescriptions': prescriptions,
        'xrays': xrays,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_amount': authorization_amount,
        'has_pending_request': has_pending_request,
    }
    return render(request, 'dental/dental_record_detail.html', context)

@login_required
def edit_dental_record(request, record_id):
    """View to edit an existing dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        form = DentalRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Dental record updated successfully.')
            return redirect('dental:dental_record_detail', record_id=record.id)
    else:
        form = DentalRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Dental Record'
    }
    return render(request, 'dental/dental_record_form.html', context)

@login_required
def delete_dental_record(request, record_id):
    """View to delete a dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Dental record deleted successfully.')
        return redirect('dental:dental_records')
    
    context = {
        'record': record
    }
    return render(request, 'dental/dental_record_confirm_delete.html', context)

@login_required
def search_dental_patients(request):
    """AJAX view for searching patients in dental module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_dental(request, record_id):
    """Create a prescription for a dental patient"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
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
                    return redirect('dental:dental_record_detail', record_id=record.pk)
                    
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
    return render(request, 'dental/create_prescription.html', context)

@login_required
def dental_services(request):
    """View to list and manage dental services"""
    services = DentalService.objects.all().order_by('name')
    
    if request.method == 'POST':
        form = DentalServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dental service created successfully.')
            return redirect('dental:dental_services')
    else:
        form = DentalServiceForm()
    
    context = {
        'services': services,
        'form': form,
    }
    return render(request, 'dental/dental_services.html', context)

@login_required
def edit_dental_service(request, service_id):
    """View to edit a dental service"""
    service = get_object_or_404(DentalService, id=service_id)
    
    if request.method == 'POST':
        form = DentalServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dental service updated successfully.')
            return redirect('dental:dental_services')
    else:
        form = DentalServiceForm(instance=service)
    
    context = {
        'form': form,
        'service': service,
        'title': 'Edit Dental Service'
    }
    return render(request, 'dental/dental_service_form.html', context)

@login_required
def delete_dental_service(request, service_id):
    """View to delete a dental service"""
    service = get_object_or_404(DentalService, id=service_id)
    
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Dental service deleted successfully.')
        return redirect('dental:dental_services')
    
    context = {
        'service': service
    }
    return render(request, 'dental/dental_service_confirm_delete.html', context)

@login_required
def add_xray_to_dental_record(request, record_id):
    """Add an X-ray to a dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        form = DentalXRayForm(request.POST, request.FILES)
        if form.is_valid():
            xray = form.save(commit=False)
            xray.dental_record = record
            xray.taken_by = request.user
            xray.save()
            messages.success(request, 'X-ray added successfully.')
            return redirect('dental:dental_record_detail', record_id=record.pk)
    else:
        form = DentalXRayForm()
    
    context = {
        'form': form,
        'record': record,
        'title': 'Add X-Ray'
    }
    return render(request, 'dental/add_xray.html', context)

@login_required
def delete_xray(request, xray_id):
    """Delete a dental X-ray"""
    xray = get_object_or_404(DentalXRay, id=xray_id)
    record_id = xray.dental_record.pk
    
    if request.method == 'POST':
        xray.delete()
        messages.success(request, 'X-ray deleted successfully.')
        return redirect('dental:dental_record_detail', record_id=record_id)
    
    context = {
        'xray': xray
    }
    return render(request, 'dental/xray_confirm_delete.html', context)

@login_required
def generate_invoice_for_dental(request, record_id):
    """Generate an invoice for a dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)

    # Check if invoice already exists
    if record.invoice:
        messages.info(request, 'An invoice already exists for this dental record.')
        return redirect('dental:dental_record_detail', record_id=record.pk)

    # **NHIA AUTHORIZATION CHECK**: Prevent invoice generation without authorization
    if record.patient.patient_type == 'nhia':
        if not record.authorization_code:
            messages.error(
                request,
                f"Cannot generate invoice for NHIA patient {record.patient.get_full_name()}. "
                f"An authorization code from the desk office is required before generating an invoice. "
                f"Please contact the desk office to obtain the authorization code."
            )
            return redirect('dental:dental_record_detail', record_id=record.pk)

        # Check if authorization is valid
        if not record.authorization_code.is_valid():
            messages.error(
                request,
                f"Cannot generate invoice. The authorization code for this dental record is expired or invalid. "
                f"Please contact the desk office for a new authorization code."
            )
            return redirect('dental:dental_record_detail', record_id=record.pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create the invoice
                invoice = Invoice.objects.create(
                    patient=record.patient,
                    issued_by=request.user,
                    total_amount=record.get_service_price(),
                    status='pending'
                )
                
                # Create invoice item
                if record.service:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        item_name=record.service.name,
                        quantity=1,
                        unit_price=record.service.price,
                        total_price=record.service.price
                    )
                
                # Link invoice to dental record
                record.invoice = invoice  # type: ignore
                record.save()
                
                messages.success(request, 'Invoice generated successfully.')
                return redirect('dental:dental_record_detail', record_id=record.pk)
                
        except Exception as e:
            messages.error(request, f'Error generating invoice: {str(e)}')
    
    context = {
        'record': record,
        'title': 'Generate Invoice'
    }
    return render(request, 'dental/generate_invoice.html', context)