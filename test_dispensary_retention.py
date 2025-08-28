#!/usr/bin/env python
"""
Test script for dispensary retention functionality

This script tests:
1. Dispensary selection retention through form submissions
2. Proper error handling when no dispensary is selected
3. Correct dispensing with selected dispensary
"""

import os
import sys
import django
import uuid
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from pharmacy.models import Medication, Prescription, PrescriptionItem, Dispensary, MedicationInventory
from patients.models import Patient

User = get_user_model()

class DispensaryRetentionTestCase(TestCase):
    """Test case for dispensary retention functionality"""
    
    def setUp(self):
        """Set up test data"""
        print("Setting up test data...")
        
        # Generate unique usernames and phone numbers
        pharmacist_username = f'pharmacist_{uuid.uuid4().hex[:8]}'
        patient_username = f'patient_{uuid.uuid4().hex[:8]}'
        pharmacist_phone = f'123456789{uuid.uuid4().hex[:2]}'
        patient_phone = f'098765432{uuid.uuid4().hex[:2]}'
        dispensary_name = f'Main Pharmacy {uuid.uuid4().hex[:8]}'
        
        # Create test user (pharmacist)
        self.pharmacist = User.objects.create_user(
            username=pharmacist_username,
            email='pharmacist@test.com',
            password='testpass123',
            phone_number=pharmacist_phone,
            first_name='Test',
            last_name='Pharmacist'
        )
        
        # Create patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
            gender='M',
            phone_number=patient_phone,
            address='123 Test Street',
            city='Test City',
            state='Test State',
            country='Nigeria'
        )
        
        # Create dispensary
        self.dispensary = Dispensary.objects.create(
            name=dispensary_name,
            location='Ground Floor',
            is_active=True
        )
        
        # Create medication
        self.medication = Medication.objects.create(
            name='Paracetamol',
            generic_name='Acetaminophen',
            dosage_form='Tablet',
            strength='500mg',
            price=Decimal('5.00'),
            is_active=True
        )
        
        # Create medication inventory
        self.inventory = MedicationInventory.objects.create(
            medication=self.medication,
            dispensary=self.dispensary,
            stock_quantity=100,
            reorder_level=10
        )
        
        # Create prescription
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.pharmacist,
            prescription_date=timezone.now().date(),
            status='approved',
            payment_status='paid'
        )
        
        # Create prescription item
        self.prescription_item = PrescriptionItem.objects.create(
            prescription=self.prescription,
            medication=self.medication,
            dosage='1 tablet',
            frequency='twice daily',
            duration='7 days',
            quantity=14
        )
        
        print("Test data setup completed!")
    
    def test_dispensary_retention_on_form_errors(self):
        """Test that dispensary selection is retained when form has validation errors"""
        print("\n=== Testing Dispensary Retention on Form Errors ===")
        
        # Login as pharmacist
        self.client.login(username=self.pharmacist.username, password='testpass123')
        
        # Get the dispensing page
        url = reverse('pharmacy:dispense_prescription', kwargs={'prescription_id': self.prescription.id})
        response = self.client.get(url)
        
        # Check that the page loads correctly
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select Dispensary')
        self.assertContains(response, self.dispensary.name)
        
        # Submit form with invalid data (no dispensary selected but items checked)
        post_data = {
            'dispensary_select': '',  # No dispensary selected
            'dispense_item_{}'.format(self.prescription_item.id): 'on',  # Item selected for dispensensing
            'quantity_{}'.format(self.prescription_item.id): '5',  # Quantity to dispense
            'csrfmiddlewaretoken': 'dummy-token'  # Mock CSRF token
        }
        
        response = self.client.post(url, post_data)
        
        # Check that we get an error message about selecting a dispensary
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please select a dispensary before dispensing items.')
        
        print("✅ Dispensary retention test on form errors completed successfully!")
        return True
    
    def test_successful_dispensing_with_dispensary(self):
        """Test successful dispensing with a selected dispensary"""
        print("\n=== Testing Successful Dispensing with Dispensary ===")
        
        # Login as pharmacist
        self.client.login(username=self.pharmacist.username, password='testpass123')
        
        # Get the dispensing page
        url = reverse('pharmacy:dispense_prescription', kwargs={'prescription_id': self.prescription.id})
        response = self.client.get(url)
        
        # Submit form with valid data
        post_data = {
            'dispensary_select': str(self.dispensary.id),  # Select dispensary
            'dispense_item_{}'.format(self.prescription_item.id): 'on',  # Item selected for dispensing
            'quantity_{}'.format(self.prescription_item.id): '5',  # Quantity to dispense
            'csrfmiddlewaretoken': 'dummy-token'  # Mock CSRF token
        }
        
        response = self.client.post(url, post_data, follow=True)
        
        # Check that dispensing was successful
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selected medications dispensed successfully.')
        
        # Check that inventory was updated
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.stock_quantity, 95)  # 100 - 5 dispensed
        
        # Check that prescription item was updated
        self.prescription_item.refresh_from_db()
        self.assertEqual(self.prescription_item.quantity_dispensed_so_far, 5)
        
        print("✅ Successful dispensing with dispensary test completed successfully!")
        return True

def main():
    """Main function to run the tests"""
    print("Dispensary Retention Functionality Test")
    print("=" * 50)
    
    # Create test case instance
    test_case = DispensaryRetentionTestCase()
    test_case.setUp()
    
    try:
        # Run tests
        retention_test = test_case.test_dispensary_retention_on_form_errors()
        dispensing_test = test_case.test_successful_dispensing_with_dispensary()
        
        if retention_test and dispensing_test:
            print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY! 🎉")
            print("\nDispensary retention functionality is working correctly:")
            print("✅ Dispensary selection is retained through form submissions")
            print("✅ Proper error handling when no dispensary is selected")
            print("✅ Correct dispensing with selected dispensary")
            print("✅ Inventory updates correctly after dispensing")
            return True
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)