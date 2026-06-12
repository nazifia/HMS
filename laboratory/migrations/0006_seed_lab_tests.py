from django.db import migrations
from decimal import Decimal


# (category, name, sample_type, price, unit, normal_range, duration)
TESTS = [
    # Haematology
    ("Haematology", "Full Blood Count (FBC)", "Blood", 3500, None, None, "1 day"),
    ("Haematology", "Erythrocyte Sedimentation Rate (ESR)", "Blood", 1500, "mm/hr", "0-20", "1 day"),
    ("Haematology", "Packed Cell Volume (PCV)", "Blood", 1000, "%", "36-50", "Same day"),
    ("Haematology", "Haemoglobin (Hb)", "Blood", 1000, "g/dL", "12-16", "Same day"),
    ("Haematology", "White Blood Cell Count (WBC)", "Blood", 1500, "x10^9/L", "4-11", "Same day"),
    ("Haematology", "Platelet Count", "Blood", 1500, "x10^9/L", "150-450", "Same day"),
    ("Haematology", "Peripheral Blood Film", "Blood", 2500, None, None, "1 day"),
    ("Haematology", "Reticulocyte Count", "Blood", 2000, "%", "0.5-1.5", "1 day"),
    ("Haematology", "Prothrombin Time (PT/INR)", "Blood", 3500, "sec", "11-13.5", "1 day"),
    ("Haematology", "Activated Partial Thromboplastin Time (APTT)", "Blood", 3500, "sec", "25-35", "1 day"),
    ("Haematology", "Bleeding Time", "Blood", 1000, "min", "2-7", "Same day"),
    ("Haematology", "Clotting Time", "Blood", 1000, "min", "5-10", "Same day"),
    ("Haematology", "Blood Group & Rhesus Factor", "Blood", 1500, None, None, "Same day"),
    ("Haematology", "Genotype (Hb Electrophoresis)", "Blood", 2500, None, None, "1 day"),
    ("Haematology", "Glucose-6-Phosphate Dehydrogenase (G6PD)", "Blood", 3000, None, None, "1 day"),
    ("Haematology", "Sickling Test", "Blood", 1500, None, None, "Same day"),
    # Clinical Chemistry
    ("Clinical Chemistry", "Fasting Blood Sugar (FBS)", "Blood", 1500, "mg/dL", "70-110", "Same day"),
    ("Clinical Chemistry", "Random Blood Sugar (RBS)", "Blood", 1500, "mg/dL", "70-140", "Same day"),
    ("Clinical Chemistry", "Oral Glucose Tolerance Test (OGTT)", "Blood", 5000, "mg/dL", None, "Same day"),
    ("Clinical Chemistry", "Glycated Haemoglobin (HbA1c)", "Blood", 5000, "%", "<5.7", "1 day"),
    ("Clinical Chemistry", "Urea", "Blood", 2000, "mg/dL", "15-45", "1 day"),
    ("Clinical Chemistry", "Creatinine", "Blood", 2000, "mg/dL", "0.6-1.3", "1 day"),
    ("Clinical Chemistry", "Electrolytes, Urea & Creatinine (E/U/Cr)", "Blood", 6000, None, None, "1 day"),
    ("Clinical Chemistry", "Uric Acid", "Blood", 2500, "mg/dL", "3.5-7.2", "1 day"),
    ("Clinical Chemistry", "Liver Function Test (LFT)", "Blood", 7000, None, None, "1 day"),
    ("Clinical Chemistry", "Aspartate Aminotransferase (AST)", "Blood", 2500, "U/L", "0-40", "1 day"),
    ("Clinical Chemistry", "Alanine Aminotransferase (ALT)", "Blood", 2500, "U/L", "0-40", "1 day"),
    ("Clinical Chemistry", "Alkaline Phosphatase (ALP)", "Blood", 2500, "U/L", "40-130", "1 day"),
    ("Clinical Chemistry", "Total & Direct Bilirubin", "Blood", 3000, "mg/dL", "0.1-1.2", "1 day"),
    ("Clinical Chemistry", "Total Protein & Albumin", "Blood", 3000, "g/dL", None, "1 day"),
    ("Clinical Chemistry", "Lipid Profile", "Blood", 7000, "mg/dL", None, "1 day"),
    ("Clinical Chemistry", "Serum Amylase", "Blood", 3500, "U/L", "30-110", "1 day"),
    ("Clinical Chemistry", "Serum Calcium", "Blood", 2500, "mg/dL", "8.5-10.5", "1 day"),
    ("Clinical Chemistry", "Serum Magnesium", "Blood", 2500, "mg/dL", "1.7-2.2", "1 day"),
    # Microbiology
    ("Microbiology", "Urine Microscopy, Culture & Sensitivity (M/C/S)", "Urine", 4000, None, None, "3 days"),
    ("Microbiology", "Stool Microscopy, Culture & Sensitivity", "Stool", 4000, None, None, "3 days"),
    ("Microbiology", "Blood Culture", "Blood", 6000, None, None, "5 days"),
    ("Microbiology", "Wound Swab M/C/S", "Swab", 4000, None, None, "3 days"),
    ("Microbiology", "High Vaginal Swab (HVS) M/C/S", "Swab", 4000, None, None, "3 days"),
    ("Microbiology", "Sputum M/C/S", "Sputum", 4000, None, None, "3 days"),
    ("Microbiology", "Sputum AFB (Ziehl-Neelsen)", "Sputum", 2500, None, None, "1 day"),
    ("Microbiology", "Urinalysis", "Urine", 1500, None, None, "Same day"),
    ("Microbiology", "Widal Test", "Blood", 2000, None, None, "Same day"),
    ("Microbiology", "Malaria Parasite (MP)", "Blood", 1500, None, None, "Same day"),
    ("Microbiology", "Malaria Rapid Diagnostic Test (mRDT)", "Blood", 1500, None, None, "Same day"),
    # Serology / Immunology
    ("Serology & Immunology", "HIV Screening", "Blood", 2000, None, None, "Same day"),
    ("Serology & Immunology", "Hepatitis B Surface Antigen (HBsAg)", "Blood", 2000, None, None, "Same day"),
    ("Serology & Immunology", "Hepatitis C Antibody (Anti-HCV)", "Blood", 2500, None, None, "Same day"),
    ("Serology & Immunology", "VDRL (Syphilis)", "Blood", 2000, None, None, "Same day"),
    ("Serology & Immunology", "H. Pylori Antibody", "Blood", 3000, None, None, "Same day"),
    ("Serology & Immunology", "Beta-hCG (Pregnancy Test)", "Blood", 2500, "mIU/mL", None, "Same day"),
    ("Serology & Immunology", "C-Reactive Protein (CRP)", "Blood", 3000, "mg/L", "<5", "1 day"),
    ("Serology & Immunology", "Rheumatoid Factor (RF)", "Blood", 3000, "IU/mL", "<14", "1 day"),
    ("Serology & Immunology", "Anti-Streptolysin O Titre (ASOT)", "Blood", 3000, "IU/mL", "<200", "1 day"),
    # Endocrinology / Hormones
    ("Endocrinology", "Thyroid Stimulating Hormone (TSH)", "Blood", 5000, "mIU/L", "0.4-4.0", "2 days"),
    ("Endocrinology", "Free Thyroxine (FT4)", "Blood", 5000, "ng/dL", "0.8-1.8", "2 days"),
    ("Endocrinology", "Triiodothyronine (T3)", "Blood", 5000, "ng/dL", "80-200", "2 days"),
    ("Endocrinology", "Prolactin", "Blood", 5000, "ng/mL", None, "2 days"),
    ("Endocrinology", "Luteinizing Hormone (LH)", "Blood", 5000, "mIU/mL", None, "2 days"),
    ("Endocrinology", "Follicle Stimulating Hormone (FSH)", "Blood", 5000, "mIU/mL", None, "2 days"),
    ("Endocrinology", "Testosterone", "Blood", 5500, "ng/dL", None, "2 days"),
    ("Endocrinology", "Estradiol (E2)", "Blood", 5500, "pg/mL", None, "2 days"),
    ("Endocrinology", "Progesterone", "Blood", 5500, "ng/mL", None, "2 days"),
    ("Endocrinology", "Prostate Specific Antigen (PSA)", "Blood", 6000, "ng/mL", "<4", "2 days"),
    # Histopathology / Cytology
    ("Histopathology", "Histology (Tissue Biopsy)", "Tissue", 15000, None, None, "7 days"),
    ("Histopathology", "Pap Smear (Cervical Cytology)", "Smear", 6000, None, None, "5 days"),
    ("Histopathology", "Fine Needle Aspiration Cytology (FNAC)", "Aspirate", 10000, None, None, "5 days"),
    # Other
    ("Other Tests", "Semen Analysis", "Semen", 4000, None, None, "Same day"),
    ("Other Tests", "Cerebrospinal Fluid (CSF) Analysis", "CSF", 6000, None, None, "1 day"),
]


def seed(apps, schema_editor):
    TestCategory = apps.get_model("laboratory", "TestCategory")
    Test = apps.get_model("laboratory", "Test")
    cat_cache = {}
    for cat, name, sample, price, unit, nrange, duration in TESTS:
        if cat not in cat_cache:
            cat_cache[cat], _ = TestCategory.objects.get_or_create(name=cat)
        Test.objects.get_or_create(
            name=name,
            defaults={
                "category": cat_cache[cat],
                "sample_type": sample,
                "price": Decimal(str(price)),
                "unit": unit,
                "normal_range": nrange,
                "duration": duration,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratory", "0005_alter_testresult_options"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
