#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import BulkStore, BulkStoreInventory, Medication

def check_bulk_store_data():
    print("=== CHECKING BULK STORE DATA ===")
    
    # Check bulk stores
    bulk_stores = BulkStore.objects.filter(is_active=True)
    print(f"\n1. Active Bulk Stores: {bulk_stores.count()}")
    for store in bulk_stores:
        print(f"   - {store.name} (ID: {store.id}) at {store.location}")
    
    # Check bulk store inventory
    inventory_items = BulkStoreInventory.objects.filter(stock_quantity__gt=0)
    print(f"\n2. Bulk Store Inventory (stock > 0): {inventory_items.count()}")
    
    # Group by bulk store
    store_inventory = {}
    for item in inventory_items.select_related('bulk_store', 'medication'):
        store_name = item.bulk_store.name
        if store_name not in store_inventory:
            store_inventory[store_name] = []
        store_inventory[store_name].append(item)
    
    for store_name, items in store_inventory.items():
        print(f"   - {store_name}: {len(items)} medications")
        for item in items[:5]:  # Show first 5 items
            print(f"     * {item.medication.name} (Batch: {item.batch_number}) - {item.stock_quantity} units")
        if len(items) > 5:
            print(f"     ... and {len(items) - 5} more")
    
    # Check medications
    medications = Medication.objects.all()
    print(f"\n3. Total Medications in System: {medications.count()}")
    
    # Summary
    if not bulk_stores.exists():
        print("\n❌ No active bulk stores found!")
        print("   You need to create bulk stores first.")
    
    if not inventory_items.exists():
        print("\n❌ No inventory found in bulk stores!")
        print("   You need to add medications to bulk stores.")
    
    if bulk_stores.exists() and inventory_items.exists():
        print("\n✅ Bulk stores and inventory data exist!")
        print("   The issue might be in the view logic.")
    else:
        print("\n⚠️  Data missing - need to populate bulk stores with medications")

if __name__ == '__main__':
    check_bulk_store_data()
