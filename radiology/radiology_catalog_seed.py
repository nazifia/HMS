"""Per-hospital radiology catalog seeding.

Canonical list of radiology procedures grouped by modality (category), each with
its billing/scheduling parameters and patient preparation instructions. Scoped to
a hospital so every tenant gets its own copy (mirrors laboratory/lab_catalog_seed.py).

Consumed by:
  - migration 0008_seed_radiology_catalog (existing tenants in prod),
  - the populate_radiology_tests management command (manual / ad-hoc re-seed).

Add/edit procedures here; re-running any consumer is idempotent (get_or_create).
Prices are placeholders in the app's base currency; adjust per tariff.
"""

from decimal import Decimal

# category (modality) -> list of procedures.
# Each procedure: (name, price, duration_minutes, description, preparation_instructions)
CATALOG = {
    "Plain Radiography (X-Ray)": [
        ("Chest X-Ray (PA View)", 6000, 15, "Single frontal projection of the chest for lungs, heart size and mediastinum.", "Remove jewellery and metal objects from the chest. No fasting required."),
        ("Chest X-Ray (PA & Lateral)", 9000, 20, "Frontal and lateral chest projections for better localisation of lesions.", "Remove jewellery and metal objects from the chest. No fasting required."),
        ("Abdominal X-Ray (Plain / KUB)", 7000, 15, "Supine/erect abdominal film for bowel gas pattern, calcification and free air.", "No fasting required unless requested. Empty bladder before erect films."),
        ("Skull X-Ray", 7000, 20, "Frontal and lateral skull projections for trauma or bony lesions.", "Remove hairpins, earrings, dentures and hearing aids."),
        ("Cervical Spine X-Ray", 7000, 20, "AP, lateral and open-mouth views of the cervical spine.", "Remove necklaces and remove clothing with metal from the neck."),
        ("Thoracic Spine X-Ray", 7000, 20, "AP and lateral projections of the thoracic spine.", "Remove metal objects from the back and chest."),
        ("Lumbosacral Spine X-Ray", 8000, 20, "AP and lateral projections of the lumbar spine and sacrum.", "Bowel prep may be requested for clearer views. Remove metal objects."),
        ("Pelvis X-Ray", 7000, 20, "AP projection of the pelvis and hip joints.", "Remove metal objects from the waist and hips."),
        ("Upper Limb X-Ray", 6000, 15, "Projections of shoulder, arm, forearm, wrist or hand as requested.", "Remove watches, rings and bandages from the affected limb."),
        ("Lower Limb X-Ray", 6000, 15, "Projections of hip, femur, knee, leg, ankle or foot as requested.", "Remove anklets and metal objects from the affected limb."),
        ("Paranasal Sinuses X-Ray", 7000, 15, "Occipitomental (Water's) view for the paranasal sinuses.", "Remove dentures, earrings and hairpins."),
        ("Dental X-Ray (Bitewing)", 4000, 10, "Intra-oral view showing crowns of upper and lower teeth.", "Remove dentures, retainers and facial jewellery."),
        ("Dental X-Ray (Panoramic / OPG)", 8000, 15, "Single panoramic image of both jaws, teeth and TMJ.", "Remove earrings, necklaces, dentures and hairpins."),
    ],
    "Ultrasonography (USS)": [
        ("Abdominal Ultrasound", 8000, 30, "Grey-scale imaging of liver, gallbladder, pancreas, spleen and kidneys.", "Fast for 6-8 hours before the scan. Water may be allowed."),
        ("Pelvic Ultrasound (Transabdominal)", 8000, 30, "Suprapubic imaging of the bladder, uterus and adnexa or prostate.", "Drink 4-6 glasses of water 1 hour before and keep a full bladder."),
        ("Obstetric Ultrasound", 8000, 30, "Assessment of fetal viability, growth, position and liquor volume.", "Full bladder required in early pregnancy; no fasting."),
        ("Transvaginal Ultrasound", 10000, 30, "High-resolution endovaginal imaging of the uterus, endometrium and ovaries.", "Empty the bladder immediately before the scan."),
        ("Breast Ultrasound", 9000, 30, "Targeted imaging of breast lumps and axillary regions.", "Avoid talcum powder, lotion or deodorant on the chest."),
        ("Thyroid Ultrasound", 9000, 30, "Imaging of thyroid lobes, isthmus and cervical lymph nodes.", "No preparation required. Remove neck jewellery."),
        ("Scrotal Ultrasound", 9000, 30, "Imaging of testes, epididymis and scrotal contents with Doppler.", "No preparation required."),
        ("Doppler Ultrasound (Lower Limb Venous)", 15000, 45, "Colour Doppler for deep vein thrombosis and venous flow.", "No preparation required. Wear loose clothing."),
        ("Echocardiography", 20000, 45, "Ultrasound assessment of cardiac chambers, valves and function.", "No preparation required. Loose upper clothing preferred."),
    ],
    "Computed Tomography (CT)": [
        ("CT Brain (Plain)", 35000, 30, "Non-contrast axial CT for haemorrhage, infarct or trauma.", "Remove hairpins, earrings and dentures. No fasting for plain scan."),
        ("CT Brain (With Contrast)", 50000, 45, "Contrast-enhanced CT for tumours, abscess or vascular lesions.", "Fast 4 hours. Recent creatinine required. Report contrast allergy."),
        ("CT Chest", 45000, 30, "Axial CT of lungs, mediastinum and pleura, with or without contrast.", "Fast 4 hours if contrast planned. Remove metal from the chest."),
        ("CT Abdomen & Pelvis", 60000, 45, "Contrast CT of abdominal and pelvic organs.", "Fast 4-6 hours. Oral contrast may be given. Recent creatinine required."),
        ("CT Spine", 45000, 30, "Axial and reconstructed CT of a spinal segment for bony detail.", "Remove metal objects. Fast 4 hours if contrast planned."),
        ("CT Angiography (CTA)", 70000, 60, "Contrast-enhanced CT of arteries for stenosis or aneurysm.", "Fast 4 hours. Recent creatinine required. Report contrast allergy."),
    ],
    "Magnetic Resonance Imaging (MRI)": [
        ("MRI Brain", 80000, 45, "Multiplanar MRI of the brain for detailed soft-tissue assessment.", "Remove all metal. Declare pacemaker, implants or metal fragments."),
        ("MRI Spine (Cervical)", 80000, 45, "Sagittal and axial MRI of the cervical spinal cord and discs.", "Remove all metal. Screen for implants and claustrophobia."),
        ("MRI Spine (Lumbar)", 80000, 45, "Sagittal and axial MRI of the lumbar spine, discs and canal.", "Remove all metal. Screen for implants and claustrophobia."),
        ("MRI Abdomen", 90000, 60, "MRI of abdominal organs, with or without contrast.", "Fast 4-6 hours. Remove all metal. Declare implants."),
        ("MRI Knee Joint", 75000, 45, "MRI for menisci, ligaments and cartilage of the knee.", "Remove all metal from the affected limb. Declare implants."),
        ("MR Angiography (MRA)", 90000, 60, "MRI assessment of vascular anatomy and flow.", "Remove all metal. Declare implants and contrast allergy."),
    ],
    "Contrast & Fluoroscopy Studies": [
        ("Barium Swallow", 18000, 45, "Fluoroscopic study of the pharynx and oesophagus using barium.", "Fast 6 hours before the study."),
        ("Barium Meal", 18000, 45, "Fluoroscopic study of the stomach and duodenum using barium.", "Fast 6-8 hours. No smoking on the morning of the study."),
        ("Barium Enema", 20000, 60, "Fluoroscopic study of the colon using rectal barium contrast.", "Low-residue diet 2 days prior, bowel prep and clear fluids the night before."),
        ("Intravenous Urography (IVU)", 25000, 60, "Contrast study of the kidneys, ureters and bladder.", "Bowel prep the night before. Fast 4-6 hours. Recent creatinine required."),
        ("Hysterosalpingography (HSG)", 22000, 45, "Contrast study of the uterine cavity and fallopian tube patency.", "Schedule days 6-12 of the cycle. Rule out pregnancy and active infection."),
        ("Voiding Cystourethrogram (VCUG)", 20000, 45, "Fluoroscopic study of the bladder and urethra during voiding.", "Rule out active urinary tract infection before the study."),
    ],
    "Specialised Imaging": [
        ("Mammography", 18000, 30, "Low-dose X-ray screening/diagnostic imaging of the breasts.", "Avoid deodorant, powder or lotion on the chest and underarms."),
        ("Bone Densitometry (DEXA)", 25000, 30, "Dual-energy scan measuring bone mineral density.", "No calcium supplements for 24 hours. Avoid recent contrast studies."),
        ("Fluoroscopy (General)", 20000, 30, "Real-time X-ray imaging for guided diagnostic assessment.", "Preparation depends on the specific study; follow radiologist instructions."),
    ],
}


def iter_procedures():
    """Yield (category, name, price, duration_minutes, description, prep) tuples."""
    for category, procedures in CATALOG.items():
        for name, price, minutes, description, prep in procedures:
            yield category, name, Decimal(str(price)), minutes, description, prep
