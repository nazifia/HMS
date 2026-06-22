from decimal import Decimal

from django.db import migrations

TRIAL_DAYS = 60  # 2-month free trial

# (name, price, interval, max_users, max_patients) — annual = monthly*12*0.8 (20% off)
ANNUAL_PLANS = [
    ("Clinic Annual", Decimal("240000"), "yearly", 25, 2000),
    ("Hospital Annual", Decimal("720000"), "yearly", 0, 0),  # 0 = unlimited
]


def apply(apps, schema_editor):
    Plan = apps.get_model("saas", "Plan")
    Plan.objects.update(trial_days=TRIAL_DAYS)
    for name, price, interval, max_users, max_patients in ANNUAL_PLANS:
        Plan.objects.get_or_create(
            name=name,
            defaults={
                "price": price,
                "interval": interval,
                "max_users": max_users,
                "max_patients": max_patients,
                "trial_days": TRIAL_DAYS,
            },
        )


def revert(apps, schema_editor):
    Plan = apps.get_model("saas", "Plan")
    Plan.objects.filter(name__in=[p[0] for p in ANNUAL_PLANS]).delete()
    Plan.objects.update(trial_days=14)


class Migration(migrations.Migration):
    dependencies = [("saas", "0002_seed_plans")]
    operations = [migrations.RunPython(apply, revert)]
