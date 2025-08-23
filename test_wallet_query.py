#!/usr/bin/env python
"""
Test script to verify that the WalletTransaction query fix works correctly.
This tests the exact query that was causing the FieldError.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import WalletTransaction
from django.db.models import Sum, Count
from datetime import date, timedelta

def test_wallet_query():
    """Test the fixed wallet transaction query"""
    print("Testing fixed WalletTransaction query...")
    
    # Test date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # The original failing query (commented out):
    # wallet_transactions = WalletTransaction.objects.filter(
    #     created_at__date__range=[start_date, end_date],
    #     transaction_type='debit',
    #     purpose__in=['payment', 'bill_payment', 'service_payment']  # This field doesn't exist!
    # )
    
    # The fixed query:
    payment_transaction_types = [
        'payment', 'lab_test_payment', 'pharmacy_payment', 
        'consultation_fee', 'procedure_fee', 'admission_fee',
        'daily_admission_charge'
    ]
    
    try:
        wallet_transactions = WalletTransaction.objects.filter(
            created_at__date__range=[start_date, end_date],
            transaction_type__in=payment_transaction_types
        ).aggregate(
            total_amount=Sum('amount'),
            total_transactions=Count('id')
        )
        
        print("✅ Query executed successfully!")
        print(f"Result: {wallet_transactions}")
        print("✅ Fix verified!")
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False

if __name__ == "__main__":
    test_wallet_query()