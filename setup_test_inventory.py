import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, Dispensary, MedicationInventory
from django.utils import timezone

def setup_inventory_for_prescription_3():
    """Set up inventory for prescription 3"""
    try:
        prescription = Prescription.objects.get(id=3)
        dispensaries = Dispensary.objects.filter(is_active=True)
        
        print(f"Setting up inventory for Prescription {prescription.id}")
        print(f"Found {dispensaries.count()} active dispensaries")
        
        for item in prescription.items.all():
            print(f"\nMedication: {item.medication.name} (Item ID: {item.id})")
            
            for dispensary in dispensaries:
                inventory, created = MedicationInventory.objects.get_or_create(
                    medication=item.medication,
                    dispensary=dispensary,
                    defaults={
                        'stock_quantity': 100,  # Plenty of stock for testing
                        'reorder_level': 10,
                        'last_restock_date': timezone.now()
                    }
                )
                
                if created:
                    print(f"  ✓ Created inventory: {dispensary.name} - {inventory.stock_quantity} units")
                else:
                    # Update stock if it's low
                    if inventory.stock_quantity < 50:
                        inventory.stock_quantity = 100
                        inventory.save()
                        print(f"  ✓ Updated inventory: {dispensary.name} - {inventory.stock_quantity} units")
                    else:
                        print(f"  ✓ Existing inventory: {dispensary.name} - {inventory.stock_quantity} units")
        
        print(f"\n✅ Inventory setup completed for prescription {prescription.id}")
        return True
        
    except Prescription.DoesNotExist:
        print("❌ Prescription 3 not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    setup_inventory_for_prescription_3()
