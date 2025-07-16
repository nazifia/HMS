from django.core.management.base import BaseCommand
from billing.models import Service, ServiceCategory

class Command(BaseCommand):
    help = 'Creates the default "Admission Fee" service if it does not exist.'

    def handle(self, *args, **options):
        # Ensure a default service category exists or create one
        service_category, created = ServiceCategory.objects.get_or_create(
            name='General Services',
            defaults={'description': 'Category for general hospital services'}
        )

        service, created = Service.objects.get_or_create(
            name='Admission Fee',
            defaults={
                'category': service_category,
                'price': 0.00,  # Default price, can be updated later
                'description': 'Fee charged for patient admission'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created "Admission Fee" service.'))
        else:
            self.stdout.write(self.style.SUCCESS('"Admission Fee" service already exists.'))