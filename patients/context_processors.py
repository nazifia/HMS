from patients.models import Patient

def all_patients(request):
    """
    Adds all registered patients to the context as 'all_patients'.
    """
    return {
        'all_patients': Patient.objects.all()
    }
