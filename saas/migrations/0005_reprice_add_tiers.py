from decimal import Decimal

from django.db import migrations

TRIAL_DAYS = 60

# Reprice existing tiers + tighten free caps.
# (name, price, max_users, max_patients)
MONTHLY_UPDATES = [
    ("Starter", Decimal("0"), 3, 100),      # tighter free funnel
    ("Clinic", Decimal("35000"), 25, 2000),
    ("Hospital", Decimal("120000"), 0, 0),  # 0 = unlimited
]

# New tiers. (name, price, interval, max_users, max_patients)
NEW_PLANS = [
    ("Solo", Decimal("15000"), "monthly", 10, 500),          # mid rung: solo doctor
    ("Solo Annual", Decimal("144000"), "yearly", 10, 500),   # 15000*12*0.8
    ("Enterprise", Decimal("250000"), "monthly", 0, 0),      # multi-branch, priority
]

# Reprice annual counterparts to track new monthly prices (20% off 12mo).
ANNUAL_UPDATES = [
    ("Clinic Annual", Decimal("336000")),    # 35000*12*0.8
    ("Hospital Annual", Decimal("1152000")), # 120000*12*0.8
]


def apply(apps, schema_editor):
    Plan = apps.get_model("saas", "Plan")
    for name, price, max_users, max_patients in MONTHLY_UPDATES:
        Plan.objects.filter(name=name).update(
            price=price, max_users=max_users, max_patients=max_patients
        )
    for name, price in ANNUAL_UPDATES:
        Plan.objects.filter(name=name).update(price=price)
    for name, price, interval, max_users, max_patients in NEW_PLANS:
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
    Plan.objects.filter(name__in=[p[0] for p in NEW_PLANS]).delete()
    # restore old prices/caps
    Plan.objects.filter(name="Starter").update(price=Decimal("0"), max_users=5, max_patients=200)
    Plan.objects.filter(name="Clinic").update(price=Decimal("25000"), max_users=25, max_patients=2000)
    Plan.objects.filter(name="Hospital").update(price=Decimal("75000"), max_users=0, max_patients=0)
    Plan.objects.filter(name="Clinic Annual").update(price=Decimal("240000"))
    Plan.objects.filter(name="Hospital Annual").update(price=Decimal("720000"))


class Migration(migrations.Migration):
    dependencies = [("saas", "0004_alter_plan_trial_days")]
    operations = [migrations.RunPython(apply, revert)]
