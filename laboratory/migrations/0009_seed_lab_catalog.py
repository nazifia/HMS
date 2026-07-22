from decimal import Decimal

from django.db import migrations

# Plain data dict only (no real model classes used here) -> safe in migrations.
from laboratory.lab_catalog_seed import CATALOG


def seed(apps, schema_editor):
    """Seed the canonical lab catalog for every existing hospital. Idempotent."""
    Hospital = apps.get_model("saas", "Hospital")
    TestCategory = apps.get_model("laboratory", "TestCategory")
    Test = apps.get_model("laboratory", "Test")
    TestParameter = apps.get_model("laboratory", "TestParameter")

    for hospital in Hospital.objects.all():
        for category_name, tests in CATALOG.items():
            category, _ = TestCategory.objects.get_or_create(
                hospital=hospital, name=category_name
            )
            for name, price, sample_type, description, params in tests:
                test, _ = Test.objects.get_or_create(
                    hospital=hospital,
                    name=name,
                    defaults={
                        "category": category,
                        "description": description,
                        "price": Decimal(str(price)),
                        "sample_type": sample_type,
                        "is_active": True,
                    },
                )
                for order, (pname, normal_range, unit) in enumerate(params, start=1):
                    TestParameter.objects.get_or_create(
                        hospital=hospital,
                        test=test,
                        name=pname,
                        defaults={
                            "normal_range": normal_range,
                            "unit": unit,
                            "order": order,
                        },
                    )


def unseed(apps, schema_editor):
    # No-op: never delete lab catalog in prod, results reference these rows.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("laboratory", "0008_alter_testresult_options"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
