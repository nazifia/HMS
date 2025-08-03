from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from theatre.models import SurgeryType, SurgicalEquipment, OperationTheatre


class Command(BaseCommand):
    help = 'Populate initial data for theatre module'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate theatre data...'))

        # Create Surgery Types
        surgery_types = [
            {
                'name': 'Appendectomy',
                'description': 'Surgical removal of the appendix',
                'average_duration': timedelta(hours=1, minutes=30),
                'preparation_time': timedelta(minutes=30),
                'recovery_time': timedelta(hours=2),
                'risk_level': 'low',
                'instructions': 'Standard laparoscopic procedure. Patient should fast 8 hours before surgery.'
            },
            {
                'name': 'Cholecystectomy',
                'description': 'Surgical removal of the gallbladder',
                'average_duration': timedelta(hours=2),
                'preparation_time': timedelta(minutes=45),
                'recovery_time': timedelta(hours=3),
                'risk_level': 'medium',
                'instructions': 'Laparoscopic approach preferred. Check for bile duct anatomy.'
            },
            {
                'name': 'Hernia Repair',
                'description': 'Surgical repair of hernia',
                'average_duration': timedelta(hours=1),
                'preparation_time': timedelta(minutes=20),
                'recovery_time': timedelta(hours=1, minutes=30),
                'risk_level': 'low',
                'instructions': 'Can be performed under local or general anesthesia.'
            },
            {
                'name': 'Cardiac Bypass',
                'description': 'Coronary artery bypass surgery',
                'average_duration': timedelta(hours=4),
                'preparation_time': timedelta(hours=1),
                'recovery_time': timedelta(hours=6),
                'risk_level': 'critical',
                'instructions': 'Requires cardiac surgery team. ICU bed must be available post-op.'
            },
            {
                'name': 'Knee Replacement',
                'description': 'Total knee joint replacement',
                'average_duration': timedelta(hours=2, minutes=30),
                'preparation_time': timedelta(minutes=45),
                'recovery_time': timedelta(hours=4),
                'risk_level': 'medium',
                'instructions': 'Orthopedic procedure. Blood bank should be notified.'
            },
            {
                'name': 'Cataract Surgery',
                'description': 'Surgical removal of cataract from eye',
                'average_duration': timedelta(minutes=30),
                'preparation_time': timedelta(minutes=15),
                'recovery_time': timedelta(hours=1),
                'risk_level': 'low',
                'instructions': 'Outpatient procedure. Local anesthesia typically used.'
            }
        ]

        for surgery_type_data in surgery_types:
            surgery_type, created = SurgeryType.objects.get_or_create(
                name=surgery_type_data['name'],
                defaults=surgery_type_data
            )
            if created:
                self.stdout.write(f'Created surgery type: {surgery_type.name}')
            else:
                self.stdout.write(f'Surgery type already exists: {surgery_type.name}')

        # Create Surgical Equipment
        equipment_list = [
            {
                'name': 'Laparoscope',
                'equipment_type': 'instrument',
                'description': 'Minimally invasive surgical camera',
                'quantity_available': 3,
                'is_available': True
            },
            {
                'name': 'Electrocautery Unit',
                'equipment_type': 'instrument',
                'description': 'Device for cutting and coagulating tissue',
                'quantity_available': 5,
                'is_available': True
            },
            {
                'name': 'Anesthesia Machine',
                'equipment_type': 'anesthesia',
                'description': 'Machine for delivering anesthesia gases',
                'quantity_available': 4,
                'is_available': True
            },
            {
                'name': 'Patient Monitor',
                'equipment_type': 'monitor',
                'description': 'Monitors vital signs during surgery',
                'quantity_available': 6,
                'is_available': True
            },
            {
                'name': 'Surgical Microscope',
                'equipment_type': 'instrument',
                'description': 'High-powered microscope for precision surgery',
                'quantity_available': 2,
                'is_available': True
            },
            {
                'name': 'C-Arm X-Ray',
                'equipment_type': 'imaging',
                'description': 'Mobile X-ray imaging device',
                'quantity_available': 2,
                'is_available': True
            },
            {
                'name': 'Defibrillator',
                'equipment_type': 'monitor',
                'description': 'Emergency cardiac resuscitation device',
                'quantity_available': 3,
                'is_available': True
            },
            {
                'name': 'Surgical Lights',
                'equipment_type': 'other',
                'description': 'High-intensity surgical lighting',
                'quantity_available': 8,
                'is_available': True
            },
            {
                'name': 'Ventilator',
                'equipment_type': 'anesthesia',
                'description': 'Mechanical ventilation device',
                'quantity_available': 4,
                'is_available': True
            },
            {
                'name': 'Ultrasound Machine',
                'equipment_type': 'imaging',
                'description': 'Portable ultrasound for surgical guidance',
                'quantity_available': 2,
                'is_available': True
            }
        ]

        for equipment_data in equipment_list:
            equipment, created = SurgicalEquipment.objects.get_or_create(
                name=equipment_data['name'],
                defaults=equipment_data
            )
            if created:
                self.stdout.write(f'Created equipment: {equipment.name}')
            else:
                self.stdout.write(f'Equipment already exists: {equipment.name}')

        # Create Operation Theatres if none exist
        if not OperationTheatre.objects.exists():
            theatres = [
                {
                    'name': 'Main Operating Theatre 1',
                    'theatre_number': 'OT-001',
                    'floor': 2,
                    'capacity': 8,
                    'is_available': True,
                    'description': 'Main theatre for general surgeries'
                },
                {
                    'name': 'Cardiac Surgery Theatre',
                    'theatre_number': 'OT-002',
                    'floor': 2,
                    'capacity': 12,
                    'is_available': True,
                    'description': 'Specialized theatre for cardiac procedures'
                },
                {
                    'name': 'Orthopedic Theatre',
                    'theatre_number': 'OT-003',
                    'floor': 2,
                    'capacity': 10,
                    'is_available': True,
                    'description': 'Theatre equipped for orthopedic surgeries'
                },
                {
                    'name': 'Minor Procedures Theatre',
                    'theatre_number': 'OT-004',
                    'floor': 1,
                    'capacity': 6,
                    'is_available': True,
                    'description': 'Theatre for minor outpatient procedures'
                }
            ]

            for theatre_data in theatres:
                theatre = OperationTheatre.objects.create(**theatre_data)
                self.stdout.write(f'Created theatre: {theatre.name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated theatre data!'))
