#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Medication, Dispensary, ActiveStoreInventory, BulkStoreInventory, ActiveStore

print("=" * 60)
print("CURRENT STATE")
print("=" * 60)

# Count medications
med_count = Medication.objects.count()
print(f"Total Medications in database: {med_count}")

# Count dispensaries
dispensary_count = Dispensary.objects.count()
print(f"Total Dispensaries: {dispensary_count}")

# Count active stores
active_store_count = ActiveStore.objects.count()
print(f"Total Active Stores: {active_store_count}")

# Count inventory records
active_inv_count = ActiveStoreInventory.objects.count()
bulk_inv_count = BulkStoreInventory.objects.count()
print(f"Active Store Inventory records: {active_inv_count}")
print(f"Bulk Store Inventory records: {bulk_inv_count}")

print("\n" + "=" * 60)
print("DISPENSARIES")
print("=" * 60)
for d in Dispensary.objects.all():
    print(f"  - {d.name} (ID: {d.id})")

print("\n" + "=" * 60)
print("ACTIVE STORES")
print("=" * 60)
for s in ActiveStore.objects.all():
    print(f"  - {s.name} (ID: {s.id})")

print("\n" + "=" * 60)
print("SAMPLE MEDICATIONS (first 10)")
print("=" * 60)
for med in Medication.objects.all()[:10]:
    print(f"  - {med.name} (ID: {med.id})")
