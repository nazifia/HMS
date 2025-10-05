"""
Views for NHIA Authorization Dashboard
Allows desk office staff to view and manage pending authorization requests
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from consultations.models import Consultation, Referral
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from nhia.models import AuthorizationCode
from patients.models import Patient
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
    
    # Get statistics
    stats = {
        'consultations': pending_consultations.count(),
        'referrals': pending_referrals.count(),
        'prescriptions': pending_prescriptions.count(),
        'lab_tests': pending_lab_tests.count(),
        'radiology': pending_radiology.count(),
        'total': (
            pending_consultations.count() +
            pending_referrals.count() +
            pending_prescriptions.count() +
            pending_lab_tests.count() +
            pending_radiology.count()
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
        'stats': stats,
        'recent_codes': recent_codes,
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
    
    context = {
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
    
    context = {
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
    codes = AuthorizationCode.objects.select_related('patient', 'generated_by').order_by('-generated_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        codes = codes.filter(status=status_filter)
    
    # Filter by patient
    patient_search = request.GET.get('patient')
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
    
    context = {
        'codes': codes,
        'page_title': 'Authorization Codes',
        'active_nav': 'desk_office',
        'status_filter': status_filter,
        'patient_search': patient_search,
        'service_type_filter': service_type_filter,
    }
    
    return render(request, 'desk_office/authorization_code_list.html', context)

