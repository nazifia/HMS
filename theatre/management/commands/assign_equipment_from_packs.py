from django.core.management.base import BaseCommand
from django.db import transaction
from theatre.models import SurgeryType, SurgicalEquipment, SurgeryTypeEquipment
from pharmacy.models import MedicalPack, MedicalPackItem


class Command(BaseCommand):
    help = 'Create SurgeryTypeEquipment records from MedicalPack equipment items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing SurgeryTypeEquipment records before creating new ones'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']

        if clear_existing and not dry_run:
            self.stdout.write('Clearing existing SurgeryTypeEquipment records...')
            SurgeryTypeEquipment.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing records.'))

        # Surgery type name mapping (from surgery type name to pack surgery_type code)
        surgery_type_mapping = {
            'Appendectomy': 'appendectomy',
            'Cholecystectomy': 'cholecystectomy',
            'Hernia Repair': 'hernia_repair',
            'Cesarean Section': 'cesarean_section',
            'Tonsillectomy': 'tonsillectomy',
        }

        created_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write('Scanning medical packs for equipment items...')
        self.stdout.write('=' * 60)

        # Get all surgery-type medical packs with equipment items
        packs_with_equipment = MedicalPack.objects.filter(
            pack_type='surgery',
            items__item_type='equipment'
        ).distinct().select_related().prefetch_related('items')

        self.stdout.write(f"Found {packs_with_equipment.count()} surgical packs with equipment items\n")

        for pack in packs_with_equipment:
            self.stdout.write(f"\nProcessing pack: {pack.name}")
            self.stdout.write(f"  Surgery type code: {pack.surgery_type}")

            # Find matching surgery type
            surgery_type = None
            for surgery_name, pack_code in surgery_type_mapping.items():
                if pack.surgery_type == pack_code:
                    try:
                        surgery_type = SurgeryType.objects.get(name=surgery_name)
                        self.stdout.write(f"  Matched to SurgeryType: {surgery_type.name}")
                        break
                    except SurgeryType.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"  SurgeryType '{surgery_name}' not found, skipping...")
                        )
                        continue

            if not surgery_type:
                self.stdout.write(
                    self.style.WARNING(f"  No matching SurgeryType found for '{pack.surgery_type}', skipping...")
                )
                skipped_count += 1
                continue

            # Process equipment items in this pack
            equipment_items = pack.items.filter(item_type='equipment').select_related('medication')

            for item in equipment_items:
                medication = item.medication
                self.stdout.write(f"  Equipment item: {medication.name} (qty: {item.quantity})")

                # Get or create SurgicalEquipment
                try:
                    equipment, created = SurgicalEquipment.objects.get_or_create(
                        name=medication.name,
                        defaults={
                            'equipment_type': 'instrument',  # Default type
                            'description': medication.description or f"Equipment for {pack.name}",
                            'quantity_available': 10,  # Default quantity
                            'is_available': True,
                        }
                    )

                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f"    Created new SurgicalEquipment: {equipment.name}")
                        )
                    else:
                        self.stdout.write(f"    Using existing SurgicalEquipment: {equipment.name}")

                    # Create SurgeryTypeEquipment link
                    if not dry_run:
                        surgery_type_equip, created = SurgeryTypeEquipment.objects.get_or_create(
                            surgery_type=surgery_type,
                            equipment=equipment,
                            defaults={
                                'quantity_required': item.quantity,
                                'is_mandatory': not item.is_optional,
                                'notes': item.usage_instructions or f"From {pack.name}",
                            }
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"    Linked to surgery type (qty: {item.quantity})")
                            )
                        else:
                            self.stdout.write(f"    Already linked to surgery type")
                    else:
                        self.stdout.write(
                            self.style.NOTICE(f"    [DRY RUN] Would create link (qty: {item.quantity})")
                        )
                        created_count += 1

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"    Error processing {medication.name}: {str(e)}")
                    )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('SUMMARY:')
        self.stdout.write(f"  Equipment links created: {created_count}")
        self.stdout.write(f"  Packs skipped (no matching surgery type): {skipped_count}")
        self.stdout.write(f"  Errors: {error_count}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nThis was a DRY RUN. No records were actually created.')
            )
            self.stdout.write('Run without --dry-run to create the records.')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created_count} equipment assignments!')
            )
