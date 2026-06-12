from django.db import migrations
from decimal import Decimal


# (category, name, generic_name, dosage_form, strength, price)
MEDICATIONS = [
    # Analgesics & Antipyretics
    ("Analgesics & Antipyretics", "Paracetamol", "Paracetamol", "Tablet", "500mg", 20),
    ("Analgesics & Antipyretics", "Paracetamol Syrup", "Paracetamol", "Syrup", "120mg/5ml", 600),
    ("Analgesics & Antipyretics", "Ibuprofen", "Ibuprofen", "Tablet", "400mg", 30),
    ("Analgesics & Antipyretics", "Diclofenac", "Diclofenac Sodium", "Tablet", "50mg", 30),
    ("Analgesics & Antipyretics", "Diclofenac Injection", "Diclofenac Sodium", "Injection", "75mg/3ml", 250),
    ("Analgesics & Antipyretics", "Aspirin", "Acetylsalicylic Acid", "Tablet", "75mg", 20),
    ("Analgesics & Antipyretics", "Tramadol", "Tramadol HCl", "Capsule", "50mg", 60),
    ("Analgesics & Antipyretics", "Tramadol Injection", "Tramadol HCl", "Injection", "100mg/2ml", 300),
    ("Analgesics & Antipyretics", "Pentazocine Injection", "Pentazocine", "Injection", "30mg/ml", 350),
    ("Analgesics & Antipyretics", "Morphine Injection", "Morphine Sulphate", "Injection", "10mg/ml", 800),
    ("Analgesics & Antipyretics", "Celecoxib", "Celecoxib", "Capsule", "200mg", 120),
    ("Analgesics & Antipyretics", "Naproxen", "Naproxen", "Tablet", "500mg", 50),
    # Antibiotics
    ("Antibiotics", "Amoxicillin", "Amoxicillin", "Capsule", "500mg", 40),
    ("Antibiotics", "Amoxicillin-Clavulanate", "Co-amoxiclav", "Tablet", "625mg", 250),
    ("Antibiotics", "Ampicillin-Cloxacillin", "Ampiclox", "Capsule", "500mg", 60),
    ("Antibiotics", "Ciprofloxacin", "Ciprofloxacin", "Tablet", "500mg", 60),
    ("Antibiotics", "Levofloxacin", "Levofloxacin", "Tablet", "500mg", 150),
    ("Antibiotics", "Azithromycin", "Azithromycin", "Tablet", "500mg", 200),
    ("Antibiotics", "Erythromycin", "Erythromycin", "Tablet", "250mg", 50),
    ("Antibiotics", "Ceftriaxone Injection", "Ceftriaxone", "Injection", "1g", 600),
    ("Antibiotics", "Cefuroxime", "Cefuroxime", "Tablet", "500mg", 200),
    ("Antibiotics", "Cefixime", "Cefixime", "Tablet", "200mg", 150),
    ("Antibiotics", "Metronidazole", "Metronidazole", "Tablet", "400mg", 20),
    ("Antibiotics", "Metronidazole Infusion", "Metronidazole", "Infusion", "500mg/100ml", 500),
    ("Antibiotics", "Gentamicin Injection", "Gentamicin", "Injection", "80mg/2ml", 150),
    ("Antibiotics", "Doxycycline", "Doxycycline", "Capsule", "100mg", 40),
    ("Antibiotics", "Cotrimoxazole", "Sulfamethoxazole-Trimethoprim", "Tablet", "960mg", 30),
    ("Antibiotics", "Clindamycin", "Clindamycin", "Capsule", "300mg", 200),
    ("Antibiotics", "Cloxacillin", "Cloxacillin", "Capsule", "500mg", 50),
    # Antimalarials
    ("Antimalarials", "Artemether-Lumefantrine", "Artemether-Lumefantrine", "Tablet", "80/480mg", 1200),
    ("Antimalarials", "Artesunate Injection", "Artesunate", "Injection", "60mg", 1500),
    ("Antimalarials", "Dihydroartemisinin-Piperaquine", "DHA-Piperaquine", "Tablet", "40/320mg", 1500),
    ("Antimalarials", "Quinine", "Quinine Sulphate", "Tablet", "300mg", 50),
    ("Antimalarials", "Sulfadoxine-Pyrimethamine", "SP", "Tablet", "500/25mg", 150),
    # Antifungals
    ("Antifungals", "Fluconazole", "Fluconazole", "Capsule", "150mg", 100),
    ("Antifungals", "Ketoconazole", "Ketoconazole", "Tablet", "200mg", 80),
    ("Antifungals", "Nystatin Suspension", "Nystatin", "Suspension", "100,000IU/ml", 800),
    ("Antifungals", "Griseofulvin", "Griseofulvin", "Tablet", "500mg", 100),
    ("Antifungals", "Clotrimazole Cream", "Clotrimazole", "Cream", "1%", 500),
    # Antivirals
    ("Antivirals", "Acyclovir", "Aciclovir", "Tablet", "400mg", 80),
    ("Antivirals", "Tenofovir-Lamivudine-Dolutegravir", "TLD", "Tablet", "300/300/50mg", 0),
    # Antihypertensives & Cardiac
    ("Cardiovascular", "Amlodipine", "Amlodipine", "Tablet", "5mg", 30),
    ("Cardiovascular", "Lisinopril", "Lisinopril", "Tablet", "10mg", 50),
    ("Cardiovascular", "Nifedipine Retard", "Nifedipine", "Tablet", "20mg", 30),
    ("Cardiovascular", "Losartan", "Losartan Potassium", "Tablet", "50mg", 60),
    ("Cardiovascular", "Hydrochlorothiazide", "Hydrochlorothiazide", "Tablet", "25mg", 20),
    ("Cardiovascular", "Furosemide", "Furosemide", "Tablet", "40mg", 20),
    ("Cardiovascular", "Furosemide Injection", "Furosemide", "Injection", "20mg/2ml", 100),
    ("Cardiovascular", "Atenolol", "Atenolol", "Tablet", "50mg", 30),
    ("Cardiovascular", "Methyldopa", "Methyldopa", "Tablet", "250mg", 50),
    ("Cardiovascular", "Spironolactone", "Spironolactone", "Tablet", "25mg", 40),
    ("Cardiovascular", "Digoxin", "Digoxin", "Tablet", "0.25mg", 30),
    ("Cardiovascular", "Atorvastatin", "Atorvastatin", "Tablet", "20mg", 80),
    ("Cardiovascular", "Clopidogrel", "Clopidogrel", "Tablet", "75mg", 100),
    ("Cardiovascular", "Glyceryl Trinitrate", "GTN", "Tablet", "0.5mg", 60),
    # Antidiabetics
    ("Antidiabetics", "Metformin", "Metformin", "Tablet", "500mg", 30),
    ("Antidiabetics", "Glibenclamide", "Glibenclamide", "Tablet", "5mg", 20),
    ("Antidiabetics", "Glimepiride", "Glimepiride", "Tablet", "2mg", 60),
    ("Antidiabetics", "Soluble Insulin", "Insulin (Regular)", "Injection", "100IU/ml", 3500),
    ("Antidiabetics", "Premixed Insulin", "Insulin (70/30)", "Injection", "100IU/ml", 3800),
    # Gastrointestinal
    ("Gastrointestinal", "Omeprazole", "Omeprazole", "Capsule", "20mg", 40),
    ("Gastrointestinal", "Esomeprazole", "Esomeprazole", "Tablet", "40mg", 120),
    ("Gastrointestinal", "Magnesium Trisilicate", "Antacid", "Tablet", "Compound", 20),
    ("Gastrointestinal", "Hyoscine Butylbromide", "Hyoscine", "Tablet", "10mg", 40),
    ("Gastrointestinal", "Metoclopramide", "Metoclopramide", "Tablet", "10mg", 30),
    ("Gastrointestinal", "Metoclopramide Injection", "Metoclopramide", "Injection", "10mg/2ml", 100),
    ("Gastrointestinal", "Ondansetron", "Ondansetron", "Tablet", "4mg", 80),
    ("Gastrointestinal", "Oral Rehydration Salts", "ORS", "Sachet", "20.5g", 150),
    ("Gastrointestinal", "Loperamide", "Loperamide", "Capsule", "2mg", 40),
    ("Gastrointestinal", "Bisacodyl", "Bisacodyl", "Tablet", "5mg", 30),
    ("Gastrointestinal", "Lactulose", "Lactulose", "Syrup", "3.35g/5ml", 1500),
    # Respiratory & Antihistamines
    ("Respiratory & Antihistamines", "Salbutamol", "Salbutamol", "Tablet", "4mg", 20),
    ("Respiratory & Antihistamines", "Salbutamol Inhaler", "Salbutamol", "Inhaler", "100mcg/dose", 2500),
    ("Respiratory & Antihistamines", "Aminophylline Injection", "Aminophylline", "Injection", "250mg/10ml", 150),
    ("Respiratory & Antihistamines", "Prednisolone", "Prednisolone", "Tablet", "5mg", 20),
    ("Respiratory & Antihistamines", "Cetirizine", "Cetirizine", "Tablet", "10mg", 30),
    ("Respiratory & Antihistamines", "Chlorpheniramine", "Chlorpheniramine", "Tablet", "4mg", 15),
    ("Respiratory & Antihistamines", "Loratadine", "Loratadine", "Tablet", "10mg", 40),
    ("Respiratory & Antihistamines", "Promethazine", "Promethazine", "Tablet", "25mg", 30),
    # Vitamins & Supplements
    ("Vitamins & Supplements", "Folic Acid", "Folic Acid", "Tablet", "5mg", 15),
    ("Vitamins & Supplements", "Ferrous Sulphate", "Ferrous Sulphate", "Tablet", "200mg", 15),
    ("Vitamins & Supplements", "Vitamin C", "Ascorbic Acid", "Tablet", "100mg", 15),
    ("Vitamins & Supplements", "Vitamin B Complex", "B-Complex", "Tablet", "Compound", 15),
    ("Vitamins & Supplements", "Multivitamin", "Multivitamin", "Tablet", "Compound", 20),
    ("Vitamins & Supplements", "Calcium + Vitamin D", "Calcium/Vit D", "Tablet", "Compound", 50),
    ("Vitamins & Supplements", "Zinc Sulphate", "Zinc", "Tablet", "20mg", 30),
    # CNS / Psychiatry
    ("Central Nervous System", "Diazepam", "Diazepam", "Tablet", "5mg", 30),
    ("Central Nervous System", "Diazepam Injection", "Diazepam", "Injection", "10mg/2ml", 150),
    ("Central Nervous System", "Phenobarbital", "Phenobarbital", "Tablet", "30mg", 30),
    ("Central Nervous System", "Carbamazepine", "Carbamazepine", "Tablet", "200mg", 50),
    ("Central Nervous System", "Phenytoin", "Phenytoin", "Tablet", "100mg", 40),
    ("Central Nervous System", "Amitriptyline", "Amitriptyline", "Tablet", "25mg", 40),
    ("Central Nervous System", "Haloperidol", "Haloperidol", "Tablet", "5mg", 50),
    ("Central Nervous System", "Chlorpromazine", "Chlorpromazine", "Tablet", "100mg", 40),
    ("Central Nervous System", "Fluoxetine", "Fluoxetine", "Capsule", "20mg", 80),
    # IV Fluids
    ("Intravenous Fluids", "Normal Saline 0.9%", "Sodium Chloride", "Infusion", "500ml", 600),
    ("Intravenous Fluids", "Dextrose 5%", "Dextrose", "Infusion", "500ml", 600),
    ("Intravenous Fluids", "Dextrose Saline", "Dextrose-Saline", "Infusion", "500ml", 600),
    ("Intravenous Fluids", "Ringer's Lactate", "Ringer's Lactate", "Infusion", "500ml", 700),
    ("Intravenous Fluids", "Dextrose 10%", "Dextrose", "Infusion", "500ml", 700),
    ("Intravenous Fluids", "Dextrose 50%", "Dextrose", "Injection", "50ml", 400),
    # Anaesthetics
    ("Anaesthetics", "Lidocaine Injection", "Lignocaine", "Injection", "2%", 200),
    ("Anaesthetics", "Bupivacaine Injection", "Bupivacaine", "Injection", "0.5%", 800),
    ("Anaesthetics", "Ketamine Injection", "Ketamine", "Injection", "50mg/ml", 1500),
    ("Anaesthetics", "Propofol Injection", "Propofol", "Injection", "10mg/ml", 2500),
    # Hormones & Emergency
    ("Hormones & Emergency", "Oxytocin Injection", "Oxytocin", "Injection", "10IU/ml", 150),
    ("Hormones & Emergency", "Hydrocortisone Injection", "Hydrocortisone", "Injection", "100mg", 300),
    ("Hormones & Emergency", "Dexamethasone Injection", "Dexamethasone", "Injection", "4mg/ml", 150),
    ("Hormones & Emergency", "Adrenaline Injection", "Epinephrine", "Injection", "1mg/ml", 200),
    ("Hormones & Emergency", "Atropine Injection", "Atropine", "Injection", "0.6mg/ml", 150),
    ("Hormones & Emergency", "Misoprostol", "Misoprostol", "Tablet", "200mcg", 200),
    ("Hormones & Emergency", "Magnesium Sulphate Injection", "Magnesium Sulphate", "Injection", "50%", 250),
    ("Hormones & Emergency", "Tranexamic Acid Injection", "Tranexamic Acid", "Injection", "500mg/5ml", 400),
    ("Hormones & Emergency", "Vitamin K Injection", "Phytomenadione", "Injection", "10mg/ml", 150),
]

