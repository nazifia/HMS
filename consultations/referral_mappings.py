"""
Referral mapping configurations for HMS
Handles unit-to-department and specialty-to-department mappings
"""

# Comprehensive mapping of units to their parent departments
UNIT_TO_DEPARTMENT_MAP = {
    # Emergency-related units
    'Emergency': 'Emergency Medicine',
    'Emergency Room': 'Emergency Medicine',
    'ER': 'Emergency Medicine',
    'Accident & Emergency': 'Emergency Medicine',
    'A&E': 'Emergency Medicine',
    
    # Critical Care units
    'ICU': 'General Medicine',
    'Intensive Care Unit': 'General Medicine',
    'Critical Care Unit': 'General Medicine',
    'CCU': 'General Medicine',
    
    # Specialized ICU units
    'NICU': 'Pediatrics',
    'Neonatal ICU': 'Pediatrics',
    'SICU': 'Surgery',
    'Surgical ICU': 'Surgery',
    'PICU': 'Pediatrics',
    'Pediatric ICU': 'Pediatrics',
    
    # Maternity and Gynecology units
    'Labor and Delivery': 'Obstetrics & Gynecology',
    'Labor Ward': 'Labor',
    'Delivery Room': 'Obstetrics & Gynecology',
    'Maternity Ward': 'Obstetrics & Gynecology',
    'Gynae Ward': 'Obstetrics & Gynecology',
    
    # ANC and Antenatal Care units
    'ANC': 'ANC',
    'Antenatal Care': 'ANC',
    'Antenatal Clinic': 'ANC',
    'Antenatal Ward': 'ANC',
    
    # Labor units
    'Labor': 'Labor',
    'Labor Room': 'Labor',
    
    # SCBU units
    'SCBU': 'SCBU',
    'Special Care Baby Unit': 'SCBU',
    'Neonatal Unit': 'SCBU',
    'NICU': 'Pediatrics',
    
    # Family Planning units
    'Family Planning': 'Family Planning',
    'FP Clinic': 'Family Planning',
    'Family Planning Clinic': 'Family Planning',
    'Contraceptive Clinic': 'Family Planning',
    
    # Dental units
    'Dental': 'Dental',
    'Dental Clinic': 'Dental',
    'Dentistry': 'Dental',
    'Oral Surgery Unit': 'Dental',
    
    # ENT units
    'ENT': 'ENT',
    'Ear Nose Throat': 'ENT',
    'ENT Clinic': 'ENT',
    'Otolaryngology': 'ENT',
    
    # Ophthalmic units
    'Ophthalmic': 'Ophthalmic',
    'Eye Clinic': 'Ophthalmic',
    'Ophthalmology': 'Ophthalmic',
    'Eye Unit': 'Ophthalmic',
    
    # Oncology units
    'Oncology': 'Oncology',
    'Cancer Unit': 'Oncology',
    'Oncology Clinic': 'Oncology',
    'Chemotherapy Unit': 'Oncology',
    'Radiotherapy Unit': 'Oncology',
    
    # Surgical units
    'Operating Theater': 'Surgery',
    'Operating Room': 'Surgery',
    'OR': 'Surgery',
    'Theater': 'Surgery',
    'Surgical Ward': 'Surgery',
    'Recovery Room': 'Surgery',
    'Post-Anesthesia Care Unit': 'Surgery',
    'PACU': 'Surgery',
    
    # Diagnostic units
    'Radiology': 'Radiology',
    'X-Ray': 'Radiology',
    'CT Scan': 'Radiology',
    'MRI': 'Radiology',
    'Ultrasound': 'Radiology',
    'Imaging': 'Radiology',
    
    'Laboratory': 'Laboratory',
    'Lab': 'Laboratory',
    'Pathology': 'Laboratory',
    'Blood Bank': 'Laboratory',
    
    # Medical units
    'Medical Ward': 'General Medicine',
    'General Ward': 'General Medicine',
    'Medical Unit': 'General Medicine',
    
    # Pediatric units
    'Pediatric Ward': 'Pediatrics',
    'Children Ward': 'Pediatrics',
    'Nursery': 'Pediatrics',
    'Baby Care Unit': 'Pediatrics',
    
    # Cardiac units
    'Cardiac Ward': 'Cardiology',
    'Cardiac Unit': 'Cardiology',
    'Cath Lab': 'Cardiology',
    
    # Neurology units
    'Neuro Ward': 'Neurology',
    'Neuro Unit': 'Neurology',
    'Stroke Unit': 'Neurology',
    
    # Orthopedic units
    'Orthopedic Ward': 'Orthopedics',
    'Fracture Clinic': 'Orthopedics',
    'Plaster Room': 'Orthopedics',
    
    # Pharmacy
    'Pharmacy': 'Pharmacy',
    'Drug Store': 'Pharmacy',
    'Dispensary': 'Pharmacy',
    
    # Administrative units
    'Reception': 'Administration',
    'Registration': 'Administration',
    'Records': 'Administration',
    'Cashier': 'Finance',
    'Billing': 'Finance',
    'Accounts': 'Finance',
    
    # Other common units
    'Outpatient': 'General Medicine',
    'OPD': 'General Medicine',
    'Clinic': 'General Medicine',
    'Consultation Room': 'General Medicine',
}

