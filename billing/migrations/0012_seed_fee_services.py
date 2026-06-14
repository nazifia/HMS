from decimal import Decimal

from django.db import migrations

REGISTRATION = "Registration Fee"
CONSULTATION = "Consultation Fee"


def seed_fee_services(apps, schema_editor):
    ServiceCategory = apps.get_model("billing", "ServiceCategory")
    Service = apps.get_model("billing", "Service")

    reg_cat, _ = ServiceCategory.objects.get_or_create(name="Registration")
    con_cat, _ = ServiceCategory.objects.get_or_create(name="Consultation")

    Service.objects.get_or_create(
        name=REGISTRATION,
        defaults={"category": reg_cat, "price": Decimal("500.00"), "is_active": True},
    )
    Service.objects.get_or_create(
        name=CONSULTATION,
        defaults={"category": con_cat, "price": Decimal("1000.00"), "is_active": True},
    )


def unseed_fee_services(apps, schema_editor):
    Service = apps.get_model("billing", "Service")
    Service.objects.filter(name__in=[REGISTRATION, CONSULTATION]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0011_alter_invoice_source_app"),
    ]

    operations = [
        migrations.RunPython(seed_fee_services, unseed_fee_services),
    ]
