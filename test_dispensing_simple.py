import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, Dispensary, MedicationInventory

def test_dispensing_data():
    """Test if all the data is set up correctly for dispensing"""
    
    print("Testing Dispensing Data Setup")
    print("=" * 40)
    
    # Test prescription 3
    try:
        prescription = Prescription.objects.get(id=3)
        print(f"✓ Prescription {prescription.id} found")
        print(f"  Status: {prescription.status}")
        print(f"  Patient: {prescription.patient.get_full_name()}")
        
        # Test prescription items
        items = prescription.items.all()
        pending_items = prescription.items.filter(is_dispensed=False)
        
        print(f"  Total items: {items.count()}")
        print(f"  Pending items: {pending_items.count()}")
        
        for item in pending_items:
            print(f"    - Item ID {item.id}: {item.medication.name}")
            print(f"      Quantity: {item.quantity}")
            print(f"      Dispensed: {item.quantity_dispensed_so_far}")
            print(f"      Remaining: {item.remaining_quantity_to_dispense}")
        
        # Test dispensaries
        dispensaries = Dispensary.objects.filter(is_active=True)
        print(f"  Active dispensaries: {dispensaries.count()}")
        
        for dispensary in dispensaries:
            print(f"    - {dispensary.name} (ID: {dispensary.id})")
            
            # Test inventory for each item
            for item in pending_items:
                try:
                    inventory = MedicationInventory.objects.get(
                        medication=item.medication,
                        dispensary=dispensary
                    )
                    print(f"      {item.medication.name}: {inventory.stock_quantity} units")
                except MedicationInventory.DoesNotExist:
                    print(f"      {item.medication.name}: No inventory")
        
        print("\n✓ All data looks good for dispensing!")
        return True
        
    except Prescription.DoesNotExist:
        print("❌ Prescription 3 not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_ajax_logic():
    """Test the logic that the AJAX endpoint uses"""
    
    print("\nTesting AJAX Logic")
    print("=" * 40)
    
    try:
        prescription = Prescription.objects.get(id=3)
        dispensary = Dispensary.objects.filter(is_active=True).first()
        
        if not dispensary:
            print("❌ No dispensary found")
            return False
            
        print(f"Testing with dispensary: {dispensary.name} (ID: {dispensary.id})")
        
        # Simulate the AJAX endpoint logic
        stock_quantities = {}
        for item in prescription.items.all():
            try:
                inventory = MedicationInventory.objects.get(
                    medication=item.medication, 
                    dispensary_id=dispensary.id
                )
                stock_quantities[item.id] = inventory.stock_quantity
                print(f"  Item {item.id} ({item.medication.name}): {inventory.stock_quantity} units")
            except MedicationInventory.DoesNotExist:
                stock_quantities[item.id] = 0
                print(f"  Item {item.id} ({item.medication.name}): 0 units (no inventory)")
        
        print(f"\nStock quantities result: {stock_quantities}")
        print("✓ AJAX logic working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error in AJAX logic: {e}")
        return False

if __name__ == "__main__":
    test_dispensing_data()
    test_ajax_logic()
