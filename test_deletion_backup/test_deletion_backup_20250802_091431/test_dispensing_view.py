import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from pharmacy.models import Prescription

User = get_user_model()

def test_dispensing_view():
    """Test the dispensing view directly"""
    
    # Create a test client
    client = Client()
    
    # Get or create a test user with proper permissions
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
    
    # Test the dispensing view
    try:
        prescription = Prescription.objects.get(id=3)
        print(f"✓ Found prescription {prescription.id}")
        
        url = f'/pharmacy/prescriptions/{prescription.id}/dispense/'
        print(f"Testing URL: {url}")
        
        response = client.get(url)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode()
            
            # Check if prescription items are in the response
            if 'AMLODIPINE' in content:
                print("✓ Prescription items found in response")
            else:
                print("❌ Prescription items NOT found in response")
                
            # Check if the table is present
            if 'prescription_items' in content:
                print("✓ prescription_items context variable found")
            else:
                print("❌ prescription_items context variable NOT found")
                
            # Check for the empty message
            if 'No items available for dispensing' in content:
                print("❌ 'No items available' message found - this means items are not being passed to template")
            else:
                print("✓ No 'No items available' message - items should be present")
                
            # Save response for inspection
            with open('dispensing_response.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✓ Response saved to dispensing_response.html for inspection")
            
            return True
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response content: {response.content.decode()}")
            return False
            
    except Prescription.DoesNotExist:
        print("❌ Prescription 3 not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Dispensing View")
    print("=" * 40)
    test_dispensing_view()
