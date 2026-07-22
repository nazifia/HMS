"""Per-hospital laboratory catalog seeding.

Canonical list of lab investigations (tests) grouped by category, each with its
result parameters and normal ranges. Scoped to a hospital so every tenant gets
its own copy (mirrors accounts/department_seed.py).

Consumed by:
  - the saas signup flow (new tenants),
  - migration 0009_seed_lab_catalog (existing tenants in prod),
  - the populate_lab_tests management command (manual / ad-hoc re-seed).

Add/edit tests here; re-running any consumer is idempotent (get_or_create).
"""

from decimal import Decimal

from .models import Test, TestCategory, TestParameter

# category -> list of tests.
# Each test: (name, price, sample_type, description, [(param, normal_range, unit), ...])
# Prices are placeholders in the app's base currency; adjust per tariff.
CATALOG = {
    "Hematology": [
        ("Complete Blood Count (CBC)", 3500, "Whole Blood", "Measures the components of blood.", [
            ("Hemoglobin (Hb)", "Male: 13.5-17.5 g/dL Female: 12.0-15.5 g/dL", "g/dL"),
            ("Hematocrit (Hct)", "Male: 41-53% Female: 36-46%", "%"),
            ("White Blood Cells (WBC)", "4,000-11,000 /uL", "/uL"),
            ("Neutrophils", "40-75% of WBCs", "%"),
            ("Lymphocytes", "20-45% of WBCs", "%"),
            ("Monocytes", "2-8% of WBCs", "%"),
            ("Eosinophils", "1-6% of WBCs", "%"),
            ("Basophils", "0-1% of WBCs", "%"),
            ("Platelets", "150,000-400,000 /uL", "/uL"),
            ("Mean Corpuscular Volume (MCV)", "80-100 fL", "fL"),
        ]),
        ("Erythrocyte Sedimentation Rate (ESR)", 1500, "Whole Blood", "Non-specific marker of inflammation.", [
            ("ESR", "Male: <15 mm/hr Female: <20 mm/hr", "mm/hr"),
        ]),
        ("Blood Group & Rhesus Factor", 1500, "Whole Blood", "ABO group and Rhesus D typing.", [
            ("ABO Group", "A / B / AB / O", ""),
            ("Rhesus (D) Factor", "Positive / Negative", ""),
        ]),
        ("Hemoglobin Electrophoresis (Genotype)", 3500, "Whole Blood", "Screens for sickle cell disease and trait.", [
            ("Hemoglobin Pattern", "HbAA (normal), HbAS (trait), HbSS (disease)", ""),
        ]),
        ("G6PD Screening", 3000, "Whole Blood", "Screens for G6PD deficiency.", [
            ("G6PD Activity", "Normal enzyme activity", ""),
        ]),
    ],
    "Liver Function Tests": [
        ("Liver Function Tests (LFTs)", 7000, "Serum", "Assesses liver function and health.", [
            ("Alanine Aminotransferase (ALT)", "7-56 U/L", "U/L"),
            ("Aspartate Aminotransferase (AST)", "10-40 U/L", "U/L"),
            ("Alkaline Phosphatase (ALP)", "40-129 U/L", "U/L"),
            ("Gamma-glutamyl Transferase (GGT)", "9-48 U/L", "U/L"),
            ("Total Bilirubin", "0.1-1.2 mg/dL", "mg/dL"),
            ("Direct Bilirubin", "0.0-0.3 mg/dL", "mg/dL"),
            ("Albumin", "3.5-5.5 g/dL", "g/dL"),
            ("Total Protein", "6.0-8.3 g/dL", "g/dL"),
        ]),
    ],
    "Renal Function Tests": [
        ("Renal Function Tests (RFTs)", 6000, "Serum/Urine", "Assesses kidney function.", [
            ("Blood Urea Nitrogen (BUN)", "7-20 mg/dL", "mg/dL"),
            ("Serum Creatinine", "Male: 0.7-1.3 mg/dL Female: 0.6-1.1 mg/dL", "mg/dL"),
            ("BUN:Creatinine Ratio", "10:1 to 20:1", "ratio"),
            ("Estimated GFR (eGFR)", ">90 mL/min/1.73 m2", "mL/min/1.73 m2"),
        ]),
    ],
    "Electrolytes": [
        ("Electrolyte Panel", 6000, "Serum", "Measures serum electrolyte levels.", [
            ("Sodium (Na+)", "135-145 mmol/L", "mmol/L"),
            ("Potassium (K+)", "3.5-5.0 mmol/L", "mmol/L"),
            ("Chloride (Cl-)", "98-106 mmol/L", "mmol/L"),
            ("Bicarbonate (HCO3-)", "22-29 mmol/L", "mmol/L"),
            ("Calcium (Total)", "8.5-10.5 mg/dL", "mg/dL"),
            ("Ionized Calcium", "4.4-5.4 mg/dL", "mg/dL"),
            ("Magnesium", "1.5-2.5 mg/dL", "mg/dL"),
            ("Phosphate (PO4)", "2.5-4.5 mg/dL", "mg/dL"),
        ]),
    ],
    "Glucose and Diabetes-Related": [
        ("Diabetes Panel", 5000, "Blood/Serum", "Tests related to glucose metabolism and diabetes.", [
            ("Fasting Blood Glucose", "70-99 mg/dL", "mg/dL"),
            ("2-Hour Postprandial Glucose", "<140 mg/dL", "mg/dL"),
            ("Random Blood Glucose", "<200 mg/dL", "mg/dL"),
            ("HbA1c (Glycated Hemoglobin)", "<5.7% Normal, 5.7-6.4% Prediabetes, >=6.5% Diabetes", "%"),
        ]),
    ],
    "Lipid Profile": [
        ("Lipid Panel", 7000, "Serum", "Measures cholesterol and triglyceride levels.", [
            ("Total Cholesterol", "<200 mg/dL", "mg/dL"),
            ("LDL Cholesterol", "<100 mg/dL", "mg/dL"),
            ("HDL Cholesterol", ">40 mg/dL (Male) >50 mg/dL (Female)", "mg/dL"),
            ("Triglycerides", "<150 mg/dL", "mg/dL"),
        ]),
    ],
    "Thyroid Function Tests": [
        ("Thyroid Panel", 15000, "Serum", "Assesses thyroid gland function.", [
            ("TSH (Thyroid Stimulating Hormone)", "0.4-4.0 mIU/L", "mIU/L"),
            ("Free T4 (Thyroxine)", "0.8-1.8 ng/dL", "ng/dL"),
            ("Free T3 (Triiodothyronine)", "2.3-4.2 pg/mL", "pg/mL"),
        ]),
    ],
    "Coagulation Profile": [
        ("Coagulation Panel", 3500, "Plasma", "Assesses blood clotting ability.", [
            ("Prothrombin Time (PT)", "11-13.5 seconds", "seconds"),
            ("INR", "0.8-1.1", ""),
            ("Activated Partial Thromboplastin Time (aPTT)", "25-35 seconds", "seconds"),
            ("D-dimer", "<0.5 ug/mL FEU", "ug/mL FEU"),
        ]),
    ],
    "Urinalysis": [
        ("Urinalysis (Random)", 1500, "Urine", "Analyzes components of a random urine sample.", [
            ("Color", "Yellow to amber", ""),
            ("Appearance", "Clear", ""),
            ("pH", "4.5-8.0", ""),
            ("Specific Gravity", "1.005-1.030", ""),
            ("Protein", "Negative", ""),
            ("Glucose", "Negative", ""),
            ("Ketones", "Negative", ""),
            ("Blood", "Negative", ""),
            ("Leukocyte Esterase", "Negative", ""),
            ("Nitrites", "Negative", ""),
        ]),
        ("Urinalysis (24-Hour Collection)", 3000, "Urine (24-hour)", "Analyzes urine collected over 24 hours.", [
            ("Color (24h)", "Yellow to amber", ""),
            ("Appearance (24h)", "Clear", ""),
            ("pH (24h)", "4.5-8.0", ""),
            ("Specific Gravity (24h)", "1.005-1.030", ""),
            ("Protein (24h)", "<150 mg/24h", "mg/24h"),
        ]),
    ],
    "Cardiac Markers": [
        ("Cardiac Enzyme Panel", 15000, "Serum", "Measures markers of heart damage.", [
            ("Troponin I", "<0.04 ng/mL", "ng/mL"),
            ("Troponin T", "<0.01 ng/mL", "ng/mL"),
            ("CK-MB (Creatine Kinase-MB)", "<5 ng/mL or <5% of total CK", "ng/mL or %"),
            ("BNP (B-type Natriuretic Peptide)", "<100 pg/mL", "pg/mL"),
            ("NT-proBNP", "<300 pg/mL (varies with age and gender)", "pg/mL"),
        ]),
    ],
    "Inflammatory Markers": [
        ("Inflammation Panel", 6000, "Serum/Plasma", "Measures markers of inflammation.", [
            ("C-Reactive Protein (CRP)", "<5 mg/L", "mg/L"),
            ("High-sensitivity CRP (hs-CRP)", "<1 mg/L (low risk)", "mg/L"),
            ("Erythrocyte Sedimentation Rate (ESR)", "Male: <15 mm/hr Female: <20 mm/hr", "mm/hr"),
            ("Ferritin (Inflammation)", "Male: 24-336 ng/mL Female: 11-307 ng/mL", "ng/mL"),
        ]),
    ],
    "Iron Studies": [
        ("Iron Panel", 9000, "Serum", "Assesses iron levels and metabolism.", [
            ("Serum Iron", "60-170 mcg/dL", "mcg/dL"),
            ("Total Iron Binding Capacity (TIBC)", "240-450 mcg/dL", "mcg/dL"),
            ("Transferrin Saturation", "20-50%", "%"),
            ("Serum Ferritin", "Male: 24-336 ng/mL Female: 11-307 ng/mL", "ng/mL"),
        ]),
    ],
    "Pancreatic Function": [
        ("Pancreatic Enzyme Tests", 5000, "Serum", "Assesses pancreatic function.", [
            ("Amylase", "30-110 U/L", "U/L"),
            ("Lipase", "0-160 U/L", "U/L"),
        ]),
    ],
    "Hormones & Endocrinology": [
        ("Hormone Panel", 20000, "Serum/Plasma", "Measures various hormone levels.", [
            ("Cortisol (Morning)", "6-23 mcg/dL", "mcg/dL"),
            ("Parathyroid Hormone (PTH)", "10-65 pg/mL", "pg/mL"),
            ("Vitamin D (25-Hydroxy)", "30-100 ng/mL", "ng/mL"),
            ("Insulin (Fasting)", "2-25 uIU/mL", "uIU/mL"),
            ("Prolactin", "Male: 2-18 ng/mL Female: 2-29 ng/mL", "ng/mL"),
            ("FSH (Follicle Stimulating Hormone)", "Male: 1.5-12.4 mIU/mL Female: varies with cycle", "mIU/mL"),
            ("LH (Luteinizing Hormone)", "Male: 1.7-8.6 mIU/mL Female: varies with cycle", "mIU/mL"),
            ("Estradiol (E2)", "Male: 10-40 pg/mL Female: varies with phase", "pg/mL"),
            ("Testosterone", "Male: 300-1000 ng/dL Female: 15-70 ng/dL", "ng/dL"),
        ]),
    ],
    "Infectious Disease Screening": [
        ("Malaria Rapid Diagnostic Test (RDT)", 1500, "Whole Blood", "Rapid antigen test for malaria.", [
            ("RDT Result", "Negative", ""),
        ]),
        ("Malaria Blood Smear", 1500, "Blood Smear", "Microscopy for malaria parasites.", [
            ("Parasite Finding", "No parasites seen", ""),
        ]),
        ("HIV 1 & 2 Antibody Test", 2000, "Serum/Plasma", "Screens for HIV antibodies.", [
            ("Antibody Result", "Negative", ""),
        ]),
        ("HIV Viral Load", 50000, "Plasma", "Measures the amount of HIV virus in blood.", [
            ("Viral Load", "<20-50 copies/mL (undetectable)", "copies/mL"),
        ]),
        ("Hepatitis B Surface Antigen (HBsAg)", 2000, "Serum", "Screens for Hepatitis B infection.", [
            ("HBsAg Result", "Negative", ""),
        ]),
        ("Hepatitis C Antibody (Anti-HCV)", 2500, "Serum", "Screens for Hepatitis C antibodies.", [
            ("HCV Antibody Result", "Negative", ""),
        ]),
        ("Tuberculosis (GeneXpert Sputum AFB)", 8000, "Sputum", "Detects Mycobacterium tuberculosis in sputum.", [
            ("GeneXpert Result", "Negative for MTB", ""),
        ]),
        ("Typhoid (Widal Test)", 2000, "Serum", "Serological test for typhoid fever.", [
            ("Widal Test Result", "Negative or <1:80 for O and H agglutinins", ""),
        ]),
        ("H. pylori Antigen/Antibody", 3000, "Stool/Serum", "Tests for Helicobacter pylori infection.", [
            ("H. pylori Result", "Negative", ""),
        ]),
        ("VDRL / RPR (Syphilis)", 2000, "Serum", "Serological screen for syphilis.", [
            ("Syphilis Serology Result", "Non-reactive", ""),
        ]),
    ],
    "Parasitology & Stool Analysis": [
        ("Stool Microscopy", 1500, "Stool", "Microscopy of stool for ova, cysts and parasites.", [
            ("Microscopic Finding", "No ova, cysts, or parasites", ""),
        ]),
        ("Stool Occult Blood", 1500, "Stool", "Checks for hidden blood in stool.", [
            ("Occult Blood Result", "Negative", ""),
        ]),
        ("Stool Reducing Substances", 1500, "Stool", "Checks for reducing substances in stool.", [
            ("Reducing Substances Result", "Negative", ""),
        ]),
        ("Giardia Lamblia Antigen", 3000, "Stool", "Detects Giardia lamblia antigen in stool.", [
            ("Giardia Antigen Result", "Negative", ""),
        ]),
        ("Entamoeba Histolytica Antigen", 3000, "Stool", "Detects Entamoeba histolytica antigen in stool.", [
            ("Entamoeba Antigen Result", "Negative", ""),
        ]),
    ],
    "Nutritional & Micronutrient Tests": [
        ("Vitamin B12 Level", 6000, "Serum", "Measures Vitamin B12 levels.", [
            ("Vitamin B12", "190-950 pg/mL", "pg/mL"),
        ]),
        ("Folate Level", 6000, "Serum", "Measures folate levels.", [
            ("Folate", "2.7-17.0 ng/mL", "ng/mL"),
        ]),
        ("Vitamin D (25-Hydroxy) Level", 8000, "Serum", "Measures Vitamin D levels.", [
            ("Vitamin D (25-Hydroxy)", "30-100 ng/mL", "ng/mL"),
        ]),
        ("Serum Zinc Level", 5000, "Serum", "Measures zinc levels.", [
            ("Serum Zinc", "70-120 ug/dL", "ug/dL"),
        ]),
    ],
    "Maternal & Pediatric Focused Tests": [
        ("Beta-hCG (Pregnancy Test)", 2500, "Serum", "Quantitative pregnancy test.", [
            ("Beta-hCG", "Non-pregnant: <5 mIU/mL", "mIU/mL"),
        ]),
        ("TORCH Panel", 20000, "Serum", "Screens for Toxoplasma, Rubella, CMV, HSV.", [
            ("Toxoplasma IgM", "Negative", ""),
            ("Rubella IgM", "Negative", ""),
            ("CMV IgM", "Negative", ""),
            ("HSV IgM", "Negative", ""),
        ]),
        ("Neonatal TSH", 5000, "Blood Spot/Serum", "Screens newborns for congenital hypothyroidism.", [
            ("TSH Level", "1-39 uIU/mL", "uIU/mL"),
        ]),
    ],
    "Microbiology & Culture": [
        ("Urine Microscopy, Culture & Sensitivity (MC&S)", 4000, "Urine", "Microscopy and culture of urine with antibiotic sensitivity.", [
            ("Microscopy (Pus Cells)", "<5 /hpf", "/hpf"),
            ("Red Blood Cells", "<3 /hpf", "/hpf"),
            ("Epithelial Cells", "Few", "/hpf"),
            ("Culture Result", "No growth / <10^5 CFU/mL", "CFU/mL"),
            ("Organism Isolated", "None", ""),
            ("Antibiotic Sensitivity", "Not applicable (no growth)", ""),
        ]),
        ("Blood Culture & Sensitivity", 6000, "Whole Blood", "Detects bacteraemia and antibiotic sensitivity.", [
            ("Culture Result", "No growth after 5 days", ""),
            ("Organism Isolated", "None", ""),
            ("Antibiotic Sensitivity", "Not applicable (no growth)", ""),
        ]),
        ("Sputum Culture & Sensitivity", 5000, "Sputum", "Culture of sputum with antibiotic sensitivity.", [
            ("Gram Stain", "No organisms seen", ""),
            ("Culture Result", "No pathogenic growth", ""),
            ("Organism Isolated", "None", ""),
            ("Antibiotic Sensitivity", "Not applicable (no growth)", ""),
        ]),
        ("Wound Swab Culture & Sensitivity", 4500, "Swab", "Culture of wound swab with antibiotic sensitivity.", [
            ("Gram Stain", "No organisms seen", ""),
            ("Culture Result", "No pathogenic growth", ""),
            ("Organism Isolated", "None", ""),
            ("Antibiotic Sensitivity", "Not applicable (no growth)", ""),
        ]),
        ("High Vaginal Swab (HVS) MC&S", 4500, "Swab", "Microscopy and culture of high vaginal swab.", [
            ("Microscopy", "No abnormal cells / organisms", ""),
            ("Culture Result", "Normal vaginal flora", ""),
            ("Organism Isolated", "None", ""),
            ("Antibiotic Sensitivity", "Not applicable (no growth)", ""),
        ]),
        ("Stool Culture & Sensitivity", 4500, "Stool", "Culture of stool for enteric pathogens.", [
            ("Culture Result", "No enteric pathogens isolated", ""),
            ("Organism Isolated", "None", ""),
            ("Antibiotic Sensitivity", "Not applicable (no growth)", ""),
        ]),
    ],
    "Tumor Markers": [
        ("Prostate Specific Antigen (PSA), Total", 8000, "Serum", "Screening/monitoring marker for prostate disease.", [
            ("Total PSA", "<4.0 ng/mL", "ng/mL"),
        ]),
        ("CA-125", 12000, "Serum", "Marker associated with ovarian cancer.", [
            ("CA-125", "<35 U/mL", "U/mL"),
        ]),
        ("Carcinoembryonic Antigen (CEA)", 10000, "Serum", "Marker used mainly in colorectal cancer monitoring.", [
            ("CEA", "Non-smoker: <3 ng/mL Smoker: <5 ng/mL", "ng/mL"),
        ]),
        ("Alpha-Fetoprotein (AFP)", 10000, "Serum", "Marker for liver cancer and germ cell tumors.", [
            ("AFP", "<10 ng/mL", "ng/mL"),
        ]),
    ],
    "Andrology & Fertility": [
        ("Seminal Fluid Analysis (Semen Analysis)", 6000, "Semen", "Assesses semen volume, count, motility and morphology.", [
            ("Volume", "1.5-6.0 mL", "mL"),
            ("Sperm Concentration", ">=15 million/mL", "million/mL"),
            ("Total Sperm Count", ">=39 million/ejaculate", "million"),
            ("Total Motility", ">=40%", "%"),
            ("Progressive Motility", ">=32%", "%"),
            ("Normal Morphology", ">=4%", "%"),
            ("pH", "7.2-8.0", ""),
            ("Liquefaction Time", "<60 minutes", "minutes"),
        ]),
    ],
    "Body Fluid Analysis": [
        ("Cerebrospinal Fluid (CSF) Analysis", 6000, "CSF", "Analysis of cerebrospinal fluid.", [
            ("Appearance", "Clear, colorless", ""),
            ("White Cell Count", "0-5 /uL", "/uL"),
            ("Protein", "15-45 mg/dL", "mg/dL"),
            ("Glucose", "50-80 mg/dL (2/3 of serum)", "mg/dL"),
            ("Gram Stain", "No organisms seen", ""),
        ]),
        ("Ascitic Fluid Analysis", 5000, "Ascitic Fluid", "Analysis of peritoneal (ascitic) fluid.", [
            ("Appearance", "Clear, straw-colored", ""),
            ("White Cell Count", "<250 /uL", "/uL"),
            ("Protein", "<2.5 g/dL (transudate)", "g/dL"),
            ("Serum-Ascites Albumin Gradient (SAAG)", ">=1.1 g/dL suggests portal hypertension", "g/dL"),
        ]),
        ("Pleural Fluid Analysis", 5000, "Pleural Fluid", "Analysis of pleural fluid.", [
            ("Appearance", "Clear, straw-colored", ""),
            ("White Cell Count", "<1000 /uL", "/uL"),
            ("Protein", "Transudate <3 g/dL", "g/dL"),
            ("LDH", "Transudate <2/3 upper serum limit", "U/L"),
        ]),
    ],
}

