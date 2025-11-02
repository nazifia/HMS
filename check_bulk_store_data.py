#!/usr/bin/env python
"""
Check bulk store data for active store transfer functionality
"""
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import BulkStore, BulkStoreInventory, Dispensary, ActiveStore, ActiveStoreInventory

print("=== Bulk Store Data Check ===")
print()

# Check bulk stores
bulk_stores = BulkStore.objects.filter(is_active=True)
print(f"Active Bulk Stores: {bulk_stores.count()}")
for bulk_store in bulk_stores:
    print(f"  - {bulk_store.name} (ID: {bulk_store.id})")

print()

# Check bulk store inventory
bulk_inventory = BulkStoreInventory.objects.filter(stock_quantity__gt=0)
print(f"Bulk Store Items with Stock: {bulk_inventory.count()}")
for item in bulk_inventory.select_related('bulk_store', 'medication'):
    print(f"  - {item.medication.name} (Store: {item.bulk_store.name}, Qty: {item.stock_quantity})")

print()

# Check dispensaries with active stores
dispensaries = Dispensary.objects.filter(is_active=True)
print(f"Active Dispensaries: {dispensaries.count()}")
for dispensary in dispensaries:
    active_store = getattr(dispensary, 'active_store', None)
    if active_store:
        print(f"  - {dispensary.name} -> Active Store: {active_store.name}")
        
        # Check active store inventory
        active_inventory = ActiveStoreInventory.objects.filter(active_store=active_store)
        print(f"    Active Store Items: {active_inventory.count()}")
        for item in active_inventory.select_related('medication'):
            print(f"      - {item.medication.name} (Qty: {item.stock_quantity})")
    else:
        print(f"  - {dispensary.name} -> No Active Store")

print()
print("=== Summary ===")
print(f"Bulk Stores with stock: {BulkStore.objects.filter(is_active=True, bulkstoreinventory__stock_quantity__gt=0).distinct().count()}")
print(f"Dispensaries with active stores: {Dispensary.objects.filter(is_active=True, activestore__isnull=False).count()}")