# Consumables stored as Medication rows under the Consumables category.
# (name, dosage_form, strength/size, price)
CONSUMABLES = [
    ("Surgical Gloves (Sterile)", "Pair", "Size 7.5", 200),
    ("Examination Gloves", "Piece", "Medium", 50),
    ("Syringe 2ml", "Piece", "2ml", 30),
    ("Syringe 5ml", "Piece", "5ml", 40),
    ("Syringe 10ml", "Piece", "10ml", 60),
    ("Hypodermic Needle", "Piece", "21G", 20),
    ("IV Cannula", "Piece", "18G", 150),
    ("IV Giving Set (Infusion Set)", "Piece", "Standard", 200),
    ("Scalp Vein Set", "Piece", "23G", 80),
    ("Cotton Wool", "Roll", "100g", 500),
    ("Gauze Swab", "Pack", "Sterile", 300),
    ("Roller Bandage", "Piece", "10cm", 200),
    ("Crepe Bandage", "Piece", "10cm", 400),
    ("Adhesive Plaster (Tape)", "Roll", "Standard", 300),
    ("Surgical Blade", "Piece", "No. 22", 80),
    ("Silk Suture", "Piece", "2/0", 600),
    ("Vicryl Suture", "Piece", "2/0", 1200),
    ("Nylon Suture", "Piece", "3/0", 700),
    ("Foley Urinary Catheter", "Piece", "16Fr", 500),
    ("Urine Drainage Bag", "Piece", "2000ml", 300),
    ("Nasogastric Tube", "Piece", "16Fr", 400),
    ("Face Mask (Surgical)", "Piece", "3-ply", 30),
    ("Surgical Gown (Disposable)", "Piece", "Standard", 800),
    ("Disposable Theatre Cap", "Piece", "Standard", 30),
    ("Spinal Needle", "Piece", "25G", 800),
    ("Blood Transfusion Set", "Piece", "Standard", 300),
    ("Methylated Spirit", "Bottle", "100ml", 400),
    ("Povidone Iodine", "Bottle", "100ml", 600),
    ("Hydrogen Peroxide", "Bottle", "100ml", 400),
    ("Glucometer Test Strips", "Pack", "50 strips", 5000),
    ("Disposable Apron", "Piece", "Standard", 60),
    ("Specimen Bottle", "Piece", "Universal", 50),
    ("Disposable Underpad", "Piece", "60x90cm", 150),
    ("Examination Tongue Depressor", "Piece", "Wooden", 20),
]


def seed(apps, schema_editor):
    MedicationCategory = apps.get_model("pharmacy", "MedicationCategory")
    Medication = apps.get_model("pharmacy", "Medication")
    cat_cache = {}

    def get_cat(name):
        if name not in cat_cache:
            cat_cache[name], _ = MedicationCategory.objects.get_or_create(name=name)
        return cat_cache[name]

    for cat, name, generic, form, strength, price in MEDICATIONS:
        Medication.objects.get_or_create(
            name=name,
            strength=strength,
            defaults={
                "generic_name": generic,
                "category": get_cat(cat),
                "dosage_form": form,
                "price": Decimal(str(price)),
                "is_active": True,
            },
        )

    consumable_cat = get_cat("Medical Consumables")
    for name, form, strength, price in CONSUMABLES:
        Medication.objects.get_or_create(
            name=name,
            strength=strength,
            defaults={
                "category": consumable_cat,
                "dosage_form": form,
                "price": Decimal(str(price)),
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0025_purchase_delivery_status_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