# Extra standard hematology tests appended to the existing Hematology category.
CATALOG["Hematology"].extend([
    ("Reticulocyte Count", 2500, "Whole Blood", "Measures immature red blood cell production.", [
        ("Reticulocyte %", "0.5-2.5%", "%"),
        ("Absolute Reticulocyte Count", "25,000-75,000 /uL", "/uL"),
    ]),
    ("Peripheral Blood Film", 2500, "Whole Blood", "Microscopic examination of blood cells.", [
        ("RBC Morphology", "Normocytic, normochromic", ""),
        ("WBC Morphology", "Normal, no immature forms", ""),
        ("Platelet Estimate", "Adequate", ""),
    ]),
    ("Sickling Test", 1500, "Whole Blood", "Screens for sickle haemoglobin.", [
        ("Sickling Result", "Negative", ""),
    ]),
    ("Bleeding Time & Clotting Time", 2000, "Whole Blood", "Bedside assessment of primary haemostasis.", [
        ("Bleeding Time", "2-7 minutes (Ivy)", "minutes"),
        ("Clotting Time", "5-10 minutes", "minutes"),
    ]),
])


def seed_lab_catalog_for(hospital):
    """Create the canonical lab catalog for `hospital` (idempotent).

    Uses all_objects so it works outside a tenant request context (signup,
    shell, management commands).
    """
    for category_name, tests in CATALOG.items():
        category, _ = TestCategory.all_objects.get_or_create(
            hospital=hospital, name=category_name
        )
        for name, price, sample_type, description, params in tests:
            test, _ = Test.all_objects.get_or_create(
                hospital=hospital,
                name=name,
                defaults={
                    "category": category,
                    "description": description,
                    "price": Decimal(str(price)),
                    "sample_type": sample_type,
                    "is_active": True,
                },
            )
            for order, (pname, normal_range, unit) in enumerate(params, start=1):
                TestParameter.all_objects.get_or_create(
                    hospital=hospital,
                    test=test,
                    name=pname,
                    defaults={"normal_range": normal_range, "unit": unit, "order": order},
                )
