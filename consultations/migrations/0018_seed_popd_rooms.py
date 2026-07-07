from django.db import migrations, models


# One consulting room for the Pediatric Outpatient clinic per hospital.
# room_number is globally unique, so it embeds the hospital id. Mirrors 0017.
CLINIC_DEPARTMENTS = ["POPD"]

CLINIC_TYPE_CHOICES = [
    ("", "N/A (General)"),
    ("mopd", "MOPD (Medical Outpatient)"),
    ("sopd", "SOPD (Surgical Outpatient)"),
    ("popd", "POPD (Pediatric Outpatient)"),
]

HELP_TEXT = "Outpatient clinic: Medical (MOPD), Surgical (SOPD) or Pediatric (POPD)"


def seed_rooms(apps, schema_editor):
    Hospital = apps.get_model("saas", "Hospital")
    Department = apps.get_model("accounts", "Department")
    ConsultingRoom = apps.get_model("consultations", "ConsultingRoom")
    db = schema_editor.connection.alias

    for hospital in Hospital.objects.using(db).all():
        for dept_name in CLINIC_DEPARTMENTS:
            department = Department.objects.using(db).filter(
                hospital=hospital, name=dept_name
            ).first()
            if department is None:
                continue
            ConsultingRoom.objects.using(db).get_or_create(
                room_number=f"{dept_name}-{hospital.id}",
                defaults={
                    "floor": "Ground",
                    "department": department,
                    "hospital": hospital,
                    "description": f"{dept_name} outpatient consulting room",
                    "is_active": True,
                },
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("consultations", "0017_seed_mopd_sopd_rooms"),
        ("accounts", "0032_seed_popd_department"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="waitinglist",
            name="clinic_type",
            field=models.CharField(
                blank=True, choices=CLINIC_TYPE_CHOICES, default="",
                help_text=HELP_TEXT, max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="consultation",
            name="clinic_type",
            field=models.CharField(
                blank=True, choices=CLINIC_TYPE_CHOICES, default="",
                help_text=HELP_TEXT, max_length=10,
            ),
        ),
        migrations.RunPython(seed_rooms, noop),
    ]
