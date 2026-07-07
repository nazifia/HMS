"""Per-hospital department seeding.

The same canonical list as migration 0026_seed_departments, but scoped to a
hospital so every new tenant gets its own copy. Names MUST match the lookups in
consultations/referral_mappings.py and inpatient/forms.py (see that migration).
"""

from .models import Department

# (name, description)
DEPARTMENTS = [
    ("General Medicine", "General and internal medicine, outpatient consultations"),
    ("MOPD", "Medical Outpatient Department"),
    ("SOPD", "Surgical Outpatient Department"),
    ("POPD", "Pediatric Outpatient Department"),
    ("Emergency Medicine", "Emergency, accident and trauma care"),
    ("Surgery", "General and specialist surgical services"),
    ("Pediatrics", "Child and neonatal medical care"),
    ("Obstetrics & Gynecology", "Maternity, obstetrics and gynecology services"),
    ("Cardiology", "Heart and cardiovascular care"),
    ("Neurology", "Brain, spine and nervous system care"),
    ("Orthopedics", "Bone, joint and musculoskeletal care"),
    ("Dermatology", "Skin care and treatment"),
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
    ("Laboratory", "Laboratory, pathology and diagnostics"),
    ("Radiology", "Medical imaging and radiology"),
    ("Pharmacy", "Pharmacy and medication dispensing"),
    ("Nursing", "Nursing and patient care services"),
    ("Administration", "Hospital administration and management"),
    ("Finance", "Billing, cashier and financial accounting"),
    ("Health Records", "Health records and medical documentation"),
    ("Information Technology", "IT systems and technical support"),
]


def seed_departments_for(hospital):
    """Create the canonical department set for `hospital` (idempotent)."""
    for name, description in DEPARTMENTS:
        Department.all_objects.get_or_create(
            hospital=hospital, name=name, defaults={"description": description}
        )
