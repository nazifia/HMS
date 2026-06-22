from decimal import Decimal

from django.db import migrations

DISCOUNT = Decimal("0.20")  # 20% off 12 months of the matching monthly plan


def apply(apps, schema_editor):
    """Reprice every yearly plan to monthly*12*(1-20%), matched by caps."""
    Plan = apps.get_model("saas", "Plan")
    for ann in Plan.objects.filter(interval="yearly"):
        monthly = (
            Plan.objects.filter(
                interval="monthly", max_users=ann.max_users, max_patients=ann.max_patients
            )
            .exclude(price=0)
            .first()
        )
        if not monthly:
            continue
        price = (monthly.price * 12 * (1 - DISCOUNT)).quantize(Decimal("1"))
        if ann.price != price:
            ann.price = price
            ann.save(update_fields=["price"])


class Migration(migrations.Migration):
    dependencies = [("saas", "0006_subscription_approved_at_subscription_approved_by_and_more")]
    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
