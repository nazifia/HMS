from django.db.models import Q
from patients.models import Patient

def search_patients_by_query(query, limit=10):
    """
    Universal patient search function that can be used across all medical modules.
    Includes all patient types: Regular, NHIA, Retainership, Insurance, Corporate, etc.
    
    Args:
        query (str): Search term to look for patients
        limit (int): Maximum number of results to return (default: 10)
        
    Returns:
        QuerySet: Patients matching the search criteria
    """
    if not query or len(query) < 2:
        return Patient.objects.none()
    
    # Include all patients regardless of is_active status to ensure comprehensive search
    # Also prefetch related NHIA and Retainership information for better display
    patients = Patient.objects.all().select_related(
        'nhia_info', 
        'retainership_info'
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query)
    )
    
    # Order by last name for better user experience
    patients = patients.order_by('last_name', 'first_name')
    
    if limit:
        patients = patients[:limit]
        
    return patients

def format_patient_search_results(patients):
    """
    Format patient search results for consistent display across modules.
    Includes patient type (Regular, NHIA, Retainership, etc.) for better identification.
    
    Args:
        patients (QuerySet): Patient objects to format
        
    Returns:
        list: Formatted patient data for display
    """
    results = []
    for patient in patients:
        # Determine patient type and additional info
        patient_type = patient.get_patient_type_display()
        type_indicator = ""
        
        # Add type-specific information
        if hasattr(patient, 'nhia_info') and patient.nhia_info and patient.nhia_info.is_active:
            type_indicator = f" [NHIA: {patient.nhia_info.nhia_reg_number}]"
        elif hasattr(patient, 'retainership_info') and patient.retainership_info and patient.retainership_info.is_active:
            type_indicator = f" [Retainership: {patient.retainership_info.retainership_reg_number}]"
        elif patient.patient_type != 'regular':
            type_indicator = f" [{patient.get_patient_type_display()}]"
        
        results.append({
            'id': patient.id,
            'text': f"{patient.get_full_name()} ({patient.patient_id}){type_indicator}",
            'patient_id': patient.patient_id,
            'name': patient.get_full_name(),
            'patient_type': patient_type,
            'gender': patient.get_gender_display(),
            'phone': patient.phone_number,
            'age': patient.get_age(),
            'type_indicator': type_indicator
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
        
        # Search by NHIA registration number
        q_objects |= Q(patient__nhia_info__nhia_reg_number__icontains=search_query)
        
        # Search by Retainership registration number
        q_objects |= Q(patient__retainership_info__retainership_reg_number__icontains=search_query)
        
        context['records'] = context['records'].filter(q_objects).select_related(
            'patient__nhia_info',
            'patient__retainership_info'
        )
    
    context['search_query'] = search_query
    return context