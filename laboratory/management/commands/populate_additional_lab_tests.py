from django.core.management.base import BaseCommand
from laboratory.models import TestCategory, Test, TestParameter

# Additional comprehensive lab tests based on web research
additional_lab_tests_data = [
    # EXPANDED CHEMISTRY PANEL
    {
        "category_name": "Clinical Chemistry - Extended",
        "test_name": "Electrolyte Panel",
        "description": "Comprehensive electrolyte analysis.",
        "price": 15.00,
        "sample_type": "Serum/Plasma",
        "is_active": True,
        "parameters": [
            {"name": "Sodium (Na+)", "normal_range": "136–145 mEq/L", "unit": "mEq/L", "order": 1},
            {"name": "Potassium (K+)", "normal_range": "3.5–5.0 mEq/L", "unit": "mEq/L", "order": 2},
            {"name": "Chloride (Cl-)", "normal_range": "98–107 mEq/L", "unit": "mEq/L", "order": 3},
            {"name": "Carbon Dioxide (CO2)", "normal_range": "22–28 mEq/L", "unit": "mEq/L", "order": 4}
        ]
    },
    {
        "category_name": "Clinical Chemistry - Extended",
        "test_name": "Cardiac Enzymes Panel",
        "description": "Markers for heart muscle damage.",
        "price": 35.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Troponin I", "normal_range": "<0.04 ng/mL", "unit": "ng/mL", "order": 1},
            {"name": "Troponin T", "normal_range": "<0.01 ng/mL", "unit": "ng/mL", "order": 2},
            {"name": "CK-MB", "normal_range": "0–6.3 ng/mL", "unit": "ng/mL", "order": 3},
            {"name": "Total CK", "normal_range": "Male: 38–174 U/L, Female: 26–140 U/L", "unit": "U/L", "order": 4}
        ]
    },
    {
        "category_name": "Clinical Chemistry - Extended",
        "test_name": "Pancreatic Function Tests",
        "description": "Assesses pancreatic function.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Amylase", "normal_range": "25–125 U/L", "unit": "U/L", "order": 1},
            {"name": "Lipase", "normal_range": "10–140 U/L", "unit": "U/L", "order": 2},
            {"name": "Trypsinogen", "normal_range": "10–57 ng/mL", "unit": "ng/mL", "order": 3}
        ]
    },
    
    # EXPANDED HEMATOLOGY
    {
        "category_name": "Hematology - Extended",
        "test_name": "Reticulocyte Count",
        "description": "Measures young red blood cells.",
        "price": 18.00,
        "sample_type": "Whole Blood",
        "is_active": True,
        "parameters": [
            {"name": "Reticulocyte %", "normal_range": "0.5–2.5%", "unit": "%", "order": 1},
            {"name": "Absolute Reticulocyte Count", "normal_range": "25,000–75,000 /µL", "unit": "/µL", "order": 2}
        ]
    },
    {
        "category_name": "Hematology - Extended",
        "test_name": "Peripheral Blood Smear",
        "description": "Microscopic examination of blood cells.",
        "price": 20.00,
        "sample_type": "Blood Smear",
        "is_active": True,
        "parameters": [
            {"name": "RBC Morphology", "normal_range": "Normal", "unit": "", "order": 1},
            {"name": "WBC Differential", "normal_range": "Normal distribution", "unit": "", "order": 2},
            {"name": "Platelet Morphology", "normal_range": "Normal", "unit": "", "order": 3}
        ]
    },
    
    # TUMOR MARKERS
    {
        "category_name": "Tumor Markers",
        "test_name": "Prostate Specific Antigen (PSA)",
        "description": "Screening for prostate cancer.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Total PSA", "normal_range": "<4.0 ng/mL", "unit": "ng/mL", "order": 1},
            {"name": "Free PSA", "normal_range": ">25% of total", "unit": "%", "order": 2}
        ]
    },
    {
        "category_name": "Tumor Markers",
        "test_name": "Alpha-Fetoprotein (AFP)",
        "description": "Liver cancer and pregnancy marker.",
        "price": 22.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "AFP Level", "normal_range": "<10 ng/mL (non-pregnant)", "unit": "ng/mL", "order": 1}
        ]
    },
    {
        "category_name": "Tumor Markers",
        "test_name": "CA 125",
        "description": "Ovarian cancer marker.",
        "price": 28.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "CA 125 Level", "normal_range": "<35 U/mL", "unit": "U/mL", "order": 1}
        ]
    },
    {
        "category_name": "Tumor Markers",
        "test_name": "CEA (Carcinoembryonic Antigen)",
        "description": "Colorectal cancer marker.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "CEA Level", "normal_range": "<3.0 ng/mL (non-smoker)", "unit": "ng/mL", "order": 1}
        ]
    },
    
    # AUTOIMMUNE TESTS
    {
        "category_name": "Autoimmune & Rheumatology",
        "test_name": "Antinuclear Antibody (ANA) Panel",
        "description": "Comprehensive autoimmune screening.",
        "price": 35.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "ANA Titer", "normal_range": "<1:80", "unit": "titer", "order": 1},
            {"name": "ANA Pattern", "normal_range": "Negative", "unit": "", "order": 2},
            {"name": "Anti-dsDNA", "normal_range": "<30 IU/mL", "unit": "IU/mL", "order": 3}
        ]
    },
    {
        "category_name": "Autoimmune & Rheumatology",
        "test_name": "Rheumatoid Arthritis Panel",
        "description": "Comprehensive RA testing.",
        "price": 30.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Rheumatoid Factor (RF)", "normal_range": "<15 IU/mL", "unit": "IU/mL", "order": 1},
            {"name": "Anti-CCP Antibodies", "normal_range": "<20 U/mL", "unit": "U/mL", "order": 2},
            {"name": "CRP", "normal_range": "<3.0 mg/L", "unit": "mg/L", "order": 3}
        ]
    },
    
    # ALLERGY TESTING
    {
        "category_name": "Allergy Testing",
        "test_name": "Total IgE",
        "description": "Overall allergic response marker.",
        "price": 20.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Total IgE", "normal_range": "<100 IU/mL", "unit": "IU/mL", "order": 1}
        ]
    },
    {
        "category_name": "Allergy Testing",
        "test_name": "Food Allergy Panel",
        "description": "Common food allergen testing.",
        "price": 45.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Milk IgE", "normal_range": "<0.35 kU/L", "unit": "kU/L", "order": 1},
            {"name": "Egg IgE", "normal_range": "<0.35 kU/L", "unit": "kU/L", "order": 2},
            {"name": "Peanut IgE", "normal_range": "<0.35 kU/L", "unit": "kU/L", "order": 3},
            {"name": "Wheat IgE", "normal_range": "<0.35 kU/L", "unit": "kU/L", "order": 4}
        ]
    },
    
    # DRUG TESTING
    {
        "category_name": "Toxicology & Drug Testing",
        "test_name": "Urine Drug Screen",
        "description": "Multi-drug screening panel.",
        "price": 30.00,
        "sample_type": "Urine",
        "is_active": True,
        "parameters": [
            {"name": "Amphetamines", "normal_range": "Negative", "unit": "", "order": 1},
            {"name": "Cocaine", "normal_range": "Negative", "unit": "", "order": 2},
            {"name": "Marijuana (THC)", "normal_range": "Negative", "unit": "", "order": 3},
            {"name": "Opiates", "normal_range": "Negative", "unit": "", "order": 4}
        ]
    },
    {
        "category_name": "Toxicology & Drug Testing",
        "test_name": "Therapeutic Drug Monitoring",
        "description": "Monitors medication levels.",
        "price": 25.00,
        "sample_type": "Serum",
        "is_active": True,
        "parameters": [
            {"name": "Digoxin", "normal_range": "0.8–2.0 ng/mL", "unit": "ng/mL", "order": 1},
            {"name": "Phenytoin", "normal_range": "10–20 µg/mL", "unit": "µg/mL", "order": 2},
            {"name": "Lithium", "normal_range": "0.6–1.2 mEq/L", "unit": "mEq/L", "order": 3}
        ]
    }
]

