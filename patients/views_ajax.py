from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from .models import Patient

@login_required
def ajax_patient_search(request):
    """AJAX endpoint for patient search with HTMX support"""
    query = request.GET.get('q', '')

    # Return empty response if query is too short
    if len(query) < 2:
        return HttpResponse('')

    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query)
    ).filter(is_active=True)[:10]

    patient_data = []
    for patient in patients:
        patient_data.append({
            'id': patient.id,
            'name': patient.get_full_name(),
            'patient_id': patient.patient_id,
            'phone_number': patient.phone_number or 'N/A',
        })

    # Render the HTML template for HTMX response
    html = render_to_string('inpatient/patient_search_results.html', {'patients': patient_data})
    return HttpResponse(html)
