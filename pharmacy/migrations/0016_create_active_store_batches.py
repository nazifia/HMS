# Generated data migration to create ActiveStoreBatch records for existing inventory

from django.db import migrations
from django.utils import timezone


def create_active_store_batches(apps, schema_editor):
    """Create ActiveStoreBatch records for existing ActiveStoreInventory records"""
    ActiveStoreInventory = apps.get_model('pharmacy', 'ActiveStoreInventory')
    ActiveStoreBatch = apps.get_model('pharmacy', 'ActiveStoreBatch')

    # Get all active store inventory items with stock
    for inventory in ActiveStoreInventory.objects.filter(stock_quantity__gt=0):
        # Check if batch already exists
        batch_exists = ActiveStoreBatch.objects.filter(
            active_inventory=inventory,
            batch_number=inventory.batch_number or 'LEGACY'
        ).exists()

        if not batch_exists:
            # Create a single batch record from the consolidated inventory
            ActiveStoreBatch.objects.create(
                active_inventory=inventory,
                batch_number=inventory.batch_number or 'LEGACY',
                quantity=inventory.stock_quantity,
                expiry_date=inventory.expiry_date or timezone.now().date(),
                unit_cost=inventory.unit_cost or 0,
            )


def reverse_create(apps, schema_editor):
    """Reverse operation - delete all ActiveStoreBatch records"""
    ActiveStoreBatch = apps.get_model('pharmacy', 'ActiveStoreBatch')
    ActiveStoreBatch.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0015_populate_markup_costs'),
    ]

    operations = [
        migrations.RunPython(create_active_store_batches, reverse_create),
    ]
