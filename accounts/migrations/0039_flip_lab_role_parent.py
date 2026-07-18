from django.db import migrations


def flip(apps, schema_editor):
    """medical_lab_scientist inherits from lab_technician (senior role)."""
    Role = apps.get_model("accounts", "Role")
    tech = Role.objects.filter(name="lab_technician").first()
    scientist = Role.objects.filter(name="medical_lab_scientist").first()
    if tech and scientist:
        tech.parent = None
        tech.save(update_fields=["parent"])
        scientist.parent = tech
        scientist.save(update_fields=["parent"])


def unflip(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    tech = Role.objects.filter(name="lab_technician").first()
    scientist = Role.objects.filter(name="medical_lab_scientist").first()
    if tech and scientist:
        scientist.parent = None
        scientist.save(update_fields=["parent"])
        tech.parent = scientist
        tech.save(update_fields=["parent"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0038_lab_technician_parent_role"),
    ]

    operations = [
        migrations.RunPython(flip, unflip),
    ]
