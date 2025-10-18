from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from patients.models import Patient


@login_required
def test_url_helpers(request):
    """View for testing URL helper functions and template tags"""
    return render(request, 'test_url_helpers.html')


@login_required
def test_performance(request):
    """Test page for HTMX and Alpine.js functionality"""
    return render(request, 'test_performance.html')


def home_view(request):
    """
    Home page view
    """
    return render(request, 'home.html')


@login_required
def notifications_list(request):
    """
    View to display notifications list
    """
    # This is a placeholder implementation
    return render(request, 'core/notifications_list.html', {
        'notifications': []
    })


@login_required
def mark_notification_read(request, notification_id):
    """
    View to mark a notification as read
    """
    # This is a placeholder implementation
    return HttpResponse(status=204)  # No content response


@login_required
def create_prescription_view(request, patient_id, module_name):
    """
    View to create a prescription
    """
    # This is a placeholder implementation
    return render(request, 'core/create_prescription.html', {
        'patient_id': patient_id,
        'module_name': module_name
    })


@login_required
def patient_prescriptions_view(request, patient_id):
    """
    View to display patient prescriptions
    """
    # This is a placeholder implementation
    return render(request, 'core/patient_prescriptions.html', {
        'patient_id': patient_id
    })


def medication_autocomplete_view(request):
    """
    View to provide medication autocomplete suggestions
    """
    # This is a placeholder implementation
    return JsonResponse({'medications': []})


@require_http_methods(["GET"])
def search_patients(request):
    """
    AJAX view to search patients by name, ID, or phone number
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'patients': []})
    
    # Search patients by name, ID, or phone
    patients = Patient.objects.filter(is_active=True).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query)
    )[:20]  # Limit to 20 results
    
    # Format the results
    patient_data = [
        {
            'id': patient.id,
            'name': f"{patient.first_name} {patient.last_name}",
            'patient_id': patient.patient_id,
            'phone': patient.phone_number or 'N/A'
        }
        for patient in patients
    ]
    
    return JsonResponse({'patients': patient_data})


@login_required
def patient_search_ajax(request):
    """
    HTMX AJAX view to search patients and return HTML
    """
    query = request.GET.get('q', '') or request.GET.get('search', '').strip()
    patient_type = request.GET.get('patient_type', '')
    
    # Default template path based on usage
    template_name = 'desk_office/partials/patient_search_results.html'
    if 'quick' in request.GET:
        template_name = 'desk_office/partials/quick_patient_search_results.html'
    
    if len(query) < 2:
        return render(request, template_name, {
            'patients': [],
            'search_query': query
        })
    
    # Build patient queryset
    patients_qs = Patient.objects.filter(is_active=True)
    
    # Filter by patient type if specified
    if patient_type:
        patients_qs = patients_qs.filter(patient_type=patient_type)
    
    # Search by name, ID, phone, or NHIA number
    patients_qs = patients_qs.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query) |
        Q(nhia_info__nhia_reg_number__icontains=query)
    ).select_related('nhia_info').order_by('first_name', 'last_name')[:15]  # Limit to 15 results
    
    return render(request, template_name, {
        'patients': patients_qs,
        'search_query': query
    })