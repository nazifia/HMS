"""Per-hospital physician specialty seeding.

Canonical list of medical specializations, scoped to a hospital so every tenant
gets its own copy (mirrors accounts/department_seed.py and
laboratory/lab_catalog_seed.py).

Consumed by:
  - the saas signup flow (new tenants),
  - migration 0005_seed_specialties (existing tenants in prod),
  - the populate_hospital_data management command (legacy ad-hoc seed).

Every name here MUST be resolvable by
consultations.referral_mappings.get_department_for_specialty(), otherwise a
referral raised against a doctor with that specialty lands in no department.
See the test in doctors/tests.py that enforces this.
"""

from .models import Specialization

# (name, description)
SPECIALTIES = [
    # --- Medical specialties ---
    ("General Medicine", "Diagnosis and treatment of common diseases in adults"),
    ("Internal Medicine", "Comprehensive adult medical care and complex diagnosis"),
    ("Family Medicine", "Primary and continuing care for patients of all ages"),
    ("Emergency Medicine", "Immediate care for acute illness and injury"),
    ("Cardiology", "Heart and blood vessel disorders"),
    ("Neurology", "Disorders of the brain, spinal cord and nerves"),
    ("Pulmonology", "Diseases of the lungs and respiratory system"),
    ("Gastroenterology", "Digestive system and liver disorders"),
    ("Nephrology", "Kidney disease, dialysis and hypertension"),
    ("Endocrinology", "Diabetes, thyroid and hormonal disorders"),
    ("Rheumatology", "Autoimmune, joint and musculoskeletal disease"),
    ("Infectious Diseases", "Bacterial, viral, fungal and parasitic infections"),
    ("Dermatology", "Skin, hair and nail disorders"),
    ("Hematology", "Blood and blood-forming organ disorders"),
    ("Medical Oncology", "Cancer treatment with chemotherapy and systemic therapy"),
    ("Radiation Oncology", "Cancer treatment with radiotherapy"),
    ("Psychiatry", "Mental, emotional and behavioural disorders"),
    ("Geriatrics", "Medical care of elderly patients"),
    ("Pediatrics", "Medical care for infants, children and adolescents"),
    ("Neonatology", "Care of newborn and premature infants"),
    # --- Surgical specialties ---
    ("General Surgery", "Surgical treatment across a broad range of conditions"),
    ("Orthopedic Surgery", "Bones, joints, ligaments, muscles and tendons"),
    ("Neurosurgery", "Surgery of the brain, spine and peripheral nerves"),
    ("Cardiac Surgery", "Surgery of the heart and great vessels"),
    ("Plastic Surgery", "Reconstructive and cosmetic surgery"),
    ("Pediatric Surgery", "Surgical care for infants, children and adolescents"),
    ("Urology", "Urinary tract and male reproductive system"),
    ("Anesthesiology", "Anesthesia and perioperative pain management"),
    ("Ophthalmology", "Eye and vision care, medical and surgical"),
    ("Otolaryngology", "Ear, nose, throat, head and neck"),
    ("Dental Surgery", "Oral, dental and maxillofacial surgery"),
    ("Obstetrics", "Pregnancy, childbirth and postnatal care"),
    ("Gynecology", "Female reproductive system health and surgery"),
    # --- Diagnostic specialties ---
    ("Radiology", "Medical imaging and image-guided diagnosis"),
    ("Pathology", "Laboratory diagnosis of disease from tissue and fluids"),
]


def seed_specialties_for(hospital):
    """Create the canonical specialty set for `hospital` (idempotent).

    Uses all_objects so it works outside a tenant request context (signup,
    shell, management commands).
    """
    for name, description in SPECIALTIES:
        Specialization.all_objects.get_or_create(
            hospital=hospital, name=name, defaults={"description": description}
        )
