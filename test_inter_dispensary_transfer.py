#!/usr/bin/env python
"""
Simple test script to validate inter-dispensary transfer functionality
"""

import os
import sys
import django

# Add the HMS directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import CustomUser
from pharmacy.models import InterDispensaryTransfer, Medication, Dispensary, MedicationInventory
from django.core.exceptions import ValidationError

def test_inter_dispensary_transfer():
    """Test basic inter-dispensary transfer functionality"""
    print("Testing Inter-Dispensary Transfer Functionality\n")
    
    try:
        # Get or create test data
        print("1. Setting up test data...")
        
        # Create test user
        user, _ = CustomUser.objects.get_or_create(
            username='test_pharmacist',
            defaults={
                'email': 'pharmacist@hms.com',
                'first_name': 'Test',
                'last_name': 'Pharmacist',
                'is_staff': True,
            }
        )
        
        # Get or create dispensaries
        source_dispensary, _ = Dispensary.objects.get_or_create(
            name='Main Pharmacy',
            defaults={
                'location': 'Building A, Floor 1',
                'is_active': True,
            }
        )
        
        dest_dispensary, _ = Dispensary.objects.get_or_create(
            name='Emergency Pharmacy',
            defaults={
                'location': 'Building B, Floor 2',
                'is_active': True,
            }
        )
        
        # Get or create medication
        medication, _ = Medication.objects.get_or_create(
            name='Paracetamol',
            defaults={
                'generic_name': 'Acetaminophen',
                'dosage_form': 'Tablet',
                'strength': '500mg',
                'price': 50.00,
                'reorder_level': 10,
                'is_active': True,
            }
        )
        
        # Set up inventory
        source_inventory, _ = MedicationInventory.objects.get_or_create(
            medication=medication,
            dispensary=source_dispensary,
            defaults={
                'stock_quantity': 100,
                'reorder_level': 10,
            }
        )
        
        # Ensure source inventory has enough stock
        source_inventory.stock_quantity = 100
        source_inventory.save()
        
        print(f"   [OK] Created test user: {user.username}")
        print(f"   [OK] Created source dispensary: {source_dispensary.name}")
        print(f"   [OK] Created destination dispensary: {dest_dispensary.name}")
        print(f"   [OK] Created medication: {medication.name}")
        print(f"   [OK] Set up inventory with {source_inventory.stock_quantity} units")
        
        # Test 1: Create Transfer
        print("\n2. Testing transfer creation...")
        transfer = InterDispensaryTransfer.create_transfer(
            medication=medication,
            from_dispensary=source_dispensary,
            to_dispensary=dest_dispensary,
            quantity=25,
            requested_by=user,
            notes="Test transfer - 25 units of paracetamol"
        )
        
        print(f"   [OK] Created transfer #{transfer.id}")
        print(f"   [OK] Status: {transfer.status}")
        print(f"   [OK] From: {transfer.from_dispensary.name}")
        print(f"   [OK] To: {transfer.to_dispensary.name}")
        print(f"   [OK] Quantity: {transfer.quantity}")
        print(f"   [OK] Notes: {transfer.notes}")
        
        # Test 2: Check availability
        print("\n3. Testing availability check...")
        can_transfer, message = transfer.check_availability()
        print(f"   Availability check: {'PASS' if can_transfer else 'FAIL'}")
        print(f"   Message: {message}")
        
        # Test 3: Approve Transfer
        print("\n4. Testing transfer approval...")
        try:
            transfer.approve_transfer(user)
            print(f"   [OK] Transfer approved successfully")
            print(f"   [OK] Status changed to: {transfer.status}")
            print(f"   [OK] Approved by: {transfer.approved_by.username}")
        except Exception as e:
            print(f"   [FAIL] Approval failed: {e}")
            return False
        
        # Test 4: Execute Transfer
        print("\n5. Testing transfer execution...")
        try:
            transfer.execute_transfer(user)
            print(f"   [OK] Transfer executed successfully")
            print(f"   [OK] Status changed to: {transfer.status}")
            print(f"   [OK] Executed by: {transfer.transferred_by.username}")
        except Exception as e:
            print(f"   [FAIL] Execution failed: {e}")
            return False
        
        # Test 5: Verify inventory updates
        print("\n6. Verifying inventory updates...")
        source_inventory.refresh_from_db()
        
        dest_inventory = MedicationInventory.objects.filter(
            medication=medication,
            dispensary=dest_dispensary
        ).first()
        
        if dest_inventory:
            print(f"   ✓ Destination inventory created")
            print(f"   ✓ Source inventory now has: {source_inventory.stock_quantity} units (expected: 75)")
            print(f"   ✓ Destination inventory now has: {dest_inventory.stock_quantity} units (expected: 25)")
            
            if source_inventory.stock_quantity == 75 and dest_inventory.stock_quantity == 25:
                print("   ✓ Inventory amounts are correct!")
            else:
                print("   ✗ Inventory amounts are incorrect!")
                return False
        else:
            print("   ✗ Destination inventory was not created!")
            return False
        
        # Test 6: Test constraints
        print("\n7. Testing transfer constraints...")
        
        try:
            # Test self-transfer prevention
            InterDispensaryTransfer.create_transfer(
                medication=medication,
                from_dispensary=source_dispensary,
                to_dispensary=source_dispensary,  # Same dispensary
                quantity=10,
                requested_by=user
            )
            print("   ✗ Self-transfer prevention failed!")
            return False
        except ValueError:
            print("   ✓ Self-transfer prevention working!")
        
        try:
            # Test insufficient stock prevention
            InterDispensaryTransfer.create_transfer(
                medication=medication,
                from_dispensary=source_dispensary,
                to_dispensary=dest_dispensary,
                quantity=1000,  # More than available
                requested_by=user
            )
            print("   ✗ Insufficient stock prevention failed!")
            return False
        except ValueError:
            print("   ✓ Insufficient stock prevention working!")
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED! ✅")
        print("Inter-dispensary transfer functionality is working correctly.")
        print("="*50)
        
        # Clean up test data (optional - uncomment if you want to cleanup)
        # transfer.delete()
        # MedicationInventory.objects.filter(medication=medication).delete()
        # medication.delete()
        # Dispensary.objects.filter(name__in=['Main Pharmacy', 'Emergency Pharmacy']).delete()
        # user.delete()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_inter_dispensary_transfer()
    sys.exit(0 if success else 1)
