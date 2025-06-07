import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from laboratory.models import TestCategory, Test, TestParameter

# =============================================================================
#  START: PASTE YOUR LAB TEST DATA HERE
# =============================================================================
#
# Instructions:
# 1. Replace the example `lab_tests_data` list below with your actual data.
# ... (rest of the instructional comments) ...

lab_tests_data = [
    {
        "category_name": "Hematology",
        "test_name": "Complete Blood Count (CBC)",
        "description": "Measures various components of blood.",
        "price": 15.00,
        "sample_type": "Whole Blood",
        "is_active": True,
        "parameters": [
            {"name": "Hemoglobin (Hb)", "normal_range": "Male: 13.5–17.5 g/dL Female: 12.0–15.5 g/dL", "unit": "g/dL", "order": 1},
            {"name": "Hematocrit (Hct)", "normal_range": "Male: 41–53% Female: 36–46%", "unit": "%", "order": 2},
            {"name": "White Blood Cells (WBC)", "normal_range": "4,000–11,000 /µL", "unit": "/µL", "order": 3},
            {"name": "Neutrophils", "normal_range": "40–75% of WBCs", "unit": "%", "order": 4},
            {"name": "Lymphocytes", "normal_range": "20–45% of WBCs", "unit": "%", "order": 5},
            {"name": "Monocytes", "normal_range": "2–8% of WBCs", "unit": "%", "order": 6},
            {"name": "Eosinophils", "normal_range": "1–6% of WBCs", "unit": "%", "order": 7},
            {"name": "Basophils", "normal_range": "0–1% of WBCs", "unit": "%", "order": 8},
            {"name": "Platelets", "normal_range": "150,000–400,000 /µL", "unit": "/µL", "order": 9},
            {"name": "Mean Corpuscular Volume (MCV)", "normal_range": "80–100 fL", "unit": "fL", "order": 10}
        ]
    },
    {
        "category_name": "Liver Function Tests",
        "test_name": "Liver Function Tests (LFTs)",
        "description": "Assesses liver function and health.",
        "price": 20.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Alanine Aminotransferase (ALT)", "normal_range": "7–56 U/L", "unit": "U/L", "order": 1},
            {"name": "Aspartate Aminotransferase (AST)", "normal_range": "10–40 U/L", "unit": "U/L", "order": 2},
            {"name": "Alkaline Phosphatase (ALP)", "normal_range": "40–129 U/L", "unit": "U/L", "order": 3},
            {"name": "Gamma-glutamyl Transferase (GGT)", "normal_range": "9–48 U/L", "unit": "U/L", "order": 4},
            {"name": "Total Bilirubin", "normal_range": "0.1–1.2 mg/dL", "unit": "mg/dL", "order": 5},
            {"name": "Direct Bilirubin", "normal_range": "0.0–0.3 mg/dL", "unit": "mg/dL", "order": 6},
            {"name": "Albumin", "normal_range": "3.5–5.5 g/dL", "unit": "g/dL", "order": 7},
            {"name": "Total Protein", "normal_range": "6.0–8.3 g/dL", "unit": "g/dL", "order": 8}
        ]
    },
    {
        "category_name": "Renal Function Tests",
        "test_name": "Renal Function Tests (RFTs)",
        "description": "Assesses kidney function.",
        "price": 18.00,
        "sample_type": "Serum/Urine",
        "is_active": True,
        "parameters": [
            {"name": "Blood Urea Nitrogen (BUN)", "normal_range": "7–20 mg/dL", "unit": "mg/dL", "order": 1},
            {"name": "Serum Creatinine", "normal_range": "Male: 0.7–1.3 mg/dL Female: 0.6–1.1 mg/dL", "unit": "mg/dL", "order": 2},
            {"name": "BUN:Creatinine Ratio", "normal_range": "10:1 to 20:1", "unit": "ratio", "order": 3},
            {"name": "Estimated GFR (eGFR)", "normal_range": ">90 mL/min/1.73 m²", "unit": "mL/min/1.73 m²", "order": 4}
        ]
    },
    {
        "category_name": "Electrolytes",
        "test_name": "Electrolyte Panel",
        "description": "Measures levels of electrolytes.",
        "price": 12.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Sodium (Na⁺)", "normal_range": "135–145 mmol/L", "unit": "mmol/L", "order": 1},
            {"name": "Potassium (K⁺)", "normal_range": "3.5–5.0 mmol/L", "unit": "mmol/L", "order": 2},
            {"name": "Chloride (Cl⁻)", "normal_range": "98–106 mmol/L", "unit": "mmol/L", "order": 3},
            {"name": "Bicarbonate (HCO₃⁻)", "normal_range": "22–29 mmol/L", "unit": "mmol/L", "order": 4},
            {"name": "Calcium (Total)", "normal_range": "8.5–10.5 mg/dL", "unit": "mg/dL", "order": 5},
            {"name": "Ionized Calcium", "normal_range": "4.4–5.4 mg/dL", "unit": "mg/dL", "order": 6},
            {"name": "Magnesium", "normal_range": "1.5–2.5 mg/dL", "unit": "mg/dL", "order": 7},
            {"name": "Phosphate (PO₄³⁻)", "normal_range": "2.5–4.5 mg/dL", "unit": "mg/dL", "order": 8}
        ]
    },
    {
        "category_name": "Glucose and Diabetes-Related",
        "test_name": "Diabetes Panel",
        "description": "Tests related to glucose metabolism and diabetes.",
        "price": 22.00,
        "sample_type": "Blood/Serum",
        "is_active": True,
        "parameters": [
            {"name": "Fasting Blood Glucose", "normal_range": "70–99 mg/dL", "unit": "mg/dL", "order": 1},
            {"name": "2-Hour Postprandial Glucose", "normal_range": "<140 mg/dL", "unit": "mg/dL", "order": 2},
            {"name": "Random Blood Glucose", "normal_range": "<200 mg/dL", "unit": "mg/dL", "order": 3},
            {"name": "HbA1c (Glycated Hemoglobin)", "normal_range": "<5.7% (Normal) 5.7–6.4% (Prediabetes) ≥6.5% (Diabetes)", "unit": "%", "order": 4}
        ]
    },
    {
        "category_name": "Lipid Profile",
        "test_name": "Lipid Panel",
        "description": "Measures cholesterol and triglyceride levels.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Total Cholesterol", "normal_range": "<200 mg/dL", "unit": "mg/dL", "order": 1},
            {"name": "LDL Cholesterol", "normal_range": "<100 mg/dL", "unit": "mg/dL", "order": 2},
            {"name": "HDL Cholesterol", "normal_range": ">40 mg/dL (Male) >50 mg/dL (Female)", "unit": "mg/dL", "order": 3},
            {"name": "Triglycerides", "normal_range": "<150 mg/dL", "unit": "mg/dL", "order": 4}
        ]
    },
    {
        "category_name": "Thyroid Function Tests",
        "test_name": "Thyroid Panel",
        "description": "Assesses thyroid gland function.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "TSH (Thyroid Stimulating Hormone)", "normal_range": "0.4–4.0 mIU/L", "unit": "mIU/L", "order": 1},
            {"name": "Free T4 (Thyroxine)", "normal_range": "0.8–1.8 ng/dL", "unit": "ng/dL", "order": 2},
            {"name": "Free T3 (Triiodothyronine)", "normal_range": "2.3–4.2 pg/mL", "unit": "pg/mL", "order": 3}
        ]
    },
    {
        "category_name": "Coagulation Profile",
        "test_name": "Coagulation Panel",
        "description": "Assesses blood clotting ability.",
        "price": 30.00,
        "sample_type": "Plasma",
        "is_active": True,
        "parameters": [
            {"name": "Prothrombin Time (PT)", "normal_range": "11–13.5 seconds", "unit": "seconds", "order": 1},
            {"name": "INR", "normal_range": "0.8–1.1", "unit": "", "order": 2},
            {"name": "Activated Partial Thromboplastin Time (aPTT)", "normal_range": "25–35 seconds", "unit": "seconds", "order": 3},
            {"name": "D-dimer", "normal_range": "<0.5 µg/mL FEU", "unit": "µg/mL FEU", "order": 4}
        ]
    },
    {
        "category_name": "Urinalysis",
        "test_name": "Urinalysis (Random)",
        "description": "Analyzes various components of urine.",
        "price": 10.00,
        "sample_type": "Urine",
        "is_active": True,
        "parameters": [
            {"name": "Color", "normal_range": "Yellow to amber", "unit": "", "order": 1},
            {"name": "Appearance", "normal_range": "Clear", "unit": "", "order": 2},
            {"name": "pH", "normal_range": "4.5–8.0", "unit": "", "order": 3},
            {"name": "Specific Gravity", "normal_range": "1.005–1.030", "unit": "", "order": 4},
            {"name": "Protein", "normal_range": "Negative", "unit": "", "order": 5},
            {"name": "Glucose", "normal_range": "Negative", "unit": "", "order": 6},
            {"name": "Ketones", "normal_range": "Negative", "unit": "", "order": 7},
            {"name": "Blood", "normal_range": "Negative", "unit": "", "order": 8},
            {"name": "Leukocyte Esterase", "normal_range": "Negative", "unit": "", "order": 9},
            {"name": "Nitrites", "normal_range": "Negative", "unit": "", "order": 10}
        ]
    },
    {
        "category_name": "Urinalysis",
        "test_name": "Urinalysis (24-Hour Collection)",
        "description": "Analyzes urine collected over 24 hours.",
        "price": 15.00,
        "sample_type": "Urine (24-hour)",
        "is_active": True,
        "parameters": [
            {"name": "Color (24h)", "normal_range": "Yellow to amber", "unit": "", "order": 1},
            {"name": "Appearance (24h)", "normal_range": "Clear", "unit": "", "order": 2},
            {"name": "pH (24h)", "normal_range": "4.5–8.0", "unit": "", "order": 3},
            {"name": "Specific Gravity (24h)", "normal_range": "1.005–1.030", "unit": "", "order": 4},
            {"name": "Protein (24h)", "normal_range": "<150 mg/24h", "unit": "mg/24h", "order": 5} 
        ]
    },
    {
        "category_name": "Cardiac Markers",
        "test_name": "Cardiac Enzyme Panel",
        "description": "Measures markers of heart damage.",
        "price": 40.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Troponin I", "normal_range": "<0.04 ng/mL", "unit": "ng/mL", "order": 1},
            {"name": "Troponin T", "normal_range": "<0.01 ng/mL", "unit": "ng/mL", "order": 2},
            {"name": "CK-MB (Creatine Kinase–MB)", "normal_range": "<5 ng/mL or <5% of total CK", "unit": "ng/mL or %", "order": 3},
            {"name": "BNP (B-type Natriuretic Peptide)", "normal_range": "<100 pg/mL", "unit": "pg/mL", "order": 4},
            {"name": "NT-proBNP", "normal_range": "<300 pg/mL (varies with age and gender)", "unit": "pg/mL", "order": 5}
        ]
    },
    {
        "category_name": "Inflammatory Markers",
        "test_name": "Inflammation Panel",
        "description": "Measures markers of inflammation.",
        "price": 20.00,
        "sample_type": "Serum/Plasma",
        "is_active": True,
        "parameters": [
            {"name": "C-Reactive Protein (CRP)", "normal_range": "<5 mg/L", "unit": "mg/L", "order": 1},
            {"name": "High-sensitivity CRP (hs-CRP)", "normal_range": "<1 mg/L (low risk)", "unit": "mg/L", "order": 2},
            {"name": "Erythrocyte Sedimentation Rate (ESR)", "normal_range": "Male: <15 mm/hr Female: <20 mm/hr", "unit": "mm/hr", "order": 3},
            {"name": "Ferritin (Inflammation)", "normal_range": "Male: 24–336 ng/mL Female: 11–307 ng/mL", "unit": "ng/mL", "order": 4}
        ]
    },
    {
        "category_name": "Iron Studies",
        "test_name": "Iron Panel",
        "description": "Assesses iron levels and metabolism.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Serum Iron", "normal_range": "60–170 mcg/dL", "unit": "mcg/dL", "order": 1},
            {"name": "Total Iron Binding Capacity (TIBC)", "normal_range": "240–450 mcg/dL", "unit": "mcg/dL", "order": 2},
            {"name": "Transferrin Saturation", "normal_range": "20–50%", "unit": "%", "order": 3},
            {"name": "Serum Ferritin", "normal_range": "Male: 24–336 ng/mL Female: 11–307 ng/mL", "unit": "ng/mL", "order": 4}
        ]
    },
    {
        "category_name": "Pancreatic Function",
        "test_name": "Pancreatic Enzyme Tests",
        "description": "Assesses pancreatic function.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Amylase", "normal_range": "30–110 U/L", "unit": "U/L", "order": 1},
            {"name": "Lipase", "normal_range": "0–160 U/L", "unit": "U/L", "order": 2}
        ]
    },
    {
        "category_name": "Hormones & Endocrinology",
        "test_name": "Hormone Panel",
        "description": "Measures various hormone levels.",
        "price": 50.00,
        "sample_type": "Serum/Plasma",
        "is_active": True,
        "parameters": [
            {"name": "Cortisol (Morning)", "normal_range": "6–23 mcg/dL", "unit": "mcg/dL", "order": 1},
            {"name": "Parathyroid Hormone (PTH)", "normal_range": "10–65 pg/mL", "unit": "pg/mL", "order": 2},
            {"name": "Vitamin D (25-Hydroxy)", "normal_range": "30–100 ng/mL", "unit": "ng/mL", "order": 3},
            {"name": "Insulin (Fasting)", "normal_range": "2–25 µIU/mL", "unit": "µIU/mL", "order": 4},
            {"name": "Prolactin", "normal_range": "Male: 2–18 ng/mL Female: 2–29 ng/mL", "unit": "ng/mL", "order": 5},
            {"name": "FSH (Follicle Stimulating Hormone)", "normal_range": "Male: 1.5–12.4 mIU/mL Female: Varies with cycle", "unit": "mIU/mL", "order": 6},
            {"name": "LH (Luteinizing Hormone)", "normal_range": "Male: 1.7–8.6 mIU/mL Female: Varies with cycle", "unit": "mIU/mL", "order": 7},
            {"name": "Estradiol (E2)", "normal_range": "Male: 10–40 pg/mL Female: Varies with phase", "unit": "pg/mL", "order": 8},
            {"name": "Testosterone", "normal_range": "Male: 300–1000 ng/dL Female: 15–70 ng/dL", "unit": "ng/dL", "order": 9}
        ]
    }
]