# Comprehensive mapping of specialties to their parent departments
SPECIALTY_TO_DEPARTMENT_MAP = {
    # Gynecology specialties
    'Gynecology': 'Obstetrics & Gynecology',
    'Gynae': 'Obstetrics & Gynecology',
    'Gynae Emergency': 'Obstetrics & Gynecology',
    'Obstetrics': 'Obstetrics & Gynecology',
    'Maternity': 'Obstetrics & Gynecology',
    'Prenatal': 'Obstetrics & Gynecology',
    'Antenatal': 'ANC',
    'Antenatal Care': 'ANC',
    
    # ANC specialties
    'ANC': 'ANC',
    
    # Labor specialties
    'Labor': 'Labor',
    'Labor and Delivery': 'Labor',
    'Delivery': 'Labor',
    
    # SCBU specialties
    'SCBU': 'SCBU',
    'Neonatal Care': 'SCBU',
    'Neonatology': 'SCBU',
    'NICU': 'Pediatrics',
    
    # Cardiology specialties
    'Cardiology': 'Cardiology',
    'Interventional Cardiology': 'Cardiology',
    'Pediatric Cardiology': 'Cardiology',
    'Electrophysiology': 'Cardiology',
    
    # Neurology specialties
    'Neurology': 'Neurology',
    'Neurosurgery': 'Neurology',
    'Stroke': 'Neurology',
    'Epilepsy': 'Neurology',
    
    # Surgical specialties
    'General Surgery': 'Surgery',
    'Orthopedic Surgery': 'Orthopedics',
    'Pediatric Surgery': 'Surgery',
    'Neurosurgery': 'Neurology',
    'Cardiac Surgery': 'Cardiology',
    'Plastic Surgery': 'Surgery',
    'Urology': 'Surgery',
    'ENT Surgery': 'ENT',
    'Ophthalmic Surgery': 'Ophthalmic',
    'Dental Surgery': 'Dental',
    
    # Medical specialties
    'General Medicine': 'General Medicine',
    'Internal Medicine': 'General Medicine',
    'Family Medicine': 'General Medicine',
    'Emergency Medicine': 'Emergency Medicine',
    
    # Pediatric specialties
    'Pediatrics': 'Pediatrics',
    'Pediatric Surgery': 'Surgery',
    
    # Family Planning specialties
    'Family Planning': 'Family Planning',
    'Contraception': 'Family Planning',
    'FP': 'Family Planning',
    
    # Dental specialties
    'Dental': 'Dental',
    'Dentistry': 'Dental',
    'Oral Surgery': 'Dental',
    'Oral Medicine': 'Dental',
    
    # ENT specialties
    'ENT': 'ENT',
    'Ear Nose and Throat': 'ENT',
    'Otolaryngology': 'ENT',
    'ENT Surgery': 'ENT',
    
    # Ophthalmic specialties
    'Ophthalmic': 'Ophthalmic',
    'Ophthalmology': 'Ophthalmic',
    'Eye Care': 'Ophthalmic',
    'Eye Surgery': 'Ophthalmic',
    
    # Oncology specialties
    'Oncology': 'Oncology',
    'Cancer Care': 'Oncology',
    'Chemotherapy': 'Oncology',
    'Radiotherapy': 'Oncology',
    'Radiation Oncology': 'Oncology',
    'Medical Oncology': 'Oncology',
    'Surgical Oncology': 'Oncology',
    
    # Dermatology specialty
    'Dermatology': 'Dermatology',
    'Skin Care': 'Dermatology',
    
    # Diagnostic specialties
    'Radiology': 'Radiology',
    'Diagnostic Radiology': 'Radiology',
    'Interventional Radiology': 'Radiology',
    'Pathology': 'Laboratory',
    'Clinical Pathology': 'Laboratory',
    'Hematology': 'Laboratory',
    
    # Other specialties
    'Orthopedics': 'Orthopedics',
    'Psychiatry': 'General Medicine',
    'Anesthesiology': 'Surgery',
}

