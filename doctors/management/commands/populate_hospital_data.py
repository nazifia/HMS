from django.core.management.base import BaseCommand
from doctors.models import Specialization
from accounts.models import Department

class Command(BaseCommand):
    help = 'Populates the database with initial hospital specializations and departments.'

    def handle(self, *args, **options):
        specializations = [
            "General Medicine", "Pediatrics", "Obstetrics and Gynecology", "General Surgery",
            "Orthopedic Surgery", "Neurosurgery", "Cardiology", "Pulmonology",
            "Gastroenterology", "Nephrology", "Neurology", "Endocrinology",
            "Dermatology", "Ophthalmology", "Otolaryngology (ENT)", "Urology",
            "Oncology", "Hematology", "Infectious Diseases", "Rheumatology",
            "Psychiatry", "Anesthesiology", "Emergency Medicine"
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
        for spec_name in specializations:
            specialization, created = Specialization.objects.get_or_create(name=spec_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Added specialization: {specialization.name}'))
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
