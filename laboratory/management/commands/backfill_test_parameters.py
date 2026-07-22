"""Backfill predefined TestParameter rows onto tests that lack them.

The rich sub-parameters live in `lab_catalog_seed.CATALOG` under canonical test
names (e.g. "Complete Blood Count (CBC)"). Legacy in-use tests often have a
different name (e.g. "Complete Blood Count") and only a single self-named
parameter, so the "Select Existing Parameter" modal shows nothing to add.

This command copies a catalog entry's parameters onto a matching test. Matching
is name-exact (normalized) only, plus an explicit ALIASES map for known legacy
names. It deliberately does NOT fuzzy-match: attaching wrong parameters to a
lab test is a clinical error, not a typo. Unmatched tests are reported so you
can extend ALIASES and re-run.

    python manage.py backfill_test_parameters --dry-run   # preview
    python manage.py backfill_test_parameters             # apply
"""
import re

from django.core.management.base import BaseCommand

from laboratory.lab_catalog_seed import CATALOG
from laboratory.models import Test, TestParameter


def normalize(name):
    """Lowercase, strip everything but a-z0-9. 'Malaria Parasite' -> 'malariaparasite'."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


# Legacy test name (normalized) -> canonical CATALOG name (as written in CATALOG).
# Extend this as unmatched tests are reported. Keep exact catalog spelling on the right.
ALIASES = {
    "completebloodcount": "Complete Blood Count (CBC)",
    "malariaparasite": "Malaria Blood Smear",
    "malaria": "Malaria Blood Smear",
    "malariardt": "Malaria Rapid Diagnostic Test (RDT)",
}


def build_catalog_index():
    """Return {normalized name: (canonical name, [(pname, normal_range, unit), ...])}."""
    index = {}
    for tests in CATALOG.values():
        for name, _price, _sample, _desc, params in tests:
            index[normalize(name)] = (name, params)
    return index


class Command(BaseCommand):
    help = "Copy predefined parameters onto tests that are missing them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would change without writing.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        index = build_catalog_index()
        alias_norm = {k: normalize(v) for k, v in ALIASES.items()}

        created = matched = unmatched = 0
        unmatched_names = set()

        # all_objects: run across every hospital, outside request tenant scope.
        for test in Test.all_objects.all():
            key = normalize(test.name)
            canon_key = key if key in index else alias_norm.get(key)
            entry = index.get(canon_key) if canon_key else None
            if not entry:
                unmatched += 1
                unmatched_names.add(test.name)
                continue

            matched += 1
            _canon_name, params = entry
            for order, (pname, normal_range, unit) in enumerate(params, start=1):
                exists = TestParameter.all_objects.filter(
                    hospital=test.hospital, test=test, name=pname
                ).exists()
                if exists:
                    continue
                created += 1
                self.stdout.write(f"  + {test.name} [h{test.hospital_id}] -> {pname}")
                if not dry:
                    TestParameter.all_objects.create(
                        hospital=test.hospital, test=test, name=pname,
                        normal_range=normal_range, unit=unit, order=order,
                    )

        self.stdout.write("")
        style = self.style.WARNING if dry else self.style.SUCCESS
        self.stdout.write(style(
            f"{'DRY-RUN ' if dry else ''}matched tests={matched}  "
            f"params created={created}  unmatched tests={unmatched}"
        ))
        if unmatched_names:
            self.stdout.write("Unmatched (add to ALIASES if they should get params):")
            for n in sorted(unmatched_names):
                self.stdout.write(f"  ? {n}  (normalized: {normalize(n)})")
