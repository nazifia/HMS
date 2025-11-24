# Generated data migration to populate markup costs for existing records

from django.db import migrations
from decimal import Decimal


def populate_markup_costs(apps, schema_editor):
    """Populate marked_up_cost for existing BulkStoreInventory records"""
    BulkStoreInventory = apps.get_model('pharmacy', 'BulkStoreInventory')

    # Get all bulk store inventory items
    for item in BulkStoreInventory.objects.all():
        # Apply default 2.5% markup if not already set
        if item.unit_cost and item.marked_up_cost == 0:
            item.markup_percentage = Decimal('2.50')
            markup_multiplier = 1 + (item.markup_percentage / 100)
            item.marked_up_cost = item.unit_cost * markup_multiplier
            item.save()


def reverse_populate(apps, schema_editor):
    """Reverse operation - reset marked_up_cost to 0"""
    BulkStoreInventory = apps.get_model('pharmacy', 'BulkStoreInventory')
    BulkStoreInventory.objects.all().update(marked_up_cost=0)


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0014_bulkstoreinventory_marked_up_cost_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_markup_costs, reverse_populate),
    ]
