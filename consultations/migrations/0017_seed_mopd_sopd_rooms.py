from django.db import migrations


# One consulting room per outpatient clinic (MOPD/SOPD) per hospital.
# room_number is globally unique, so it embeds the hospital id.
CLINIC_DEPARTMENTS = ["MOPD", "SOPD"]


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
        ("consultations", "0016_consultation_clinic_type_waitinglist_clinic_type"),
        ("accounts", "0031_seed_mopd_sopd_departments"),
        ("saas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_rooms, noop),
    ]
