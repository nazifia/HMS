from decimal import Decimal

from django.db import migrations

# (name, price, interval, max_users, max_patients, trial_days)
PLANS = [
    ("Starter", Decimal("0"), "monthly", 5, 200, 14),
    ("Clinic", Decimal("25000"), "monthly", 25, 2000, 14),
    ("Hospital", Decimal("75000"), "monthly", 0, 0, 14),  # 0 = unlimited
]


def seed(apps, schema_editor):
    Plan = apps.get_model("saas", "Plan")
    for name, price, interval, max_users, max_patients, trial_days in PLANS:
        Plan.objects.get_or_create(
            name=name,
            defaults={
                "price": price,
                "interval": interval,
                "max_users": max_users,
                "max_patients": max_patients,
                "trial_days": trial_days,
            },
        )


def unseed(apps, schema_editor):
    Plan = apps.get_model("saas", "Plan")
    Plan.objects.filter(name__in=[p[0] for p in PLANS]).delete()


class Migration(migrations.Migration):
    dependencies = [("saas", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
