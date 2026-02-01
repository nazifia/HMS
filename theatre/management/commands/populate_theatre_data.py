from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from theatre.models import (
    SurgeryType, 
    SurgicalEquipment, 
    OperationTheatre,
    SurgeryTypeEquipment
)


class Command(BaseCommand):
    help = 'Populate comprehensive theatre data including surgery types, equipment, theatres, and equipment assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating (use with caution)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip existing records instead of updating'
        )

    def handle(self, *args, **options):
        clear = options['clear']
        skip_existing = options['skip_existing']
        
        if clear:
            self.stdout.write(self.style.WARNING('Clearing existing theatre data...'))
            SurgeryTypeEquipment.objects.all().delete()
            SurgicalEquipment.objects.all().delete()
            OperationTheatre.objects.all().delete()
            SurgeryType.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Starting to populate comprehensive theatre data...\n'))

        # Step 1: Create Surgery Types
        self.create_surgery_types(skip_existing)
        
        # Step 2: Create Operation Theatres
        self.create_operation_theatres(skip_existing)
        
        # Step 3: Create Surgical Equipment
        self.create_surgical_equipment(skip_existing)
        
        # Step 4: Assign Equipment to Surgery Types
        self.assign_equipment_to_surgery_types(skip_existing)

        self.stdout.write(self.style.SUCCESS('\n✓ Successfully populated all theatre data!'))
        self.stdout.write(self.style.SUCCESS(f'  - Surgery Types: {SurgeryType.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Operation Theatres: {OperationTheatre.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Surgical Equipment: {SurgicalEquipment.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Equipment Assignments: {SurgeryTypeEquipment.objects.count()}'))

    def create_surgery_types(self, skip_existing):
        """Create comprehensive surgery types with fees"""
        self.stdout.write('\nCreating Surgery Types...')
        
        surgery_types = [
            {
                'name': 'Appendectomy',
                'description': 'Surgical removal of the appendix. Most commonly performed as a laparoscopic procedure.',
                'average_duration': timedelta(hours=1, minutes=30),
                'preparation_time': timedelta(minutes=30),
                'recovery_time': timedelta(hours=2),
                'risk_level': 'low',
                'fee': Decimal('150000.00'),
                'instructions': 'Standard laparoscopic procedure. Patient should fast 8 hours before surgery. Pre-operative antibiotics required.'
            },
            {
                'name': 'Cholecystectomy',
                'description': 'Surgical removal of the gallbladder. Laparoscopic approach is preferred.',
                'average_duration': timedelta(hours=2),
                'preparation_time': timedelta(minutes=45),
                'recovery_time': timedelta(hours=3),
                'risk_level': 'medium',
                'fee': Decimal('200000.00'),
                'instructions': 'Laparoscopic approach preferred. Check for bile duct anatomy. Intraoperative cholangiogram if needed.'
            },
            {
                'name': 'Hernia Repair',
                'description': 'Surgical repair of hernia including inguinal, femoral, and incisional hernias.',
                'average_duration': timedelta(hours=1, minutes=30),
                'preparation_time': timedelta(minutes=30),
                'recovery_time': timedelta(hours=2),
                'risk_level': 'low',
                'fee': Decimal('120000.00'),
                'instructions': 'Can be performed under local, regional, or general anesthesia. Mesh repair for recurrent hernias.'
            },
            {
                'name': 'Cesarean Section',
                'description': 'Surgical delivery of baby through incisions in abdomen and uterus.',
                'average_duration': timedelta(hours=1, minutes=15),
                'preparation_time': timedelta(minutes=30),
                'recovery_time': timedelta(hours=4),
                'risk_level': 'medium',
                'fee': Decimal('180000.00'),
                'instructions': 'Emergency or elective. Spinal or epidural anesthesia preferred. Pediatric team standby.'
            },
            {
                'name': 'Cardiac Bypass',
                'description': 'Coronary artery bypass graft (CABG) surgery to improve blood flow to heart.',
                'average_duration': timedelta(hours=4),
                'preparation_time': timedelta(hours=1),
                'recovery_time': timedelta(hours=6),
                'risk_level': 'critical',
                'fee': Decimal('850000.00'),
                'instructions': 'Requires full cardiac surgery team. Cardiopulmonary bypass machine. ICU bed mandatory post-op. Blood products available.'
            },
            {
                'name': 'Knee Replacement',
                'description': 'Total knee arthroplasty - replacement of knee joint surfaces.',
                'average_duration': timedelta(hours=2, minutes=30),
                'preparation_time': timedelta(minutes=45),
                'recovery_time': timedelta(hours=4),
                'risk_level': 'medium',
                'fee': Decimal('450000.00'),
                'instructions': 'Orthopedic procedure. Blood bank should be notified. Prophylactic antibiotics. Physiotherapy referral post-op.'
            },
            {
                'name': 'Cataract Surgery',
                'description': 'Phacoemulsification and intraocular lens implantation.',
                'average_duration': timedelta(minutes=45),
                'preparation_time': timedelta(minutes=20),
                'recovery_time': timedelta(hours=1),
                'risk_level': 'low',
                'fee': Decimal('80000.00'),
                'instructions': 'Day case procedure. Topical or local anesthesia. Patient can go home same day.'
            },
            {
                'name': 'Tonsillectomy',
                'description': 'Surgical removal of tonsils.',
                'average_duration': timedelta(minutes=45),
                'preparation_time': timedelta(minutes=20),
                'recovery_time': timedelta(hours=2),
                'risk_level': 'low',
                'fee': Decimal('70000.00'),
                'instructions': 'Common pediatric procedure. Coblation or electrocautery technique. Monitor for bleeding post-op.'
            },
            {
                'name': 'Thyroidectomy',
                'description': 'Surgical removal of part or all of thyroid gland.',
                'average_duration': timedelta(hours=2),
                'preparation_time': timedelta(minutes=45),
                'recovery_time': timedelta(hours=3),
                'risk_level': 'medium',
                'fee': Decimal('250000.00'),
                'instructions': 'Check vocal cords pre and post-op. Monitor calcium levels. Recurrent laryngeal nerve identification critical.'
            },
            {
                'name': 'Laparotomy',
                'description': 'Open abdominal surgery for various conditions including trauma, cancer, or obstruction.',
                'average_duration': timedelta(hours=3),
                'preparation_time': timedelta(minutes=45),
                'recovery_time': timedelta(hours=5),
                'risk_level': 'high',
                'fee': Decimal('300000.00'),
                'instructions': 'Major abdominal procedure. Nasogastric tube placement. Bowel prep if elective. ICU monitoring for high-risk patients.'
            }
        ]

        for surgery_type_data in surgery_types:
            if skip_existing:
                surgery_type, created = SurgeryType.objects.get_or_create(
                    name=surgery_type_data['name'],
                    defaults=surgery_type_data
                )
            else:
                surgery_type, created = SurgeryType.objects.update_or_create(
                    name=surgery_type_data['name'],
                    defaults=surgery_type_data
                )
            
            status = 'Created' if created else 'Updated' if not skip_existing else 'Exists'
            self.stdout.write(f'  {status}: {surgery_type.name} (₦{surgery_type.fee:,.2f})')

    def create_operation_theatres(self, skip_existing):
        """Create operation theatres"""
        self.stdout.write('\nCreating Operation Theatres...')
        
        theatres = [
            {
                'name': 'Main Operating Theatre 1',
                'theatre_number': 'OT-001',
                'floor': '2',
                'capacity': 8,
                'is_available': True,
                'description': 'Main theatre for general surgeries with full laparoscopic setup',
                'equipment_list': 'Laparoscope, Electrocautery Unit, Anesthesia Machine, Patient Monitor, Surgical Lights'
            },
            {
                'name': 'Main Operating Theatre 2',
                'theatre_number': 'OT-002',
                'floor': '2',
                'capacity': 8,
                'is_available': True,
                'description': 'Multi-purpose theatre for general and emergency surgeries',
                'equipment_list': 'Laparoscope, Electrocautery Unit, Anesthesia Machine, Patient Monitor, Defibrillator'
            },
            {
                'name': 'Cardiac Surgery Theatre',
                'theatre_number': 'OT-003',
                'floor': '2',
                'capacity': 12,
                'is_available': True,
                'description': 'Specialized theatre for cardiac and thoracic procedures',
                'equipment_list': 'Heart-Lung Machine, Cardiac Monitors, Defibrillator, Anesthesia Machine, Blood Warmer'
            },
            {
                'name': 'Orthopedic Theatre',
                'theatre_number': 'OT-004',
                'floor': '2',
                'capacity': 10,
                'is_available': True,
                'description': 'Theatre equipped for orthopedic and trauma surgeries',
                'equipment_list': 'C-Arm X-Ray, Orthopedic Table, Surgical Drills, Anesthesia Machine, Tourniquet System'
            },
            {
                'name': 'Ophthalmic Theatre',
                'theatre_number': 'OT-005',
                'floor': '1',
                'capacity': 6,
                'is_available': True,
                'description': 'Specialized theatre for eye surgeries',
                'equipment_list': 'Operating Microscope, Phacoemulsification Machine, Anesthesia Machine, Specialized Lighting'
            },
            {
                'name': 'Emergency Theatre',
                'theatre_number': 'OT-006',
                'floor': '1',
                'capacity': 8,
                'is_available': True,
                'description': '24/7 theatre for emergency trauma and acute surgeries',
                'equipment_list': 'Emergency Surgical Set, Anesthesia Machine, Defibrillator, Portable X-Ray, Blood Warmer'
            },
            {
                'name': 'Minor Procedures Theatre',
                'theatre_number': 'OT-007',
                'floor': '1',
                'capacity': 4,
                'is_available': True,
                'description': 'Day case theatre for minor outpatient procedures',
                'equipment_list': 'Minor Surgery Set, Local Anesthesia Equipment, Patient Monitor'
            },
            {
                'name': 'Labor Theatre',
                'theatre_number': 'OT-008',
                'floor': '3',
                'capacity': 8,
                'is_available': True,
                'description': 'Dedicated theatre for cesarean sections and obstetric emergencies',
                'equipment_list': 'Obstetric Bed, Anesthesia Machine, Infant Warmer, Fetal Monitor, Emergency Delivery Set'
            }
        ]

        for theatre_data in theatres:
            if skip_existing:
                theatre, created = OperationTheatre.objects.get_or_create(
                    theatre_number=theatre_data['theatre_number'],
                    defaults=theatre_data
                )
            else:
                theatre, created = OperationTheatre.objects.update_or_create(
                    theatre_number=theatre_data['theatre_number'],
                    defaults=theatre_data
                )
            
            status = 'Created' if created else 'Updated' if not skip_existing else 'Exists'
            self.stdout.write(f'  {status}: {theatre.name}')

    def create_surgical_equipment(self, skip_existing):
        """Create comprehensive surgical equipment inventory"""
        self.stdout.write('\nCreating Surgical Equipment...')
        
        equipment_list = [
            # Instruments
            {
                'name': 'Laparoscope',
                'equipment_type': 'instrument',
                'description': 'High-definition laparoscopic camera and tower with insufflator',
                'quantity_available': 4,
                'is_available': True
            },
            {
                'name': 'Electrocautery Unit',
                'equipment_type': 'instrument',
                'description': 'Advanced electrosurgical unit for cutting and coagulation',
                'quantity_available': 6,
                'is_available': True
            },
            {
                'name': 'Surgical Microscope',
                'equipment_type': 'instrument',
                'description': 'Operating microscope with high magnification for precision surgery',
                'quantity_available': 2,
                'is_available': True
            },
            {
                'name': 'Surgical Drill',
                'equipment_type': 'instrument',
                'description': 'Orthopedic surgical drill and saw system',
                'quantity_available': 3,
                'is_available': True
            },
            {
                'name': 'Phacoemulsification Machine',
                'equipment_type': 'instrument',
                'description': 'Cataract extraction system with IOL insertion capability',
                'quantity_available': 1,
                'is_available': True
            },
            
            # Monitors
            {
                'name': 'Multi-Parameter Patient Monitor',
                'equipment_type': 'monitor',
                'description': 'Monitors ECG, BP, SpO2, temperature, and respiratory rate',
                'quantity_available': 8,
                'is_available': True
            },
            {
                'name': 'Defibrillator',
                'equipment_type': 'monitor',
                'description': 'Biphasic defibrillator with pacing capability',
                'quantity_available': 4,
                'is_available': True
            },
            {
                'name': 'Cardiac Monitor',
                'equipment_type': 'monitor',
                'description': 'Advanced cardiac monitoring with 12-lead ECG',
                'quantity_available': 3,
                'is_available': True
            },
            {
                'name': 'Fetal Monitor',
                'equipment_type': 'monitor',
                'description': 'Cardiotocography (CTG) monitor for fetal heart rate and contractions',
                'quantity_available': 3,
                'is_available': True
            },
            
            # Anesthesia
            {
                'name': 'Anesthesia Workstation',
                'equipment_type': 'anesthesia',
                'description': 'Complete anesthesia machine with ventilator and vaporizers',
                'quantity_available': 7,
                'is_available': True
            },
            {
                'name': 'Ventilator',
                'equipment_type': 'anesthesia',
                'description': 'Intensive care ventilator with multiple modes',
                'quantity_available': 5,
                'is_available': True
            },
            {
                'name': 'Ultrasound Machine',
                'equipment_type': 'imaging',
                'description': 'Portable ultrasound for surgical guidance and vascular access',
                'quantity_available': 3,
                'is_available': True
            },
            {
                'name': 'C-Arm X-Ray',
                'equipment_type': 'imaging',
                'description': 'Mobile fluoroscopy unit for real-time imaging',
                'quantity_available': 2,
                'is_available': True
            },
            {
                'name': 'Surgical Lights',
                'equipment_type': 'other',
                'description': 'LED surgical lights with adjustable intensity',
                'quantity_available': 10,
                'is_available': True
            },
            {
                'name': 'Electrosurgical Generator',
                'equipment_type': 'instrument',
                'description': 'Advanced ESU for cutting, coagulation, and vessel sealing',
                'quantity_available': 6,
                'is_available': True
            },
            {
                'name': 'Infant Warmer',
                'equipment_type': 'other',
                'description': 'Radiant warmer for newborn stabilization',
                'quantity_available': 2,
                'is_available': True
            },
            {
                'name': 'Blood Warmer',
                'equipment_type': 'other',
                'description': 'Rapid infusion blood and fluid warming device',
                'quantity_available': 4,
                'is_available': True
            },
            {
                'name': 'Suction Machine',
                'equipment_type': 'other',
                'description': 'High-powered surgical suction system',
                'quantity_available': 8,
                'is_available': True
            },
            {
                'name': 'Tourniquet System',
                'equipment_type': 'other',
                'description': 'Pneumatic tourniquet system for limb surgeries',
                'quantity_available': 3,
                'is_available': True
            },
            {
                'name': 'Diathermy Machine',
                'equipment_type': 'instrument',
                'description': 'High-frequency electrosurgical unit',
                'quantity_available': 5,
                'is_available': True
            }
        ]

        for equipment_data in equipment_list:
            if skip_existing:
                equipment, created = SurgicalEquipment.objects.get_or_create(
                    name=equipment_data['name'],
                    defaults=equipment_data
                )
            else:
                equipment, created = SurgicalEquipment.objects.update_or_create(
                    name=equipment_data['name'],
                    defaults=equipment_data
                )
            
            status = 'Created' if created else 'Updated' if not skip_existing else 'Exists'
            self.stdout.write(f'  {status}: {equipment.name}')

    def assign_equipment_to_surgery_types(self, skip_existing):
        """Assign required equipment to surgery types"""
        self.stdout.write('\nAssigning Equipment to Surgery Types...')
        
        # Define equipment assignments for each surgery type
        assignments = {
            'Appendectomy': [
                {'name': 'Laparoscope', 'qty': 1, 'mandatory': True, 'notes': 'Primary visualization'},
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'For dissection and hemostasis'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'General anesthesia'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Continuous monitoring'},
                {'name': 'Surgical Lights', 'qty': 1, 'mandatory': False, 'notes': 'Optimal visualization'},
                {'name': 'Suction Machine', 'qty': 1, 'mandatory': True, 'notes': 'Fluid evacuation'},
            ],
            'Cholecystectomy': [
                {'name': 'Laparoscope', 'qty': 1, 'mandatory': True, 'notes': 'Laparoscopic approach'},
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Critical for gallbladder removal'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'General anesthesia required'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Vital signs monitoring'},
                {'name': 'C-Arm X-Ray', 'qty': 1, 'mandatory': False, 'notes': 'Intraoperative cholangiogram if needed'},
                {'name': 'Suction Machine', 'qty': 1, 'mandatory': True, 'notes': 'Smoke and fluid evacuation'},
            ],
            'Hernia Repair': [
                {'name': 'Laparoscope', 'qty': 1, 'mandatory': False, 'notes': 'For laparoscopic repair'},
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Tissue dissection'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': False, 'notes': 'For general anesthesia (optional - local possible)'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Patient monitoring'},
                {'name': 'Surgical Lights', 'qty': 1, 'mandatory': True, 'notes': 'Essential for field visualization'},
            ],
            'Cesarean Section': [
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'Spinal/epidural or general anesthesia'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Maternal monitoring'},
                {'name': 'Fetal Monitor', 'qty': 1, 'mandatory': False, 'notes': 'Pre-operative fetal assessment'},
                {'name': 'Infant Warmer', 'qty': 1, 'mandatory': True, 'notes': 'Newborn stabilization'},
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Hemostasis'},
                {'name': 'Suction Machine', 'qty': 1, 'mandatory': True, 'notes': 'Fluid management'},
                {'name': 'Blood Warmer', 'qty': 1, 'mandatory': False, 'notes': 'If transfusion needed'},
            ],
            'Cardiac Bypass': [
                {'name': 'Cardiac Monitor', 'qty': 2, 'mandatory': True, 'notes': 'Continuous cardiac monitoring'},
                {'name': 'Defibrillator', 'qty': 1, 'mandatory': True, 'notes': 'Emergency resuscitation'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'Full anesthesia support'},
                {'name': 'Ventilator', 'qty': 1, 'mandatory': True, 'notes': 'Mechanical ventilation'},
                {'name': 'Blood Warmer', 'qty': 2, 'mandatory': True, 'notes': 'Cardiopulmonary bypass'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 2, 'mandatory': True, 'notes': 'Extensive monitoring'},
                {'name': 'Surgical Lights', 'qty': 2, 'mandatory': True, 'notes': 'Optimal field illumination'},
            ],
            'Knee Replacement': [
                {'name': 'Surgical Drill', 'qty': 1, 'mandatory': True, 'notes': 'Bone preparation'},
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Soft tissue management'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'Regional or general anesthesia'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Patient monitoring'},
                {'name': 'C-Arm X-Ray', 'qty': 1, 'mandatory': True, 'notes': 'Intraoperative imaging'},
                {'name': 'Tourniquet System', 'qty': 1, 'mandatory': True, 'notes': 'Bloodless field'},
                {'name': 'Surgical Lights', 'qty': 1, 'mandatory': True, 'notes': 'Visualization'},
            ],
            'Cataract Surgery': [
                {'name': 'Phacoemulsification Machine', 'qty': 1, 'mandatory': True, 'notes': 'Lens extraction'},
                {'name': 'Surgical Microscope', 'qty': 1, 'mandatory': True, 'notes': 'Essential magnification'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': False, 'notes': 'Topical/local anesthesia preferred'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': False, 'notes': 'Basic monitoring'},
                {'name': 'Surgical Lights', 'qty': 1, 'mandatory': True, 'notes': 'Red-free filter lighting'},
            ],
            'Tonsillectomy': [
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Coblation or cautery'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'General anesthesia'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Pediatric monitoring'},
                {'name': 'Suction Machine', 'qty': 2, 'mandatory': True, 'notes': 'Blood and tissue evacuation'},
                {'name': 'Surgical Lights', 'qty': 1, 'mandatory': True, 'notes': 'Headlight or overhead'},
            ],
            'Thyroidectomy': [
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Nerve monitoring capable'},
                {'name': 'Surgical Microscope', 'qty': 1, 'mandatory': False, 'notes': 'For nerve identification'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'General anesthesia'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Continuous monitoring'},
                {'name': 'Surgical Lights', 'qty': 1, 'mandatory': True, 'notes': 'Neck field illumination'},
                {'name': 'Suction Machine', 'qty': 1, 'mandatory': True, 'notes': 'Fluid management'},
            ],
            'Laparotomy': [
                {'name': 'Electrocautery Unit', 'qty': 1, 'mandatory': True, 'notes': 'Major vessel control'},
                {'name': 'Anesthesia Workstation', 'qty': 1, 'mandatory': True, 'notes': 'General anesthesia'},
                {'name': 'Multi-Parameter Patient Monitor', 'qty': 1, 'mandatory': True, 'notes': 'Hemodynamic monitoring'},
                {'name': 'Blood Warmer', 'qty': 1, 'mandatory': False, 'notes': 'If massive transfusion'},
                {'name': 'Surgical Lights', 'qty': 2, 'mandatory': True, 'notes': 'Large field coverage'},
                {'name': 'Suction Machine', 'qty': 2, 'mandatory': True, 'notes': 'High-volume suction'},
                {'name': 'Defibrillator', 'qty': 1, 'mandatory': False, 'notes': 'Emergency backup'},
            ],
        }

        created_count = 0
        skipped_count = 0
        
        for surgery_name, equipment_list in assignments.items():
            try:
                surgery_type = SurgeryType.objects.get(name=surgery_name)
                
                for equip_data in equipment_list:
                    try:
                        equipment = SurgicalEquipment.objects.get(name=equip_data['name'])
                        
                        if skip_existing:
                            assignment, created = SurgeryTypeEquipment.objects.get_or_create(
                                surgery_type=surgery_type,
                                equipment=equipment,
                                defaults={
                                    'quantity_required': equip_data['qty'],
                                    'is_mandatory': equip_data['mandatory'],
                                    'notes': equip_data['notes']
                                }
                            )
                        else:
                            assignment, created = SurgeryTypeEquipment.objects.update_or_create(
                                surgery_type=surgery_type,
                                equipment=equipment,
                                defaults={
                                    'quantity_required': equip_data['qty'],
                                    'is_mandatory': equip_data['mandatory'],
                                    'notes': equip_data['notes']
                                }
                            )
                        
                        if created:
                            created_count += 1
                            self.stdout.write(f'  Assigned: {equipment.name} to {surgery_type.name}')
                        else:
                            skipped_count += 1
                            
                    except SurgicalEquipment.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'  Equipment not found: {equip_data["name"]}')
                        )
                        
            except SurgeryType.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  Surgery type not found: {surgery_name}')
                )
        
        self.stdout.write(f'  Created {created_count} new assignments')
        if skipped_count > 0:
            self.stdout.write(f'  Skipped {skipped_count} existing assignments')
