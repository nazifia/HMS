from django.db import migrations

CODENAMES = [
    "add_prescription",
    "change_prescription",
    "view_prescription",
    "add_prescriptionitem",
    "change_prescriptionitem",
    "view_prescriptionitem",
]


def grant(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("auth", "Permission")
    perms = list(
        Permission.objects.filter(
            content_type__app_label="pharmacy", codename__in=CODENAMES
        )
    )
    # Duplicate role rows exist in some deployments ("Doctor" and "doctor");
    # grant to every case variant so users on either row are covered.
    for role in Role.objects.filter(name__iexact="doctor"):
        role.permissions.add(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0039_flip_lab_role_parent"),
        ("pharmacy", "0001_initial"),
    ]

    operations = [migrations.RunPython(grant, migrations.RunPython.noop)]
