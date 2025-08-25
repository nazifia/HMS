from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def test_url_helpers(request):
    """View for testing URL helper functions and template tags"""
    return render(request, 'test_url_helpers.html')


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