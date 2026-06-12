from django.db import migrations
from datetime import timedelta
from decimal import Decimal


# (name, avg_minutes, prep_minutes, recovery_minutes, risk_level, fee)
SURGERIES = [
    ("Appendectomy", 60, 30, 120, "medium", 150000),
    ("Cholecystectomy", 120, 45, 180, "medium", 350000),
    ("Inguinal Herniorrhaphy", 90, 30, 120, "low", 180000),
    ("Umbilical Herniorrhaphy", 75, 30, 120, "low", 160000),
    ("Exploratory Laparotomy", 150, 45, 240, "high", 300000),
    ("Hemorrhoidectomy", 60, 30, 90, "low", 120000),
    ("Thyroidectomy", 150, 45, 180, "high", 400000),
    ("Mastectomy", 150, 45, 180, "high", 350000),
    ("Lumpectomy (Breast Lump Excision)", 60, 30, 90, "medium", 150000),
    ("Caesarean Section", 60, 30, 180, "high", 250000),
    ("Myomectomy", 150, 45, 240, "high", 350000),
    ("Total Abdominal Hysterectomy", 150, 45, 240, "high", 400000),
    ("Vaginal Hysterectomy", 120, 45, 180, "high", 380000),
    ("Ovarian Cystectomy", 120, 45, 180, "medium", 300000),
    ("Salpingectomy (Ectopic Pregnancy)", 90, 30, 180, "high", 250000),
    ("Dilatation & Curettage (D&C)", 30, 20, 60, "low", 80000),
    ("Transurethral Resection of Prostate (TURP)", 90, 45, 180, "high", 450000),
    ("Circumcision", 30, 15, 30, "low", 50000),
    ("Orchidopexy", 90, 30, 120, "medium", 200000),
    ("Hydrocelectomy", 60, 30, 90, "low", 150000),
    ("Vasectomy", 30, 15, 30, "low", 80000),
    ("Nephrectomy", 180, 60, 300, "critical", 600000),
    ("Open Reduction & Internal Fixation (ORIF)", 180, 60, 240, "high", 500000),
    ("Lower Limb Amputation", 120, 45, 240, "critical", 350000),
    ("Skin Grafting", 120, 45, 180, "medium", 250000),
    ("Wound Debridement", 45, 20, 60, "low", 80000),
    ("Incision & Drainage of Abscess", 30, 15, 30, "low", 50000),
    ("Tonsillectomy", 60, 30, 120, "medium", 180000),
    ("Adenoidectomy", 45, 30, 90, "medium", 160000),
    ("Tracheostomy", 60, 30, 120, "high", 250000),
    ("Septoplasty", 90, 30, 120, "medium", 250000),
    ("Cataract Extraction (with IOL)", 45, 30, 60, "medium", 200000),
    ("Craniotomy", 240, 90, 360, "critical", 1200000),
    ("Laminectomy", 180, 60, 300, "high", 700000),
    ("Splenectomy", 150, 45, 240, "high", 400000),
    ("Gastrectomy", 240, 60, 360, "critical", 700000),
    ("Colostomy", 120, 45, 240, "high", 350000),
    ("Bowel Resection & Anastomosis", 180, 60, 300, "high", 500000),
    ("Fistulectomy", 75, 30, 120, "medium", 180000),
    ("Lymph Node Biopsy", 45, 20, 60, "low", 100000),
]


def seed(apps, schema_editor):
    SurgeryType = apps.get_model("theatre", "SurgeryType")
    for name, avg, prep, recov, risk, fee in SURGERIES:
        SurgeryType.objects.get_or_create(
            name=name,
            defaults={
                "average_duration": timedelta(minutes=avg),
                "preparation_time": timedelta(minutes=prep),
                "recovery_time": timedelta(minutes=recov),
                "risk_level": risk,
                "fee": Decimal(str(fee)),
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("theatre", "0014_surgery_source_referral"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
