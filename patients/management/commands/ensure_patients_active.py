from django.core.management.base import BaseCommand
from django.db import transaction
from patients.models import Patient


class Command(BaseCommand):
    help = 'Ensure all patients are active by default (maintenance command)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-inactive',
            action='store_true',
            help='Automatically activate any inactive patients',
        )

    def handle(self, *args, **options):
        fix_inactive = options['fix_inactive']

        self.stdout.write(
            self.style.SUCCESS('Patient Status Maintenance Check')
        )
        self.stdout.write('=' * 50)

        # Get all patients
        all_patients = Patient.objects.all()
        active_patients = Patient.objects.filter(is_active=True)
        inactive_patients = Patient.objects.filter(is_active=False)

        self.stdout.write(f"📊 Total patients: {all_patients.count()}")
        self.stdout.write(f"✅ Active patients: {active_patients.count()}")
        self.stdout.write(f"❌ Inactive patients: {inactive_patients.count()}")

        if inactive_patients.exists():
            self.stdout.write("\n" + "-" * 40)
            self.stdout.write("⚠️  Found inactive patients:")
            for patient in inactive_patients:
                self.stdout.write(f"  - {patient.get_full_name()} ({patient.patient_id})")

            if fix_inactive:
                self.stdout.write("\n🔧 Fixing inactive patients...")
                with transaction.atomic():
                    updated_count = inactive_patients.update(is_active=True)
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Activated {updated_count} patients")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("\n💡 To fix inactive patients, run:")
                )
                self.stdout.write("   python manage.py ensure_patients_active --fix-inactive")
        else:
            self.stdout.write(
                self.style.SUCCESS("\n🎉 All patients are active! No issues found.")
            )

        # Additional checks
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("🔍 Additional checks:")
        
        # Check for patients with null is_active (shouldn't happen but let's be safe)
        null_active_patients = Patient.objects.filter(is_active__isnull=True)
        if null_active_patients.exists():
            self.stdout.write(
                self.style.ERROR(f"⚠️  Found {null_active_patients.count()} patients with null is_active field")
            )
            if fix_inactive:
                null_active_patients.update(is_active=True)
                self.stdout.write(
                    self.style.SUCCESS("✅ Fixed null is_active fields")
                )
        else:
            self.stdout.write("✅ No null is_active fields found")

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if fix_inactive and inactive_patients.exists():
            self.stdout.write(
                self.style.SUCCESS("✅ Maintenance completed - All patients are now active")
            )
        else:
            self.stdout.write("ℹ️  Maintenance check completed")

        # Recommendations
        self.stdout.write("\n💡 Recommendations:")
        self.stdout.write("  - Run this command regularly to ensure patient status consistency")
        self.stdout.write("  - Use 'Delete' button carefully (it deactivates, doesn't delete)")
        self.stdout.write("  - Use activate_patients command for specific patient management")
