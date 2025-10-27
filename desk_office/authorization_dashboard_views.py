"""
Views for NHIA Authorization Dashboard
Allows desk office staff to view and manage pending authorization requests
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from consultations.models import Consultation, Referral
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from theatre.models import Surgery
from nhia.models import AuthorizationCode
from patients.models import Patient
from .forms import PatientSearchForm, AuthorizationCodeForm
import string
import random


def generate_authorization_code_string():
    """Generate a unique authorization code"""
    date_str = timezone.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AUTH-{date_str}-{random_str}"


@login_required
def authorization_dashboard(request):
    """
    Dashboard showing all pending authorization requests across the system
    """
    # Initialize patient search form and variables
    patient_search_form = PatientSearchForm()
    search_results = None
    search_query = None
    selected_patient = None
    authorization_form = None
    
    # Handle patient search
    if request.method == 'POST' and 'search_patients' in request.POST:
        patient_search_form = PatientSearchForm(request.POST)
        if patient_search_form.is_valid():
            search_query = patient_search_form.cleaned_data.get('search')
            if search_query:
                # Search for NHIA patients by name, patient ID, or NHIA number
                patients = Patient.objects.filter(
                    patient_type='nhia'
                ).filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(patient_id__icontains=search_query) |
                    Q(nhia_info__nhia_reg_number__icontains=search_query) |
                    Q(phone_number__icontains=search_query)
                ).select_related('nhia_info').order_by('first_name', 'last_name')
                
                # Pagination for search results
                paginator = Paginator(patients, 10)
                page_number = request.GET.get('page')
                search_results = paginator.get_page(page_number)
    
    # Handle patient selection
    elif request.method == 'GET' and 'patient_id' in request.GET:
        try:
            selected_patient = Patient.objects.get(id=request.GET.get('patient_id'), patient_type='nhia')
            authorization_form = AuthorizationCodeForm(patient=selected_patient)
            messages.info(request, f'Selected patient: {selected_patient.get_full_name()}')
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')
    
    # Handle authorization code generation
    elif request.method == 'POST' and 'generate_code' in request.POST:
        try:
            patient_id = request.POST.get('patient_id')
            selected_patient = Patient.objects.get(id=patient_id, patient_type='nhia')
            
            # Handle quick code generation (from modal)
            is_quick_code = request.POST.get('quick_code') == '1'
            
            if is_quick_code:
                # Quick code generation - use form data directly
                amount = float(request.POST.get('amount', '0.00'))
                expiry_days = int(request.POST.get('expiry_days', '30'))
                expiry_date = timezone.now().date() + timezone.timedelta(days=expiry_days)
                notes = f"Quick-generated authorization code for {selected_patient.get_full_name()}"
                
                # Generate unique code
                while True:
                    code_str = generate_authorization_code_string()
                    if not AuthorizationCode.objects.filter(code=code_str).exists():
                        break
                
                # Create authorization code directly
                auth_code = AuthorizationCode.objects.create(
                    code=code_str,
                    patient=selected_patient,
                    service_type='general',
                    amount=amount,
                    expiry_date=expiry_date,
                    status='active',
                    notes=notes,
                    generated_by=request.user
                )
                
                messages.success(request, f'Quick authorization code {auth_code.code} generated successfully for {selected_patient.get_full_name()}.')
                
                # Handle AJAX response for quick code
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Authorization code {auth_code.code} generated successfully.',
                        'code': auth_code.code,
                        'patient_name': selected_patient.get_full_name()
                    })
                
                return redirect('desk_office:authorization_dashboard')
            else:
                # Regular code generation using form
                authorization_form = AuthorizationCodeForm(request.POST, patient=selected_patient)
                
                if authorization_form.is_valid():
                    auth_code = authorization_form.save(commit=False)
                    auth_code.generated_by = request.user
                    
                    # Generate unique code if not provided
                    if not getattr(auth_code, 'code', None):
                        while True:
                            auth_code.code = generate_authorization_code_string()
                            if not AuthorizationCode.objects.filter(code=auth_code.code).exists():
                                break
                    
                    auth_code.save()
                    messages.success(request, f'Authorization code {auth_code.code} generated successfully for {selected_patient.get_full_name()}.')
                    
                    # Clear form and patient selection
                    return redirect('desk_office:authorization_dashboard')
                else:
                    messages.error(request, 'Please correct the errors in the form.')
                    
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Selected patient not found or is not an NHIA patient.'})
        except ValueError as e:
            messages.error(request, f'Invalid amount value: {str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'Invalid amount value: {str(e)}'})
        except Exception as e:
            messages.error(request, f'Error generating authorization code: {str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'Error generating authorization code: {str(e)}'})
    
    # Get all consultations requiring authorization
    pending_consultations = Consultation.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'doctor', 'consulting_room').order_by('-consultation_date')

    # Get all referrals requiring authorization
    pending_referrals = Referral.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'referring_doctor', 'referred_to_doctor', 'referred_to_department', 'assigned_doctor').order_by('-referral_date')

    # Get all prescriptions requiring authorization
    pending_prescriptions = Prescription.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'doctor').order_by('-prescription_date')

    # Get all lab test requests requiring authorization
    pending_lab_tests = TestRequest.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'doctor').order_by('-request_date')

    # Get all radiology orders requiring authorization
    pending_radiology = RadiologyOrder.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'referring_doctor', 'test').order_by('-order_date')

    # Get all surgeries requiring authorization
    pending_surgeries = Surgery.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'surgery_type', 'primary_surgeon', 'theatre').order_by('-scheduled_date')

    # Get statistics
    stats = {
        'consultations': pending_consultations.count(),
        'referrals': pending_referrals.count(),
        'prescriptions': pending_prescriptions.count(),
        'lab_tests': pending_lab_tests.count(),
        'radiology': pending_radiology.count(),
        'surgeries': pending_surgeries.count(),
        'total': (
            pending_consultations.count() +
            pending_referrals.count() +
            pending_prescriptions.count() +
            pending_lab_tests.count() +
            pending_radiology.count() +
            pending_surgeries.count()
        )
    }

    # Get recent authorization codes
    recent_codes = AuthorizationCode.objects.select_related('patient').order_by('-generated_at')[:10]

    context = {
        'pending_consultations': pending_consultations[:10],  # Show top 10
        'pending_referrals': pending_referrals[:10],
        'pending_prescriptions': pending_prescriptions[:10],
        'pending_lab_tests': pending_lab_tests[:10],
        'pending_radiology': pending_radiology[:10],
        'pending_surgeries': pending_surgeries[:10],
        'stats': stats,
        'recent_codes': recent_codes,
        'patient_search_form': patient_search_form,
        'search_results': search_results,
        'search_query': search_query,
        'selected_patient': selected_patient,
        'authorization_form': authorization_form,
        'page_title': 'NHIA Authorization Dashboard',
        'active_nav': 'desk_office',
    }
    
    return render(request, 'desk_office/authorization_dashboard.html', context)


@login_required
def pending_consultations_list(request):
    """List all consultations requiring authorization"""
    consultations = Consultation.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'doctor', 'consulting_room').order_by('-consultation_date')
    
    # Create a simple paginator-like object for the main template
    from django.core.paginator import Paginator
    paginator = Paginator(consultations, 25)  # 25 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Calculate stats for the main template
    total_pending = consultations.count()
    nhia_count = consultations.filter(patient__patient_type='nhia').count()
    high_urgency_count = 0  # Consultations don't have urgency field in this model
    authorized_today = 0  # Would need additional query to get today's authorized count
    
    context = {
        # Main template expected variables
        'page_obj': page_obj,
        'total_pending': total_pending,
        'nhia_count': nhia_count,
        'high_urgency_count': high_urgency_count,
        'authorized_today': authorized_today,
        # Original variables for fallback
        'consultations': consultations,
        'page_title': 'Pending Consultation Authorizations',
        'active_nav': 'desk_office',
    }
    
    return render(request, 'desk_office/pending_consultations.html', context)


@login_required
def pending_referrals_list(request):
    """List all referrals requiring authorization"""
    referrals = Referral.objects.filter(
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related('patient', 'referring_doctor', 'referred_to_doctor', 'referred_to_department', 'assigned_doctor').order_by('-referral_date')
    
    # Create a simple paginator-like object for main template
    from django.core.paginator import Paginator
    paginator = Paginator(referrals, 25)  # 25 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Calculate stats for main template
    total_pending = referrals.count()
    nhia_count = referrals.filter(patient__patient_type='nhia').count()
    high_urgency_count = 0  # Default for now, would need urgency field
    authorized_today = 0  # Would need additional query to get today's authorized count
    
    # Get unique destinations for filter dropdown
    destinations = []
    for referral in referrals:
        dest = referral.get_referral_destination()
        if dest not in destinations:
            destinations.append(dest)
    
    context = {
        # Main template expected variables
        'page_obj': page_obj,
        'total_pending': total_pending,
        'nhia_count': nhia_count,
        'high_urgency_count': high_urgency_count,
        'authorized_today': authorized_today,
        'destinations': destinations,
        # Original variables for fallback
        'referrals': referrals,
        'page_title': 'Pending Referral Authorizations',
        'active_nav': 'desk_office',
    }
    
    return render(request, 'desk_office/pending_referrals.html', context)


@login_required
def authorize_consultation(request, consultation_id):
    """Generate authorization code for a specific consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    if not consultation.requires_authorization:
        messages.error(request, 'This consultation does not require authorization.')
        return redirect('desk_office:authorization_dashboard')
    
    if request.method == 'POST':
        # Get form data
        amount = request.POST.get('amount', '0.00')
        expiry_days = int(request.POST.get('expiry_days', '30'))
        expiry_date = timezone.now().date() + timezone.timedelta(days=expiry_days)
        notes = request.POST.get('notes', '')
        code_type = request.POST.get('code_type', 'auto')
        manual_code = request.POST.get('manual_code', '').strip().upper()

        # Determine service type based on consultation
        service_type = 'general'

        # Handle code generation (auto or manual)
        if code_type == 'manual':
            if not manual_code:
                messages.error(request, 'Please enter a manual authorization code.')
                context = {
                    'consultation': consultation,
                    'page_title': f'Authorize Consultation #{consultation.id}',
                    'active_nav': 'desk_office',
                    'form_data': request.POST,
                }
                return render(request, 'desk_office/authorize_consultation.html', context)

            # Check if manual code already exists
            if AuthorizationCode.objects.filter(code=manual_code).exists():
                messages.error(request, f'Authorization code "{manual_code}" already exists. Please use a different code.')
                context = {
                    'consultation': consultation,
                    'page_title': f'Authorize Consultation #{consultation.id}',
                    'active_nav': 'desk_office',
                    'form_data': request.POST,
                }
                return render(request, 'desk_office/authorize_consultation.html', context)

            code_str = manual_code
            code_source = "Manual"
        else:
            # Auto-generate authorization code
            while True:
                code_str = generate_authorization_code_string()
                if not AuthorizationCode.objects.filter(code=code_str).exists():
                    break
            code_source = "System"

        # Create authorization code
        auth_code = AuthorizationCode.objects.create(
            code=code_str,
            patient=consultation.patient,
            service_type=service_type,
            amount=amount,
            expiry_date=expiry_date,
            status='active',
            notes=f"{code_source}-generated for consultation #{consultation.id} in {consultation.consulting_room}. {notes}",
            generated_by=request.user
        )

        # Link authorization code to consultation
        consultation.authorization_code = auth_code
        consultation.authorization_status = 'authorized'
        consultation.save()

        messages.success(request, f'Authorization code {auth_code.code} generated successfully for consultation #{consultation.id}.')
        return redirect('desk_office:authorization_dashboard')
    
    context = {
        'consultation': consultation,
        'page_title': f'Authorize Consultation #{consultation.id}',
        'active_nav': 'desk_office',
    }
    
    return render(request, 'desk_office/authorize_consultation.html', context)


