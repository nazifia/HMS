from django.db import migrations

# Canonical role names as defined in accounts.permissions.ROLE_PERMISSIONS.
# Non-canonical variants found in production DBs map onto these.
ALIASES = {
    "med_lab_scientist": "medical_lab_scientist",
    "med_lab_technician": "lab_technician",
}


def canonical_name(name):
    lowered = name.strip().lower()
    return ALIASES.get(lowered, lowered)


def merge(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")

    roles_by_canonical = {}
    for role in Role.objects.order_by("pk"):
        roles_by_canonical.setdefault(canonical_name(role.name), []).append(role)

    for canon, roles in roles_by_canonical.items():
        # Prefer the row already bearing the canonical name; else oldest row.
        target = next((r for r in roles if r.name == canon), roles[0])
        if target.name != canon:
            target.name = canon
            target.save(update_fields=["name"])

        for dupe in roles:
            if dupe.pk == target.pk:
                continue
            target.permissions.add(*dupe.permissions.all())
            for user in dupe.customuser_roles.all():
                user.roles.add(target)
                user.roles.remove(dupe)
            # Re-parent any child roles pointing at the duplicate.
            Role.objects.filter(parent=dupe).update(parent=target)
            dupe.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0040_grant_doctor_prescription_perms"),
    ]

    operations = [migrations.RunPython(merge, migrations.RunPython.noop)]
