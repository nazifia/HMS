"""Backlog #6: retire the legacy MedicationInventory (dispensary-shelf) tier.

Before the model is dropped, fold any remaining shelf stock into the
dispensary's active store so no stock is lost. Each legacy row's quantity is
added to the matching ActiveStoreInventory (created if absent) and recorded as
a synthetic ActiveStoreBatch so the batch sum stays consistent with the
summary quantity. Idempotent inputs: legacy rows are zeroed as they are folded.
"""
from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def fold_in(apps, schema_editor):
    MedicationInventory = apps.get_model("pharmacy", "MedicationInventory")
    ActiveStore = apps.get_model("pharmacy", "ActiveStore")
    ActiveStoreInventory = apps.get_model("pharmacy", "ActiveStoreInventory")
    ActiveStoreBatch = apps.get_model("pharmacy", "ActiveStoreBatch")

    now = timezone.now()
    far_future = now.date() + timedelta(days=3650)  # legacy stock has no expiry
    moved = 0

    for legacy in MedicationInventory.objects.filter(stock_quantity__gt=0):
        qty = legacy.stock_quantity
        active_store = ActiveStore.objects.filter(dispensary_id=legacy.dispensary_id).first()
        if active_store is None:
            # Every dispensary has a 1:1 active store today; if one is missing,
            # create it so the fold-in never silently drops stock.
            active_store = ActiveStore.objects.create(
                dispensary_id=legacy.dispensary_id,
                name="Active Store",
                capacity=1000,
            )

        inv, _ = ActiveStoreInventory.objects.get_or_create(
            medication_id=legacy.medication_id,
            active_store=active_store,
            defaults={"stock_quantity": 0, "reorder_level": legacy.reorder_level},
        )
        inv.stock_quantity += qty
        inv.last_restock_date = now
        inv.save()

        ActiveStoreBatch.objects.create(
            active_inventory=inv,
            batch_number=f"LEGACY-FOLD-{legacy.id}",
            quantity=qty,
            expiry_date=far_future,
            unit_cost=0,
            received_date=now,
        )

        moved += qty
        legacy.stock_quantity = 0
        legacy.save()

    remaining = (
        MedicationInventory.objects.filter(stock_quantity__gt=0).count()
    )
    assert remaining == 0, f"{remaining} legacy rows still hold stock after fold-in"
    print(f"  folded {moved} units of legacy shelf stock into active stores")


def noop_reverse(apps, schema_editor):
    # Stock has been merged into the active store; we do not split it back out.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0027_unify_pharmacy_billing"),
    ]

    operations = [
        migrations.RunPython(fold_in, noop_reverse),
    ]
