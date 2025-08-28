#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary, Medication, MedicationInventory, ActiveStore, ActiveStoreInventory

def test_dispensary_functionality():
    """Test dispensary selection and inventory checking functionality"""
    print("Testing dispensary functionality...")
    
    # Check if THEATRE-PH dispensary exists
    try:
        theatre_ph = Dispensary.objects.get(name='THEATRE-PH')
        print(f"THEATRE-PH dispensary exists with ID: {theatre_ph.id}")
    except Dispensary.DoesNotExist:
        print("THEATRE-PH dispensary does not exist")
        return
    
    # Check if it has an active store
    active_store = getattr(theatre_ph, 'active_store', None)
    if active_store:
        print(f"THEATRE-PH has an active store: {active_store.name}")
    else:
        print("THEATRE-PH does not have an active store")
    
    # Create a test medication with a unique name
    unique_med_name = 'Test Medication For Dispensary Testing'
    medication, created = Medication.objects.get_or_create(
        name=unique_med_name,
        defaults={
            'generic_name': 'Test Generic',
            'description': 'Test medication for dispensary functionality testing',
            'price': 10.00,
            'is_active': True
        }
    )
    if created:
        print(f"Created test medication: {medication.name}")
    else:
        print(f"Using existing test medication: {medication.name}")
    
    # Add inventory to the dispensary using ActiveStoreInventory
    if active_store:
        inventory, created = ActiveStoreInventory.objects.get_or_create(
            medication=medication,
            active_store=active_store,
            defaults={
                'stock_quantity': 50,
                'reorder_level': 10
            }
        )
        if created:
            print(f"Created ActiveStoreInventory for {medication.name} with {inventory.stock_quantity} units")
        else:
            print(f"Found existing ActiveStoreInventory for {medication.name} with {inventory.stock_quantity} units")
    
    # Also add to legacy MedicationInventory for comparison
    legacy_inventory, created = MedicationInventory.objects.get_or_create(
        medication=medication,
        dispensary=theatre_ph,
        defaults={
            'stock_quantity': 30,
            'reorder_level': 5
        }
    )
    if created:
        print(f"Created MedicationInventory for {medication.name} with {legacy_inventory.stock_quantity} units")
    else:
        print(f"Found existing MedicationInventory for {medication.name} with {legacy_inventory.stock_quantity} units")
    
    print("Test completed successfully!")

if __name__ == '__main__':
    test_dispensary_functionality()