# --- NEW DATA TO BE APPENDED ---
new_lab_tests_data = [
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "Malaria Rapid Diagnostic Test (RDT)",
        "description": "Rapid test for malaria.",
        "price": 10.00,
        "sample_type": "Blood",
        "is_active": True,
        "parameters": [
            {"name": "RDT Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "Malaria Blood Smear",
        "description": "Microscopic examination for malaria parasites.",
        "price": 12.00,
        "sample_type": "Blood Smear",
        "is_active": True,
        "parameters": [
            {"name": "Parasite Finding", "normal_range": "No parasites seen", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "HIV 1 & 2 Antibody Test",
        "description": "Screens for HIV antibodies.",
        "price": 15.00,
        "sample_type": "Serum/Plasma",
        "is_active": True,
        "parameters": [
            {"name": "Antibody Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "HIV Viral Load",
        "description": "Measures the amount of HIV virus in the blood.",
        "price": 50.00,
        "sample_type": "Plasma",
        "is_active": True,
        "parameters": [
            {"name": "Viral Load", "normal_range": "<20–50 copies/mL (undetectable)", "unit": "copies/mL", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "Hepatitis B Surface Antigen (HBsAg)",
        "description": "Screens for Hepatitis B infection.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "HBsAg Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "Hepatitis C Antibody",
        "description": "Screens for Hepatitis C antibodies.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "HCV Antibody Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "Tuberculosis (GeneXpert Sputum AFB)",
        "description": "Detects Mycobacterium tuberculosis in sputum.",
        "price": 30.00,
        "sample_type": "Sputum",
        "is_active": True,
        "parameters": [
            {"name": "GeneXpert Result", "normal_range": "Negative for MTB", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "Typhoid (Widal Test / Blood Culture)",
        "description": "Tests for typhoid fever.",
        "price": 15.00,
        "sample_type": "Serum/Blood",
        "is_active": True,
        "parameters": [
            {"name": "Widal Test Result", "normal_range": "Negative or <1:80 for O and H agglutinins", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Infectious Disease Screening (Common in Africa)",
        "test_name": "H. pylori Antigen/Antibody",
        "description": "Tests for Helicobacter pylori infection.",
        "price": 20.00,
        "sample_type": "Stool/Serum",
        "is_active": True,
        "parameters": [
            {"name": "H. pylori Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Parasitology & Stool Analysis",
        "test_name": "Stool Microscopy",
        "description": "Microscopic examination of stool for parasites.",
        "price": 10.00,
        "sample_type": "Stool",
        "is_active": True,
        "parameters": [
            {"name": "Microscopic Finding", "normal_range": "No ova, cysts, or parasites", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Parasitology & Stool Analysis",
        "test_name": "Stool Occult Blood",
        "description": "Checks for hidden blood in stool.",
        "price": 8.00,
        "sample_type": "Stool",
        "is_active": True,
        "parameters": [
            {"name": "Occult Blood Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Parasitology & Stool Analysis",
        "test_name": "Stool Reducing Substances",
        "description": "Checks for reducing substances in stool.",
        "price": 8.00,
        "sample_type": "Stool",
        "is_active": True,
        "parameters": [
            {"name": "Reducing Substances Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Parasitology & Stool Analysis",
        "test_name": "Stool pH",
        "description": "Measures the pH of stool.",
        "price": 5.00,
        "sample_type": "Stool",
        "is_active": True,
        "parameters": [
            {"name": "pH Value", "normal_range": "6.5–7.5", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Parasitology & Stool Analysis",
        "test_name": "Giardia Lamblia Antigen",
        "description": "Detects Giardia Lamblia antigen in stool.",
        "price": 15.00,
        "sample_type": "Stool",
        "is_active": True,
        "parameters": [
            {"name": "Giardia Antigen Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Parasitology & Stool Analysis",
        "test_name": "Entamoeba Histolytica Antigen",
        "description": "Detects Entamoeba Histolytica antigen in stool.",
        "price": 15.00,
        "sample_type": "Stool",
        "is_active": True,
        "parameters": [
            {"name": "Entamoeba Antigen Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Serology Rapid Tests",
        "test_name": "Syphilis (VDRL/RPR/TPHA)",
        "description": "Serological tests for syphilis.",
        "price": 12.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Syphilis Serology Result", "normal_range": "Non-reactive", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Serology Rapid Tests",
        "test_name": "Hepatitis A IgM",
        "description": "Detects IgM antibodies to Hepatitis A virus.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Hepatitis A IgM Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Serology Rapid Tests",
        "test_name": "Brucella Agglutination Test",
        "description": "Tests for Brucellosis.",
        "price": 15.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Brucella Agglutination Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Serology Rapid Tests",
        "test_name": "Schistosoma Antibody/Ova",
        "description": "Tests for Schistosomiasis.",
        "price": 16.00,
        "sample_type": "Serum/Urine/Stool",
        "is_active": True,
        "parameters": [
            {"name": "Schistosoma Result", "normal_range": "Negative", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Nutritional & Micronutrient Tests",
        "test_name": "Vitamin B12 Level",
        "description": "Measures Vitamin B12 levels.",
        "price": 20.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Vitamin B12", "normal_range": "190–950 pg/mL", "unit": "pg/mL", "order": 1}
        ]
    },
    {
        "category_name": "Nutritional & Micronutrient Tests",
        "test_name": "Folate Level",
        "description": "Measures folate levels.",
        "price": 20.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Folate", "normal_range": "2.7–17.0 ng/mL", "unit": "ng/mL", "order": 1}
        ]
    },
    {
        "category_name": "Nutritional & Micronutrient Tests",
        "test_name": "Vitamin D (25-Hydroxy) Level", # Differentiated from the one in Hormones
        "description": "Measures Vitamin D levels.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Vitamin D (25-Hydroxy)", "normal_range": "30–100 ng/mL", "unit": "ng/mL", "order": 1}
        ]
    },
    {
        "category_name": "Nutritional & Micronutrient Tests",
        "test_name": "Serum Zinc Level",
        "description": "Measures zinc levels.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Serum Zinc", "normal_range": "70–120 µg/dL", "unit": "µg/dL", "order": 1}
        ]
    },
    {
        "category_name": "Nutritional & Micronutrient Tests",
        "test_name": "Serum Copper Level",
        "description": "Measures copper levels.",
        "price": 18.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Serum Copper", "normal_range": "70–140 µg/dL", "unit": "µg/dL", "order": 1}
        ]
    },
    {
        "category_name": "Maternal & Pediatric Focused Tests",
        "test_name": "Rapid Plasma Reagin (RPR) – Antenatal",
        "description": "Antenatal screening for syphilis.",
        "price": 10.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "RPR Result", "normal_range": "Non-reactive", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Maternal & Pediatric Focused Tests",
        "test_name": "Hemoglobin Electrophoresis (Sickle Cell Screen)",
        "description": "Screens for sickle cell disease and trait.",
        "price": 35.00,
        "sample_type": "Whole Blood",
        "is_active": True,
        "parameters": [
            {"name": "Hemoglobin Pattern", "normal_range": "HbAA (normal), HbAS (trait), HbSS (disease)", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Maternal & Pediatric Focused Tests",
        "test_name": "G6PD Screening",
        "description": "Screens for G6PD deficiency.",
        "price": 20.00,
        "sample_type": "Whole Blood",
        "is_active": True,
        "parameters": [
            {"name": "G6PD Activity", "normal_range": "Normal enzyme activity", "unit": "", "order": 1}
        ]
    },
    {
        "category_name": "Maternal & Pediatric Focused Tests",
        "test_name": "TORCH Panel",
        "description": "Screens for Toxoplasmosis, Rubella, CMV, HSV.",
        "price": 60.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Toxoplasma IgM", "normal_range": "Negative", "unit": "", "order": 1},
            {"name": "Rubella IgM", "normal_range": "Negative", "unit": "", "order": 2},
            {"name": "CMV IgM", "normal_range": "Negative", "unit": "", "order": 3},
            {"name": "HSV IgM", "normal_range": "Negative", "unit": "", "order": 4}
        ]
    },
    {
        "category_name": "Maternal & Pediatric Focused Tests",
        "test_name": "Neonatal TSH",
        "description": "Screens newborns for congenital hypothyroidism.",
        "price": 20.00,
        "sample_type": "Blood Spot/Serum",
        "is_active": True,
        "parameters": [
            {"name": "TSH Level", "normal_range": "1–39 µIU/mL", "unit": "µIU/mL", "order": 1}
        ]
    }
]

lab_tests_data.extend(new_lab_tests_data)
# =============================================================================
#  END: PASTE YOUR LAB TEST DATA HERE
# =============================================================================

class Command(BaseCommand):
    help = 'Populates the database with a predefined list of laboratory tests and their parameters.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not lab_tests_data:
            self.stdout.write(self.style.WARNING('No lab test data provided in the script. Exiting.'))
            return

        self.stdout.write(self.style.SUCCESS('Starting to populate lab tests...'))

        for test_data in lab_tests_data:
            category_name = test_data.get("category_name", "Uncategorized")
            test_name = test_data.get("test_name")
            
            if not test_name:
                self.stdout.write(self.style.WARNING(f'Skipping entry due to missing test_name: {test_data}'))
                continue

            category, created = TestCategory.objects.get_or_create(
                name=category_name,
                defaults={'description': test_data.get("category_description", "")}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: "{category.name}"'))

            test_instance, created = Test.objects.update_or_create(
                name=test_name,
                category=category,
                defaults={
                    'description': test_data.get("description", ""),
                    'price': test_data.get("price", 0.00),
                    'sample_type': test_data.get("sample_type", ""),
                    'preparation_instructions': test_data.get("preparation_instructions", ""),
                    'duration': test_data.get("duration", ""),
                    'is_active': test_data.get("is_active", True),
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created test: "{test_instance.name}" in category "{category.name}"'))
            else:
                self.stdout.write(self.style.NOTICE(f'  Updated test: "{test_instance.name}" in category "{category.name}"'))

            if "parameters" in test_data and isinstance(test_data["parameters"], list):
                for param_data in test_data["parameters"]:
                    param_name = param_data.get("name")
                    if not param_name:
                        self.stdout.write(self.style.WARNING(f'    Skipping parameter due to missing name for test "{test_name}": {param_data}'))
                        continue
                    
                    parameter_instance, param_created = TestParameter.objects.update_or_create(
                        test=test_instance,
                        name=param_name,
                        defaults={
                            'normal_range': param_data.get("normal_range", ""),
                            'unit': param_data.get("unit", ""),
                            'order': param_data.get("order", 0)
                        }
                    )
                    if param_created:
                        self.stdout.write(self.style.SUCCESS(f'    Added parameter: "{parameter_instance.name}" to test "{test_name}"'))
                    else:
                        self.stdout.write(self.style.NOTICE(f'    Updated parameter: "{parameter_instance.name}" for test "{test_name}"'))
            
            self.stdout.write("---")

        self.stdout.write(self.style.SUCCESS('Successfully populated lab tests and parameters.'))