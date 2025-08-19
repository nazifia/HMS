from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from pharmacy.models import (
    MedicationCategory, Medication, Supplier, Prescription, PrescriptionItem
)

class PharmacyModelsTest(TestCase):
    def setUp(self):
        # Create test data
        self.category = MedicationCategory.objects.create(
            name="Antibiotics",
            description="Antibiotic medications"
        )
        
        self.medication = Medication.objects.create(
            name="Amoxicillin",
            generic_name="Amoxicillin",
            category=self.category,
            description="Antibiotic medication",
            dosage_form="Capsule",
            strength="500mg",
            manufacturer="PharmaCorp",
            price=Decimal('25.00'),
            reorder_level=10
        )
        
        self.supplier = Supplier.objects.create(
            name="MedSupply Inc.",
            contact_person="John Doe",
            email="john@medsupply.com",
            phone_number="1234567890",
            address="123 Medical Street",
            city="Healthville",
            state="Medstate",
            country="Medland"
        )
        
        # Create a test user (using the existing CustomUser model)
        from accounts.models import CustomUser
        self.user = CustomUser.objects.create_user(
            phone_number="9876543210",
            username="testuser",
            password="testpass123"
        )
        
        # Create a test patient (using the existing Patient model)
        from patients.models import Patient
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            gender="M",
            address="456 Patient Street",
            city="Patientville",
            state="Patientstate",
            country="Patientland",
            patient_id="P000000001"
        )
        
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.user,
            prescription_date=timezone.now().date(),
            diagnosis="Bacterial infection"
        )
        
        self.prescription_item = PrescriptionItem.objects.create(
            prescription=self.prescription,
            medication=self.medication,
            dosage="1 capsule",
            frequency="Twice daily",
            duration="7 days",
            quantity=14
        )

    def test_medication_category_creation(self):
        """Test that medication category is created correctly"""
        self.assertEqual(self.category.name, "Antibiotics")
        self.assertEqual(self.category.description, "Antibiotic medications")
        self.assertEqual(str(self.category), "Antibiotics")

    def test_medication_creation(self):
        """Test that medication is created correctly"""
        self.assertEqual(self.medication.name, "Amoxicillin")
        self.assertEqual(self.medication.generic_name, "Amoxicillin")
        self.assertEqual(self.medication.category, self.category)
        self.assertEqual(self.medication.price, Decimal('25.00'))
        self.assertEqual(str(self.medication), "Amoxicillin (500mg)")

    def test_supplier_creation(self):
        """Test that supplier is created correctly"""
        self.assertEqual(self.supplier.name, "MedSupply Inc.")
        self.assertEqual(self.supplier.contact_person, "John Doe")
        self.assertTrue(self.supplier.is_active)
        self.assertEqual(str(self.supplier), "MedSupply Inc.")

    def test_prescription_creation(self):
        """Test that prescription is created correctly"""
        self.assertEqual(self.prescription.patient, self.patient)
        self.assertEqual(self.prescription.doctor, self.user)
        self.assertEqual(self.prescription.diagnosis, "Bacterial infection")
        self.assertEqual(self.prescription.status, "pending")
        self.assertEqual(str(self.prescription), f"Prescription for John Doe - {self.prescription.prescription_date}")

    def test_prescription_item_creation(self):
        """Test that prescription item is created correctly"""
        self.assertEqual(self.prescription_item.prescription, self.prescription)
        self.assertEqual(self.prescription_item.medication, self.medication)
        self.assertEqual(self.prescription_item.quantity, 14)
        self.assertEqual(self.prescription_item.quantity_dispensed_so_far, 0)
        self.assertFalse(self.prescription_item.is_dispensed)
        self.assertEqual(str(self.prescription_item), "Amoxicillin (14) for John Doe")

    def test_prescription_total_price(self):
        """Test that prescription calculates total price correctly"""
        expected_total = self.medication.price * self.prescription_item.quantity
        self.assertEqual(self.prescription.get_total_prescribed_price(), expected_total)

    def test_prescription_item_remaining_quantity(self):
        """Test that prescription item calculates remaining quantity correctly"""
        self.assertEqual(self.prescription_item.remaining_quantity_to_dispense, 14)
        
        # Test after dispensing some quantity
        self.prescription_item.quantity_dispensed_so_far = 5
        self.prescription_item.save()
        self.assertEqual(self.prescription_item.remaining_quantity_to_dispense, 9)