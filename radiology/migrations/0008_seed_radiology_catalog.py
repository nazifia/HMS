from django.db import migrations

# Plain data only (no real model classes) -> safe to import in a migration.
from radiology.radiology_catalog_seed import CATALOG


def seed(apps, schema_editor):
    """Seed the canonical radiology catalog for every existing hospital. Idempotent."""
    from decimal import Decimal

    Hospital = apps.get_model("saas", "Hospital")
    RadiologyCategory = apps.get_model("radiology", "RadiologyCategory")
    RadiologyTest = apps.get_model("radiology", "RadiologyTest")

    for hospital in Hospital.objects.all():
        for category_name, procedures in CATALOG.items():
            category, _ = RadiologyCategory.objects.get_or_create(
                hospital=hospital, name=category_name
            )
            for name, price, minutes, description, prep in procedures:
                RadiologyTest.objects.get_or_create(
                    hospital=hospital,
                    name=name,
                    defaults={
                        "category": category,
                        "description": description,
                        "preparation_instructions": prep,
                        "price": Decimal(str(price)),
                        "duration_minutes": minutes,
                        "is_active": True,
                    },
                )


def unseed(apps, schema_editor):
    # No-op: never delete the radiology catalog in prod, orders reference these rows.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("radiology", "0007_radiologycategory_hospital_radiologyorder_hospital_and_more"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
