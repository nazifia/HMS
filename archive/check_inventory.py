#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import MedicationInventory, Dispensary, Prescription

def check_inventory():
    """Check inventory for prescription #33"""
    dispensary = Dispensary.objects.first()
    prescription = Prescription.objects.get(id=33)
    
    print(f'Dispensary: {dispensary}')
    print(f'Prescription items: {prescription.items.count()}')
    print('Checking inventory for each medication in prescription #33:')
    
    for item in prescription.items.all():
        inventory = MedicationInventory.objects.filter(
            medication=item.medication, 
            dispensary=dispensary
        )
        print(f'{item.medication.name}: {inventory.count()} records')
        if inventory.count() > 0:
            inv = inventory.first()
            print(f'  Stock quantity: {inv.stock_quantity}')
    
    print('\nAll medications with inventory in the system:')
    for inv in MedicationInventory.objects.all():
        print(f'{inv.medication.name} at {inv.dispensary.name}: {inv.stock_quantity}')

if __name__ == '__main__':
    check_inventory()