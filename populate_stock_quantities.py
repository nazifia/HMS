#!/usr/bin/env python
"""
Script to populate stock quantities for all medications in active stores,
taking into account medical pack requirements to ensure packs can be ordered.
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta

# Setup Django
sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Medication, ActiveStore, ActiveStoreInventory, MedicalPack, MedicalPackItem
from django.db import transaction
from django.db.models import Sum, F

def populate_stock_quantities():
    """Populate stock quantities with realistic values and ensure pack requirements"""

    print("=" * 70)
    print("POPULATING STOCK QUANTITIES")
    print("=" * 70)

    # Get all active stores and medications
    active_stores = ActiveStore.objects.filter(is_active=True).all()
    medications = Medication.objects.filter(is_active=True).all()

    # First, check medical pack requirements
    print("\n" + "=" * 70)
    print("ANALYZING MEDICAL PACK REQUIREMENTS")
    print("=" * 70)

    packs = MedicalPack.objects.filter(is_active=True).all()
    print(f"Found {packs.count()} active medical packs")

    # Calculate minimum stock needed per medication to fulfill all packs
    min_stock_needed = {}  # {medication_id: quantity_needed}
    pack_requirements = {}  # {medication_id: [(pack_name, quantity)...]}

    for pack in packs:
        items = pack.items.all()
        print(f"\n{pack.name} (Type: {pack.pack_type})")
        print(f"  Total items: {items.count()}")

        for item in items:
            med_id = item.medication_id
            qty = item.quantity

            if med_id not in min_stock_needed:
                min_stock_needed[med_id] = 0
                pack_requirements[med_id] = []

            min_stock_needed[med_id] += qty
            pack_requirements[med_id].append((pack.name, qty))

    print("\n" + "=" * 70)
    print("MEDICATIONS WITH PACK REQUIREMENTS")
    print("=" * 70)

    for med_id, total_qty in min_stock_needed.items():
        try:
            med = Medication.objects.get(id=med_id)
            print(f"\n{med.name} ({med.strength}): {total_qty} units needed")
            for pack_name, qty in pack_requirements[med_id][:3]:  # Show first 3 packs
                print(f"  - {pack_name}: {qty}")
            if len(pack_requirements[med_id]) > 3:
                print(f"  ... and {len(pack_requirements[med_id])-3} more packs")
        except Medication.DoesNotExist:
            print(f"\nMedication ID {med_id} not found (skipping)")

    # Now populate stock quantities
    print("\n" + "=" * 70)
    print("POPULATING STOCK QUANTITIES")
    print("=" * 70)

    # Define stock ranges based on store name
    def get_stock_range(store_name, medication_price=None):
        """Determine stock quantity range based on store type"""
        store_lower = store_name.lower()

        if 'emergency' in store_lower:
            # Emergency: Moderate stock, focus on essentials
            return (20, 200)
        elif 'main' in store_lower:
            # Main Pharmacy: High stock, comprehensive inventory
            return (100, 1000)
        elif 'outpatient' in store_lower:
            # Outpatient: Medium stock
            return (50, 500)
        elif 'test' in store_lower:
            # Test dispensaries: Lower stock
            return (10, 100)
        else:
            # Default
            return (30, 300)

    created_count = 0
    updated_count = 0

    with transaction.atomic():
        for store in active_stores:
            print(f"\nProcessing: {store.name}")
            store_created = 0
            store_updated = 0

            for medication in medications:
                inventory, created = ActiveStoreInventory.objects.get_or_create(
                    medication=medication,
                    active_store=store
                )

                # Determine base stock
                stock_range = get_stock_range(store.name, medication.price)
                base_stock = random.randint(stock_range[0], stock_range[1])

                # If this medication is needed for medical packs, ensure it meets minimum
                med_id = medication.id
                if med_id in min_stock_needed:
                    required_qty = min_stock_needed[med_id]
                    # Add some buffer (50% more than minimum needed)
                    buffer_qty = int(required_qty * 1.5)
                    if base_stock < buffer_qty:
                        base_stock = buffer_qty + random.randint(0, 100)

                # Set or update stock quantity
                if created or inventory.stock_quantity == 0:
                    inventory.stock_quantity = base_stock
                    store_created += 1
                elif inventory.stock_quantity < base_stock:
                    inventory.stock_quantity = base_stock
                    store_updated += 1
                # If existing stock is already sufficient, leave it

                # Add some realistic metadata
                if not inventory.last_restock_date:
                    days_ago = random.randint(1, 90)
                    inventory.last_restock_date = datetime.now() - timedelta(days=days_ago)

                if not inventory.unit_cost and medication.price:
                    # Estimate unit cost as 80% of retail price
                    inventory.unit_cost = float(medication.price) * 0.8

                inventory.save()
                created_count += 1 if created else 0
                updated_count += 1 if not created else 0

            print(f"  Created: {store_created}, Updated: {store_updated}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total inventory records: {ActiveStoreInventory.objects.count()}")
    print(f"Newly created records: {created_count}")
    print(f"Updated records: {updated_count}")

    # Show stock levels
    print("\n" + "=" * 70)
    print("STOCK LEVEL VERIFICATION")
    print("=" * 70)

    total_stock = ActiveStoreInventory.objects.aggregate(total=Sum('stock_quantity'))['total'] or 0
    print(f"Total medication units across all stores: {total_stock:,}")

    # Show top 10 stocked medications
    top_meds = ActiveStoreInventory.objects.values(
        'medication__name'
    ).annotate(
        total_stock=Sum('stock_quantity')
    ).order_by('-total_stock')[:10]

    print("\nTop 10 medications by total stock:")
    for i, med in enumerate(top_meds, 1):
        print(f"  {i}. {med['medication__name']}: {med['total_stock']:,} units")

    # Verify pack requirements can be met
    print("\n" + "=" * 70)
    print("PACK REQUIREMENTS VERIFICATION")
    print("=" * 70)

    all_ok = True
    for pack in packs:
        print(f"\nChecking: {pack.name}")
        pack_missing = []

        for item in pack.items.all():
            total_available = ActiveStoreInventory.objects.filter(
                medication=item.medication
            ).aggregate(total=Sum('stock_quantity'))['total'] or 0

            if total_available < item.quantity:
                all_ok = False
                pack_missing.append({
                    'medication': item.medication.name,
                    'needed': item.quantity,
                    'available': total_available,
                    'shortage': item.quantity - total_available
                })

        if pack_missing:
            print(f"  ❌ Insufficient stock:")
            for m in pack_missing:
                print(f"     - {m['medication']}: need {m['needed']}, have {m['available']} (short {m['shortage']})")
        else:
            print(f"  ✓ All items available (total value: ₦{pack.get_total_value():,.2f})")

    if all_ok:
        print("\n" + "=" * 70)
        print("✓ ALL MEDICAL PACKS CAN BE ORDERED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠ SOME PACKS HAVE INSUFFICIENT STOCK")
        print("=" * 70)

    print("\nDone!")

if __name__ == '__main__':
    populate_stock_quantities()
