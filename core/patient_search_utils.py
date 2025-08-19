from django.db.models import Q
from patients.models import Patient

def search_patients_by_query(query, limit=10):
    """
    Universal patient search function that can be used across all medical modules.
    
    Args:
        query (str): Search term to look for patients
        limit (int): Maximum number of results to return (default: 10)
        
    Returns:
        QuerySet: Patients matching the search criteria
    """
    if not query or len(query) < 2:
        return Patient.objects.none()
    
    patients = Patient.objects.filter(is_active=True).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query)
    )
    
    if limit:
        patients = patients[:limit]
        
    return patients

def format_patient_search_results(patients):
    """
    Format patient search results for consistent display across modules.
    
    Args:
        patients (QuerySet): Patient objects to format
        
    Returns:
        list: Formatted patient data for display
    """
    results = []
    for patient in patients:
        results.append({
            'id': patient.id,
            'text': f"{patient.get_full_name()} ({patient.patient_id})",
            'patient_id': patient.patient_id,
            'name': patient.get_full_name(),
            'gender': patient.get_gender_display(),
            'phone': patient.phone_number,
            'age': patient.get_age()
        })
    return results

def add_patient_search_context(context, request, model_class, search_fields=None):
    """
    Add patient search functionality to any medical module's context.
    
    Args:
        context (dict): Existing context dictionary
        request (HttpRequest): Current request object
        model_class (Model): The model class for the current module
        search_fields (list): Additional fields to search in the module's records
        
    Returns:
        dict: Updated context with search functionality
    """
    if search_fields is None:
        search_fields = ['patient__first_name', 'patient__last_name', 'patient__patient_id']
    
    search_query = request.GET.get('search', '')
    
    if search_query:
        q_objects = Q()
        for field in search_fields:
            q_objects |= Q(**{f"{field}__icontains": search_query})
        
        # Also search by patient phone number
        q_objects |= Q(patient__phone_number__icontains=search_query)
        
        context['records'] = context['records'].filter(q_objects)
    
    context['search_query'] = search_query
    return context