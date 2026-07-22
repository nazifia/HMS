from django.core.management.base import BaseCommand

from radiology.models import RadiologyCategory, RadiologyTest
from radiology.radiology_catalog_seed import CATALOG
from saas.models import Hospital


class Command(BaseCommand):
    help = "Populate radiology categories and procedures for every hospital (idempotent)."

    def handle(self, *args, **options):
        from decimal import Decimal

        hospitals = list(Hospital.objects.all())
        if not hospitals:
            self.stdout.write(self.style.WARNING("No hospitals found; nothing to seed."))
            return

        for hospital in hospitals:
            for category_name, procedures in CATALOG.items():
                category, _ = RadiologyCategory.objects.get_or_create(
                    hospital=hospital, name=category_name
                )
                for name, price, minutes, description, prep in procedures:
                    RadiologyTest.objects.get_or_create(
                        hospital=hospital,
                        name=name,
                        defaults={
                            "category": category,
                            "description": description,
                            "preparation_instructions": prep,
                            "price": Decimal(str(price)),
                            "duration_minutes": minutes,
                            "is_active": True,
                        },
                    )
        self.stdout.write(
            self.style.SUCCESS(
                f"Radiology catalog seeded for {len(hospitals)} hospital(s)."
            )
        )
