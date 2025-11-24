# Data migration to update existing records to 20% markup

from django.db import migrations
from decimal import Decimal


def update_to_20_percent(apps, schema_editor):
    """Update all existing BulkStoreInventory records to 20% markup"""
    BulkStoreInventory = apps.get_model('pharmacy', 'BulkStoreInventory')

    # Update all items to 20% markup
    for item in BulkStoreInventory.objects.all():
        if item.unit_cost:
            item.markup_percentage = Decimal('20.00')
            markup_multiplier = 1 + (item.markup_percentage / 100)
            item.marked_up_cost = item.unit_cost * markup_multiplier
            item.save()


def reverse_update(apps, schema_editor):
    """Reverse operation - revert to 2.5% markup"""
    BulkStoreInventory = apps.get_model('pharmacy', 'BulkStoreInventory')

    for item in BulkStoreInventory.objects.all():
        if item.unit_cost:
            item.markup_percentage = Decimal('2.50')
            markup_multiplier = 1 + (item.markup_percentage / 100)
            item.marked_up_cost = item.unit_cost * markup_multiplier
            item.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0017_change_default_markup_to_20'),
    ]

    operations = [
        migrations.RunPython(update_to_20_percent, reverse_update),
    ]