def get_department_for_unit(unit_name):
    """
    Get the parent department for a given unit name
    
    Args:
        unit_name (str): Name of the unit
        
    Returns:
        str: Name of the parent department, or None if not found
    """
    if not unit_name:
        return None
    
    # Clean the unit name - remove extra whitespace and convert to title case
    clean_unit = unit_name.strip().title()
    
    # Try exact match first
    if clean_unit in UNIT_TO_DEPARTMENT_MAP:
        return UNIT_TO_DEPARTMENT_MAP[clean_unit]
    
    # Try case-insensitive match
    for unit, dept in UNIT_TO_DEPARTMENT_MAP.items():
        if unit.lower() == clean_unit.lower():
            return dept
    
    # Try partial match (contains)
    for unit, dept in UNIT_TO_DEPARTMENT_MAP.items():
        if clean_unit.lower() in unit.lower() or unit.lower() in clean_unit.lower():
            return dept
    
    return None

def get_department_for_specialty(specialty_name, preferred_unit=None):
    """
    Get the parent department for a given specialty name
    
    Args:
        specialty_name (str): Name of the specialty
        preferred_unit (str): Optional unit name to prioritize matching departments
        
    Returns:
        str: Name of the parent department, or None if not found
    """
    if not specialty_name:
        return None
    
    # Clean the specialty name
    clean_specialty = specialty_name.strip().title()
    
    # Try exact match first
    if clean_specialty in SPECIALTY_TO_DEPARTMENT_MAP:
        mapped_dept = SPECIALTY_TO_DEPARTMENT_MAP[clean_specialty]
        
        # If preferred_unit is provided, check if the mapped department conflicts
        if preferred_unit:
            unit_dept = get_department_for_unit(preferred_unit)
            if unit_dept and unit_dept != mapped_dept:
                # Unit and specialty map to different departments, prioritize unit
                return unit_dept
        
        return mapped_dept
    
    # Try case-insensitive match
    for specialty, dept in SPECIALTY_TO_DEPARTMENT_MAP.items():
        if specialty.lower() == clean_specialty.lower():
            mapped_dept = dept
            
            # If preferred_unit is provided, check for conflicts
            if preferred_unit:
                unit_dept = get_department_for_unit(preferred_unit)
                if unit_dept and unit_dept != mapped_dept:
                    return unit_dept
            
            return mapped_dept
    
    # Try partial match (contains)
    for specialty, dept in SPECIALTY_TO_DEPARTMENT_MAP.items():
        if clean_specialty.lower() in specialty.lower() or specialty.lower() in clean_specialty.lower():
            mapped_dept = dept
            
            # If preferred_unit is provided, check for conflicts
            if preferred_unit:
                unit_dept = get_department_for_unit(preferred_unit)
                if unit_dept and unit_dept != mapped_dept:
                    return unit_dept
            
            return mapped_dept
    
    return None

