"""Report rows that would break the per-hospital unique constraints.

Run this on the target database BEFORE migrating. It reads the model
definitions for every unique rule that includes `hospital` and looks for rows
that already violate it, so a deploy fails here rather than half-way through
`migrate`.

    python manage.py check_tenant_uniques

Exits 1 when something would clash, so it can gate a deploy script.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models import Count, UniqueConstraint


class Command(BaseCommand):
    help = "Report rows that would violate the per-hospital unique constraints."

    def handle(self, *args, **options):
        clashes = 0
        for model in apps.get_models():
            for fields in self._tenant_unique_rules(model):
                others = [f for f in fields if f != "hospital"]
                if not others:
                    continue
                clashes += self._report(model, ["hospital"] + others)
                # The partial constraints guard tenant-less rows separately:
                # SQL treats NULL hospital as distinct.
                clashes += self._report(model, others, tenantless=True)

        if clashes:
            self.stderr.write(
                self.style.ERROR(f"{clashes} clash(es) found — resolve before migrating.")
            )
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("No clashes. Safe to migrate."))

    @staticmethod
    def _tenant_unique_rules(model):
        """Every unique rule on `model` that is scoped by hospital."""
        for fields in model._meta.unique_together or ():
            if "hospital" in fields:
                yield list(fields)
        for constraint in model._meta.constraints:
            fields = list(getattr(constraint, "fields", None) or ())
            if isinstance(constraint, UniqueConstraint) and "hospital" in fields:
                yield fields

    def _report(self, model, fields, tenantless=False):
        rows = model._base_manager.all()
        if tenantless:
            rows = rows.filter(hospital__isnull=True)
        # A NULL in any column makes the row unique in SQL, so skip those.
        for field in fields:
            rows = rows.exclude(**{f"{field}__isnull": True})

        dupes = (
            rows.values(*fields)
            .annotate(n=Count("pk"))
            .filter(n__gt=1)
            .order_by()
        )
        scope = "hospital IS NULL" if tenantless else "per hospital"
        found = 0
        for row in dupes:
            found += 1
            values = ", ".join(f"{f}={row[f]!r}" for f in fields)
            self.stdout.write(
                self.style.WARNING(
                    f"  {model._meta.label} ({scope}): {values} — {row['n']} rows"
                )
            )
        return found
