from django.core.management.base import BaseCommand
from radiology.models import RadiologyCategory, RadiologyTest

# Enhanced radiology tests with realistic pricing and detailed procedures
ENHANCED_CATEGORIES = [
    {
        "name": "X-ray (Radiography)",
        "description": "Quick imaging of bones and some soft tissues using ionizing radiation.",
        "tests": [
            {"name": "Chest X-ray (PA & Lateral)", "price": 45.00, "duration": 15, "description": "Standard chest imaging for lung and heart evaluation"},
            {"name": "Chest X-ray (Single View)", "price": 35.00, "duration": 10, "description": "Single view chest X-ray"},
            {"name": "Abdominal X-ray (KUB)", "price": 50.00, "duration": 15, "description": "Kidneys, ureters, and bladder imaging"},
            {"name": "Spine X-ray (Cervical)", "price": 65.00, "duration": 20, "description": "Cervical spine imaging"},
            {"name": "Spine X-ray (Lumbar)", "price": 70.00, "duration": 20, "description": "Lumbar spine imaging"},
            {"name": "Extremity X-ray (Single)", "price": 55.00, "duration": 15, "description": "Single extremity imaging"},
            {"name": "Extremity X-ray (Multiple Views)", "price": 75.00, "duration": 25, "description": "Multiple view extremity imaging"},
            {"name": "Skull X-ray", "price": 60.00, "duration": 20, "description": "Skull and facial bone imaging"},
            {"name": "Dental X-rays (Bitewing)", "price": 25.00, "duration": 10, "description": "Dental bitewing radiographs"},
            {"name": "Dental X-rays (Panoramic)", "price": 85.00, "duration": 15, "description": "Full mouth panoramic radiograph"},
            {"name": "Pelvis X-ray", "price": 65.00, "duration": 15, "description": "Pelvic bone imaging"},
        ],
    },
    {
        "name": "Computed Tomography (CT)",
        "description": "Cross-sectional imaging using X-rays and computer processing.",
        "tests": [
            {"name": "CT Head/Brain (Non-contrast)", "price": 350.00, "duration": 30, "description": "Brain imaging without contrast"},
            {"name": "CT Head/Brain (With Contrast)", "price": 450.00, "duration": 45, "description": "Brain imaging with IV contrast"},
            {"name": "CT Chest (Non-contrast)", "price": 400.00, "duration": 30, "description": "Chest imaging without contrast"},
            {"name": "CT Chest (With Contrast)", "price": 500.00, "duration": 45, "description": "Chest imaging with IV contrast"},
            {"name": "CT Abdomen & Pelvis", "price": 550.00, "duration": 45, "description": "Abdominal and pelvic imaging"},
            {"name": "CT Spine (Cervical)", "price": 450.00, "duration": 30, "description": "Cervical spine CT"},
            {"name": "CT Spine (Lumbar)", "price": 450.00, "duration": 30, "description": "Lumbar spine CT"},
            {"name": "CT Angiography (CTA) Head", "price": 650.00, "duration": 60, "description": "CT angiography of head vessels"},
            {"name": "CT Angiography (CTA) Chest", "price": 700.00, "duration": 60, "description": "CT angiography of chest vessels"},
            {"name": "CT Colonography", "price": 600.00, "duration": 45, "description": "Virtual colonoscopy"},
        ],
    },
    {
        "name": "Magnetic Resonance Imaging (MRI)",
        "description": "Detailed soft tissue imaging using magnetic fields and radio waves.",
        "tests": [
            {"name": "MRI Brain (Non-contrast)", "price": 800.00, "duration": 45, "description": "Brain MRI without contrast"},
            {"name": "MRI Brain (With Contrast)", "price": 950.00, "duration": 60, "description": "Brain MRI with gadolinium contrast"},
            {"name": "MRI Spine (Cervical)", "price": 850.00, "duration": 45, "description": "Cervical spine MRI"},
            {"name": "MRI Spine (Lumbar)", "price": 850.00, "duration": 45, "description": "Lumbar spine MRI"},
            {"name": "MRI Knee", "price": 750.00, "duration": 40, "description": "Knee joint MRI"},
            {"name": "MRI Shoulder", "price": 750.00, "duration": 40, "description": "Shoulder joint MRI"},
            {"name": "MRI Abdomen", "price": 900.00, "duration": 60, "description": "Abdominal MRI"},
            {"name": "MRI Pelvis", "price": 900.00, "duration": 60, "description": "Pelvic MRI"},
            {"name": "Cardiac MRI", "price": 1200.00, "duration": 90, "description": "Comprehensive cardiac MRI"},
            {"name": "MR Angiography (MRA)", "price": 1000.00, "duration": 60, "description": "MR angiography"},
            {"name": "Functional MRI (fMRI)", "price": 1500.00, "duration": 120, "description": "Functional brain MRI"},
        ],
    },
    {
        "name": "Ultrasound (Sonography)",
        "description": "Real-time imaging using high-frequency sound waves.",
        "tests": [
            {"name": "Abdominal Ultrasound", "price": 150.00, "duration": 30, "description": "Complete abdominal ultrasound"},
            {"name": "Pelvic Ultrasound", "price": 140.00, "duration": 30, "description": "Pelvic ultrasound examination"},
            {"name": "Obstetric Ultrasound (1st Trimester)", "price": 120.00, "duration": 20, "description": "Early pregnancy ultrasound"},
            {"name": "Obstetric Ultrasound (2nd/3rd Trimester)", "price": 180.00, "duration": 45, "description": "Detailed fetal ultrasound"},
            {"name": "Thyroid Ultrasound", "price": 130.00, "duration": 25, "description": "Thyroid gland ultrasound"},
            {"name": "Breast Ultrasound", "price": 160.00, "duration": 30, "description": "Breast tissue ultrasound"},
            {"name": "Carotid Doppler Ultrasound", "price": 200.00, "duration": 45, "description": "Carotid artery blood flow study"},
            {"name": "Lower Extremity Doppler", "price": 220.00, "duration": 45, "description": "Leg vessel blood flow study"},
            {"name": "Transvaginal Ultrasound", "price": 160.00, "duration": 30, "description": "Internal pelvic ultrasound"},
            {"name": "Renal Ultrasound", "price": 140.00, "duration": 30, "description": "Kidney ultrasound"},
            {"name": "Echocardiogram", "price": 250.00, "duration": 60, "description": "Heart ultrasound"},
        ],
    },
    {
        "name": "Nuclear Medicine",
        "description": "Functional imaging using small amounts of radioactive tracers.",
        "tests": [
            {"name": "Bone Scan (Whole Body)", "price": 400.00, "duration": 180, "description": "Full body bone scan"},
            {"name": "Thyroid Scan", "price": 300.00, "duration": 120, "description": "Thyroid function imaging"},
            {"name": "Renal Scan", "price": 350.00, "duration": 150, "description": "Kidney function study"},
            {"name": "Lung V/Q Scan", "price": 450.00, "duration": 120, "description": "Lung ventilation/perfusion scan"},
            {"name": "PET Scan (Whole Body)", "price": 2500.00, "duration": 180, "description": "Positron emission tomography"},
            {"name": "PET-CT Scan", "price": 3000.00, "duration": 120, "description": "Combined PET and CT imaging"},
            {"name": "SPECT Scan", "price": 800.00, "duration": 90, "description": "Single photon emission CT"},
            {"name": "Cardiac Stress Test (Nuclear)", "price": 600.00, "duration": 240, "description": "Nuclear cardiac stress test"},
            {"name": "Gallium Scan", "price": 500.00, "duration": 180, "description": "Infection/inflammation imaging"},
        ],
    },
    {
        "name": "Fluoroscopy & Contrast Studies",
        "description": "Real-time X-ray imaging with contrast agents.",
        "tests": [
            {"name": "Barium Swallow", "price": 200.00, "duration": 45, "description": "Esophageal contrast study"},
            {"name": "Upper GI Series", "price": 250.00, "duration": 60, "description": "Upper gastrointestinal study"},
            {"name": "Barium Enema", "price": 300.00, "duration": 90, "description": "Lower gastrointestinal study"},
            {"name": "Hysterosalpingography (HSG)", "price": 350.00, "duration": 30, "description": "Fallopian tube imaging"},
            {"name": "Voiding Cystourethrogram (VCUG)", "price": 280.00, "duration": 45, "description": "Bladder function study"},
            {"name": "Myelogram", "price": 600.00, "duration": 90, "description": "Spinal cord imaging"},
            {"name": "Arthrogram", "price": 400.00, "duration": 60, "description": "Joint imaging with contrast"},
            {"name": "IVP (Intravenous Pyelogram)", "price": 320.00, "duration": 120, "description": "Kidney and ureter imaging"},
        ],
    },
    {
        "name": "Interventional Radiology",
        "description": "Minimally invasive image-guided therapeutic procedures.",
        "tests": [
            {"name": "CT-Guided Biopsy", "price": 800.00, "duration": 90, "description": "CT-guided tissue biopsy"},
            {"name": "Ultrasound-Guided Biopsy", "price": 600.00, "duration": 60, "description": "Ultrasound-guided biopsy"},
            {"name": "Angioplasty", "price": 2500.00, "duration": 180, "description": "Vessel dilation procedure"},
            {"name": "Stent Placement", "price": 3000.00, "duration": 120, "description": "Vascular stent insertion"},
            {"name": "Drainage Procedure", "price": 700.00, "duration": 90, "description": "Image-guided drainage"},
            {"name": "Embolization", "price": 1500.00, "duration": 150, "description": "Vessel blocking procedure"},
            {"name": "Central Line Placement", "price": 500.00, "duration": 60, "description": "Central venous catheter insertion"},
            {"name": "Tumor Ablation", "price": 2000.00, "duration": 180, "description": "Tumor destruction procedure"},
        ],
    },
    {
        "name": "Mammography & Women's Imaging",
        "description": "Specialized imaging for women's health.",
        "tests": [
            {"name": "Screening Mammography", "price": 180.00, "duration": 20, "description": "Routine breast cancer screening"},
            {"name": "Diagnostic Mammography", "price": 220.00, "duration": 30, "description": "Problem-focused breast imaging"},
            {"name": "Breast MRI", "price": 1200.00, "duration": 60, "description": "Detailed breast MRI"},
            {"name": "Breast Biopsy (Stereotactic)", "price": 800.00, "duration": 90, "description": "Image-guided breast biopsy"},
            {"name": "Bone Density (DEXA)", "price": 150.00, "duration": 30, "description": "Osteoporosis screening"},
        ],
    }
]

