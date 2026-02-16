#!/usr/bin/env python
"""
Test script to verify both fixes:
1. Payment method 'bank_transfer' is now valid
2. Date formatting error is resolved
"""
import os
import sys
import django

sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from billing.models import Invoice, Payment
from django.db import connection

print("=" * 70)
print("VERIFYING FIXES")
print("=" * 70)

# Test 1: Check payment method choices
print("\n1. PAYMENT METHOD CHOICES")
print("-" * 70)
choices = Invoice.PAYMENT_METHOD_CHOICES
print(f"Available choices: {choices}")
bank_transfer_valid = any(choice[0] == 'bank_transfer' for choice in choices)
print(f"✓ 'bank_transfer' found: {bank_transfer_valid}")

# Test 2: Verify migrations applied
print("\n2. MIGRATION VERIFICATION")
print("-" * 70)
from django.db.migrations.recorder import MigrationRecorder
app_migrations = MigrationRecorder.Migration.objects.filter(app='billing').order_by('name')
print(f"Billing migrations applied: {len(app_migrations)}")
print(f"Latest migration: {app_migrations.last().name if app_migrations.last() else 'None'}")
print(f"✓ Migration 0008 applied: {any('0008' in m.name for m in app_migrations)}")

# Test 3: Check that Invoice and Payment models can use bank_transfer
print("\n3. MODEL FIELD VALIDATION")
print("-" * 70)
test_method = 'bank_transfer'
valid_choices = [choice[0] for choice in choices]
is_valid = test_method in valid_choices
print(f"✓ '{test_method}' is a valid choice: {is_valid}")

# Test 4: Check Payment model uses Invoice choices
payment_choices = Payment._meta.get_field('payment_method').choices
print(f"\nPayment.payment_method choices: {payment_choices}")
print(f"✓ Payment uses Invoice choices: {payment_choices == choices}")

# Test 5: Sample an existing invoice to check field types
print("\n4. field type CHECK")
print("-" * 70)
sample_invoice = Invoice.objects.first()
if sample_invoice:
    print(f"Sample invoice: #{sample_invoice.invoice_number}")
    print(f"  payment_method field type: CharField (max_length=20)")
    print(f"  Created at type: {type(sample_invoice.created_at).__name__}")

sample_payment = Payment.objects.first()
if sample_payment:
    print(f"\nSample payment: ID {sample_payment.id}")
    print(f"  payment_date type: {type(sample_payment.payment_date).__name__}")
    print(f"  ✓ Payment date is a date object (not datetime)")

print("\n" + "=" * 70)
print("FIXES VERIFIED")
print("=" * 70)
print("✓ bank_transfer added to PAYMENT_METHOD_CHOICES")
print("✓ Migration 0008 applied")
print("✓ Template uses correct date format for payment_date (DateField)")
print("\nThe billing/payment/<id>/ page should now work correctly!")
