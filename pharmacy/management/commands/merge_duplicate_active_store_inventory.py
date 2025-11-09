from django.core.management.base import BaseCommand
from django.db import transaction

from pharmacy.models import ActiveStoreInventory


class Command(BaseCommand):
    help = "Delete duplicate ActiveStoreInventory records keeping a single entry per key without altering quantities."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without modifying any data.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        duplicates_found = 0
        groups_processed = 0

        with transaction.atomic():
            # group by unique identity (excluding quantity) so we consolidate exact duplicates
            qs = (
                ActiveStoreInventory.objects.values(
                    "active_store_id",
                    "medication_id",
                    "batch_number",
                    "expiry_date",
                    "unit_cost",
                )
                .order_by()
            )

            from django.db.models import Count, Sum

            dup_keys = [
                row
                for row in qs.annotate(c=Count("id")).filter(c__gt=1)
            ]

            if not dup_keys:
                self.stdout.write(self.style.SUCCESS("No duplicate ActiveStoreInventory records found."))
                return

            for key in dup_keys:
                items = ActiveStoreInventory.objects.filter(
                    active_store_id=key["active_store_id"],
                    medication_id=key["medication_id"],
                    batch_number=key["batch_number"],
                    expiry_date=key["expiry_date"],
                    unit_cost=key["unit_cost"],
                ).order_by("id")

                keeper = items.first()
                to_delete = items.exclude(id=keeper.id)

                if to_delete.exists():
                    duplicates_found += to_delete.count()
                    groups_processed += 1

                    msg = (
                        f"ActiveStore {keeper.active_store_id} Medication {keeper.medication_id} "
                        f"Batch {keeper.batch_number} Exp {keeper.expiry_date} UnitCost {keeper.unit_cost}: "
                        f"delete {to_delete.count()} duplicates, keeping ID {keeper.id} with existing qty {keeper.stock_quantity}"
                    )

                    if dry_run:
                        self.stdout.write(msg)
                    else:
                        to_delete.delete()

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {groups_processed} groups; {duplicates_found} duplicate records {'would be ' if dry_run else ''}deleted."
            )
        )
