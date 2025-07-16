#!/usr/bin/env python
"""
Test script to verify the new pricing logic for NHIA vs non-NHIA patients
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription
from patients.models import Patient
from decimal import Decimal

def test_pricing_logic():
    """Test the new pricing logic for different patient types"""
    print("=== Testing Pricing Logic ===")
    print()
    
    # Test with existing prescription (ID 5 - NHIA patient)
    try:
        prescription = Prescription.objects.get(id=5)
        print(f"Testing with Prescription #{prescription.id}")
        print(f"Patient: {prescription.patient.get_full_name()}")
        print(f"Patient Type: {prescription.patient.patient_type}")
        print()
        
        # Test pricing methods
        total_price = prescription.get_total_prescribed_price()
        patient_payable = prescription.get_patient_payable_amount()
        pricing_breakdown = prescription.get_pricing_breakdown()
        
        print("=== Pricing Results ===")
        print(f"Total Medication Cost: ₦{total_price}")
        print(f"Patient Payable Amount: ₦{patient_payable}")
        print()
        
        print("=== Detailed Breakdown ===")
        print(f"Total Medication Cost: ₦{pricing_breakdown['total_medication_cost']}")
        print(f"Patient Portion: ₦{pricing_breakdown['patient_portion']}")
        print(f"NHIA Portion: ₦{pricing_breakdown['nhia_portion']}")
        print(f"Is NHIA Patient: {pricing_breakdown['is_nhia_patient']}")
        print(f"Discount Percentage: {pricing_breakdown['discount_percentage']}%")
        print()
        
        # Verify calculations
        if pricing_breakdown['is_nhia_patient']:
            expected_patient_portion = pricing_breakdown['total_medication_cost'] * Decimal('0.10')
            expected_nhia_portion = pricing_breakdown['total_medication_cost'] * Decimal('0.90')
            
            print("=== Verification ===")
            print(f"Expected Patient Portion (10%): ₦{expected_patient_portion}")
            print(f"Calculated Patient Portion: ₦{pricing_breakdown['patient_portion']}")
            print(f"Match: {expected_patient_portion == pricing_breakdown['patient_portion']}")
            print()
            print(f"Expected NHIA Portion (90%): ₦{expected_nhia_portion}")
            print(f"Calculated NHIA Portion: ₦{pricing_breakdown['nhia_portion']}")
            print(f"Match: {expected_nhia_portion == pricing_breakdown['nhia_portion']}")
        else:
            print("=== Verification ===")
            print(f"Non-NHIA patient should pay full amount")
            print(f"Expected: ₦{pricing_breakdown['total_medication_cost']}")
            print(f"Calculated: ₦{pricing_breakdown['patient_portion']}")
            print(f"Match: {pricing_breakdown['total_medication_cost'] == pricing_breakdown['patient_portion']}")
        
        print()
        print("=== Item-Level Breakdown ===")
        items = prescription.items.all()
        for item in items:
            item_total = item.medication.price * item.quantity
            if pricing_breakdown['is_nhia_patient']:
                patient_pays = item_total * Decimal('0.10')
                nhia_covers = item_total * Decimal('0.90')
            else:
                patient_pays = item_total
                nhia_covers = Decimal('0.00')
            
            print(f"• {item.medication.name}: {item.quantity} units @ ₦{item.medication.price}")
            print(f"  Total Cost: ₦{item_total}")
            print(f"  Patient Pays: ₦{patient_pays}")
            if pricing_breakdown['is_nhia_patient']:
                print(f"  NHIA Covers: ₦{nhia_covers}")
            print()
        
        return True
        
    except Prescription.DoesNotExist:
        print("❌ Prescription with ID 5 not found!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_non_nhia_patient():
    """Test with a non-NHIA patient if available"""
    print("=== Testing Non-NHIA Patient ===")
    
    # Find a non-NHIA patient
    non_nhia_patients = Patient.objects.exclude(patient_type='nhia')[:1]
    if not non_nhia_patients.exists():
        print("No non-NHIA patients found. Creating test scenario...")
        return
    
    # Find prescriptions for non-NHIA patients
    non_nhia_prescriptions = Prescription.objects.filter(
        patient__patient_type__in=['private', 'insurance', 'staff']
    )[:1]
    
    if non_nhia_prescriptions.exists():
        prescription = non_nhia_prescriptions.first()
        print(f"Testing with Prescription #{prescription.id}")
        print(f"Patient: {prescription.patient.get_full_name()}")
        print(f"Patient Type: {prescription.patient.patient_type}")
        
        pricing_breakdown = prescription.get_pricing_breakdown()
        print(f"Patient should pay 100%: ₦{pricing_breakdown['patient_portion']}")
        print(f"NHIA covers: ₦{pricing_breakdown['nhia_portion']}")
        print(f"Discount: {pricing_breakdown['discount_percentage']}%")
    else:
        print("No prescriptions found for non-NHIA patients.")

if __name__ == "__main__":
    success = test_pricing_logic()
    print()
    test_non_nhia_patient()
    
    if success:
        print("\n✅ Pricing logic test completed!")
    else:
        print("\n❌ Pricing logic test failed!")
