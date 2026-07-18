from django.db import migrations


def set_parent(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    child = Role.objects.filter(name="lab_technician").first()
    parent = Role.objects.filter(name="medical_lab_scientist").first()
    if child and parent:
        child.parent = parent
        child.save(update_fields=["parent"])


def unset_parent(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(name="lab_technician").update(parent=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0037_alter_customuserprofile_role"),
    ]

    operations = [
        migrations.RunPython(set_parent, unset_parent),
    ]
