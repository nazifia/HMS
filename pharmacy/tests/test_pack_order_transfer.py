from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from pharmacy.models import (
    Medication, MedicationCategory, MedicalPack, MedicalPackItem, PackOrder,
    Dispensary, ActiveStore, ActiveStoreInventory, ActiveStoreBatch, MedicationInventory
)
from patients.models import Patient
from datetime import timedelta

User = get_user_model()


class PackOrderTransferTest(TestCase):
    """Tests for pack order processing and transfers"""

    def setUp(self):
        """Set up test data for pack order tests"""
        # Create test user
        self.user = User.objects.create_user(
            phone_number='1234567890',
            username='testuser',
            password='testpass123'
        )

        # Create medication category
        self.category = MedicationCategory.objects.create(
            name='Test Category'
        )

        # Create medications
        self.medication1 = Medication.objects.create(
            name='Paracetamol',
            category=self.category,
            dosage_form='Tablet',
            strength='500mg',
            price=10.00
        )

        self.medication2 = Medication.objects.create(
            name='Amoxicillin',
            category=self.category,
            dosage_form='Capsule',
            strength='250mg',
            price=15.00
        )

        # Create dispensary (ActiveStore is auto-created via signal)
        self.dispensary = Dispensary.objects.create(
            name='Main Dispensary'
        )

        # Get the auto-created active store
        self.active_store = self.dispensary.active_store

        # Create medical pack
        self.pack = MedicalPack.objects.create(
            name='Test Pack',
            pack_type='routine'
        )

        # Add items to pack
        MedicalPackItem.objects.create(
            pack=self.pack,
            medication=self.medication1,
            quantity=5
        )

        MedicalPackItem.objects.create(
            pack=self.pack,
            medication=self.medication2,
            quantity=3
        )

        # Create test patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth=timezone.now().date(),
            gender='M',
            address='Test Address',
            city='Test City',
            state='Test State'
        )

        # Create pack order
        self.pack_order = PackOrder.objects.create(
            patient=self.patient,
            pack=self.pack,
            ordered_by=self.user
        )

    def test_pack_order_creation(self):
        """Test that pack order is created correctly"""
        self.assertEqual(self.pack_order.status, 'pending')
        self.assertEqual(self.pack_order.pack, self.pack)
        self.assertEqual(self.pack_order.patient, self.patient)
        self.assertEqual(self.pack_order.ordered_by, self.user)

    def test_active_store_auto_created(self):
        """Test that ActiveStore is auto-created when Dispensary is created"""
        self.assertIsNotNone(self.active_store)
        self.assertEqual(self.active_store.dispensary, self.dispensary)
        self.assertEqual(self.dispensary.active_store, self.active_store)

    def test_active_store_unique_per_dispensary(self):
        """Test that each dispensary can only have one active store (OneToOne)"""
        # Attempting to create another ActiveStore for the same dispensary should fail
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            ActiveStore.objects.create(
                dispensary=self.dispensary,
                name='Duplicate Active Store',
                capacity=1000
            )

    def test_active_store_inventory_unique_constraint(self):
        """Test that ActiveStoreInventory has unique constraint on (medication, active_store)"""
        from django.db.utils import IntegrityError

        future_date = timezone.now().date() + timedelta(days=365)

        # Create first inventory record
        ActiveStoreInventory.objects.create(
            medication=self.medication1,
            active_store=self.active_store,
            batch_number='BATCH001',
            stock_quantity=10,
            expiry_date=future_date,
            unit_cost=8.00
        )

        # Attempting to create another inventory for same medication+active_store should fail
        with self.assertRaises(IntegrityError):
            ActiveStoreInventory.objects.create(
                medication=self.medication1,
                active_store=self.active_store,
                batch_number='BATCH002',
                stock_quantity=5,
                expiry_date=future_date,
                unit_cost=9.00
            )

    def test_medical_pack_items(self):
        """Test that medical pack items are created correctly"""
        items = self.pack.items.all()
        self.assertEqual(items.count(), 2)

        item1 = items.get(medication=self.medication1)
        self.assertEqual(item1.quantity, 5)

        item2 = items.get(medication=self.medication2)
        self.assertEqual(item2.quantity, 3)

    def test_dispensary_active_store_relationship(self):
        """Test the OneToOne relationship between Dispensary and ActiveStore"""
        # Accessing active_store from dispensary should work
        self.assertEqual(self.dispensary.active_store, self.active_store)

        # Accessing dispensary from active_store should work
        self.assertEqual(self.active_store.dispensary, self.dispensary)

    def test_pack_order_process_creates_prescription(self):
        """Test that processing a pack order creates a prescription"""
        # Add inventory to active store for processing
        future_date = timezone.now().date() + timedelta(days=365)

        inventory1 = ActiveStoreInventory.objects.create(
            medication=self.medication1,
            active_store=self.active_store,
            batch_number='BATCH001',
            stock_quantity=10,
            expiry_date=future_date,
            unit_cost=8.00
        )

        inventory2 = ActiveStoreInventory.objects.create(
            medication=self.medication2,
            active_store=self.active_store,
            batch_number='BATCH002',
            stock_quantity=10,
            expiry_date=future_date,
            unit_cost=12.00
        )

        # Create batches for FIFO processing
        ActiveStoreBatch.objects.create(
            active_inventory=inventory1,
            batch_number='BATCH001',
            quantity=10,
            expiry_date=future_date,
            unit_cost=8.00
        )

        ActiveStoreBatch.objects.create(
            active_inventory=inventory2,
            batch_number='BATCH002',
            quantity=10,
            expiry_date=future_date,
            unit_cost=12.00
        )

        # Process the pack order
        prescription = self.pack_order.process_order(self.user)

        # Check that pack order status is updated
        self.assertEqual(self.pack_order.status, 'ready')

        # Check that prescription is created
        self.assertIsNotNone(prescription)
        self.assertEqual(prescription.status, 'approved')
        self.assertEqual(prescription.patient, self.patient)

        # Check that prescription items were created
        self.assertEqual(prescription.items.count(), 2)
