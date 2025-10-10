"""
Script to test and reproduce the wallet_net_impact URL reversal issue
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory
from django.urls import reverse
from patients.models import Patient, PatientWallet

def test_dashboard_view():
    """Test the dashboard view to see if URL reversal errors occur"""
    from dashboard.views import dashboard
    
    factory = RequestFactory()
    request = factory.get('/dashboard/')
    
    print("Testing dashboard view...")
    
    try:
        response = dashboard(request)
        print("Dashboard view executed successfully")
        print(f"Response status: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error in dashboard view: {e}")
        print(f"Error type: {type(e)}")
        return False

def test_wallet_net_impact_urls():
    """Test wallet net impact URL reversals"""
    print("\nTesting wallet net impact URL reversals...")
    
    # Test 1: Try to reverse without patient_id (should fail)
    try:
        url = reverse('patients:wallet_net_impact')
        print(f"ERROR: URL reverse should have failed but got: {url}")
        return False
    except Exception as e:
        print(f"Expected error when reversing without patient_id: {e}")
    
    # Test 2: Try to reverse with patient_id (should work)
    try:
        # Get a patient ID
        patient = Patient.objects.first()
        if patient:
            url = reverse('patients:wallet_net_impact', kwargs={'patient_id': patient.id})
            print(f"Successfully reversed URL with patient_id {patient.id}: {url}")
        else:
            print("No patients found in database")
            return False
    except Exception as e:
        print(f"ERROR: URL reverse with patient_id failed: {e}")
        return False
    
    # Test 3: Try to reverse global URL (should work)
    try:
        url = reverse('patients:wallet_net_impact_global')
        print(f"Successfully reversed global URL: {url}")
    except Exception as e:
        print(f"ERROR: Global URL reverse failed: {e}")
        return False
    
    return True

def test_template_compilation():
    """Test template compilation to see if URL tags cause issues"""
    from django.template import Template, Context
    
    print("\nTesting template compilation...")
    
    # Test template with URL tag without parameters
    template_content = """
    {% load patient_tags %}
    <a href="{% url 'patients:wallet_net_impact' %}">Test</a>
    """
    
    try:
        template = Template(template_content)
        print("Template compiled (Django defers URL resolution until rendering)")
        
        # Now try to render it
        context = Context({})
        rendered = template.render(context)
        print("ERROR: Template rendering should have failed!")
        return False
    except Exception as e:
        print(f"Expected error in template rendering: {e}")
    
    # Test template with safe URL tag
    template_content_safe = """
    {% load patient_tags %}
    <a href="{% safe_wallet_net_impact_url None %}">Test</a>
    """
    
    try:
        template = Template(template_content_safe)
        context = Context({})
        rendered = template.render(context)
        print("Safe URL template rendered successfully")
        return True
    except Exception as e:
        print(f"ERROR: Safe URL template compilation failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing wallet_net_impact URL reversal issue...")
    
    success = True
    
    if not test_wallet_net_impact_urls():
        success = False
    
    if not test_template_compilation():
        success = False
    
    if not test_dashboard_view():
        success = False
    
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
