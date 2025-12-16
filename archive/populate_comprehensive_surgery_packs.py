"""
Comprehensive script to populate all surgery packs with detailed medications and consumables
Run with: python manage.py shell < populate_comprehensive_surgery_packs.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Medication, MedicationCategory, MedicalPack, MedicalPackItem
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

def create_medications():
    """Create all necessary medications and consumables"""
    
    print("\n📦 Creating Medications and Consumables...")
    
    # Get or create categories
    anesthetic_cat, _ = MedicationCategory.objects.get_or_create(
        name='Anesthetics',
        defaults={'description': 'Anesthetic medications'}
    )
    antibiotic_cat, _ = MedicationCategory.objects.get_or_create(
        name='Antibiotics',
        defaults={'description': 'Antibiotic medications'}
    )
    analgesic_cat, _ = MedicationCategory.objects.get_or_create(
        name='Analgesics',
        defaults={'description': 'Pain relief medications'}
    )
    antiseptic_cat, _ = MedicationCategory.objects.get_or_create(
        name='Antiseptics',
        defaults={'description': 'Antiseptic solutions'}
    )
    consumable_cat, _ = MedicationCategory.objects.get_or_create(
        name='Consumables',
        defaults={'description': 'Medical consumables and supplies'}
    )
    iv_fluids_cat, _ = MedicationCategory.objects.get_or_create(
        name='IV Fluids',
        defaults={'description': 'Intravenous fluids'}
    )
    antiemetic_cat, _ = MedicationCategory.objects.get_or_create(
        name='Antiemetics',
        defaults={'description': 'Anti-nausea medications'}
    )
    muscle_relaxant_cat, _ = MedicationCategory.objects.get_or_create(
        name='Muscle Relaxants',
        defaults={'description': 'Muscle relaxant medications'}
    )
    
    # Comprehensive medication list
    medications = [
        # Anesthetics
        ('Lidocaine', '2%', 'injection', anesthetic_cat, Decimal('50.00'), 'Local anesthetic'),
        ('Bupivacaine', '0.5%', 'injection', anesthetic_cat, Decimal('80.00'), 'Long-acting local anesthetic'),
        ('Propofol', '10mg/ml', 'injection', anesthetic_cat, Decimal('150.00'), 'General anesthetic'),
        ('Ketamine', '50mg/ml', 'injection', anesthetic_cat, Decimal('120.00'), 'Dissociative anesthetic'),
        ('Sevoflurane', '250ml', 'inhalation', anesthetic_cat, Decimal('200.00'), 'Inhalation anesthetic'),
        
        # Antibiotics
        ('Ceftriaxone', '1g', 'injection', antibiotic_cat, Decimal('100.00'), 'Broad-spectrum antibiotic'),
        ('Metronidazole', '500mg', 'injection', antibiotic_cat, Decimal('60.00'), 'Antibiotic for anaerobic bacteria'),
        ('Gentamicin', '80mg', 'injection', antibiotic_cat, Decimal('70.00'), 'Aminoglycoside antibiotic'),
        ('Cefazolin', '1g', 'injection', antibiotic_cat, Decimal('90.00'), 'Prophylactic antibiotic'),
        ('Amoxicillin-Clavulanate', '625mg', 'tablet', antibiotic_cat, Decimal('30.00'), 'Oral antibiotic'),
        
        # Analgesics
        ('Morphine', '10mg/ml', 'injection', analgesic_cat, Decimal('80.00'), 'Opioid analgesic'),
        ('Fentanyl', '50mcg/ml', 'injection', analgesic_cat, Decimal('100.00'), 'Potent opioid analgesic'),
        ('Tramadol', '50mg/ml', 'injection', analgesic_cat, Decimal('60.00'), 'Moderate opioid analgesic'),
        ('Paracetamol', '1g', 'injection', analgesic_cat, Decimal('40.00'), 'Non-opioid analgesic'),
        ('Diclofenac', '75mg', 'injection', analgesic_cat, Decimal('50.00'), 'NSAID analgesic'),
        ('Ibuprofen', '400mg', 'tablet', analgesic_cat, Decimal('20.00'), 'Oral NSAID'),
        
        # Antiseptics
        ('Povidone Iodine', '10%', 'solution', antiseptic_cat, Decimal('30.00'), 'Antiseptic solution'),
        ('Chlorhexidine', '4%', 'solution', antiseptic_cat, Decimal('40.00'), 'Antiseptic solution'),
        ('Alcohol Swabs', 'Pack of 100', 'swab', antiseptic_cat, Decimal('25.00'), 'Alcohol prep pads'),
        
        # IV Fluids
        ('Normal Saline', '1000ml', 'infusion', iv_fluids_cat, Decimal('50.00'), '0.9% NaCl solution'),
        ('Ringer Lactate', '1000ml', 'infusion', iv_fluids_cat, Decimal('55.00'), 'Lactated Ringer solution'),
        ('Dextrose 5%', '1000ml', 'infusion', iv_fluids_cat, Decimal('50.00'), '5% Dextrose solution'),
        
        # Antiemetics
        ('Ondansetron', '4mg', 'injection', antiemetic_cat, Decimal('70.00'), 'Anti-nausea medication'),
        ('Metoclopramide', '10mg', 'injection', antiemetic_cat, Decimal('40.00'), 'Anti-nausea medication'),
        
        # Muscle Relaxants
        ('Atracurium', '10mg/ml', 'injection', muscle_relaxant_cat, Decimal('90.00'), 'Muscle relaxant'),
        ('Rocuronium', '10mg/ml', 'injection', muscle_relaxant_cat, Decimal('100.00'), 'Muscle relaxant'),
        
        # Consumables and Supplies
        ('Surgical Gloves', 'Size 7.5', 'pair', consumable_cat, Decimal('15.00'), 'Sterile surgical gloves'),
        ('Gauze Pads', '4x4 inch', 'pack', consumable_cat, Decimal('10.00'), 'Sterile gauze pads'),
        ('Suture Material', '2-0 Vicryl', 'pack', consumable_cat, Decimal('80.00'), 'Absorbable suture'),
        ('Suture Material Silk', '2-0 Silk', 'pack', consumable_cat, Decimal('70.00'), 'Non-absorbable suture'),
        ('Scalpel Blade', 'No. 15', 'piece', consumable_cat, Decimal('20.00'), 'Surgical blade'),
        ('Surgical Drapes', 'Sterile', 'pack', consumable_cat, Decimal('50.00'), 'Sterile surgical drapes'),
        ('Surgical Mask', 'Disposable', 'piece', consumable_cat, Decimal('5.00'), 'Surgical face mask'),
        ('Surgical Gown', 'Sterile', 'piece', consumable_cat, Decimal('40.00'), 'Sterile surgical gown'),
        ('Catheter Foley', '16Fr', 'piece', consumable_cat, Decimal('60.00'), 'Urinary catheter'),
        ('IV Cannula', '18G', 'piece', consumable_cat, Decimal('30.00'), 'Intravenous cannula'),
        ('Syringe', '10ml', 'piece', consumable_cat, Decimal('5.00'), 'Disposable syringe'),
        ('Needle', '21G', 'piece', consumable_cat, Decimal('3.00'), 'Hypodermic needle'),
        ('Bandage', 'Elastic 4 inch', 'roll', consumable_cat, Decimal('15.00'), 'Elastic bandage'),
        ('Cotton Wool', '500g', 'pack', consumable_cat, Decimal('20.00'), 'Absorbent cotton'),
        ('Adhesive Tape', '2 inch', 'roll', consumable_cat, Decimal('10.00'), 'Medical adhesive tape'),
        ('Nasogastric Tube', '16Fr', 'piece', consumable_cat, Decimal('50.00'), 'NG tube'),
        ('Oxygen Mask', 'Adult', 'piece', consumable_cat, Decimal('25.00'), 'Oxygen delivery mask'),
        ('Surgical Sponges', 'Pack of 10', 'pack', consumable_cat, Decimal('30.00'), 'Surgical sponges'),
        ('Electrocautery Pad', 'Disposable', 'piece', consumable_cat, Decimal('40.00'), 'Grounding pad'),
        ('Specimen Container', 'Sterile', 'piece', consumable_cat, Decimal('15.00'), 'Sample collection container'),
    ]
    
    created_count = 0
    for name, strength, dosage_form, category, price, description in medications:
        med, created = Medication.objects.get_or_create(
            name=name,
            strength=strength,
            defaults={
                'dosage_form': dosage_form,
                'category': category,
                'price': price,
                'description': description,
                'is_active': True,
                'reorder_level': 20
            }
        )
        if created:
            created_count += 1
            print(f"   ✓ Created: {name} ({strength})")
    
    print(f"\n✅ Created {created_count} new medications/consumables")
    return created_count

def create_surgery_packs():
    """Create comprehensive surgery packs with all necessary items"""
    
    print("\n🏥 Creating Surgery Packs...")
    
    # Get a user for created_by field
    user = User.objects.filter(is_staff=True).first()
    if not user:
        user = User.objects.first()
    
    # Define comprehensive surgery packs
    surgery_packs = [
        {
            'name': 'Appendectomy Surgery Pack',
            'pack_type': 'surgery',
            'surgery_type': 'appendectomy',
            'risk_level': 'medium',
            'description': 'Comprehensive pack for appendectomy procedures',
            'items': [
                # Anesthetics
                ('Propofol', 2),
                ('Fentanyl', 2),
                ('Lidocaine', 2),
                ('Atracurium', 1),
                # Antibiotics
                ('Ceftriaxone', 2),
                ('Metronidazole', 2),
                # Analgesics
                ('Morphine', 2),
                ('Paracetamol', 3),
                ('Diclofenac', 2),
                # Antiseptics & IV Fluids
                ('Povidone Iodine', 2),
                ('Chlorhexidine', 1),
                ('Normal Saline', 3),
                ('Ringer Lactate', 2),
                # Antiemetics
                ('Ondansetron', 2),
                # Consumables
                ('Surgical Gloves', 6),
                ('Gauze Pads', 10),
                ('Suture Material', 3),
                ('Scalpel Blade', 3),
                ('Surgical Drapes', 2),
                ('Surgical Mask', 4),
                ('Surgical Gown', 3),
                ('Catheter Foley', 1),
                ('IV Cannula', 2),
                ('Syringe', 10),
                ('Needle', 10),
                ('Bandage', 2),
                ('Adhesive Tape', 2),
                ('Surgical Sponges', 5),
                ('Electrocautery Pad', 1),
                ('Specimen Container', 1),
            ]
        },
        {
            'name': 'Cholecystectomy Surgery Pack',
            'pack_type': 'surgery',
            'surgery_type': 'cholecystectomy',
            'risk_level': 'medium',
            'description': 'Comprehensive pack for gallbladder removal surgery',
            'items': [
                # Anesthetics
                ('Propofol', 3),
                ('Fentanyl', 3),
                ('Sevoflurane', 1),
                ('Rocuronium', 2),
                # Antibiotics
                ('Ceftriaxone', 3),
                ('Metronidazole', 2),
                ('Gentamicin', 1),
                # Analgesics
                ('Morphine', 3),
                ('Tramadol', 2),
                ('Paracetamol', 4),
                ('Diclofenac', 3),
                # Antiseptics & IV Fluids
                ('Povidone Iodine', 3),
                ('Chlorhexidine', 2),
                ('Normal Saline', 4),
                ('Ringer Lactate', 3),
                # Antiemetics
                ('Ondansetron', 3),
                ('Metoclopramide', 2),
                # Consumables
                ('Surgical Gloves', 8),
                ('Gauze Pads', 15),
                ('Suture Material', 4),
                ('Suture Material Silk', 2),
                ('Scalpel Blade', 4),
                ('Surgical Drapes', 3),
                ('Surgical Mask', 5),
                ('Surgical Gown', 4),
                ('Catheter Foley', 1),
                ('IV Cannula', 3),
                ('Nasogastric Tube', 1),
                ('Syringe', 15),
                ('Needle', 15),
                ('Bandage', 3),
                ('Adhesive Tape', 3),
                ('Surgical Sponges', 8),
                ('Electrocautery Pad', 1),
                ('Specimen Container', 1),
            ]
        },
        {
            'name': 'Hernia Repair Surgery Pack',
            'pack_type': 'surgery',
            'surgery_type': 'hernia_repair',
            'risk_level': 'low',
            'description': 'Comprehensive pack for hernia repair procedures',
            'items': [
                # Anesthetics
                ('Propofol', 2),
                ('Lidocaine', 3),
                ('Bupivacaine', 2),
                ('Fentanyl', 2),
                # Antibiotics
                ('Cefazolin', 2),
                ('Ceftriaxone', 1),
                # Analgesics
                ('Morphine', 2),
                ('Tramadol', 2),
                ('Paracetamol', 3),
                ('Ibuprofen', 3),
                # Antiseptics & IV Fluids
                ('Povidone Iodine', 2),
                ('Chlorhexidine', 1),
                ('Alcohol Swabs', 2),
                ('Normal Saline', 3),
                ('Ringer Lactate', 2),
                # Antiemetics
                ('Ondansetron', 2),
                # Consumables
                ('Surgical Gloves', 6),
                ('Gauze Pads', 12),
                ('Suture Material', 4),
                ('Suture Material Silk', 3),
                ('Scalpel Blade', 3),
                ('Surgical Drapes', 2),
                ('Surgical Mask', 4),
                ('Surgical Gown', 3),
                ('IV Cannula', 2),
                ('Syringe', 12),
                ('Needle', 12),
                ('Bandage', 3),
                ('Cotton Wool', 1),
                ('Adhesive Tape', 2),
                ('Surgical Sponges', 6),
                ('Electrocautery Pad', 1),
            ]
        },
        {
            'name': 'Cesarean Section Surgery Pack',
            'pack_type': 'surgery',
            'surgery_type': 'cesarean_section',
            'risk_level': 'high',
            'description': 'Comprehensive pack for cesarean section delivery',
            'items': [
                # Anesthetics
                ('Bupivacaine', 3),
                ('Lidocaine', 2),
                ('Fentanyl', 3),
                ('Propofol', 2),
                # Antibiotics
                ('Ceftriaxone', 3),
                ('Metronidazole', 2),
                ('Gentamicin', 2),
                # Analgesics
                ('Morphine', 3),
                ('Tramadol', 3),
                ('Paracetamol', 5),
                ('Diclofenac', 3),
                # Antiseptics & IV Fluids
                ('Povidone Iodine', 3),
                ('Chlorhexidine', 2),
                ('Normal Saline', 5),
                ('Ringer Lactate', 4),
                ('Dextrose 5%', 2),
                # Antiemetics
                ('Ondansetron', 3),
                ('Metoclopramide', 2),
                # Consumables
                ('Surgical Gloves', 10),
                ('Gauze Pads', 20),
                ('Suture Material', 5),
                ('Suture Material Silk', 3),
                ('Scalpel Blade', 4),
                ('Surgical Drapes', 4),
                ('Surgical Mask', 6),
                ('Surgical Gown', 5),
                ('Catheter Foley', 1),
                ('IV Cannula', 3),
                ('Syringe', 20),
                ('Needle', 20),
                ('Bandage', 4),
                ('Cotton Wool', 2),
                ('Adhesive Tape', 4),
                ('Surgical Sponges', 10),
                ('Electrocautery Pad', 1),
                ('Oxygen Mask', 1),
            ]
        },
        {
            'name': 'Tonsillectomy Surgery Pack',
            'pack_type': 'surgery',
            'surgery_type': 'tonsillectomy',
            'risk_level': 'low',
            'description': 'Comprehensive pack for tonsil removal surgery',
            'items': [
                # Anesthetics
                ('Propofol', 2),
                ('Sevoflurane', 1),
                ('Fentanyl', 2),
                ('Lidocaine', 2),
                # Antibiotics
                ('Ceftriaxone', 2),
                ('Amoxicillin-Clavulanate', 3),
                # Analgesics
                ('Morphine', 2),
                ('Paracetamol', 4),
                ('Ibuprofen', 4),
                # Antiseptics & IV Fluids
                ('Povidone Iodine', 1),
                ('Chlorhexidine', 1),
                ('Normal Saline', 3),
                ('Ringer Lactate', 2),
                # Antiemetics
                ('Ondansetron', 2),
                ('Metoclopramide', 1),
                # Consumables
                ('Surgical Gloves', 6),
                ('Gauze Pads', 10),
                ('Suture Material', 2),
                ('Scalpel Blade', 2),
                ('Surgical Drapes', 2),
                ('Surgical Mask', 4),
                ('Surgical Gown', 3),
                ('IV Cannula', 2),
                ('Syringe', 10),
                ('Needle', 10),
                ('Bandage', 2),
                ('Cotton Wool', 1),
                ('Adhesive Tape', 2),
                ('Surgical Sponges', 5),
                ('Oxygen Mask', 1),
            ]
        },
    ]

    packs_created = 0
    items_created = 0

    for pack_data in surgery_packs:
        # Check if pack already exists
        existing_pack = MedicalPack.objects.filter(
            name=pack_data['name'],
            pack_type=pack_data['pack_type']
        ).first()

        if existing_pack:
            print(f"\n   ⚠ Pack already exists: {pack_data['name']}")
            # Delete existing items and recreate
            existing_pack.items.all().delete()
            pack = existing_pack
            # Update pack details
            pack.description = pack_data['description']
            pack.surgery_type = pack_data.get('surgery_type')
            pack.labor_type = pack_data.get('labor_type')
            pack.risk_level = pack_data['risk_level']
            pack.save()
            print(f"   ↻ Updating pack items...")
        else:
            # Create new pack using get_or_create to avoid total_cost issue
            pack, created = MedicalPack.objects.get_or_create(
                name=pack_data['name'],
                pack_type=pack_data['pack_type'],
                defaults={
                    'description': pack_data['description'],
                    'surgery_type': pack_data.get('surgery_type'),
                    'labor_type': pack_data.get('labor_type'),
                    'risk_level': pack_data['risk_level'],
                    'requires_approval': False,
                    'is_active': True
                }
            )
            if created:
                packs_created += 1
                print(f"\n   ✓ Created pack: {pack_data['name']}")
            else:
                print(f"\n   ⚠ Pack found: {pack_data['name']}")

        # Add items to pack
        for item_name, quantity in pack_data['items']:
            # Find medication by name (ignoring strength for matching)
            medication = Medication.objects.filter(name=item_name).first()

            if medication:
                # Determine item type
                item_type = 'medication'
                is_critical = True

                if medication.category.name == 'Consumables':
                    item_type = 'supply'
                    is_critical = False
                elif medication.category.name in ['Anesthetics', 'Antibiotics']:
                    is_critical = True

                # Create pack item
                pack_item, created = MedicalPackItem.objects.get_or_create(
                    pack=pack,
                    medication=medication,
                    defaults={
                        'quantity': quantity,
                        'item_type': item_type,
                        'is_critical': is_critical,
                        'is_optional': False,
                        'order': 0
                    }
                )

                if created:
                    items_created += 1
                else:
                    # Update quantity if item already exists
                    pack_item.quantity = quantity
                    pack_item.save()
            else:
                print(f"      ⚠ Medication not found: {item_name}")

    print(f"\n✅ Created/Updated {packs_created} packs with {items_created} items")
    return packs_created, items_created


def main():
    """Main function to populate all surgery packs"""
    print("=" * 70)
    print("🏥 COMPREHENSIVE SURGERY PACKS POPULATION SCRIPT")
    print("=" * 70)

    # Step 1: Create medications
    meds_created = create_medications()

    # Step 2: Create surgery packs
    packs_created, items_created = create_surgery_packs()

    print("\n" + "=" * 70)
    print("✅ POPULATION COMPLETE!")
    print("=" * 70)
    print(f"   📦 Medications Created: {meds_created}")
    print(f"   🏥 Surgery Packs Created/Updated: {packs_created}")
    print(f"   📋 Pack Items Created: {items_created}")
    print("=" * 70)

    # Display summary of packs
    print("\n📊 SURGERY PACKS SUMMARY:")
    print("-" * 70)

    all_packs = MedicalPack.objects.filter(pack_type='surgery', is_active=True)
    for pack in all_packs:
        item_count = pack.items.count()
        total_cost = pack.get_total_cost()
        print(f"\n   {pack.name}")
        print(f"   └─ Type: {pack.get_surgery_type_display() if pack.surgery_type else 'General'}")
        print(f"   └─ Risk Level: {pack.get_risk_level_display()}")
        print(f"   └─ Items: {item_count}")
        print(f"   └─ Total Cost: ₦{total_cost:,.2f}")

    print("\n" + "=" * 70)
    print("🎉 All surgery packs are now ready for use!")
    print("=" * 70)


if __name__ == '__main__':
    main()


