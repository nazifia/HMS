from django.core.management.base import BaseCommand
from django.db import transaction
from pharmacy.models import MedicalPack, PackItem, Medication, MedicationCategory
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate predefined medical packs for surgeries and labor procedures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing packs before populating'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing medical packs...')
            MedicalPack.objects.all().delete()

        self.stdout.write('Creating medication categories if they don\'t exist...')
        self.create_medication_categories()
        
        self.stdout.write('Creating medications if they don\'t exist...')
        self.create_medications()
        
        self.stdout.write('Creating surgical packs...')
        self.create_surgical_packs()
        
        self.stdout.write('Creating labor/delivery packs...')
        self.create_labor_packs()
        
        self.stdout.write('Creating emergency packs...')
        self.create_emergency_packs()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated medical packs!'))

    def create_medication_categories(self):
        """Create necessary medication categories"""
        categories = [
            ('Anesthetics', 'Medications for anesthesia'),
            ('Antibiotics', 'Anti-bacterial medications'),
            ('Analgesics', 'Pain relief medications'),
            ('Antiseptics', 'Antiseptic solutions and preparations'),
            ('Surgical Supplies', 'Surgical consumables and supplies'),
            ('Obstetric Medications', 'Medications for pregnancy and childbirth'),
            ('Emergency Medications', 'Emergency and resuscitation medications'),
            ('IV Solutions', 'Intravenous fluids and solutions'),
            ('Consumables', 'Medical consumables and disposables'),
        ]
        
        for name, description in categories:
            MedicationCategory.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )

    def create_medications(self):
        """Create common medications used in surgical and labor packs"""
        
        # Get categories
        anesthetics = MedicationCategory.objects.get(name='Anesthetics')
        antibiotics = MedicationCategory.objects.get(name='Antibiotics')
        analgesics = MedicationCategory.objects.get(name='Analgesics')
        antiseptics = MedicationCategory.objects.get(name='Antiseptics')
        surgical_supplies = MedicationCategory.objects.get(name='Surgical Supplies')
        obstetric = MedicationCategory.objects.get(name='Obstetric Medications')
        emergency = MedicationCategory.objects.get(name='Emergency Medications')
        iv_solutions = MedicationCategory.objects.get(name='IV Solutions')
        consumables = MedicationCategory.objects.get(name='Consumables')
        
        medications = [
            # Anesthetics
            ('Lidocaine', '1%', 'injection', anesthetics, Decimal('15.00'), 'Local anesthetic injection'),
            ('Bupivacaine', '0.5%', 'injection', anesthetics, Decimal('25.00'), 'Long-acting local anesthetic'),
            ('Propofol', '10mg/ml', 'injection', anesthetics, Decimal('45.00'), 'General anesthetic'),
            ('Ketamine', '50mg/ml', 'injection', anesthetics, Decimal('35.00'), 'Dissociative anesthetic'),
            
            # Antibiotics
            ('Ceftriaxone', '1g', 'injection', antibiotics, Decimal('12.00'), 'Third-generation cephalosporin'),
            ('Metronidazole', '500mg', 'injection', antibiotics, Decimal('8.00'), 'Antiprotozoal and antibacterial'),
            ('Ampicillin', '1g', 'injection', antibiotics, Decimal('10.00'), 'Broad-spectrum penicillin'),
            ('Gentamicin', '80mg', 'injection', antibiotics, Decimal('6.00'), 'Aminoglycoside antibiotic'),
            
            # Analgesics
            ('Morphine', '10mg/ml', 'injection', analgesics, Decimal('20.00'), 'Opioid analgesic'),
            ('Tramadol', '100mg', 'injection', analgesics, Decimal('15.00'), 'Synthetic opioid'),
            ('Diclofenac', '75mg', 'injection', analgesics, Decimal('5.00'), 'NSAID'),
            ('Paracetamol', '1g', 'injection', analgesics, Decimal('8.00'), 'Non-opioid analgesic'),
            
            # Antiseptics
            ('Povidone Iodine', '10%', 'solution', antiseptics, Decimal('12.00'), 'Antiseptic solution'),
            ('Chlorhexidine', '4%', 'solution', antiseptics, Decimal('15.00'), 'Antiseptic scrub'),
            ('Alcohol Swabs', '70%', 'pad', antiseptics, Decimal('2.00'), 'Alcohol antiseptic pads'),
            
            # Surgical Supplies
            ('Surgical Gloves', 'Size 7', 'pair', surgical_supplies, Decimal('3.00'), 'Sterile surgical gloves'),
            ('Surgical Mask', 'N95', 'piece', surgical_supplies, Decimal('2.00'), 'Protective face mask'),
            ('Gauze Pads', '4x4', 'piece', surgical_supplies, Decimal('1.00'), 'Sterile gauze pads'),
            ('Surgical Tape', '1 inch', 'roll', surgical_supplies, Decimal('4.00'), 'Medical adhesive tape'),
            ('Suture Material', '3-0', 'pack', surgical_supplies, Decimal('25.00'), 'Absorbable sutures'),
            ('Scalpel Blade', 'No. 15', 'piece', surgical_supplies, Decimal('5.00'), 'Surgical scalpel blade'),
            ('Needle Holder', '6 inch', 'piece', surgical_supplies, Decimal('45.00'), 'Surgical needle holder'),
            
            # Obstetric Medications
            ('Oxytocin', '10IU', 'injection', obstetric, Decimal('8.00'), 'Uterine contractant'),
            ('Ergometrine', '0.5mg', 'injection', obstetric, Decimal('6.00'), 'Ergot alkaloid'),
            ('Magnesium Sulfate', '50%', 'injection', obstetric, Decimal('10.00'), 'Anticonvulsant'),
            ('Nifedipine', '20mg', 'tablet', obstetric, Decimal('4.00'), 'Calcium channel blocker'),
            
            # Emergency Medications
            ('Epinephrine', '1:1000', 'injection', emergency, Decimal('12.00'), 'Emergency medication'),
            ('Atropine', '1mg', 'injection', emergency, Decimal('8.00'), 'Anticholinergic'),
            ('Furosemide', '20mg', 'injection', emergency, Decimal('6.00'), 'Loop diuretic'),
            
            # IV Solutions
            ('Normal Saline', '1000ml', 'bag', iv_solutions, Decimal('15.00'), '0.9% sodium chloride'),
            ('Ringer\'s Lactate', '1000ml', 'bag', iv_solutions, Decimal('18.00'), 'Balanced crystalloid'),
            ('Dextrose 5%', '1000ml', 'bag', iv_solutions, Decimal('16.00'), '5% dextrose in water'),
            
            # Consumables
            ('Urinary Catheter', '16Fr', 'piece', consumables, Decimal('25.00'), 'Foley catheter'),
            ('IV Cannula', '18G', 'piece', consumables, Decimal('8.00'), 'Intravenous cannula'),
            ('Syringe', '10ml', 'piece', consumables, Decimal('1.00'), 'Disposable syringe'),
            ('Nasogastric Tube', '16Fr', 'piece', consumables, Decimal('15.00'), 'NG tube'),
            ('Oxygen Mask', 'Adult', 'piece', consumables, Decimal('12.00'), 'Non-rebreather mask'),
        ]
        
        for name, strength, dosage_form, category, price, description in medications:
            Medication.objects.get_or_create(
                name=name,
                strength=strength,
                defaults={
                    'dosage_form': dosage_form,
                    'category': category,
                    'price': price,
                    'description': description,
                    'is_active': True,
                    'reorder_level': 10
                }
            )

    def create_surgical_packs(self):
        """Create predefined surgical packs"""
        
        surgical_packs = [
            {
                'name': 'Appendectomy Basic Pack',
                'pack_type': 'surgery',
                'surgery_type': 'appendectomy',
                'risk_level': 'low',
                'description': 'Standard pack for appendectomy procedures',
                'items': [
                    ('Lidocaine', 2),
                    ('Ceftriaxone', 1),
                    ('Morphine', 1),
                    ('Povidone Iodine', 1),
                    ('Surgical Gloves', 3),
                    ('Gauze Pads', 10),
                    ('Suture Material', 2),
                    ('Scalpel Blade', 2),
                    ('Normal Saline', 2),
                ]
            },
            {
                'name': 'Cholecystectomy Pack',
                'pack_type': 'surgery',
                'surgery_type': 'cholecystectomy',
                'risk_level': 'medium',
                'description': 'Laparoscopic cholecystectomy pack',
                'items': [
                    ('Propofol', 1),
                    ('Bupivacaine', 2),
                    ('Ceftriaxone', 2),
                    ('Tramadol', 2),
                    ('Chlorhexidine', 1),
                    ('Surgical Gloves', 4),
                    ('Surgical Mask', 4),
                    ('Gauze Pads', 15),
                    ('Surgical Tape', 2),
                    ('Suture Material', 3),
                    ('IV Cannula', 2),
                    ('Normal Saline', 3),
                ]
            },
            {
                'name': 'Hernia Repair Pack',
                'pack_type': 'surgery',
                'surgery_type': 'hernia_repair',
                'risk_level': 'low',
                'description': 'Inguinal hernia repair pack',
                'items': [
                    ('Lidocaine', 3),
                    ('Ampicillin', 1),
                    ('Diclofenac', 2),
                    ('Povidone Iodine', 1),
                    ('Surgical Gloves', 3),
                    ('Gauze Pads', 12),
                    ('Suture Material', 2),
                    ('Scalpel Blade', 2),
                    ('Needle Holder', 1),
                    ('Normal Saline', 2),
                ]
            },
            {
                'name': 'Cesarean Section Pack',
                'pack_type': 'surgery',
                'surgery_type': 'cesarean_section',
                'risk_level': 'high',
                'description': 'Comprehensive C-section delivery pack',
                'items': [
                    ('Bupivacaine', 3),
                    ('Ceftriaxone', 2),
                    ('Morphine', 2),
                    ('Oxytocin', 2),
                    ('Chlorhexidine', 2),
                    ('Surgical Gloves', 6),
                    ('Surgical Mask', 4),
                    ('Gauze Pads', 20),
                    ('Surgical Tape', 3),
                    ('Suture Material', 4),
                    ('Urinary Catheter', 1),
                    ('IV Cannula', 2),
                    ('Normal Saline', 4),
                    ('Ringer\'s Lactate', 2),
                ]
            },
            {
                'name': 'General Surgery Pack',
                'pack_type': 'surgery',
                'surgery_type': 'general_surgery',
                'risk_level': 'medium',
                'description': 'Standard pack for general surgical procedures',
                'items': [
                    ('Lidocaine', 2),
                    ('Propofol', 1),
                    ('Ceftriaxone', 1),
                    ('Tramadol', 2),
                    ('Povidone Iodine', 1),
                    ('Surgical Gloves', 4),
                    ('Surgical Mask', 3),
                    ('Gauze Pads', 15),
                    ('Surgical Tape', 2),
                    ('Suture Material', 3),
                    ('Scalpel Blade', 3),
                    ('Normal Saline', 3),
                ]
            }
        ]
        
        self.create_packs(surgical_packs)

    def create_labor_packs(self):
        """Create predefined labor and delivery packs"""
        
        labor_packs = [
            {
                'name': 'Normal Delivery Pack',
                'pack_type': 'labor',
                'labor_type': 'normal_delivery',
                'risk_level': 'low',
                'description': 'Standard pack for normal vaginal delivery',
                'items': [
                    ('Lidocaine', 1),
                    ('Oxytocin', 2),
                    ('Povidone Iodine', 2),
                    ('Surgical Gloves', 4),
                    ('Gauze Pads', 15),
                    ('Surgical Tape', 2),
                    ('Episiotomy Kit', 1) if self.medication_exists('Episiotomy Kit') else ('Suture Material', 2),
                    ('Urinary Catheter', 1),
                    ('Normal Saline', 2),
                ]
            },
            {
                'name': 'Assisted Delivery Pack',
                'pack_type': 'labor',
                'labor_type': 'assisted_delivery',
                'risk_level': 'medium',
                'description': 'Pack for vacuum/forceps assisted delivery',
                'items': [
                    ('Lidocaine', 2),
                    ('Oxytocin', 2),
                    ('Ergometrine', 1),
                    ('Povidone Iodine', 2),
                    ('Surgical Gloves', 6),
                    ('Gauze Pads', 20),
                    ('Surgical Tape', 3),
                    ('Suture Material', 3),
                    ('Urinary Catheter', 1),
                    ('IV Cannula', 2),
                    ('Normal Saline', 3),
                    ('Ringer\'s Lactate', 2),
                ]
            },
            {
                'name': 'Labor Induction Pack',
                'pack_type': 'labor',
                'labor_type': 'labor_induction',
                'risk_level': 'medium',
                'description': 'Pack for labor induction procedures',
                'items': [
                    ('Oxytocin', 3),
                    ('Magnesium Sulfate', 1),
                    ('Nifedipine', 1),
                    ('Povidone Iodine', 1),
                    ('Surgical Gloves', 4),
                    ('Gauze Pads', 10),
                    ('Urinary Catheter', 1),
                    ('IV Cannula', 2),
                    ('Normal Saline', 3),
                    ('Dextrose 5%', 2),
                ]
            },
            {
                'name': 'Emergency Delivery Pack',
                'pack_type': 'labor',
                'labor_type': 'emergency_delivery',
                'risk_level': 'high',
                'description': 'Emergency obstetric pack',
                'items': [
                    ('Oxytocin', 3),
                    ('Ergometrine', 2),
                    ('Magnesium Sulfate', 2),
                    ('Epinephrine', 1),
                    ('Atropine', 1),
                    ('Chlorhexidine', 2),
                    ('Surgical Gloves', 8),
                    ('Surgical Mask', 4),
                    ('Gauze Pads', 25),
                    ('Surgical Tape', 4),
                    ('Suture Material', 4),
                    ('Urinary Catheter', 2),
                    ('IV Cannula', 3),
                    ('Normal Saline', 4),
                    ('Ringer\'s Lactate', 3),
                    ('Oxygen Mask', 2),
                ]
            }
        ]
        
        self.create_packs(labor_packs)

    def create_emergency_packs(self):
        """Create emergency medical packs"""
        
        emergency_packs = [
            {
                'name': 'Resuscitation Pack',
                'pack_type': 'emergency',
                'surgery_type': None,
                'labor_type': None,
                'risk_level': 'critical',
                'description': 'Emergency resuscitation pack',
                'items': [
                    ('Epinephrine', 3),
                    ('Atropine', 2),
                    ('Furosemide', 1),
                    ('Normal Saline', 4),
                    ('IV Cannula', 4),
                    ('Syringe', 10),
                    ('Oxygen Mask', 3),
                    ('Surgical Gloves', 6),
                ]
            }
        ]
        
        self.create_packs(emergency_packs)

    def create_packs(self, packs_data):
        """Create packs from data structure"""
        
        for pack_data in packs_data:
            with transaction.atomic():
                # Create the pack
                pack = MedicalPack.objects.create(
                    name=pack_data['name'],
                    description=pack_data['description'],
                    pack_type=pack_data['pack_type'],
                    surgery_type=pack_data.get('surgery_type'),
                    labor_type=pack_data.get('labor_type'),
                    risk_level=pack_data['risk_level'],
                    is_active=True,
                    requires_approval=pack_data['risk_level'] in ['high', 'critical']
                )
                
                # Add items to the pack
                for item_name, quantity in pack_data['items']:
                    try:
                        medication = Medication.objects.get(name=item_name)
                        PackItem.objects.create(
                            pack=pack,
                            medication=medication,
                            quantity=quantity,
                            item_type='medication' if medication.category.name not in ['Consumables', 'Surgical Supplies'] else 'consumable',
                            is_critical=pack_data['risk_level'] == 'critical',
                            order=0
                        )
                    except Medication.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Medication "{item_name}" not found for pack "{pack.name}"')
                        )
                
                # Update total cost
                pack.update_total_cost()
                
                self.stdout.write(f'Created pack: {pack.name}')

    def medication_exists(self, name):
        """Check if medication exists"""
        return Medication.objects.filter(name=name).exists()