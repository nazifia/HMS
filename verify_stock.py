#!/usr/bin/env python
import os
import sys
import django

sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import ActiveStoreInventory
from django.db.models import Sum, Count

print("=" * 70)
print("STOCK QUANTITIES VERIFICATION")
print("=" * 70)

total = ActiveStoreInventory.objects.aggregate(total=Sum('stock_quantity'))['total']
print(f"\nTotal stock units across all stores: {total:,}")

zero_count = ActiveStoreInventory.objects.filter(stock_quantity=0).count()
print(f"Records with zero stock: {zero_count}")

low_stock = ActiveStoreInventory.objects.filter(stock_quantity__lt=20).count()
print(f"Records with stock < 20: {low_stock}")

high_stock = ActiveStoreInventory.objects.filter(stock_quantity__gte=500).count()
print(f"Records with stock >= 500: {high_stock}")

# Check by store
print("\n" + "=" * 70)
print("STOCK BY STORE")
print("=" * 70)

from pharmacy.models import ActiveStore
for store in ActiveStore.objects.all():
    store_total = ActiveStoreInventory.objects.filter(active_store=store).aggregate(total=Sum('stock_quantity'))['total']
    store_count = ActiveStoreInventory.objects.filter(active_store=store).count()
    print(f"\n{store.name}:")
    print(f"  Medications: {store_count}")
    print(f"  Total units: {store_total:,}")

print("\nDone!")
