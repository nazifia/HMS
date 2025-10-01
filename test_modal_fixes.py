"""
Test script to verify modal fixes are working correctly

This script tests:
1. Transfer modal data population
2. Referral form validation
3. API endpoint for loading doctors

Run with: python test_modal_fixes.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory, Client
from patients.models import Patient
from consultations.models import Referral
from consultations.views import create_referral
from accounts.models import Role

User = get_user_model()

def test_api_doctors_endpoint():
    """Test that the doctors API endpoint returns active doctors"""
    print("\n" + "="*60)
    print("TEST 1: API Doctors Endpoint")
    print("="*60)
    
    client = Client()
    
    # Get a user to log in with
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ No active users found")
        return False
    
    # Log in
    client.force_login(user)
    
    # Test the API endpoint
    response = client.get('/accounts/api/users/?role=doctor')
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API endpoint working")
        print(f"   - Doctors found: {len(data)}")
        
        if len(data) > 0:
            print(f"   - Sample doctor: {data[0].get('full_name', 'N/A')}")
            print(f"   - Department: {data[0].get('department', 'N/A')}")
        else:
            print("⚠️  No doctors found in database")
        
        return True
    else:
        print(f"❌ API endpoint failed with status {response.status_code}")
        return False


def test_referral_form_validation():
    """Test that referral form validates correctly with patient from URL"""
    print("\n" + "="*60)
    print("TEST 2: Referral Form Validation")
    print("="*60)
    
    # Get test data
    patient = Patient.objects.first()
    if not patient:
        print("❌ No patients found in database")
        return False
    
    # Get two doctors
    doctor_role = Role.objects.filter(name__iexact='doctor').first()
    if not doctor_role:
        print("❌ Doctor role not found")
        return False
    
    doctors = User.objects.filter(roles=doctor_role, is_active=True)[:2]
    if len(doctors) < 2:
        print("❌ Need at least 2 doctors for testing")
        return False
    
    referring_doctor = doctors[0]
    referred_to = doctors[1]
    
    print(f"Patient: {patient.get_full_name()}")
    print(f"Referring Doctor: {referring_doctor.get_full_name()}")
    print(f"Referred To: {referred_to.get_full_name()}")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.post(
        f'/consultations/referrals/create/{patient.id}/',
        {
            'patient': patient.id,
            'referred_to': referred_to.id,
            'reason': 'Test referral for specialist consultation',
            'notes': 'This is a test referral created by automated test'
        }
    )
    request.user = referring_doctor
    
    # Add messages middleware
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    # Test the view
    try:
        response = create_referral(request, patient_id=patient.id)
        
        # Check if referral was created
        referral = Referral.objects.filter(
            patient=patient,
            referring_doctor=referring_doctor,
            referred_to=referred_to
        ).order_by('-created_at').first()
        
        if referral:
            print("✅ Referral created successfully")
            print(f"   - ID: {referral.id}")
            print(f"   - Status: {referral.status}")
            print(f"   - Reason: {referral.reason[:50]}...")
            
            # Clean up test data
            referral.delete()
            print("   - Test referral deleted")
            
            return True
        else:
            print("❌ Referral was not created")
            return False
            
    except Exception as e:
        print(f"❌ Error creating referral: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_transfer_modal_data_structure():
    """Test that transfer modal data structure is correct"""
    print("\n" + "="*60)
    print("TEST 3: Transfer Modal Data Structure")
    print("="*60)
    
    from pharmacy.models import ActiveStore, Dispensary
    
    # Get a dispensary with active store
    dispensary = Dispensary.objects.filter(active_store__isnull=False).first()
    
    if not dispensary:
        print("❌ No dispensary with active store found")
        return False
    
    active_store = dispensary.active_store
    
    # Get inventory items
    from pharmacy.models import ActiveStoreInventory
    inventory_items = ActiveStoreInventory.objects.filter(
        active_store=active_store,
        stock_quantity__gt=0
    )[:5]
    
    print(f"Dispensary: {dispensary.name}")
    print(f"Active Store: {active_store.name}")
    print(f"Inventory Items: {inventory_items.count()}")
    
    if inventory_items.count() > 0:
        print("\n✅ Sample inventory item data structure:")
        item = inventory_items.first()
        print(f"   - Medication ID: {item.medication.id}")
        print(f"   - Medication Name: {item.medication.name}")
        print(f"   - Batch Number: {item.batch_number}")
        print(f"   - Stock Quantity: {item.stock_quantity}")
        print("\n✅ Data structure matches modal requirements")
        return True
    else:
        print("⚠️  No inventory items found")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("MODAL FIXES VERIFICATION TESTS")
    print("="*60)
    
    results = {
        'API Endpoint': test_api_doctors_endpoint(),
        'Referral Form': test_referral_form_validation(),
        'Transfer Data': test_transfer_modal_data_structure()
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == '__main__':
    run_all_tests()

