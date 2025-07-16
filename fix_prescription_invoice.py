#!/usr/bin/env python
"""
Fix the invoice for prescription ID 5
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription
from pharmacy_billing.models import Invoice as PharmacyInvoice

def fix_prescription_invoice():
    """Fix the invoice for prescription ID 5"""
    try:
        prescription = Prescription.objects.get(id=5)
        print(f"=== Fixing Invoice for Prescription {prescription.id} ===")
        
        # Calculate the correct total
        total_prescription_price = prescription.get_total_prescribed_price()
        print(f"Total prescription price: ₦{total_prescription_price}")
        
        # Check if patient is NHIA
        is_nhia_patient = (prescription.patient.patient_type == 'nhia')
        print(f"Is NHIA patient: {is_nhia_patient}")
        
        if is_nhia_patient:
            # NHIA patients pay 10% of the medication cost
            adjusted_total = total_prescription_price * Decimal('0.10')
            print(f"NHIA adjusted total (10%): ₦{adjusted_total}")
        else:
            adjusted_total = total_prescription_price
        
        # Get the existing invoice
        if hasattr(prescription, 'invoice') and prescription.invoice:
            invoice = prescription.invoice
            print(f"Found existing invoice ID: {invoice.id}")
            print(f"Current invoice total: ₦{invoice.total_amount}")
            print(f"Current invoice subtotal: ₦{invoice.subtotal}")
            
            # Update the invoice with correct amounts
            invoice.subtotal = adjusted_total
            invoice.total_amount = adjusted_total
            invoice.save()
            
            print(f"Updated invoice total to: ₦{invoice.total_amount}")
            print(f"Updated invoice subtotal to: ₦{invoice.subtotal}")
            print(f"Invoice balance: ₦{invoice.get_balance()}")
            
            # Verify the prescription payment verification now
            print("\n=== Verification After Fix ===")
            is_verified = prescription.is_payment_verified()
            can_dispense, reason = prescription.can_be_dispensed()
            
            print(f"is_payment_verified(): {is_verified}")
            print(f"can_be_dispensed(): {can_dispense}")
            print(f"Reason: {reason}")
            
            if not can_dispense and 'payment' in reason.lower():
                print("✅ Payment verification is working correctly - dispensing blocked until payment")
            else:
                print("❌ Payment verification may not be working correctly")
                
            return True
        else:
            print("❌ No invoice found for this prescription")
            return False
            
    except Prescription.DoesNotExist:
        print("❌ Prescription with ID 5 not found!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_prescription_invoice()
    if success:
        print("\n✅ Invoice fix completed successfully!")
    else:
        print("\n❌ Invoice fix failed!")
