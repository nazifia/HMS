#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary, ActiveStore, ActiveStoreInventory, MedicationInventory

def check_theatre_ph_inventory():
    """Check inventory situation for THEATRE-PH dispensary"""
    try:
        dispensary = Dispensary.objects.get(name='THEATRE-PH')
        print(f'Dispensary: {dispensary.name} (ID: {dispensary.id})')
        
        # Check if it has an active store
        active_store = getattr(dispensary, 'active_store', None)
        print(f'Active Store: {active_store}')
        
        if active_store:
            active_store_inventory_count = ActiveStoreInventory.objects.filter(active_store=active_store).count()
            print(f'Active Store Inventory Count: {active_store_inventory_count}')
        
        medication_inventory_count = MedicationInventory.objects.filter(dispensary=dispensary).count()
        print(f'Medication Inventory Count: {medication_inventory_count}')
        
        # List the medication inventory items
        if medication_inventory_count > 0:
            print('\nMedication Inventory Items:')
            for item in MedicationInventory.objects.filter(dispensary=dispensary):
                print(f'  - {item.medication.name}: {item.stock_quantity} units')
        
        # List the active store inventory items
        if active_store and active_store_inventory_count > 0:
            print('\nActive Store Inventory Items:')
            for item in ActiveStoreInventory.objects.filter(active_store=active_store):
                print(f'  - {item.medication.name}: {item.stock_quantity} units')
                
    except Dispensary.DoesNotExist:
        print('THEATRE-PH dispensary not found!')

if __name__ == '__main__':
    check_theatre_ph_inventory()