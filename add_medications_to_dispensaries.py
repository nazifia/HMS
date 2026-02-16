#!/usr/bin/env python
"""
Script to add all medications to all active stores/dispensaries.
This will create ActiveStoreInventory records for any medication that doesn't
already exist in each active store.
"""
import os
import sys
import django

# Setup Django
sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Medication, ActiveStore, ActiveStoreInventory
from django.db import transaction

def add_medications_to_all_active_stores():
    """Add all medications to all active stores"""

    print("=" * 60)
    print("ADDING MEDICATIONS TO ACTIVE STORES")
    print("=" * 60)

    # Get all active stores
    active_stores = ActiveStore.objects.filter(is_active=True).all()
    print(f"Found {active_stores.count()} active stores")

    # Get all medications
    medications = Medication.objects.filter(is_active=True).all()
    print(f"Found {medications.count()} active medications")

    created_count = 0
    existing_count = 0

    with transaction.atomic():
        for store in active_stores:
            print(f"\nProcessing store: {store.name}")
            store_created = 0
            store_existing = 0

            for medication in medications:
                # Check if inventory record already exists
                inventory, created = ActiveStoreInventory.objects.get_or_create(
                    medication=medication,
                    active_store=store,
                    defaults={
                        'stock_quantity': 0,
                        'reorder_level': medication.reorder_level,
                        'expiry_date': None,
                        'unit_cost': 0.00,
                    }
                )

                if created:
                    created_count += 1
                    store_created += 1
                else:
                    existing_count += 1
                    store_existing += 1

            print(f"  Created: {store_created}, Already existed: {store_existing}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total records created: {created_count}")
    print(f"Total records already existed: {existing_count}")
    print(f"Total inventory records now: {ActiveStoreInventory.objects.count()}")

    # Verify coverage
    print("\n" + "=" * 60)
    print("COVERAGE CHECK")
    print("=" * 60)
    expected_records = active_stores.count() * medications.count()
    actual_records = ActiveStoreInventory.objects.count()
    coverage_percent = (actual_records / expected_records * 100) if expected_records > 0 else 0
    print(f"Expected records: {expected_records}")
    print(f"Actual records: {actual_records}")
    print(f"Coverage: {coverage_percent:.1f}%")

if __name__ == '__main__':
    add_medications_to_all_active_stores()
