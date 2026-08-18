from django.db import migrations

# Departments created before the tenant FK existed (migration 0026 and friends)
# have hospital=None, so TenantManager hides them from every tenant. They belong
# to the original tenant: the lowest-pk hospital.
#
# For an orphan whose name already exists under that hospital, the orphan is a
# duplicate: references are repointed at the surviving row and the orphan is
# deleted. Leaving both would break the seeders' get_or_create(hospital, name).

# (model label, field name) for every FK/M2M pointing at accounts.Department.
DEPARTMENT_REFS = [
    ("accounts.CustomUserProfile", "department"),
    ("accounts.StaffDepartmentAssignment", "department"),
    ("core.ServicePoint", "department"),
    ("patients.ClinicalNote", "department"),
    ("doctors.Doctor", "department"),
    ("appointments.Appointment", "department"),
    ("hr.Designation", "department"),
    ("hr.StaffProfile", "department"),
    ("consultations.ConsultingRoom", "department"),
    ("consultations.Referral", "referred_to_department"),
    ("emergency.EmergencyRecord", "referred_to_department"),
]
DEPARTMENT_M2M_REFS = [
    ("accounts.CustomUserProfile", "departments"),
]


def repoint(apps, orphan, twin):
    for label, field in DEPARTMENT_REFS:
        try:
            model = apps.get_model(label)
        except LookupError:  # app removed from the project
            continue
        model.objects.filter(**{field: orphan}).update(**{field: twin})

    for label, field in DEPARTMENT_M2M_REFS:
        try:
            model = apps.get_model(label)
        except LookupError:
            continue
        for obj in model.objects.filter(**{field: orphan}):
            getattr(obj, field).add(twin)
            getattr(obj, field).remove(orphan)


def backfill(apps, schema_editor):
    Hospital = apps.get_model("saas", "Hospital")
    Department = apps.get_model("accounts", "Department")

    hospital = Hospital.objects.order_by("pk").first()
    if hospital is None:  # fresh install, no tenants yet
        return

    for orphan in Department.objects.filter(hospital__isnull=True).order_by("pk"):
        twin = (
            Department.objects.filter(hospital=hospital, name=orphan.name)
            .exclude(pk=orphan.pk)
            .order_by("pk")
            .first()
        )
        if twin is None:
            orphan.hospital = hospital
            orphan.save(update_fields=["hospital"])
            continue
        repoint(apps, orphan, twin)
        orphan.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0041_merge_duplicate_roles"),
        ("saas", "0001_initial"),
    ]

    # No reverse: the deleted duplicates cannot be reconstructed.
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
