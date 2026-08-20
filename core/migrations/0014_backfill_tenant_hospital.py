"""Give the remaining pre-tenancy rows the hospital their parent already has.

Same rot as pharmacy.0037, across every other tenant table: rows written before
`hospital` existed are NULL, and the tenant-scoped manager filters them out, so
an invoice/consultation/log is invisible even to the hospital that owns it.

Each table names the fields to inherit from, in order — first parent with a
hospital wins. Rows whose parents are all NULL too are left alone; the tables
here are ordered parent-before-child so a row fixed above can feed the one below.
"""

from collections import defaultdict

from django.db import migrations

# model label -> FK fields to inherit the hospital from, best source first.
SOURCES = [
    ("billing.Service", ["category"]),
    ("consultations.Consultation", ["patient", "doctor"]),
    ("consultations.SOAPNote", ["consultation", "created_by"]),
    ("consultations.ConsultationOrder", ["consultation", "created_by"]),
    ("laboratory.TestRequest", ["patient", "doctor", "created_by"]),
    ("radiology.RadiologyResult", ["order", "performed_by"]),
    ("inpatient.InpatientMedication", ["admission", "prescription", "ordered_by"]),
    ("pharmacy.PrescriptionItem", ["prescription"]),
    ("pharmacy.PrescriptionCart", ["prescription", "dispensary", "created_by"]),
    ("pharmacy.PrescriptionCartItem", ["cart", "prescription_item"]),
    ("pharmacy.DispensingLog", ["prescription_item", "dispensary", "dispensed_by"]),
    ("billing.Invoice", ["patient", "created_by"]),
    ("billing.InvoiceItem", ["invoice", "service"]),
    ("billing.Payment", ["invoice", "received_by"]),
    ("patients.WalletTransaction", ["patient", "patient_wallet", "invoice"]),
    ("nhia.AuthorizationCode", ["patient", "generated_by"]),
    ("desk_office.AuthorizationCode", ["patient"]),
    ("core.InternalNotification", ["user", "sender"]),
    ("core.AuditLog", ["user"]),
    ("core.ActivityLog", ["user"]),
    ("accounts.AuditLog", ["user", "target_user"]),
    ("accounts.ActivityAlert", ["user", "resolved_by"]),
    ("accounts.UserActivity", ["user"]),
    ("accounts.UserSession", ["user"]),
]


def backfill(apps, schema_editor):
    for label, sources in SOURCES:
        model = apps.get_model(label)
        for source in sources:
            # Set-based: one SELECT per source, then one UPDATE per hospital.
            # ActivityLog alone has thousands of rows — saving them one by one
            # would be thousands of round trips.
            rows = model.objects.filter(
                hospital__isnull=True, **{f"{source}__hospital__isnull": False}
            ).values_list("pk", f"{source}__hospital_id")
            by_hospital = defaultdict(list)
            for pk, hospital_id in rows:
                by_hospital[hospital_id].append(pk)
            for hospital_id, pks in by_hospital.items():
                model.objects.filter(pk__in=pks).update(hospital_id=hospital_id)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_servicepoint_department"),
        ("accounts", "0043_alter_customuser_username_and_more"),
        ("billing", "0015_alter_payment_options"),
        ("consultations", "0019_alter_consultingroom_room_number_and_more"),
        ("desk_office", "0006_authorizationcode_hospital"),
        ("inpatient", "0011_alter_admission_options"),
        ("laboratory", "0012_testresult_verified_date"),
        ("nhia", "0007_alter_authorizationcode_code_and_more"),
        ("patients", "0029_alter_patientwallet_options"),
        ("pharmacy", "0037_backfill_prescription_hospital"),
        ("radiology", "0008_seed_radiology_catalog"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
