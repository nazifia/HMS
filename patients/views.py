from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import Patient
from .forms import PatientForm
from appointments.models import Appointment
from consultations.models import Consultation
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from datetime import datetime, timedelta


@login_required
def patient_list(request):
    """View for listing all patients with search and pagination"""
    # Get all active patients
    patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(patient_id__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(patients, 10)  # Show 10 patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'page_title': 'Patient List',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/patient_list.html', context)


@login_required
def register_patient(request):
    """View for registering a new patient"""
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.get_full_name()} registered successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm()
    
    context = {
        'form': form,
        'page_title': 'Register Patient',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/register.html', context)


@login_required
def patient_detail(request, patient_id):
    """View for displaying patient details"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Calculate patient age
    today = timezone.now().date()
    age = today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )
    
    # Get recent appointments
    recent_appointments = Appointment.objects.filter(
        patient=patient
    ).order_by('-appointment_date')[:5]
    
    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        patient=patient
    ).order_by('-consultation_date')[:5]
    
    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.filter(
        patient=patient
    ).order_by('-prescription_date')[:5]
    
    context = {
        'patient': patient,
        'age': age,
        'recent_appointments': recent_appointments,
        'recent_consultations': recent_consultations,
        'recent_prescriptions': recent_prescriptions,
        'page_title': f'Patient Details - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/patient_detail.html', context)


@login_required
def edit_patient(request, patient_id):
    """View for editing patient information"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.get_full_name()} updated successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm(instance=patient)
    
    context = {
        'form': form,
        'patient': patient,
        'page_title': f'Edit Patient - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/edit.html', context)


@login_required
def toggle_patient_status(request, patient_id):
    """View for toggling patient active status"""
    patient = get_object_or_404(Patient, id=patient_id)
    patient.is_active = not patient.is_active
    patient.save()
    
    status = "activated" if patient.is_active else "deactivated"
    messages.success(request, f'Patient {patient.get_full_name()} has been {status}.')
    
    return redirect('patients:detail', patient_id=patient.id)


@login_required
def search_patients(request):
    """View for searching patients via AJAX"""
    query = request.GET.get('q', '')
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query)
    ).filter(is_active=True)[:10]
    
    patient_data = []
    for patient in patients:
        patient_data.append({
            'id': patient.id,
            'name': patient.get_full_name(),
            'patient_id': patient.patient_id,
            'phone_number': patient.phone_number,
        })
    
    return JsonResponse({'patients': patient_data})


@login_required
def edit_medical_history(request, history_id):
    """View for editing patient medical history"""
    # Implementation would depend on the medical history model
    pass


@login_required
def delete_medical_history(request, history_id):
    """View for deleting patient medical history"""
    # Implementation would depend on the medical history model
    pass


@login_required
def patient_medical_history(request, patient_id):
    """View for displaying patient medical history"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation would depend on the medical history model
    pass


@login_required
def patient_vitals(request, patient_id):
    """View for displaying patient vitals"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation would depend on the vitals model
    pass


@login_required
def pwa_manifest(request):
    """View for PWA manifest"""
    # Implementation for PWA manifest
    pass


@login_required
def service_worker(request):
    """View for service worker"""
    # Implementation for service worker
    pass


@login_required
def offline_fallback(request):
    """View for offline fallback"""
    # Implementation for offline fallback
    pass


@login_required
def pwa_demo(request):
    """View for PWA demo"""
    # Implementation for PWA demo
    pass


@login_required
def demo_push_notification(request):
    """View for demo push notification"""
    # Implementation for demo push notification
    pass


@login_required
def check_patient_nhia(request):
    """View for checking patient NHIA status"""
    # Implementation for checking patient NHIA status
    pass


@login_required
def wallet_dashboard(request, patient_id):
    """View for patient wallet dashboard"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for wallet dashboard
    pass


@login_required
def add_funds_to_wallet(request, patient_id):
    """View for adding funds to patient wallet"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for adding funds to wallet
    pass


@login_required
def wallet_transactions(request, patient_id):
    """View for displaying patient wallet transactions"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for wallet transactions
    pass


@login_required
def wallet_withdrawal(request, patient_id):
    """View for patient wallet withdrawal"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for wallet withdrawal
    pass


@login_required
def wallet_transfer(request, patient_id):
    """View for patient wallet transfer"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for wallet transfer
    pass


@login_required
def wallet_refund(request, patient_id):
    """View for patient wallet refund"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for wallet refund
    pass


@login_required
def wallet_adjustment(request, patient_id):
    """View for patient wallet adjustment"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for wallet adjustment
    pass


@login_required
def register_nhia_patient(request, patient_id):
    """View for registering NHIA patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for registering NHIA patient
    pass


@login_required
def edit_nhia_patient(request, patient_id):
    """View for editing NHIA patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for editing NHIA patient
    pass


@login_required
def patient_dashboard(request, patient_id):
    """Enhanced patient dashboard showing comprehensive patient information"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Calculate patient age
    today = timezone.now().date()
    age = today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )
    
    # Get recent appointments (last 6 months)
    six_months_ago = today - timedelta(days=180)
    recent_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=six_months_ago
    ).order_by('-appointment_date')
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=today,
        status__in=['scheduled', 'confirmed']
    ).order_by('appointment_date')
    
    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        patient=patient
    ).order_by('-consultation_date')[:5]
    
    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.filter(
        patient=patient
    ).order_by('-prescription_date')[:5]
    
    # Get recent lab tests
    recent_lab_tests = TestRequest.objects.filter(
        patient=patient
    ).order_by('-request_date')[:5]
    
    # Get recent radiology orders
    recent_radiology_orders = RadiologyOrder.objects.filter(
        patient=patient
    ).order_by('-order_date')[:5]
    
    # Get appointment statistics
    total_appointments = Appointment.objects.filter(patient=patient).count()
    completed_appointments = Appointment.objects.filter(
        patient=patient, 
        status='completed'
    ).count()
    
    # Get consultation statistics
    total_consultations = Consultation.objects.filter(patient=patient).count()
    completed_consultations = Consultation.objects.filter(
        patient=patient, 
        status='completed'
    ).count()
    
    context = {
        'patient': patient,
        'age': age,
        'recent_appointments': recent_appointments,
        'upcoming_appointments': upcoming_appointments,
        'recent_consultations': recent_consultations,
        'recent_prescriptions': recent_prescriptions,
        'recent_lab_tests': recent_lab_tests,
        'recent_radiology_orders': recent_radiology_orders,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'total_consultations': total_consultations,
        'completed_consultations': completed_consultations,
        'page_title': f'Patient Dashboard - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/patient_dashboard.html', context)