def get_all_units_for_department(department_name):
    """
    Get all units that belong to a specific department
    
    Args:
        department_name (str): Name of the department
        
    Returns:
        list: List of unit names belonging to the department
    """
    if not department_name:
        return []
    
    units = []
    department_name = department_name.strip()
    
    for unit, dept in UNIT_TO_DEPARTMENT_MAP.items():
        # Case-insensitive comparison for department names
        if dept.lower() == department_name.lower():
            units.append(unit)
    
    # Also include the department name itself as a potential unit reference
    # This handles cases where referred_to_unit contains the department name directly
    if department_name not in units:
        units.append(department_name)
    
    # DEBUG: Log what we're returning
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_all_units_for_department('{department_name}'): {units}")
    
    return sorted(set(units))


def get_all_specialties_for_department(department_name):
    """
    Get all specialties that belong to a specific department
    
    Args:
        department_name (str): Name of the department
        
    Returns:
        list: List of specialty names belonging to the department
    """
    if not department_name:
        return []
    
    specialties = []
    department_name = department_name.strip()
    
    for specialty, dept in SPECIALTY_TO_DEPARTMENT_MAP.items():
        # Case-insensitive comparison for department names
        if dept.lower() == department_name.lower():
            specialties.append(specialty)
    
    # Also include the department name itself as a potential specialty reference
    # This handles cases where referred_to_specialty contains the department name directly
    if department_name not in specialties:
        specialties.append(department_name)
    
    return sorted(set(specialties))
def normalize_unit_name(unit_name):
    """
    Normalize a unit name to a standard format
    
    Args:
        unit_name (str): Raw unit name
        
    Returns:
        str: Normalized unit name
    """
    if not unit_name:
        return None
    
    clean_name = unit_name.strip().title()
    
    # Common abbreviations expansions
    abbreviations = {
        'Er': 'Emergency',
        'Icu': 'Intensive Care Unit',
        'CcU': 'Critical Care Unit',
        'Nicu': 'Neonatal Intensive Care Unit',
        'Picu': 'Pediatric Intensive Care Unit',
        'Sicu': 'Surgical Intensive Care Unit',
        'Or': 'Operating Room',
        'Opd': 'Outpatient',
        'Lab': 'Laboratory',
        'A&E': 'Accident & Emergency',
    }
    
    # Expand abbreviations
    for abbr, expansion in abbreviations.items():
        if clean_name.lower() == abbr.lower():
            return expansion
        elif f' {abbr} ' in f' {clean_name} '.lower():
            clean_name = clean_name.replace(abbr, expansion, 1).replace('  ', ' ').strip()
    
    return clean_name

def normalize_specialty_name(specialty_name):
    """
    Normalize a specialty name to a standard format
    
    Args:
        specialty_name (str): Raw specialty name
        
    Returns:
        str: Normalized specialty name
    """
    if not specialty_name:
        return None
    
    clean_name = specialty_name.strip().title()
    
    # Common specialty variations
    variations = {
        'Gynae': 'Gynecology',
        'Obs': 'Obstetrics',
        'Paeds': 'Pediatrics',
        'Paediatric': 'Pediatric',
    }
    
    # Apply variations
    for variation, standard in variations.items():
        if clean_name.lower() == variation.lower():
            return standard
        elif f' {variation} ' in f' {clean_name} '.lower():
            clean_name = clean_name.replace(variation, standard, 1).replace('  ', ' ').strip()
    
    return clean_name