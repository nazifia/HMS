#!/usr/bin/env python
"""
Debug script to check the current state of prescription ID 5
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription
from pharmacy_billing.models import Invoice as PharmacyInvoice

def debug_prescription_state():
    """Debug the current state of prescription ID 5"""
    try:
        prescription = Prescription.objects.get(id=5)
        print(f"=== Prescription {prescription.id} Debug Info ===")
        print(f"Patient: {prescription.patient.get_full_name()}")
        print(f"Patient Type: {prescription.patient.patient_type}")
        print(f"Is NHIA Patient: {prescription.patient.patient_type == 'nhia'}")
        print(f"Doctor: {prescription.doctor}")
        print(f"Status: {prescription.status}")
        print(f"Payment Status: {prescription.payment_status}")
        print(f"Prescription Type: {prescription.prescription_type}")
        print()
        
        # Check payment verification methods
        print("=== Payment Verification Methods ===")
        is_verified = prescription.is_payment_verified()
        can_dispense, reason = prescription.can_be_dispensed()
        payment_info = prescription.get_payment_status_display_info()
        
        print(f"is_payment_verified(): {is_verified}")
        print(f"can_be_dispensed(): {can_dispense}")
        print(f"Reason: {reason}")
        print(f"Payment status info: {payment_info}")
        print()
        
        # Check invoice relationship
        print("=== Invoice Information ===")
        if hasattr(prescription, 'invoice') and prescription.invoice:
            invoice = prescription.invoice
            print(f"Has invoice: Yes (ID: {invoice.id})")
            print(f"Invoice status: {invoice.status}")
            print(f"Invoice total: {invoice.total_amount}")
            print(f"Invoice amount paid: {invoice.amount_paid}")
            if hasattr(invoice, 'get_balance'):
                print(f"Invoice balance: {invoice.get_balance()}")
            else:
                print("Invoice balance method not available")
        else:
            print("Has invoice: No")
        
        # Check pharmacy_billing invoice
        try:
            pharmacy_invoices = PharmacyInvoice.objects.filter(prescription=prescription)
            print(f"Pharmacy billing invoices: {pharmacy_invoices.count()}")
            for inv in pharmacy_invoices:
                print(f"  - Invoice ID: {inv.id}, Status: {inv.status}, Total: {inv.total_amount}, Paid: {inv.amount_paid}")
        except Exception as e:
            print(f"Error checking pharmacy invoices: {e}")
        
        print()
        print("=== Prescription Items ===")
        items = prescription.items.all()
        print(f"Total items: {items.count()}")
        total_calculated = 0
        for item in items:
            item_total = item.medication.price * item.quantity
            total_calculated += item_total
            print(f"  - {item.medication.name}: {item.quantity} units @ ₦{item.medication.price} = ₦{item_total}")
            print(f"    Status: {'Dispensed' if item.is_dispensed else 'Pending'}")

        print(f"Calculated total from items: ₦{total_calculated}")
        print(f"get_total_prescribed_price(): ₦{prescription.get_total_prescribed_price()}")

        return prescription
        
    except Prescription.DoesNotExist:
        print("Prescription with ID 5 not found!")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    debug_prescription_state()
