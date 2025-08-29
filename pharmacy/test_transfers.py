from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    Medication, MedicationCategory, Pack, PackItem, PackOrder, 
    Dispensary, ActiveStore, ActiveStoreInventory, MedicationInventory
)

User = get_user_model()

class PackOrderTransferTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
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
        
        # Create dispensary
        self.dispensary = Dispensary.objects.create(
            name='Main Dispensary'
        )
        
        # Create active store
        self.active_store = ActiveStore.objects.create(
            dispensary=self.dispensary,
            name='Main Active Store',
            capacity=1000
        )
        
        # Create pack
        self.pack = Pack.objects.create(
            name='Test Pack'
        )
        
        # Add items to pack
        PackItem.objects.create(
            pack=self.pack,
            medication=self.medication1,
            quantity=5
        )
        
        PackItem.objects.create(
            pack=self.pack,
            medication=self.medication2,
            quantity=3
        )
        
        # Add inventory to active store
        ActiveStoreInventory.objects.create(
            medication=self.medication1,
            active_store=self.active_store,
            batch_number='BATCH001',
            stock_quantity=10,
            expiry_date=timezone.now().date(),
            unit_cost=8.00
        )
        
        ActiveStoreInventory.objects.create(
            medication=self.medication2,
            active_store=self.active_store,
            batch_number='BATCH002',
            stock_quantity=10,
            expiry_date=timezone.now().date(),
            unit_cost=12.00
        )
        
        # Create pack order
        self.pack_order = PackOrder.objects.create(
            patient=None,  # For simplicity in test
            pack=self.pack,
            ordered_by=self.user
        )

    def test_transfer_from_active_store_to_dispensary(self):
        """Test that medications are transferred from active store to dispensary"""
        # Ensure dispensary inventory is empty initially
        self.assertEqual(MedicationInventory.objects.filter(dispensary=self.dispensary).count(), 0)
        
        # Process the pack order
        prescription = self.pack_order.process_order(self.user)
        
        # Check that pack order status is updated
        self.assertEqual(self.pack_order.status, 'ready')
        
        # Check that prescription is created
        self.assertIsNotNone(prescription)
        
        # Check that medications were transferred to dispensary
        # (This would be verified by checking MedicationInventory records)
        medication1_inventory = MedicationInventory.objects.filter(
            medication=self.medication1,
            dispensary=self.dispensary
        ).first()
        
        medication2_inventory = MedicationInventory.objects.filter(
            medication=self.medication2,
            dispensary=self.dispensary
        ).first()
        
        # Verify that inventory was created and quantities are correct
        self.assertIsNotNone(medication1_inventory)
        self.assertEqual(medication1_inventory.stock_quantity, 5)
        
        self.assertIsNotNone(medication2_inventory)
        self.assertEqual(medication2_inventory.stock_quantity, 3)
        
        # Verify that active store inventory was reduced
        active_inventory1 = ActiveStoreInventory.objects.get(
            medication=self.medication1,
            active_store=self.active_store
        )
        self.assertEqual(active_inventory1.stock_quantity, 5)  # 10 - 5 = 5
        
        active_inventory2 = ActiveStoreInventory.objects.get(
            medication=self.medication2,
            active_store=self.active_store
        )
        self.assertEqual(active_inventory2.stock_quantity, 7)  # 10 - 3 = 7