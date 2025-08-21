from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Patient
from appointments.models import Appointment
from consultations.models import Consultation
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from datetime import datetime, timedelta
from django.utils import timezone


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