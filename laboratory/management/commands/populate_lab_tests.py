"""Seed the canonical lab test catalog (see laboratory/lab_catalog_seed.py).

    python manage.py populate_lab_tests                 # all hospitals
    python manage.py populate_lab_tests --subdomain x   # one hospital

Idempotent: re-running only fills in missing categories/tests/parameters.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from laboratory.lab_catalog_seed import seed_lab_catalog_for
from saas.models import Hospital


class Command(BaseCommand):
    help = "Populate the lab test catalog (categories, tests, parameters) per hospital."

    def add_arguments(self, parser):
        parser.add_argument("--subdomain", help="Seed only this hospital.")

    @transaction.atomic
    def handle(self, *args, **options):
        hospitals = Hospital.objects.all()
        if options.get("subdomain"):
            hospitals = hospitals.filter(subdomain=options["subdomain"])
        if not hospitals:
            self.stdout.write(self.style.WARNING("No matching hospitals. Nothing seeded."))
            return
        for hospital in hospitals:
            seed_lab_catalog_for(hospital)
            self.stdout.write(self.style.SUCCESS(f"Seeded lab catalog for {hospital.name}"))
        self.stdout.write(self.style.SUCCESS("Done."))
