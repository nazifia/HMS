#!/usr/bin/env python
"""
Test script to verify dispensed prescription message styling
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.append(r'C:\Users\dell\Desktop\MY_PRODUCTS\HMS')

django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from pharmacy.models import Prescription, PrescriptionItem, Medication
from patients.models import Patient

def test_dispensed_message_styling():
    """Test that dispensed prescription messages have proper styling"""
    
    print("🧪 Testing Dispensed Prescription Message Styling...")
    
    # Create test data
    user = User.objects.create_user(username='testuser', password='testpass')
    patient = Patient.objects.create(first_name='Test', last_name='Patient')
    medication = Medication.objects.create(name='Test Med', price=100)
    
    # Create dispensed prescription
    prescription = Prescription.objects.create(
        patient=patient,
        doctor=user,
        notes='Test prescription',
        status='dispensed'
    )
    
    prescription_item = PrescriptionItem.objects.create(
        prescription=prescription,
        medication=medication,
        quantity=5,
        price=100
    )
    
    print(f"✅ Created dispensed prescription #{prescription.id}")
    
    # Test can_be_dispensed method
    can_dispense, message = prescription.can_be_dispensed()
    
    print(f"📊 Can dispense: {can_dispense}")
    print(f"📝 Message: {message}")
    
    if not can_dispense and 'Cannot dispense prescription with status: Dispensed' in message:
        print("✅ Correct error message generated")
    else:
        print("❌ Unexpected result")
        return False
    
    # Test client response
    client = Client()
    client.force_login(user)
    
    # Test dispense view (should show styled message)
    url = reverse('pharmacy:dispense_prescription', kwargs={'prescription_id': prescription.id})
    print(f"🌐 Testing URL: {url}")
    
    response = client.get(url, follow=True)
    
    # Check response status
    print(f"📄 Response status: {response.status_code}")
    
    if response.status_code == 302:  # Redirect expected
        print("✅ Correct redirect behavior")
        
        # Check final response content for styling
        final_response = client.get(reverse('pharmacy:prescription_detail', kwargs={'prescription_id': prescription.id}))
        
        # Look for custom styling classes
        content = final_response.content.decode('utf-8')
        
        if 'alert-dispensed' in content:
            print("✅ Custom dispensed alert class found")
        else:
            print("❌ Custom dispensed alert class NOT found")
            
        if 'alert-icon' in content:
            print("✅ Alert icon styling found")
        else:
            print("❌ Alert icon styling NOT found")
            
        if 'background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)' in content:
            print("✅ Green gradient background styling found")
        else:
            print("❌ Green gradient background NOT found")
    else:
        print(f"❌ Unexpected response status: {response.status_code}")
    
    # Cleanup
    prescription_item.delete()
    prescription.delete()
    medication.delete()
    patient.delete()
    user.delete()
    
    print("🧹 Test data cleaned up")
    print("🎉 Dispensed message styling test completed!")
    
    return True

if __name__ == '__main__':
    test_dispensed_message_styling()
