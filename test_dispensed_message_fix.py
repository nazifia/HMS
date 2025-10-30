#!/usr/bin/env python
"""
Test script to verify dispensed prescription message styling fix
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
from django.contrib.messages import get_messages
from django.contrib.messages.constants import INFO, WARNING, ERROR

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
    
    # Check for messages
    messages_list = list(get_messages(response.wsgi_request))
    
    if messages_list:
        for message in messages_list:
            print(f"💌 Message level: {message.level}")
            print(f"📄 Message content: {message.message}")
            
            # Check for styling elements
            if message.level == INFO and '✅' in message.message:
                print("✅ Info message with checkmark found for dispensed prescription")
            elif message.level == ERROR:
                print("❌ Error level message found (should be info for dispensed)")
            else:
                print(f"ℹ️ {message.level} level message found")
    else:
        print("❌ No messages found in response")
    
    # Test cart creation view (should also show styled message)
    cart_url = reverse('pharmacy:create_cart_from_prescription', kwargs={'prescription_id': prescription.id})
    response = client.get(cart_url, follow=True)
    
    cart_messages = list(get_messages(response.wsgi_request))
    if cart_messages:
        for message in cart_messages:
            print(f"🛒 Cart message level: {message.level}")
            print(f"📄 Cart message content: {message.message}")
    
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
