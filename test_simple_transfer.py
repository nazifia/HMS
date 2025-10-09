import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import CustomUser
from pharmacy.models import InterDispensaryTransfer, Medication, Dispensary, MedicationInventory

def test_transfer():
    print("Testing Inter-Dispensary Transfers")
    
    try:
        # Create test data
        user, _ = CustomUser.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com', 'is_staff': True}
        )
        
        source_disp, _ = Dispensary.objects.get_or_create(
            name='Source Dispensary',
            defaults={'location': 'Location A', 'is_active': True}
        )
        
        dest_disp, _ = Dispensary.objects.get_or_create(
            name='Dest Dispensary', 
            defaults={'location': 'Location B', 'is_active': True}
        )
        
        medication, created = Medication.objects.get_or_create(
            name='Test Medication' + str(user.id),  # Make it unique
            defaults={'dosage_form': 'Tablet', 'strength': '500mg', 'price': 50.00, 'is_active': True}
        )
        
        if not created:
            # Use the existing medication by its ID
            medication = Medication.objects.filter(name__contains='Test Medication').first()
        
        # Set up inventory
        source_inventory, _ = MedicationInventory.objects.get_or_create(
            medication=medication,
            dispensary=source_disp,
            defaults={'stock_quantity': 100, 'reorder_level': 10}
        )
        source_inventory.stock_quantity = 100
        source_inventory.save()
        
        print("Test data created successfully")
        
        # Test transfer creation
        transfer = InterDispensaryTransfer.create_transfer(
            medication=medication,
            from_dispensary=source_disp,
            to_dispensary=dest_disp,
            quantity=25,
            requested_by=user,
            notes="Test transfer"
        )
        
        print(f"Transfer created: #{transfer.id}")
        
        # Test availability check
        can_transfer, message = transfer.check_availability()
        print(f"Availability check: {can_transfer} - {message}")
        
        # Test approval
        transfer.approve_transfer(user)
        print(f"Transfer approved, status: {transfer.status}")
        
        # Test execution
        transfer.execute_transfer(user)
        print(f"Transfer executed, status: {transfer.status}")
        
        # Verify inventory
        source_inventory.refresh_from_db()
        dest_inventory = MedicationInventory.objects.get(medication=medication, dispensary=dest_disp)
        
        print(f"Source stock: {source_inventory.stock_quantity} (expected: 75)")
        print(f"Dest stock: {dest_inventory.stock_quantity} (expected: 25)")
        
        if source_inventory.stock_quantity == 75 and dest_inventory.stock_quantity == 25:
            print("SUCCESS: Inventory levels are correct!")
            return True
        else:
            print("FAILURE: Inventory levels are incorrect!")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == '__main__':
    success = test_transfer()
    sys.exit(0 if success else 1)
