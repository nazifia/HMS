import random
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Update existing retainership patient IDs to start with 3"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )

    def _generate_new_id(self, existing_ids):
        for _ in range(200):
            new_id = "3" + "".join([str(random.randint(0, 9)) for _ in range(9)])
            if new_id not in existing_ids:
                return new_id
        raise RuntimeError("Could not generate a unique retainership patient ID after 200 attempts")

    def handle(self, *args, **options):
        from patients.models import Patient
        from retainership.models import RetainershipPatient

        dry_run = options["dry_run"]

        # Collect all patients that are retainership (by type or by linked record)
        by_type = set(
            Patient.objects.filter(patient_type="retainership").values_list("id", flat=True)
        )
        by_link = set(
            RetainershipPatient.objects.values_list("patient_id", flat=True)
        )
        all_ids = by_type | by_link

        patients = Patient.objects.filter(id__in=all_ids)
        needs_update = [p for p in patients if not p.patient_id.startswith("3")]

        if not needs_update:
            self.stdout.write(self.style.SUCCESS("All retainership patient IDs already start with 3. Nothing to do."))
            return

        self.stdout.write(f"Found {len(needs_update)} retainership patient(s) with IDs not starting with 3.")

        # Build set of all current patient IDs to avoid collisions
        existing_ids = set(Patient.objects.values_list("patient_id", flat=True))

        with transaction.atomic():
            for patient in needs_update:
                old_id = patient.patient_id
                new_id = self._generate_new_id(existing_ids)
                existing_ids.add(new_id)
                existing_ids.discard(old_id)

                if dry_run:
                    self.stdout.write(f"  [DRY RUN] {patient.get_full_name()} — {old_id} → {new_id}")
                else:
                    patient.patient_id = new_id
                    Patient.objects.filter(pk=patient.pk).update(patient_id=new_id)
                    self.stdout.write(f"  Updated {patient.get_full_name()} — {old_id} → {new_id}")

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run complete — no changes saved."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Done. Updated {len(needs_update)} patient ID(s)."))
