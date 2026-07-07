from django.db import migrations


# Pediatric Outpatient Department. Mirrors 0031; names MUST match
# consultations/referral_mappings.py and accounts/department_seed.py.
NEW_DEPARTMENTS = [
    ("POPD", "Pediatric Outpatient Department"),
]


def seed(apps, schema_editor):
    Department = apps.get_model("accounts", "Department")
    Hospital = apps.get_model("saas", "Hospital")
    db = schema_editor.connection.alias

    hospitals = list(Hospital.objects.using(db).all())
    for name, description in NEW_DEPARTMENTS:
        # Tenant-less fallback (guarded by uniq_department_name_when_no_hospital).
        Department.objects.using(db).get_or_create(
            hospital=None, name=name, defaults={"description": description}
        )
        for hospital in hospitals:
            Department.objects.using(db).get_or_create(
                hospital=hospital, name=name, defaults={"description": description}
            )


def noop(apps, schema_editor):
    # Never delete departments in production; they may be referenced.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0031_seed_mopd_sopd_departments"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, noop),
    ]
