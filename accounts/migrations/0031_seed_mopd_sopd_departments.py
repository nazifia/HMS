from django.db import migrations


# Medical / Surgical Outpatient Departments. Added after 0026 so existing
# tenants get them too. Names MUST match consultations/referral_mappings.py.
NEW_DEPARTMENTS = [
    ("MOPD", "Medical Outpatient Department"),
    ("SOPD", "Surgical Outpatient Department"),
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
        ("accounts", "0030_department_uniq_department_name_when_no_hospital"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, noop),
    ]