@login_required
def authorize_referral(request, referral_id):
    """Generate authorization code for a specific referral"""
    referral = get_object_or_404(Referral, id=referral_id)

    if not referral.requires_authorization:
        messages.error(request, 'This referral does not require authorization.')
        return redirect('desk_office:authorization_dashboard')

    if request.method == 'POST':
        # Get form data
        amount = request.POST.get('amount', '0.00')
        expiry_days = int(request.POST.get('expiry_days', '30'))
        expiry_date = timezone.now().date() + timezone.timedelta(days=expiry_days)
        notes = request.POST.get('notes', '')
        code_type = request.POST.get('code_type', 'auto')
        manual_code = request.POST.get('manual_code', '').strip().upper()

        # Determine service type
        service_type = 'general'

        # Handle code generation (auto or manual)
        if code_type == 'manual':
            if not manual_code:
                messages.error(request, 'Please enter a manual authorization code.')
                context = {
                    'referral': referral,
                    'page_title': f'Authorize Referral #{referral.id}',
                    'active_nav': 'desk_office',
                    'form_data': request.POST,
                }
                return render(request, 'desk_office/authorize_referral.html', context)

            # Check if manual code already exists
            if AuthorizationCode.objects.filter(code=manual_code).exists():
                messages.error(request, f'Authorization code "{manual_code}" already exists. Please use a different code.')
                context = {
                    'referral': referral,
                    'page_title': f'Authorize Referral #{referral.id}',
                    'active_nav': 'desk_office',
                    'form_data': request.POST,
                }
                return render(request, 'desk_office/authorize_referral.html', context)

            code_str = manual_code
            code_source = "Manual"
        else:
            # Auto-generate authorization code
            while True:
                code_str = generate_authorization_code_string()
                if not AuthorizationCode.objects.filter(code=code_str).exists():
                    break
            code_source = "System"

        # Create authorization code
        auth_code = AuthorizationCode.objects.create(
            code=code_str,
            patient=referral.patient,
            service_type=service_type,
            amount=amount,
            expiry_date=expiry_date,
            status='active',
            notes=f"{code_source}-generated for referral #{referral.id} to {referral.get_referral_destination()}. {notes}",
            generated_by=request.user
        )

        # Link authorization code to referral
        referral.authorization_code = auth_code
        referral.authorization_status = 'authorized'
        referral.save()

        messages.success(request, f'Authorization code {auth_code.code} generated successfully for referral #{referral.id}.')
        return redirect('desk_office:authorization_dashboard')
    
    context = {
        'referral': referral,
        'page_title': f'Authorize Referral #{referral.id}',
        'active_nav': 'desk_office',
    }
    
    return render(request, 'desk_office/authorize_referral.html', context)