class Command(BaseCommand):
    help = "Populate enhanced radiology categories and tests with realistic pricing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting enhanced radiology test population...'))
        
        for cat_data in ENHANCED_CATEGORIES:
            # Get or create category
            category, cat_created = RadiologyCategory.objects.get_or_create(
                name=cat_data["name"], 
                defaults={"description": cat_data["description"]}
            )
            
            if cat_created:
                self.stdout.write(f"Created new category: {category.name}")
            else:
                # Update description if category exists
                category.description = cat_data["description"]
                category.save()
                self.stdout.write(f"Updated category: {category.name}")
            
            # Create or update tests
            for test_data in cat_data["tests"]:
                test, test_created = RadiologyTest.objects.get_or_create(
                    name=test_data["name"],
                    category=category,
                    defaults={
                        "description": test_data["description"],
                        "price": test_data["price"],
                        "duration_minutes": test_data["duration"],
                        "is_active": True,
                    },
                )
                
                if test_created:
                    self.stdout.write(f"  Created test: {test.name} - ${test.price}")
                else:
                    # Update existing test with new pricing and details
                    test.price = test_data["price"]
                    test.duration_minutes = test_data["duration"]
                    test.description = test_data["description"]
                    test.save()
                    self.stdout.write(f"  Updated test: {test.name} - ${test.price}")
        
        # Summary statistics
        total_categories = RadiologyCategory.objects.count()
        total_tests = RadiologyTest.objects.count()
        active_tests = RadiologyTest.objects.filter(is_active=True).count()
        
        self.stdout.write(self.style.SUCCESS(f'Enhanced radiology tests populated successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Total Categories: {total_categories}'))
        self.stdout.write(self.style.SUCCESS(f'Total Tests: {total_tests}'))
        self.stdout.write(self.style.SUCCESS(f'Active Tests: {active_tests}'))
