from django.core.management.base import BaseCommand
from doctors.models import Specialization
from accounts.models import Department

class Command(BaseCommand):
    help = 'Populates the database with initial hospital specializations and departments.'

    def handle(self, *args, **options):
        specializations = [
            ("General Medicine", "Diagnosis and treatment of common diseases and health issues in adults"),
            ("Pediatrics", "Medical care for infants, children, and adolescents"),
            ("Obstetrics and Gynecology", "Women's health care, pregnancy, childbirth, and reproductive health"),
            ("General Surgery", "Surgical treatment of a wide range of diseases and conditions"),
            ("Orthopedic Surgery", "Treatment of musculoskeletal system including bones, joints, ligaments, muscles, and tendons"),
            ("Neurosurgery", "Surgical treatment of the nervous system including brain, spinal cord, and peripheral nerves"),
            ("Cardiology", "Diagnosis and treatment of heart and blood vessel disorders"),
            ("Pulmonology", "Treatment of diseases of the respiratory system including lungs and airways"),
            ("Gastroenterology", "Diagnosis and treatment of digestive system disorders"),
            ("Nephrology", "Treatment of kidney diseases and hypertension"),
            ("Neurology", "Diagnosis and treatment of disorders of the brain, spinal cord, and nerves"),
            ("Endocrinology", "Treatment of endocrine system disorders including diabetes and hormonal imbalances"),
            ("Dermatology", "Diagnosis and treatment of skin, hair, and nail disorders"),
            ("Ophthalmology", "Eye and vision care including surgery and medical treatment of eye diseases"),
            ("Otolaryngology (ENT)", "Treatment of ear, nose, throat, and related head and neck structures"),
            ("Urology", "Treatment of urinary tract system and male reproductive organs"),
            ("Oncology", "Diagnosis and treatment of cancer and tumors"),
            ("Hematology", "Treatment of blood disorders and diseases of the blood-forming organs"),
            ("Infectious Diseases", "Diagnosis and treatment of infections caused by bacteria, viruses, fungi, and parasites"),
            ("Rheumatology", "Treatment of autoimmune diseases, joint disorders, and musculoskeletal conditions"),
            ("Psychiatry", "Diagnosis and treatment of mental, emotional, and behavioral disorders"),
            ("Anesthesiology", "Pain management and anesthesia during surgical procedures"),
            ("Emergency Medicine", "Immediate medical care for acute illnesses and injuries")
        ]

        departments = [
            "Emergency Department", "Outpatient Department", "Inpatient Wards",
            "Operating Theatres", "Pharmacy", "Laboratory", "Radiology",
            "Physiotherapy", "Dietetics and Nutrition", "Dental Department",
            "Blood Bank", "Administration", "Human Resources", "Finance",
            "Information Technology", "Medical Records", "Nursing Administration",
            "Quality Assurance", "Housekeeping", "Security", "Biomedical Engineering",
            "Public Relations", "Social Work", "Central Sterile Supply Department"
        ]

        self.stdout.write("Populating Specializations...")
        for spec_name, spec_description in specializations:
            specialization, created = Specialization.objects.get_or_create(
                name=spec_name,
                defaults={'description': spec_description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Added specialization: {specialization.name}'))
            else:
                # Update description if specialization already exists but has no description
                if not specialization.description:
                    specialization.description = spec_description
                    specialization.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated description for: {specialization.name}'))
                else:
                    self.stdout.write(f'Specialization already exists: {specialization.name}')

        self.stdout.write("\nPopulating Departments...")
        for dept_name in departments:
            department, created = Department.objects.get_or_create(name=dept_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Added department: {department.name}'))
            else:
                self.stdout.write(f'Department already exists: {department.name}')

        self.stdout.write("\nInitial hospital data population complete.")
