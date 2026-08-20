"""Give legacy prescriptions the hospital their patient already has.

Rows created before tenancy landed have hospital=NULL, which the tenant-scoped
manager filters out — the prescription 404s for every user, its own staff
included.
"""

from django.db import migrations


def backfill(apps, schema_editor):
    Prescription = apps.get_model("pharmacy", "Prescription")
    for prescription in Prescription.objects.filter(
        hospital__isnull=True, patient__hospital__isnull=False
    ).select_related("patient"):
        prescription.hospital_id = prescription.patient.hospital_id
        prescription.save(update_fields=["hospital"])


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0036_alter_bulkstore_name_alter_dispensary_name_and_more"),
        # The patient__hospital lookup needs Patient.hospital to exist first;
        # without this a fresh database can order 0023 after us and blow up.
        ("patients", "0023_patient_hospital"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
