from django.db import migrations
from decimal import Decimal


# (category, name, price, duration_minutes)
TESTS = [
    # Plain Radiography (X-ray)
    ("Plain Radiography (X-Ray)", "Chest X-Ray (PA View)", 6000, 15),
    ("Plain Radiography (X-Ray)", "Chest X-Ray (PA & Lateral)", 9000, 20),
    ("Plain Radiography (X-Ray)", "Abdominal X-Ray (Plain)", 7000, 15),
    ("Plain Radiography (X-Ray)", "Skull X-Ray", 7000, 20),
    ("Plain Radiography (X-Ray)", "Cervical Spine X-Ray", 7000, 20),
    ("Plain Radiography (X-Ray)", "Thoracic Spine X-Ray", 7000, 20),
    ("Plain Radiography (X-Ray)", "Lumbosacral Spine X-Ray", 8000, 20),
    ("Plain Radiography (X-Ray)", "Pelvis X-Ray", 7000, 20),
    ("Plain Radiography (X-Ray)", "Upper Limb X-Ray", 6000, 15),
    ("Plain Radiography (X-Ray)", "Lower Limb X-Ray", 6000, 15),
    ("Plain Radiography (X-Ray)", "Kidney-Ureter-Bladder (KUB) X-Ray", 7000, 15),
    ("Plain Radiography (X-Ray)", "Paranasal Sinuses X-Ray", 7000, 15),
    # Ultrasound
    ("Ultrasonography (USS)", "Abdominal Ultrasound", 8000, 30),
    ("Ultrasonography (USS)", "Pelvic Ultrasound", 8000, 30),
    ("Ultrasonography (USS)", "Obstetric Ultrasound", 8000, 30),
    ("Ultrasonography (USS)", "Transvaginal Ultrasound", 10000, 30),
    ("Ultrasonography (USS)", "Breast Ultrasound", 9000, 30),
    ("Ultrasonography (USS)", "Thyroid Ultrasound", 9000, 30),
    ("Ultrasonography (USS)", "Scrotal Ultrasound", 9000, 30),
    ("Ultrasonography (USS)", "Doppler Ultrasound (Lower Limb)", 15000, 45),
    ("Ultrasonography (USS)", "Echocardiography", 20000, 45),
    # CT
    ("Computed Tomography (CT)", "CT Brain (Plain)", 35000, 30),
    ("Computed Tomography (CT)", "CT Brain (With Contrast)", 50000, 45),
    ("Computed Tomography (CT)", "CT Chest", 45000, 30),
    ("Computed Tomography (CT)", "CT Abdomen & Pelvis", 60000, 45),
    ("Computed Tomography (CT)", "CT Spine", 45000, 30),
    ("Computed Tomography (CT)", "CT Angiography", 70000, 60),
    # MRI
    ("Magnetic Resonance Imaging (MRI)", "MRI Brain", 80000, 45),
    ("Magnetic Resonance Imaging (MRI)", "MRI Spine (Cervical)", 80000, 45),
    ("Magnetic Resonance Imaging (MRI)", "MRI Spine (Lumbar)", 80000, 45),
    ("Magnetic Resonance Imaging (MRI)", "MRI Abdomen", 90000, 60),
    ("Magnetic Resonance Imaging (MRI)", "MRI Knee Joint", 75000, 45),
    # Contrast / Special
    ("Contrast Studies", "Barium Swallow", 18000, 45),
    ("Contrast Studies", "Barium Meal", 18000, 45),
    ("Contrast Studies", "Barium Enema", 20000, 60),
    ("Contrast Studies", "Intravenous Urography (IVU)", 25000, 60),
    ("Contrast Studies", "Hysterosalpingography (HSG)", 22000, 45),
    # Other
    ("Other Imaging", "Mammography", 18000, 30),
    ("Other Imaging", "Fluoroscopy", 20000, 30),
    ("Other Imaging", "Bone Densitometry (DEXA)", 25000, 30),
]


def seed(apps, schema_editor):
    RadiologyCategory = apps.get_model("radiology", "RadiologyCategory")
    RadiologyTest = apps.get_model("radiology", "RadiologyTest")
    cat_cache = {}
    for cat, name, price, minutes in TESTS:
        if cat not in cat_cache:
            cat_cache[cat], _ = RadiologyCategory.objects.get_or_create(name=cat)
        RadiologyTest.objects.get_or_create(
            name=name,
            defaults={
                "category": cat_cache[cat],
                "price": Decimal(str(price)),
                "duration_minutes": minutes,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("radiology", "0005_alter_radiologyresult_study_date"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
