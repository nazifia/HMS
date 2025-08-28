#!/usr/bin/env python
"""
Test script for Pharmacy Pack System Functionality

This script tests:
1. Medical Pack CRUD operations
2. Pack Item management
3. Pack Order creation and processing
4. Prescription creation from pack orders
5. Integration between pharmacy and clinical modules
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from pharmacy.models import MedicalPack, PackItem, PackOrder, Medication, MedicationCategory
from patients.models import Patient
from accounts.models import CustomUser

User = get_user_model()

class PharmacyPackSystemTestCase(TestCase):
    """Test case for the complete pharmacy pack system"""

    def setUp(self):
        """Set up test data"""
        print("Setting up test data...")
        
        # Create or get test user (pharmacist)
        try:
            self.pharmacist = User.objects.create_user(
                username='testpharmacist',
                email='pharmacist@test.com',
                password='testpass123',
                phone_number='1234567890',
                first_name='Test',
                last_name='Pharmacist'
            )
        except Exception as e:
            # User already exists, get it
            self.pharmacist = User.objects.get(username='testpharmacist')
        
        # Create or get test doctor
        try:
            self.doctor = User.objects.create_user(
                username='testdoctor',
                email='doctor@test.com',
                password='testpass123',
                phone_number='0987654321',
                first_name='Test',
                last_name='Doctor'
            )
        except Exception as e:
            # User already exists, get it
            self.doctor = User.objects.get(username='testdoctor')
        
        # Create or get test patient
        try:
            self.patient = Patient.objects.create(
                first_name='John',
                last_name='Doe',
                date_of_birth='1980-01-01',
                gender='male',
                phone_number='1234567890',
                email='john.doe@example.com',
                patient_type='paying'
            )
        except Exception as e:
            # Patient already exists, get it
            self.patient = Patient.objects.get(email='john.doe@example.com')
        
        # Create or get medication category
        try:
            self.med_category = MedicationCategory.objects.create(
                name='Surgical Supplies',
                description='Medical supplies for surgical procedures'
            )
        except Exception as e:
            # Category already exists, get it
            self.med_category = MedicationCategory.objects.get(name='Surgical Supplies')
        
        # Create or get test medications
        try:
            self.medication1 = Medication.objects.create(
                name='Surgical Gauze',
                category=self.med_category,
                dosage_form='pad',
                strength='4x4 inch',
                price=Decimal('5.00'),
                is_active=True
            )
        except Exception as e:
            # Medication already exists, get it
            self.medication1 = Medication.objects.get(name='Surgical Gauze')
        
        try:
            self.medication2 = Medication.objects.create(
                name='Antiseptic Solution',
                category=self.med_category,
                dosage_form='solution',
                strength='250ml',
                price=Decimal('15.00'),
                is_active=True
            )
        except Exception as e:
            # Medication already exists, get it
            self.medication2 = Medication.objects.get(name='Antiseptic Solution')
        
        # Set up test client
        self.client = Client()
        self.client.login(username='testpharmacist', password='testpass123')
        
        print("Test data setup completed!")

    def test_medical_pack_crud_operations(self):
        """Test CRUD operations for medical packs"""
        print("\n=== Testing Medical Pack CRUD Operations ===")
        
        # Test CREATE operation
        print("1. Testing pack creation...")
        pack_data = {
            'name': 'Basic Surgery Pack',
            'description': 'Standard pack for basic surgical procedures',
            'pack_type': 'surgery',
            'surgery_type': 'general',
            'risk_level': 'medium',
            'requires_approval': False,
            'is_active': True
        }
        
        pack = MedicalPack.objects.create(
            name=pack_data['name'],
            description=pack_data['description'],
            pack_type=pack_data['pack_type'],
            surgery_type=pack_data['surgery_type'],
            risk_level=pack_data['risk_level'],
            requires_approval=pack_data['requires_approval'],
            is_active=pack_data['is_active'],
            created_by=self.pharmacist
        )
        
        # Verify pack was created
        self.assertIsNotNone(pack)
        self.assertEqual(pack.name, 'Basic Surgery Pack')
        self.assertEqual(pack.pack_type, 'surgery')
        self.assertTrue(pack.is_active)
        print("✓ Pack creation successful")
        
        # Test READ operation
        print("2. Testing pack retrieval...")
        retrieved_pack = MedicalPack.objects.get(id=pack.id)
        self.assertEqual(retrieved_pack.name, pack.name)
        print("✓ Pack retrieval successful")
        
        # Test UPDATE operation
        print("3. Testing pack update...")
        pack.description = 'Updated description for basic surgery pack'
        pack.save()
        pack.refresh_from_db()
        self.assertEqual(pack.description, 'Updated description for basic surgery pack')
        print("✓ Pack update successful")
        
        # Test adding items to pack
        print("4. Testing pack item management...")
        pack_item1 = PackItem.objects.create(
            pack=pack,
            medication=self.medication1,
            quantity=10,
            item_type='consumable',
            usage_instructions='Use for wound dressing',
            is_critical=True,
            order=1
        )
        
        pack_item2 = PackItem.objects.create(
            pack=pack,
            medication=self.medication2,
            quantity=5,
            item_type='consumable',
            usage_instructions='Use for cleaning wounds',
            is_critical=False,
            order=2
        )
        
        # Verify items were added
        self.assertEqual(pack.items.count(), 2)
        self.assertEqual(pack.get_total_cost(), Decimal('125.00'))  # (10 * 5) + (5 * 15) = 125
        print("✓ Pack item management successful")
        
        print("All Medical Pack CRUD operations completed successfully!")
        return pack

    def test_pack_order_management(self):
        """Test pack order creation and management"""
        print("\n=== Testing Pack Order Management ===")
        
        # Create a medical pack first
        pack = self.test_medical_pack_crud_operations()
        
        # Test pack order creation
        print("1. Testing pack order creation...")
        pack_order = PackOrder.objects.create(
            pack=pack,
            patient=self.patient,
            ordered_by=self.doctor,
            scheduled_date=timezone.now() + timedelta(days=1),
            order_notes='Pack needed for upcoming surgery'
        )
        
        # Verify pack order was created
        self.assertIsNotNone(pack_order)
        self.assertEqual(pack_order.status, 'pending')
        self.assertEqual(pack_order.ordered_by, self.doctor)
        self.assertEqual(pack_order.patient, self.patient)
        print("✓ Pack order creation successful")
        
        # Test pack order approval
        print("2. Testing pack order approval...")
        pack_order.approve_order(self.pharmacist)
        pack_order.refresh_from_db()
        self.assertEqual(pack_order.status, 'approved')
        self.assertIsNotNone(pack_order.approved_at)
        print("✓ Pack order approval successful")
        
        print("Pack Order Management tests completed successfully!")
        return pack_order

    def test_prescription_creation_from_pack_order(self):
        """Test prescription creation from pack order"""
        print("\n=== Testing Prescription Creation from Pack Order ===")
        
        # Create pack and pack order
        pack = self.test_medical_pack_crud_operations()
        pack_order = PackOrder.objects.create(
            pack=pack,
            patient=self.patient,
            ordered_by=self.doctor,
            scheduled_date=timezone.now() + timedelta(days=1)
        )
        
        # Test prescription creation
        print("1. Testing prescription creation from pack order...")
        prescription = pack_order.create_prescription()
        
        # Verify prescription was created
        self.assertIsNotNone(prescription)
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.doctor, self.doctor)
        self.assertEqual(prescription.prescription_type, 'outpatient')
        self.assertIn('Pack order', prescription.diagnosis)
        print("✓ Prescription creation successful")
        
        # Verify prescription items were created
        print("2. Testing prescription items creation...")
        prescription_items = prescription.items.all()
        self.assertEqual(prescription_items.count(), pack.items.count())
        
        # Verify each pack item was converted to prescription item
        for pack_item in pack.items.all():
            prescription_item = prescription_items.filter(medication=pack_item.medication).first()
            self.assertIsNotNone(prescription_item)
            self.assertEqual(prescription_item.quantity, pack_item.quantity)
            self.assertEqual(prescription_item.instructions, pack_item.usage_instructions or 'Use as directed for procedure')
        print("✓ Prescription items creation successful")
        
        # Verify pack order is linked to prescription
        print("3. Testing pack order to prescription linking...")
        pack_order.refresh_from_db()
        self.assertEqual(pack_order.prescription, prescription)
        print("✓ Pack order to prescription linking successful")
        
        print("Prescription Creation tests completed successfully!")
        return pack_order, prescription

    def test_pack_order_processing_workflow(self):
        """Test the complete pack order processing workflow"""
        print("\n=== Testing Pack Order Processing Workflow ===")
        
        # Create pack and pack order
        pack = self.test_medical_pack_crud_operations()
        pack_order = PackOrder.objects.create(
            pack=pack,
            patient=self.patient,
            ordered_by=self.doctor,
            scheduled_date=timezone.now() + timedelta(days=1)
        )
        
        # Test the complete processing workflow
        print("1. Testing pack order processing...")
        prescription = pack_order.process_order(self.pharmacist)
        
        # Verify the workflow results
        pack_order.refresh_from_db()
        self.assertEqual(pack_order.status, 'ready')
        self.assertEqual(pack_order.processed_by, self.pharmacist)
        self.assertIsNotNone(pack_order.processed_at)
        self.assertIsNotNone(prescription)
        print("✓ Pack order processing successful")
        
        # Test dispensing
        print("2. Testing pack order dispensing...")
        pack_order.dispense_order(self.pharmacist)
        pack_order.refresh_from_db()
        self.assertEqual(pack_order.status, 'dispensed')
        self.assertEqual(pack_order.dispensed_by, self.pharmacist)
        self.assertIsNotNone(pack_order.dispensed_at)
        print("✓ Pack order dispensing successful")
        
        print("Pack Order Processing Workflow tests completed successfully!")
        return pack_order, prescription

    def test_pack_availability_check(self):
        """Test pack availability checking functionality"""
        print("\n=== Testing Pack Availability Check ===")
        
        # Create pack and items
        pack = self.test_medical_pack_crud_operations()
        
        # Test pack availability when items are available
        print("1. Testing pack availability with sufficient stock...")
        can_order = pack.can_be_ordered()
        self.assertTrue(can_order)
        print("✓ Pack availability check successful")
        
        print("Pack Availability Check tests completed successfully!")
        return pack

    def run_all_tests(self):
        """Run all test methods"""
        print("🚀 Starting Pharmacy Pack System Tests...\n")
        
        try:
            # Run all test methods
            self.test_medical_pack_crud_operations()
            self.test_pack_order_management()
            self.test_prescription_creation_from_pack_order()
            self.test_pack_order_processing_workflow()
            self.test_pack_availability_check()
            
            print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY! 🎉")
            print("\nPharmacy Pack System is working correctly:")
            print("✅ Medical Pack CRUD operations")
            print("✅ Pack Order management")
            print("✅ Prescription creation from pack orders")
            print("✅ Complete pack order processing workflow")
            print("✅ Pack availability checking")
            
            return True
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main function to run the tests"""
    print("Pharmacy Pack System Test Suite")
    print("=" * 40)
    
    # Create test case instance
    test_case = PharmacyPackSystemTestCase()
    test_case.setUp()
    
    # Run tests
    success = test_case.run_all_tests()
    
    if success:
        print("\n✅ All features are working correctly!")
        print("\nThe system now supports:")
        print("• Complete CRUD operations for medical packs")
        print("• Pack item management with cost calculation")
        print("• Pack order creation and status management")
        print("• Automatic prescription creation from pack orders")
        print("• Complete processing workflow (approve → process → dispense)")
        print("• Pack availability checking")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
    
    return success

if __name__ == '__main__':
    main()