@login_required
def authorization_code_list(request):
    """List all authorization codes with filtering"""
    import csv
    from django.http import HttpResponse

    codes = AuthorizationCode.objects.select_related('patient', 'generated_by').order_by('-generated_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        codes = codes.filter(status=status_filter)
    
    # Filter by patient
    patient_search = request.GET.get('patient_search')
    if patient_search:
        codes = codes.filter(
            Q(patient__first_name__icontains=patient_search) |
            Q(patient__last_name__icontains=patient_search) |
            Q(patient__patient_id__icontains=patient_search)
        )
    
    # Filter by service type
    service_type_filter = request.GET.get('service_type')
    if service_type_filter:
        codes = codes.filter(service_type=service_type_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    if date_from:
        codes = codes.filter(generated_at__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        codes = codes.filter(generated_at__date__lte=date_to)

    # Handle export request
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="authorization_codes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Code', 'Patient Name', 'Patient ID', 'NHIA Number', 'Amount',
            'Status', 'Generated By', 'Generated At', 'Expiry Date',
            'Used At', 'Notes'
        ])

        for code in codes:
            nhia_number = code.patient.nhia_info.nhia_reg_number if hasattr(code.patient, 'nhia_info') and code.patient.nhia_info else 'N/A'
            writer.writerow([
                code.code,
                code.patient.get_full_name(),
                code.patient.patient_id,
                nhia_number,
                f"{code.amount:.2f}",
                code.get_status_display(),
                code.generated_by.get_full_name() if code.generated_by else 'System',
                code.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
                code.expiry_date.strftime('%Y-%m-%d') if code.expiry_date else 'Never',
                code.used_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(code, 'used_at') and code.used_at else 'Not used',
                code.notes or ''
            ])

        return response

    # Pagination
    paginator = Paginator(codes, 20)  # 20 codes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    from django.db.models import Count
    all_codes = AuthorizationCode.objects.all()
    stats = {
        'total': all_codes.count(),
        'active': all_codes.filter(status='active').count(),
        'used': all_codes.filter(status='used').count(),
        'expired': all_codes.filter(status='expired').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'page_title': 'Authorization Codes',
        'active_nav': 'desk_office',
        'status_filter': status_filter,
        'patient_search': patient_search,
        'service_type_filter': service_type_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'desk_office/authorization_code_list.html', context)


@login_required
def bulk_authorize_consultations(request):
    """Bulk authorize multiple consultations"""
    if request.method == 'POST':
        consultation_ids = request.POST.getlist('consultation_ids')
        
        if not consultation_ids:
            messages.error(request, 'No consultations selected for authorization.')
            return redirect('desk_office:pending_consultations')
        
        authorized_count = 0
        for consultation_id in consultation_ids:
            try:
                consultation = Consultation.objects.get(id=consultation_id)
                
                # Only authorize NHIA patients
                if consultation.patient.patient_type == 'nhia':
                    # Create authorization code for each consultation
                    date_str = timezone.now().strftime('%Y%m%d')
                    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    code_str = f"AUTH-{date_str}-{random_str}"
                    
                    # Check for duplicate codes
                    if not AuthorizationCode.objects.filter(code=code_str).exists():
                        auth_code = AuthorizationCode.objects.create(
                            code=code_str,
                            patient=consultation.patient,
                            service_type='consultation',
                            amount=5000.00,  # Default consultation amount
                            status='active',
                            generated_by=request.user,
                            notes=f"Auto-authorized consultation for {consultation.patient.get_full_name()}"
                        )
                        authorized_count += 1
                
            except Consultation.DoesNotExist:
                continue
        
        if authorized_count > 0:
            messages.success(request, f'{authorized_count} consultations have been authorized.')
        else:
            messages.warning(request, 'No NHIA consultations were found among the selected items.')
    
    return redirect('desk_office:pending_consultations')


@login_required
def bulk_authorize_referrals(request):
    """Bulk authorize multiple referrals"""
    if request.method == 'POST':
        referral_ids = request.POST.getlist('referral_ids')
        
        if not referral_ids:
            messages.error(request, 'No referrals selected for authorization.')
            return redirect('desk_office:pending_referrals')
        
        authorized_count = 0
        for referral_id in referral_ids:
            try:
                referral = Referral.objects.get(id=referral_id)
                
                # Only authorize NHIA patients
                if referral.patient.patient_type == 'nhia':
                    # Create authorization code for each referral
                    date_str = timezone.now().strftime('%Y%m%d')
                    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    code_str = f"AUTH-{date_str}-{random_str}"
                    
                    # Check for duplicate codes
                    if not AuthorizationCode.objects.filter(code=code_str).exists():
                        auth_code = AuthorizationCode.objects.create(
                            code=code_str,
                            patient=referral.patient,
                            service_type='referral',
                            amount=10000.00,  # Default referral amount
                            status='active',
                            generated_by=request.user,
                            notes=f"Auto-authorized referral for {referral.patient.get_full_name()} to {referral.get_referral_destination()}"
                        )
                        authorized_count += 1
                
            except Referral.DoesNotExist:
                continue
        
        if authorized_count > 0:
            messages.success(request, f'{authorized_count} referrals have been authorized.')
        else:
            messages.warning(request, 'No NHIA referrals were found among the selected items.')
    
    return redirect('desk_office:pending_referrals')

