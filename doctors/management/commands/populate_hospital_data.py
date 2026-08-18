from django.core.management.base import BaseCommand

from accounts.department_seed import DEPARTMENTS, seed_departments_for
from doctors.specialty_seed import SPECIALTIES, seed_specialties_for
from saas.models import Hospital


class Command(BaseCommand):
    help = (
        'Seeds the canonical specialization and department lists for every '
        'hospital. Idempotent; safe to re-run.'
    )

    def handle(self, *args, **options):
        hospitals = list(Hospital.objects.all())
        if not hospitals:
            self.stdout.write(self.style.WARNING('No hospitals exist, nothing to seed.'))
            return

        for hospital in hospitals:
            seed_specialties_for(hospital)
            seed_departments_for(hospital)
            self.stdout.write(
                self.style.SUCCESS(
                    f'{hospital.name}: {len(SPECIALTIES)} specializations, '
                    f'{len(DEPARTMENTS)} departments ensured'
                )
            )

        self.stdout.write(self.style.SUCCESS('\nHospital data population complete.'))
