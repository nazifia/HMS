import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from pharmacy.models import Prescription, Dispensary

User = get_user_model()

def test_stock_quantities_endpoint():
    """Test the stock quantities AJAX endpoint"""
    
    # Create a test client
    client = Client()
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    # Login the user
    client.force_login(user)
    
    # Get prescription 3
    try:
        prescription = Prescription.objects.get(id=3)
        print(f"✓ Found prescription {prescription.id}")
        
        # Get a dispensary
        dispensary = Dispensary.objects.filter(is_active=True).first()
        if not dispensary:
            print("❌ No active dispensary found")
            return False
            
        print(f"✓ Using dispensary: {dispensary.name} (ID: {dispensary.id})")
        
        # Test the AJAX endpoint
        url = f'/pharmacy/prescriptions/{prescription.id}/stock-quantities/'
        data = {'dispensary_id': dispensary.id}
        
        print(f"Testing URL: {url}")
        print(f"POST data: {data}")
        
        response = client.post(url, data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content.decode()}")
        
        if response.status_code == 200:
            import json
            response_data = json.loads(response.content)
            print(f"Response JSON: {response_data}")
            
            if response_data.get('success'):
                print("✅ AJAX endpoint working correctly")
                stock_quantities = response_data.get('stock_quantities', {})
                print(f"Stock quantities: {stock_quantities}")
                return True
            else:
                print(f"❌ AJAX endpoint returned error: {response_data.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Prescription.DoesNotExist:
        print("❌ Prescription 3 not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing AJAX Stock Quantities Endpoint")
    print("=" * 50)
    test_stock_quantities_endpoint()
