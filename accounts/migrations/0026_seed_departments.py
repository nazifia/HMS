from django.db import migrations


# Canonical department list for HMS.
#
# Names here MUST match the target department names used elsewhere in the
# codebase, otherwise lookups fail in production:
#   - consultations/referral_mappings.py (UNIT_TO_DEPARTMENT_MAP /
#     SPECIALTY_TO_DEPARTMENT_MAP values) — referrals do
#     Department.objects.get(name=...) against these exact names.
#   - inpatient/forms.py uses Department.objects.get(name='Nursing').
#   - consultations.Referral.get_theatre_department() resolves 'Theatre'.
#
# (name, description)
DEPARTMENTS = [
    # --- Clinical / consulting departments (referral targets) ---
    ("General Medicine", "General and internal medicine, outpatient consultations"),
    ("Emergency Medicine", "Emergency, accident and trauma care"),
    ("Surgery", "General and specialist surgical services"),
    ("Pediatrics", "Child and neonatal medical care"),
    ("Obstetrics & Gynecology", "Maternity, obstetrics and gynecology services"),
    ("Cardiology", "Heart and cardiovascular care"),
    ("Neurology", "Brain, spine and nervous system care"),
    ("Orthopedics", "Bone, joint and musculoskeletal care"),
    ("Dermatology", "Skin care and treatment"),
    # --- Specialty modules (own departments) ---
    ("ANC", "Antenatal care services"),
    ("Labor", "Labor and delivery services"),
    ("SCBU", "Special Care Baby Unit / neonatal care"),
    ("ICU", "Intensive care unit"),
    ("Gynae Emergency", "Gynecological emergency services"),
    ("Family Planning", "Family planning and contraceptive services"),
    ("Dental", "Dental and oral health services"),
    ("ENT", "Ear, nose and throat services"),
    ("Ophthalmic", "Eye care and ophthalmology services"),
    ("Oncology", "Cancer care, chemotherapy and radiotherapy"),
    ("Theatre", "Surgical operating theatre"),
    # --- Diagnostic / clinical support ---
    ("Laboratory", "Laboratory, pathology and diagnostics"),
    ("Radiology", "Medical imaging and radiology"),
    ("Pharmacy", "Pharmacy and medication dispensing"),
    ("Nursing", "Nursing and patient care services"),
    # --- Administrative / organisational ---
    ("Administration", "Hospital administration and management"),
    ("Finance", "Billing, cashier and financial accounting"),
    ("Health Records", "Health records and medical documentation"),
    ("Information Technology", "IT systems and technical support"),
]


def seed_departments(apps, schema_editor):
    Department = apps.get_model("accounts", "Department")
    for name, description in DEPARTMENTS:
        Department.objects.get_or_create(
            name=name,
            defaults={"description": description},
        )


def unseed_departments(apps, schema_editor):
    # No-op on reverse: never delete departments in production, they may be
    # referenced by staff profiles, referrals, consultations, etc.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0025_alter_customuserprofile_role"),
    ]

    operations = [
        migrations.RunPython(seed_departments, unseed_departments),
    ]
