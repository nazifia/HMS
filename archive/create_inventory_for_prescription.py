#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary, Medication, MedicationInventory
from pharmacy.models import Prescription

def create_inventory_for_prescription():
    """Create inventory records for prescription #33 medications at THEATRE-PH"""
    # Get THEATRE-PH dispensary
    try:
        dispensary = Dispensary.objects.get(name='THEATRE-PH')
        print(f'Using dispensary: {dispensary.name} (ID: {dispensary.id})')
    except Dispensary.DoesNotExist:
        print('THEATRE-PH dispensary not found!')
        return

    # Get prescription #33
    try:
        prescription = Prescription.objects.get(id=33)
        print(f'Processing prescription #{prescription.id}')
    except Prescription.DoesNotExist:
        print('Prescription #33 not found!')
        return

    print('Creating inventory for prescription items:')
    for item in prescription.items.all():
        print(f'  - {item.medication.name}')
        
        # Create or update inventory record
        inventory, created = MedicationInventory.objects.get_or_create(
            medication=item.medication,
            dispensary=dispensary,
            defaults={
                'stock_quantity': 100,  # Set initial stock to 100
                'reorder_level': 10     # Set reorder level to 10
            }
        )
        
        if created:
            print(f'    Created new inventory record with {inventory.stock_quantity} in stock')
        else:
            # If inventory already exists, update stock quantity if it's low
            if inventory.stock_quantity < 50:
                inventory.stock_quantity = 100
                inventory.save()
                print(f'    Updated existing inventory record to {inventory.stock_quantity} in stock')
            else:
                print(f'    Existing inventory record has {inventory.stock_quantity} in stock')

if __name__ == '__main__':
    create_inventory_for_prescription()