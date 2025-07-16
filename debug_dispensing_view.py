import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, Dispensary

def debug_dispensing_logic():
    """Debug the exact logic used in the dispensing view"""
    
    print("Debugging Dispensing View Logic")
    print("=" * 50)
    
    try:
        prescription = Prescription.objects.get(id=3)
        print(f"✓ Found prescription {prescription.id}")
        print(f"  Status: {prescription.status}")
        print(f"  Patient: {prescription.patient.get_full_name()}")
        
        # Check if prescription is in a dispensable state
        if prescription.status in ['cancelled', 'dispensed']:
            print(f"❌ Prescription status '{prescription.status}' prevents dispensing")
            return False
        else:
            print(f"✓ Prescription status '{prescription.status}' allows dispensing")
        
        # Get pending items (same logic as in the view)
        pending_items = prescription.items.filter(is_dispensed=False).select_related('medication')
        
        print(f"  Total items: {prescription.items.count()}")
        print(f"  Pending items: {pending_items.count()}")
        
        if not pending_items.exists():
            print("❌ No pending items found - this would redirect to prescription detail")
            return False
        else:
            print("✓ Pending items found - dispensing page should show items")
        
        # List all pending items
        for item in pending_items:
            print(f"    - Item ID {item.id}: {item.medication.name}")
            print(f"      Prescribed: {item.quantity}")
            print(f"      Dispensed: {item.quantity_dispensed_so_far}")
            print(f"      Remaining: {item.remaining_quantity_to_dispense}")
            print(f"      Is dispensed: {item.is_dispensed}")
        
        # Check dispensaries
        dispensaries = Dispensary.objects.filter(is_active=True).order_by('name')
        print(f"  Active dispensaries: {dispensaries.count()}")
        
        for dispensary in dispensaries:
            print(f"    - {dispensary.name} (ID: {dispensary.id})")
        
        print("\n✅ All logic checks passed - items should be visible on dispensing page")
        return True
        
    except Prescription.DoesNotExist:
        print("❌ Prescription 3 not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_dispensing_logic()
