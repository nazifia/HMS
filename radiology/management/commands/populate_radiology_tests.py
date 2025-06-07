from django.core.management.base import BaseCommand
from radiology.models import RadiologyCategory, RadiologyTest

CATEGORIES = [
    {
        "name": "X-ray (Radiography)",
        "description": "Quick imaging of bones and some soft tissues.",
        "tests": [
            "Chest X-ray",
            "Abdominal X-ray",
            "Limb X-ray",
            "Spine X-ray",
            "Skull X-ray",
            "Dental X-rays (bitewing)",
            "Dental X-rays (panoramic)",
        ],
    },
    {
        "name": "Computed Tomography (CT or CAT Scan)",
        "description": "Cross-sectional images of body structures.",
        "tests": [
            "CT Head/Brain",
            "CT Chest",
            "CT Abdomen and Pelvis",
            "CT Spine",
            "CT Angiography (CTA)",
            "CT Colonography (virtual colonoscopy)",
        ],
    },
    {
        "name": "Magnetic Resonance Imaging (MRI)",
        "description": "Detailed images of soft tissues, joints, brain, spinal cord.",
        "tests": [
            "MRI Brain",
            "MRI Spine",
            "MRI Knee/Shoulder",
            "MRI Abdomen/Pelvis",
            "Cardiac MRI",
            "Functional MRI (fMRI)",
            "MR Angiography (MRA)",
        ],
    },
    {
        "name": "Ultrasound (Sonography)",
        "description": "Real-time imaging using sound waves; no radiation.",
        "tests": [
            "Abdominal Ultrasound",
            "Pelvic Ultrasound",
            "Obstetric Ultrasound (fetal scan)",
            "Thyroid Ultrasound",
            "Breast Ultrasound",
            "Doppler Ultrasound (for blood flow)",
            "Transvaginal Ultrasound",
            "Transrectal Ultrasound",
        ],
    },
    {
        "name": "Nuclear Medicine",
        "description": "Uses small amounts of radioactive material to examine organ function.",
        "tests": [
            "Bone Scan",
            "Thyroid Scan",
            "Renal Scan",
            "Lung Perfusion and Ventilation (V/Q) Scan",
            "PET Scan (Positron Emission Tomography)",
            "SPECT Scan (Single-Photon Emission Computed Tomography)",
            "Cardiac Stress Test (Nuclear)",
        ],
    },
    {
        "name": "Fluoroscopy",
        "description": "Real-time X-ray imaging, often for guided procedures.",
        "tests": [
            "Barium Swallow",
            "Barium Meal",
            "Barium Enema",
            "Hysterosalpingography (HSG)",
            "Voiding Cystourethrogram (VCUG)",
            "Myelogram",
            "Arthrogram",
        ],
    },
    {
        "name": "Interventional Radiology (IR)",
        "description": "Minimally invasive, image-guided procedures.",
        "tests": [
            "Angioplasty and Stenting",
            "Image-guided Biopsies",
            "Drainage Procedures",
            "Uterine Fibroid Embolization",
            "Tumor Ablation (radiofrequency)",
            "Central line or catheter placements",
        ],
    },
]

class Command(BaseCommand):
    help = "Populate the database with radiology categories and tests."

    def handle(self, *args, **options):
        for cat in CATEGORIES:
            category, created = RadiologyCategory.objects.get_or_create(
                name=cat["name"], defaults={"description": cat["description"]}
            )
            if not created:
                category.description = cat["description"]
                category.save()
            for test_name in cat["tests"]:
                RadiologyTest.objects.get_or_create(
                    name=test_name,
                    category=category,
                    defaults={
                        "description": f"{test_name} under {cat['name']}",
                        "price": 1000.00,
                        "duration_minutes": 30,
                        "is_active": True,
                    },
                )
        self.stdout.write(self.style.SUCCESS("Radiology categories and tests populated successfully."))
