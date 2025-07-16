
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hms.settings")
django.setup()

from billing.models import Service, ServiceCategory

def create_medication_dispensing_service():
    # Get or create the 'Pharmacy' service category
    pharmacy_category, created = ServiceCategory.objects.get_or_create(name='Pharmacy')
    if created:
        print("Created 'Pharmacy' service category.")

    # Check if the 'Medication Dispensing' service already exists
    if not Service.objects.filter(name='Medication Dispensing').exists():
        # Create the 'Medication Dispensing' service
        Service.objects.create(
            name='Medication Dispensing',
            category=pharmacy_category,
            price=0.00,  # Set a default price, can be adjusted later
            description='Service for dispensing medications from the pharmacy.'
        )
        print("Successfully created the 'Medication Dispensing' service.")
    else:
        print("'Medication Dispensing' service already exists.")

if __name__ == '__main__':
    create_medication_dispensing_service()
