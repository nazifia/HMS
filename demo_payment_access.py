#!/usr/bin/env python
"""
Demo script to show how billing officers can access payment functionality
for prescribed medications in the HMS system.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.urls import reverse
from pharmacy.models import Prescription
from pharmacy_billing.models import Invoice as PharmacyInvoice
from billing.models import Invoice as BillingInvoice


def demonstrate_payment_access():
    """Demonstrate how to access payment functionality for medications"""
    
    print("🏥 HMS Medication Payment Access Demo")
    print("=" * 50)
    
    # Find prescriptions with invoices
    prescriptions_with_invoices = Prescription.objects.filter(invoice__isnull=False)
    
    if not prescriptions_with_invoices.exists():
        print("❌ No prescriptions with invoices found.")
        print("💡 Create a prescription first to generate an invoice.")
        return
    
    print(f"✅ Found {prescriptions_with_invoices.count()} prescriptions with invoices")
    print()
    
    for prescription in prescriptions_with_invoices[:3]:  # Show first 3
        print(f"📋 Prescription #{prescription.id}")
        print(f"   Patient: {prescription.patient.get_full_name()}")
        print(f"   Doctor: {prescription.doctor.get_full_name()}")
        print(f"   Status: {prescription.status}")
        print(f"   Payment Status: {prescription.payment_status}")
        
        if prescription.invoice:
            invoice = prescription.invoice
            print(f"   📄 Invoice #{invoice.id}")
            print(f"      Total Amount: ₦{invoice.total_amount}")
            print(f"      Status: {invoice.status}")
            
            # Show payment access URLs
            print(f"   🔗 Payment Access URLs:")
            
            # Method 1: From prescription detail
            prescription_detail_url = reverse('pharmacy:prescription_detail', args=[prescription.id])
            print(f"      1. Prescription Detail: {prescription_detail_url}")
            
            # Method 2: From billing system (if invoice exists in billing system)
            try:
                billing_invoice = BillingInvoice.objects.filter(prescription=prescription).first()
                if billing_invoice:
                    payment_url = reverse('billing:payment', args=[billing_invoice.id])
                    invoice_detail_url = reverse('billing:detail', args=[billing_invoice.id])
                    print(f"      2. Direct Payment: {payment_url}")
                    print(f"      3. Invoice Detail: {invoice_detail_url}")
                else:
                    print(f"      2. Pharmacy Invoice (use pharmacy billing system)")
            except Exception as e:
                print(f"      2. Pharmacy Invoice (separate billing system)")
            
            # Show payment verification status
            can_dispense, reason = prescription.can_be_dispensed()
            print(f"   🚦 Dispensing Status: {'✅ Allowed' if can_dispense else '❌ Blocked'}")
            if not can_dispense:
                print(f"      Reason: {reason}")
            
        print("-" * 40)
    
    print()
    print("📝 Payment Process Summary:")
    print("1. Navigate to prescription or invoice")
    print("2. Click 'Record Payment' or 'Pay Invoice' button")
    print("3. Fill payment form with amount and method")
    print("4. Submit payment")
    print("5. System updates prescription status")
    print("6. Dispensing becomes available")
    
    print()
    print("🔑 Key URLs for Billing Officers:")
    print(f"   • Prescription List: {reverse('pharmacy:prescriptions')}")
    print(f"   • Billing Invoices: {reverse('billing:list')}")
    
    # Show available payment methods
    print()
    print("💳 Available Payment Methods:")
    from billing.models import Invoice
    for code, name in Invoice.PAYMENT_METHOD_CHOICES:
        print(f"   • {name} ({code})")


def show_payment_form_structure():
    """Show the structure of the payment form"""
    
    print()
    print("📋 Payment Form Structure:")
    print("=" * 30)
    
    form_fields = [
        ("amount", "Payment Amount", "Decimal field, pre-filled with balance"),
        ("payment_method", "Payment Method", "Dropdown with available methods"),
        ("payment_date", "Payment Date", "Date picker, defaults to today"),
        ("transaction_id", "Transaction ID", "Optional text field for reference"),
        ("notes", "Notes", "Optional textarea for additional info")
    ]
    
    for field, label, description in form_fields:
        print(f"   {label}:")
        print(f"      Field: {field}")
        print(f"      Description: {description}")
        print()
    
    print("🔒 Form Validation:")
    print("   • Amount cannot exceed remaining balance")
    print("   • Amount must be greater than 0")
    print("   • Payment date cannot be in the future")
    print("   • Wallet payments check available balance")


def show_system_integration():
    """Show how payment integrates with the system"""
    
    print()
    print("🔄 System Integration After Payment:")
    print("=" * 35)
    
    integration_steps = [
        "Payment record created in database",
        "Invoice amount_paid field updated",
        "Invoice status updated (paid/partially_paid)",
        "Prescription payment_status updated to 'paid'",
        "Dispensing buttons become active",
        "Notifications sent to relevant staff",
        "Audit log entry created",
        "Email notifications triggered"
    ]
    
    for i, step in enumerate(integration_steps, 1):
        print(f"   {i}. {step}")
    
    print()
    print("📊 Real-time Updates:")
    print("   • Prescription detail page shows updated payment status")
    print("   • Dispensing pages become accessible")
    print("   • Invoice list shows updated balance")
    print("   • Payment history is immediately visible")


if __name__ == "__main__":
    try:
        demonstrate_payment_access()
        show_payment_form_structure()
        show_system_integration()
        
        print()
        print("🎉 Demo completed successfully!")
        print("💡 Use this information to guide billing officers through the payment process.")
        
    except Exception as e:
        print(f"❌ Error during demo: {str(e)}")
        import traceback
        traceback.print_exc()
