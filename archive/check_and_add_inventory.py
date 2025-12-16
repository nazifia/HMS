"""
Script to check and add inventory to active store for testing transfer functionality
"""

import os
import django
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.utils import timezone
from pharmacy.models import (
    ActiveStoreInventory, Dispensary, Medication,
    BulkStoreInventory, BulkStore, MedicationTransfer
)
from django.contrib.auth import get_user_model

User = get_user_model()

def check_inventory():
    """Check current inventory status"""
    print("="*60)
    print("CHECKING INVENTORY STATUS")
    print("="*60)
    
    # Get the dispensary
    try:
        dispensary = Dispensary.objects.get(id=43)
        print(f"\n✅ Dispensary: {dispensary.name}")
        
        # Get active store
        active_store = dispensary.active_store
        print(f"✅ Active Store: {active_store.name}")
        
        # Check active store inventory
        active_inv = ActiveStoreInventory.objects.filter(active_store=active_store)
        print(f"\n📦 Active Store Inventory: {active_inv.count()} items")
        
        if active_inv.count() > 0:
            print("\nActive Store Items:")
            for item in active_inv[:10]:
                print(f"  - {item.medication.name}: {item.stock_quantity} units (Batch: {item.batch_number})")
        else:
            print("  ❌ No items in active store")
        
        # Check bulk store inventory
        bulk_store = BulkStore.objects.first()
        if bulk_store:
            print(f"\n✅ Bulk Store: {bulk_store.name}")
            bulk_inv = BulkStoreInventory.objects.filter(
                bulk_store=bulk_store,
                stock_quantity__gt=0
            )
            print(f"📦 Bulk Store Inventory: {bulk_inv.count()} items with stock")
            
            if bulk_inv.count() > 0:
                print("\nBulk Store Items (with stock):")
                for item in bulk_inv[:10]:
                    print(f"  - {item.medication.name}: {item.stock_quantity} units (Batch: {item.batch_number})")
        
        return dispensary, active_store, bulk_store
        
    except Dispensary.DoesNotExist:
        print("❌ Dispensary with ID 43 not found")
        return None, None, None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, None, None


def add_test_inventory(dispensary, active_store, bulk_store):
    """Add test inventory to active store"""
    print("\n" + "="*60)
    print("ADDING TEST INVENTORY TO ACTIVE STORE")
    print("="*60)
    
    if not bulk_store:
        print("❌ No bulk store found")
        return False
    
    # Get some medications from bulk store
    bulk_items = BulkStoreInventory.objects.filter(
        bulk_store=bulk_store,
        stock_quantity__gt=50  # At least 50 units
    )[:5]
    
    if bulk_items.count() == 0:
        print("❌ No bulk store items with sufficient stock")
        return False
    
    # Get a user for the transfer
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ No active user found")
        return False
    
    print(f"\n✅ Found {bulk_items.count()} items to transfer")
    print(f"✅ Using user: {user.get_full_name()}")
    
    # Transfer items from bulk to active store
    for bulk_item in bulk_items:
        try:
            # Check if item already exists in active store
            existing = ActiveStoreInventory.objects.filter(
                medication=bulk_item.medication,
                active_store=active_store,
                batch_number=bulk_item.batch_number
            ).first()
            
            if existing:
                print(f"\n⚠️  {bulk_item.medication.name} already exists in active store")
                continue
            
            # Transfer 30 units
            transfer_qty = min(30, bulk_item.stock_quantity)
            
            # Create medication transfer
            transfer = MedicationTransfer.objects.create(
                medication=bulk_item.medication,
                from_bulk_store=bulk_store,
                to_active_store=active_store,
                quantity=transfer_qty,
                batch_number=bulk_item.batch_number,
                expiry_date=bulk_item.expiry_date,
                unit_cost=bulk_item.unit_cost,
                status='pending',
                requested_by=user
            )
            
            # Approve and execute
            transfer.approved_by = user
            transfer.approved_at = timezone.now()
            transfer.status = 'in_transit'
            transfer.save()
            
            transfer.execute_transfer(user)
            
            print(f"\n✅ Transferred {transfer_qty} units of {bulk_item.medication.name}")
            print(f"   Batch: {bulk_item.batch_number}")
            print(f"   From: {bulk_store.name} → {active_store.name}")
            
        except Exception as e:
            print(f"\n❌ Error transferring {bulk_item.medication.name}: {str(e)}")
    
    return True


def main():
    """Main function"""
    # Check current status
    dispensary, active_store, bulk_store = check_inventory()
    
    if not dispensary or not active_store:
        print("\n❌ Cannot proceed without dispensary and active store")
        return
    
    # Check if active store has inventory
    active_inv_count = ActiveStoreInventory.objects.filter(
        active_store=active_store,
        stock_quantity__gt=0
    ).count()
    
    if active_inv_count == 0:
        print("\n⚠️  Active store has no inventory")
        response = input("\nDo you want to add test inventory? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            success = add_test_inventory(dispensary, active_store, bulk_store)
            
            if success:
                print("\n" + "="*60)
                print("FINAL INVENTORY STATUS")
                print("="*60)
                check_inventory()
            else:
                print("\n❌ Failed to add test inventory")
        else:
            print("\n⏭️  Skipping inventory addition")
    else:
        print(f"\n✅ Active store already has {active_inv_count} items with stock")
        print("   Ready for transfer testing!")


if __name__ == '__main__':
    main()

