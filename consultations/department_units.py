# Department Units Configuration
# This file defines common hospital units for the referral system

DEPARTMENT_UNITS = {
    'General': ['Emergency', 'Outpatient', 'Inpatient', 'Day Care'],
    'Specialized': [
        'Intensive Care Unit (ICU)',
        'Neonatal Intensive Care Unit (NICU)',
        'Pediatric Intensive Care Unit (PICU)',
        'Coronary Care Unit (CCU)',
        'High Dependency Unit (HDU)',
        'Burn Unit',
        'Stroke Unit',
        'Oncology Unit',
        'Hematology Unit',
        'Nephrology Unit (Dialysis)',
        'Pulmonary Unit',
        'Gastroenterology Unit',
        'Endocrinology Unit',
        'Rheumatology Unit',
        'Infectious Diseases Unit',
        'Geriatric Unit'
    ],
    'Surgical': [
        'Operating Theater',
        'Post-Anesthesia Care Unit (PACU)',
        'Surgical Ward',
        'Ambulatory Surgery Unit',
        'Preoperative Assessment Unit',
        'Endoscopy Suite',
        'Minor Procedures Unit'
    ],
    'Maternity': [
        'Labor and Delivery',
        'Postpartum Unit',
        'Antenatal Clinic',
        'Postnatal Clinic',
        'Fetal Medicine Unit'
    ],
    'Pediatric': [
        'Pediatric Ward',
        'Pediatric Emergency',
        'Pediatric Outpatient',
        'Adolescent Medicine Unit',
        'Pediatric Surgery Unit'
    ],
    'Diagnostic': [
        'Radiology Unit',
        'Imaging Center',
        'Laboratory Services',
        'Pathology Unit',
        'Nuclear Medicine Unit',
        'Endoscopy Unit',
        'Electrophysiology Unit'
    ],
    'Rehabilitation': [
        'Physical Therapy Unit',
        'Occupational Therapy Unit',
        'Speech Therapy Unit',
        'Cardiac Rehabilitation',
        'Pulmonary Rehabilitation',
        'Neurological Rehabilitation',
        'Sports Medicine Unit'
    ],
    'Mental Health': [
        'Psychiatry Unit',
        'Psychology Services',
        'Addiction Treatment Unit',
        'Child and Adolescent Mental Health',
        'Geriatric Psychiatry Unit',
        'Forensic Psychiatry Unit'
    ],
    'Support Services': [
        'Pharmacy Services',
        'Nutrition and Dietetics',
        'Social Work Services',
        'Palliative Care Unit',
        'Pain Management Unit',
        'Wound Care Unit',
        'Infection Control Unit',
        'Medical Records',
        'Patient Education Unit'
    ],
    'Specialty Clinics': [
        'Cardiology Clinic',
        'Neurology Clinic',
        'Dermatology Clinic',
        'Ophthalmology Clinic',
        'ENT Clinic',
        'Urology Clinic',
        'Orthopedics Clinic',
        'Rheumatology Clinic',
        'Endocrinology Clinic',
        'Gastroenterology Clinic',
        'Hematology Clinic',
        'Oncology Clinic',
        'Pulmonology Clinic',
        'Nephrology Clinic'
    ]
}

# Flat list of all units for autocomplete/dropdown
def get_all_units():
    """Return a flat list of all available units"""
    units = []
    for category_units in DEPARTMENT_UNITS.values():
        units.extend(category_units)
    return sorted(list(set(units)))  # Remove duplicates and sort

# Get units by category
def get_units_by_category(category):
    """Return units for a specific category"""
    return DEPARTMENT_UNITS.get(category, [])

# Common units for quick access
COMMON_UNITS = [
    'Emergency',
    'Intensive Care Unit (ICU)',
    'Neonatal Intensive Care Unit (NICU)',
    'Pediatric Intensive Care Unit (PICU)',
    'Operating Theater',
    'Labor and Delivery',
    'Post-Anesthesia Care Unit (PACU)',
    'Radiology Unit',
    'Laboratory Services',
    'Physical Therapy Unit'
]
