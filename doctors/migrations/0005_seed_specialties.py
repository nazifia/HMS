from django.db import migrations

# Plain data list only (no real model classes used here) -> safe in migrations.
from doctors.specialty_seed import SPECIALTIES


def seed(apps, schema_editor):
    """Seed the canonical specialty list for every existing hospital. Idempotent."""
    Hospital = apps.get_model("saas", "Hospital")
    Specialization = apps.get_model("doctors", "Specialization")

    for hospital in Hospital.objects.all():
        for name, description in SPECIALTIES:
            Specialization.objects.get_or_create(
                hospital=hospital,
                name=name,
                defaults={"description": description},
            )


def unseed(apps, schema_editor):
    # No-op: never delete specialties in prod, doctor profiles reference them.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("doctors", "0004_doctor_hospital_doctoravailability_hospital_and_more"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
