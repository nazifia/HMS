#!/usr/bin/env python
"""
Debug script to check prescription 6 and its invoice relationship
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription
from pharmacy_billing.models import Invoice as PharmacyInvoice

def debug_prescription_6():
    """Debug prescription 6 and its invoice"""
    try:
        prescription = Prescription.objects.get(id=6)
        print(f"=== Prescription {prescription.id} Debug ===")
        print(f"Patient: {prescription.patient.get_full_name()}")
        print(f"Patient Type: {prescription.patient.patient_type}")
        print(f"Payment Status: {prescription.payment_status}")
        print()
        
        # Check pricing
        pricing = prescription.get_pricing_breakdown()
        print("=== Pricing Breakdown ===")
        print(f"Total Cost: ₦{pricing['total_medication_cost']}")
        print(f"Patient Pays: ₦{pricing['patient_portion']}")
        print(f"NHIA Covers: ₦{pricing['nhia_portion']}")
        print(f"Is NHIA: {pricing['is_nhia_patient']}")
        print()
        
        # Check pharmacy_billing invoices
        pharmacy_invoices = PharmacyInvoice.objects.filter(prescription=prescription)
        print(f"=== Pharmacy Billing Invoices ===")
        print(f"Count: {pharmacy_invoices.count()}")
        
        for invoice in pharmacy_invoices:
            print(f"Invoice ID: {invoice.id}")
            print(f"Status: {invoice.status}")
            print(f"Total: ₦{invoice.total_amount}")
            print(f"Paid: ₦{invoice.amount_paid}")
            print(f"Balance: ₦{invoice.get_balance()}")
            print()
        
        # Check if prescription has invoice attribute
        print("=== Prescription Invoice Relationship ===")
        if hasattr(prescription, 'invoice') and prescription.invoice:
            print(f"prescription.invoice exists: {prescription.invoice.id}")
        else:
            print("prescription.invoice: None")
            
        if hasattr(prescription, 'invoice_prescription') and prescription.invoice_prescription:
            print(f"prescription.invoice_prescription exists: {prescription.invoice_prescription.id}")
        else:
            print("prescription.invoice_prescription: None")
        
        return prescription
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    debug_prescription_6()
