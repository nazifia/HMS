#!/usr/bin/env python
"""
Test script for NHIA patient 10% payment integration for surgery packs

This script tests:
1. NHIA patient identification in surgery pack billing
2. 10% payment calculation for NHIA patients
3. Proper invoice creation with discounted amounts
4. Integration between theatre and billing modules
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from pharmacy.models import MedicalPack, PackItem, PackOrder
from theatre.models import Surgery, SurgeryType, OperationTheatre
from patients.models import Patient
from billing.models import Invoice, InvoiceItem
from accounts.models import CustomUser

User = get_user_model()

class NHIASurgeryPackPaymentTestCase(TestCase):
    """Test case for NHIA patient 10% payment integration for surgery packs"""
    
    def setUp(self):
        """Set up test data"""
        print("Setting up test data...")
        
        # Create test users
        self.doctor = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='testpass123',
            phone_number='1234567890',
            first_name='Test',
            last_name='Doctor'
        )
        
        self.billing_staff = User.objects.create_user(
            username='billingstaff',
            email='billing@test.com',
            password='testpass123',
            phone_number='0987654321',
            first_name='Billing',
            last_name='Staff'
        )
        
        # Create regular patient
        self.regular_patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='M',
            patient_type='regular',
            address='123 Test Street',
            city='Test City',
            state='Test State',
            country='Nigeria',
            phone_number='1111111111'
        )
        
        # Create NHIA patient
        self.nhia_patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            date_of_birth='1985-05-10',
            gender='F',
            patient_type='nhia',
            address='456 NHIA Street',
            city='NHIA City',
            state='NHIA State',
            country='Nigeria',
            phone_number='2222222222'
        )
        
        # Create surgery type
        self.surgery_type = SurgeryType.objects.create(
            name='Appendectomy',
            description='Surgical removal of appendix',
            average_duration=timedelta(hours=2),
            preparation_time=timedelta(minutes=30),
            recovery_time=timedelta(hours=4),
            risk_level='medium'
        )
        
        # Create operation theatre
        self.theatre = OperationTheatre.objects.create(
            name='Theatre 1',
            theatre_number='T001',
            floor='2nd Floor',
            is_available=True,
            capacity=1
        )
        
        # Create medical pack
        self.medical_pack = MedicalPack.objects.create(
            name='Appendectomy Surgery Pack',
            description='Standard pack for appendectomy procedures',
            pack_type='surgery',
            surgery_type='appendectomy',
            risk_level='medium',
            is_active=True,
            created_by=self.doctor
        )
        
        print("Test data setup completed!")
    
    def test_nhia_patient_surgery_pack_payment(self):
        """Test NHIA patient 10% payment for surgery packs"""
        print("\n=== Testing NHIA Patient Surgery Pack Payment ===")
        
        # Create surgery for NHIA patient
        surgery = Surgery.objects.create(
            patient=self.nhia_patient,
            surgery_type=self.surgery_type,
            surgeon=self.doctor,
            scheduled_date=timezone.now() + timedelta(days=1),
            status='scheduled',
            theatre=self.theatre
        )
        
        # Create pack order for surgery
        pack_order = PackOrder.objects.create(
            pack=self.medical_pack,
            patient=self.nhia_patient,
            surgery=surgery,
            ordered_by=self.doctor,
            scheduled_date=surgery.scheduled_date
        )
        
        print(f"1. Created surgery for NHIA patient: {surgery}")
        print(f"2. Created pack order: {pack_order}")
        
        # Process the pack order to create prescription
        prescription = pack_order.process_order(self.doctor)
        print(f"3. Processed pack order, created prescription: #{prescription.id}")
        
        # Check that invoice was created for surgery
        invoice = surgery.invoice
        self.assertIsNotNone(invoice, "Surgery invoice should be created")
        print(f"4. Surgery invoice created: #{invoice.invoice_number}")
        
        # Verify NHIA patient pricing
        is_nhia = surgery.patient.patient_type == 'nhia'
        self.assertTrue(is_nhia, "Patient should be identified as NHIA")
        print("5. Patient correctly identified as NHIA")
        
        # Check invoice items for proper pricing
        invoice_items = invoice.items.all()
        self.assertGreater(len(invoice_items), 0, "Invoice should have items")
        
        # Get the pack item
        pack_item = None
        for item in invoice_items:
            if "Medical Pack" in item.description:
                pack_item = item
                break
        
        self.assertIsNotNone(pack_item, "Should find medical pack item in invoice")
        
        # Verify that the pack cost reflects 10% payment for NHIA patients
        original_pack_cost = self.medical_pack.get_total_cost()
        expected_nhia_cost = original_pack_cost * Decimal('0.10')
        
        self.assertEqual(
            pack_item.total_amount, 
            expected_nhia_cost,
            f"NHIA patient should pay 10% of pack cost. Expected: {expected_nhia_cost}, Got: {pack_item.total_amount}"
        )
        
        print(f"6. Original pack cost: ₦{original_pack_cost}")
        print(f"7. NHIA patient pays (10%): ₦{pack_item.total_amount}")
        print(f"8. NHIA discount applied: ₦{original_pack_cost - pack_item.total_amount}")
        
        print("✅ NHIA patient surgery pack payment test completed successfully!")
        return True
    
    def test_regular_patient_surgery_pack_payment(self):
        """Test regular patient full payment for surgery packs"""
        print("\n=== Testing Regular Patient Surgery Pack Payment ===")
        
        # Create surgery for regular patient
        surgery = Surgery.objects.create(
            patient=self.regular_patient,
            surgery_type=self.surgery_type,
            surgeon=self.doctor,
            scheduled_date=timezone.now() + timedelta(days=1),
            status='scheduled',
            theatre=self.theatre
        )
        
        # Create pack order for surgery
        pack_order = PackOrder.objects.create(
            pack=self.medical_pack,
            patient=self.regular_patient,
            surgery=surgery,
            ordered_by=self.doctor,
            scheduled_date=surgery.scheduled_date
        )
        
        print(f"1. Created surgery for regular patient: {surgery}")
        print(f"2. Created pack order: {pack_order}")
        
        # Process the pack order to create prescription
        prescription = pack_order.process_order(self.doctor)
        print(f"3. Processed pack order, created prescription: #{prescription.id}")
        
        # Check that invoice was created for surgery
        invoice = surgery.invoice
        self.assertIsNotNone(invoice, "Surgery invoice should be created")
        print(f"4. Surgery invoice created: #{invoice.invoice_number}")
        
        # Verify regular patient (not NHIA)
        is_nhia = surgery.patient.patient_type == 'nhia'
        self.assertFalse(is_nhia, "Patient should not be identified as NHIA")
        print("5. Patient correctly identified as regular (non-NHIA)")
        
        # Check invoice items for proper pricing
        invoice_items = invoice.items.all()
        self.assertGreater(len(invoice_items), 0, "Invoice should have items")
        
        # Get the pack item
        pack_item = None
        for item in invoice_items:
            if "Medical Pack" in item.description:
                pack_item = item
                break
        
        self.assertIsNotNone(pack_item, "Should find medical pack item in invoice")
        
        # Verify that the pack cost reflects full payment for regular patients
        original_pack_cost = self.medical_pack.get_total_cost()
        
        self.assertEqual(
            pack_item.total_amount, 
            original_pack_cost,
            f"Regular patient should pay full pack cost. Expected: {original_pack_cost}, Got: {pack_item.total_amount}"
        )
        
        print(f"6. Original pack cost: ₦{original_pack_cost}")
        print(f"7. Regular patient pays (100%): ₦{pack_item.total_amount}")
        
        print("✅ Regular patient surgery pack payment test completed successfully!")
        return True

def main():
    """Main function to run the tests"""
    print("NHIA Patient Surgery Pack Payment Integration Test")
    print("=" * 50)
    
    # Create test case instance
    test_case = NHIASurgeryPackPaymentTestCase()
    test_case.setUp()
    
    try:
        # Run tests
        nhia_test = test_case.test_nhia_patient_surgery_pack_payment()
        regular_test = test_case.test_regular_patient_surgery_pack_payment()
        
        if nhia_test and regular_test:
            print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY! 🎉")
            print("\nNHIA Patient Surgery Pack Payment Integration is working correctly:")
            print("✅ NHIA patients pay 10% of surgery pack costs")
            print("✅ Regular patients pay 100% of surgery pack costs")
            print("✅ Proper invoice creation with correct pricing")
            print("✅ Integration between theatre and billing modules")
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