"""Assign all legacy (hospital IS NULL) rows to one default hospital.

Re-runnable: only touches rows where hospital is still null. Run once after the
multi-tenant FKs land, then again any time stray null rows appear.

    python manage.py backfill_tenant                # default: Main Hospital / main
    python manage.py backfill_tenant --name "X" --subdomain x
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from saas.models import Hospital

# saas's own tables (Hospital/Plan/Subscription) are not tenant-scoped rows.
SKIP_APPS = {"saas"}


class Command(BaseCommand):
    help = "Backfill null hospital FKs onto a default tenant."

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Main Hospital")
        parser.add_argument("--subdomain", default="main")

    @transaction.atomic
    def handle(self, *args, **opts):
        hospital, created = Hospital.objects.get_or_create(
            subdomain=opts["subdomain"], defaults={"name": opts["name"]}
        )
        verb = "Created" if created else "Using existing"
        self.stdout.write(f"{verb} hospital: {hospital.name} ({hospital.subdomain})")

        total = 0
        for model in apps.get_models():
            if model._meta.app_label in SKIP_APPS:
                continue
            field = next(
                (f for f in model._meta.local_fields if f.name == "hospital"), None
            )
            if field is None:
                continue
            n = model._base_manager.filter(hospital__isnull=True).update(
                hospital=hospital
            )
            if n:
                total += n
                self.stdout.write(f"  {model._meta.label}: {n}")

        self.stdout.write(self.style.SUCCESS(f"Backfilled {total} rows."))
