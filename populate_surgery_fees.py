"""
Script to populate surgery type fees based on surgery complexity and risk level
"""

import os
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from theatre.models import SurgeryType


def populate_surgery_fees():
    """Populate fees for all surgery types based on risk level"""
    
    # Define fee structure based on risk level
    fee_structure = {
        'low': Decimal('50000.00'),      # ₦50,000 for low risk surgeries
        'medium': Decimal('100000.00'),  # ₦100,000 for medium risk surgeries
        'high': Decimal('200000.00'),    # ₦200,000 for high risk surgeries
        'critical': Decimal('350000.00'), # ₦350,000 for critical risk surgeries
    }
    
    # Custom fees for specific surgery types (override risk-based pricing)
    custom_fees = {
        'Appendectomy': Decimal('80000.00'),
        'Cholecystectomy': Decimal('150000.00'),
        'Hernia Repair': Decimal('75000.00'),
        'Cesarean Section': Decimal('120000.00'),
        'Tonsillectomy': Decimal('60000.00'),
        'Hysterectomy': Decimal('180000.00'),
        'Mastectomy': Decimal('250000.00'),
        'Prostatectomy': Decimal('220000.00'),
        'Thyroidectomy': Decimal('160000.00'),
        'Splenectomy': Decimal('140000.00'),
        'Nephrectomy': Decimal('200000.00'),
        'Colectomy': Decimal('190000.00'),
        'Gastrectomy': Decimal('210000.00'),
        'Craniotomy': Decimal('400000.00'),
        'Laminectomy': Decimal('180000.00'),
        'Hip Replacement': Decimal('350000.00'),
        'Knee Replacement': Decimal('320000.00'),
        'Coronary Artery Bypass': Decimal('500000.00'),
        'Valve Replacement': Decimal('450000.00'),
        'Cataract Surgery': Decimal('50000.00'),
        'Laparoscopic Surgery': Decimal('120000.00'),
    }
    
    print("=" * 80)
    print("SURGERY TYPE FEE POPULATION SCRIPT")
    print("=" * 80)
    
    surgery_types = SurgeryType.objects.all()
    updated_count = 0
    
    for surgery_type in surgery_types:
        # Check if custom fee exists for this surgery type
        if surgery_type.name in custom_fees:
            fee = custom_fees[surgery_type.name]
            print(f"\n✓ {surgery_type.name}")
            print(f"  └─ Custom Fee: ₦{fee:,.2f}")
        else:
            # Use risk-based fee
            fee = fee_structure.get(surgery_type.risk_level, Decimal('100000.00'))
            print(f"\n✓ {surgery_type.name}")
            print(f"  └─ Risk Level: {surgery_type.get_risk_level_display()}")
            print(f"  └─ Fee: ₦{fee:,.2f}")
        
        # Update the surgery type fee
        surgery_type.fee = fee
        surgery_type.save()
        updated_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ COMPLETED! Updated {updated_count} surgery types with fees")
    print("=" * 80)
    
    # Display summary
    print("\n📊 FEE SUMMARY BY RISK LEVEL:")
    print("-" * 80)
    for risk_level, risk_display in SurgeryType.RISK_LEVELS:
        count = SurgeryType.objects.filter(risk_level=risk_level).count()
        avg_fee = SurgeryType.objects.filter(risk_level=risk_level).aggregate(
            avg_fee=django.db.models.Avg('fee')
        )['avg_fee'] or Decimal('0.00')
        print(f"\n{risk_display}:")
        print(f"  └─ Count: {count}")
        print(f"  └─ Average Fee: ₦{avg_fee:,.2f}")
    
    print("\n" + "=" * 80)
    print("🎉 All surgery types now have fees assigned!")
    print("=" * 80)


if __name__ == '__main__':
    populate_surgery_fees()

