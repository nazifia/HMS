"""Reconcile test request statuses with the sign-off rule.

Requests used to be closed as soon as every test had a result. Completion now
means every test has a *verified* result, so requests closed under the old rule
may still be sitting at 'completed' with unverified results.

    python manage.py resync_test_request_status --dry-run
    python manage.py resync_test_request_status
"""
from django.core.management.base import BaseCommand

from laboratory.models import TestRequest
from laboratory.services import sync_request_completion


class Command(BaseCommand):
    help = "Recompute test request statuses from their results (sign-off rule)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without saving.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        changed = 0

        queryset = TestRequest.objects.exclude(
            status__in=["cancelled", "awaiting_payment"]
        ).prefetch_related("tests", "results")

        for test_request in queryset:
            before = test_request.status
            if dry_run:
                # Work out the answer without touching the row.
                ordered = set(test_request.tests.values_list("id", flat=True))
                verified = set(
                    test_request.results.filter(verified_by__isnull=False)
                    .values_list("test_id", flat=True)
                )
                if ordered and ordered <= verified:
                    after = "completed"
                elif test_request.results.exists() or before == "completed":
                    after = "processing"
                else:
                    after = before
            else:
                sync_request_completion(test_request)
                after = test_request.status

            if after != before:
                changed += 1
                self.stdout.write(
                    f"Request #{test_request.id} "
                    f"({test_request.patient.get_full_name()}): {before} -> {after}"
                )

        verb = "would change" if dry_run else "changed"
        self.stdout.write(
            self.style.SUCCESS(f"{changed} of {queryset.count()} requests {verb}.")
        )