class Command(BaseCommand):
    help = 'Populates the database with additional comprehensive laboratory tests.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate additional lab tests...'))
        
        for test_data in additional_lab_tests_data:
            # Get or create category
            category, created = TestCategory.objects.get_or_create(
                name=test_data["category_name"],
                defaults={"description": f"Category for {test_data['category_name']} tests"}
            )
            
            if created:
                self.stdout.write(f"Created new category: {category.name}")
            
            # Get or create test
            test, test_created = Test.objects.get_or_create(
                name=test_data["test_name"],
                category=category,
                defaults={
                    "description": test_data["description"],
                    "price": test_data["price"],
                    "sample_type": test_data["sample_type"],
                    "is_active": test_data["is_active"]
                }
            )
            
            if test_created:
                self.stdout.write(f"Created new test: {test.name}")
                
                # Create test parameters
                for param_data in test_data["parameters"]:
                    TestParameter.objects.get_or_create(
                        test=test,
                        name=param_data["name"],
                        defaults={
                            "normal_range": param_data["normal_range"],
                            "unit": param_data["unit"],
                            "order": param_data["order"]
                        }
                    )
            else:
                self.stdout.write(f"Test already exists: {test.name}")

        # Summary statistics
        total_categories = TestCategory.objects.count()
        total_tests = Test.objects.count()
        total_parameters = TestParameter.objects.count()

        self.stdout.write(self.style.SUCCESS(f'Successfully populated additional lab tests!'))
        self.stdout.write(self.style.SUCCESS(f'Total Categories: {total_categories}'))
        self.stdout.write(self.style.SUCCESS(f'Total Tests: {total_tests}'))
        self.stdout.write(self.style.SUCCESS(f'Total Parameters: {total_parameters}'))
