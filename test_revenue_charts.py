#!/usr/bin/env python
"""
Test script to create minimal test data and verify the revenue analysis functionality
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import Patient, PatientWallet, WalletTransaction
from billing.models import Invoice, Payment as BillingPayment
from pharmacy_billing.models import Payment as PharmacyPayment
from django.utils import timezone

def create_minimal_test_data():
    """Create minimal test data for revenue analysis"""
    print("Creating minimal test data...")
    
    # Create a test patient if doesn't exist
    patient, created = Patient.objects.get_or_create(
        patient_id='TEST001',
        defaults={
            'first_name': 'Test',
            'last_name': 'Patient',
            'phone_number': '08012345678',
            'email': 'test@example.com',
            'gender': 'male',
            'date_of_birth': date(1990, 1, 1)
        }
    )
    
    if created:
        print(f"Created test patient: {patient.get_full_name()}")
    
    # Create wallet for patient
    wallet, wallet_created = PatientWallet.objects.get_or_create(
        patient=patient,
        defaults={'balance': Decimal('5000.00')}
    )
    
    if wallet_created:
        print(f"Created wallet for patient: {patient.get_full_name()}")
    
    # Create some wallet transactions
    payment_types = ['payment', 'lab_test_payment', 'pharmacy_payment', 'consultation_fee']
    
    for i, payment_type in enumerate(payment_types):
        amount = Decimal(str(100 * (i + 1)))  # 100, 200, 300, 400
        
        transaction, created = WalletTransaction.objects.get_or_create(
            wallet=wallet,
            transaction_type=payment_type,
            amount=amount,
            defaults={
                'balance_after': wallet.balance - amount,
                'description': f'Test {payment_type} transaction',
                'created_at': timezone.now() - timedelta(days=i)
            }
        )
        
        if created:
            print(f"Created wallet transaction: {payment_type} - ₦{amount}")
    
    print("✅ Minimal test data created successfully!")

def test_revenue_service():
    """Test the revenue aggregation service"""
    print("\n" + "="*50)
    print("Testing Revenue Aggregation Service...")
    
    try:
        from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper
        
        # Get current month date range
        start_date, end_date = MonthFilterHelper.get_current_month()
        print(f"Date range: {start_date} to {end_date}")
        
        # Initialize revenue service
        revenue_service = RevenueAggregationService(start_date, end_date)
        
        # Get comprehensive revenue data
        comprehensive_data = revenue_service.get_comprehensive_revenue()
        
        print("\n📊 Revenue Breakdown:")
        print(f"Total Revenue: ₦{comprehensive_data['total_revenue']:.2f}")
        
        departments = [
            ('pharmacy_revenue', 'Pharmacy'),
            ('laboratory_revenue', 'Laboratory'),
            ('consultation_revenue', 'Consultations'),
            ('theatre_revenue', 'Theatre'),
            ('admission_revenue', 'Admissions'),
            ('general_revenue', 'General & Others'),
            ('wallet_revenue', 'Wallet Transactions')
        ]
        
        for dept_key, dept_name in departments:
            dept_data = comprehensive_data[dept_key]
            revenue = dept_data['total_revenue']
            transactions = dept_data.get('total_payments', dept_data.get('total_transactions', 0))
            print(f"  {dept_name}: ₦{revenue:.2f} ({transactions} transactions)")
        
        # Test monthly trends
        monthly_trends = revenue_service.get_monthly_trends(3)
        print(f"\n📈 Monthly Trends ({len(monthly_trends)} months):")
        for trend in monthly_trends:
            print(f"  {trend['month']}: ₦{trend['total_revenue']:.2f}")
        
        print("✅ Revenue service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Revenue service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chart_data():
    """Test chart data JSON conversion"""
    print("\n" + "="*50)
    print("Testing Chart Data JSON Conversion...")
    
    try:
        from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper
        import json
        
        # Get current month date range
        start_date, end_date = MonthFilterHelper.get_current_month()
        
        # Initialize revenue service
        revenue_service = RevenueAggregationService(start_date, end_date)
        
        # Get monthly trends
        monthly_trends = revenue_service.get_monthly_trends(6)
        
        # Prepare chart data like in the view
        chart_months = [trend['month'] for trend in monthly_trends]
        chart_data = {
            'months': json.dumps(chart_months),
            'pharmacy': json.dumps([float(trend['pharmacy']) for trend in monthly_trends]),
            'laboratory': json.dumps([float(trend['laboratory']) for trend in monthly_trends]),
            'total': json.dumps([float(trend['total_revenue']) for trend in monthly_trends])
        }
        
        print("📊 Chart Data Preview:")
        print(f"  Months: {chart_data['months']}")
        print(f"  Pharmacy Data: {chart_data['pharmacy']}")
        print(f"  Laboratory Data: {chart_data['laboratory']}")
        print(f"  Total Data: {chart_data['total']}")
        
        print("✅ Chart data conversion test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Chart data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Revenue Analysis Test Script")
    print("="*50)
    
    # Create test data
    create_minimal_test_data()
    
    # Test revenue service
    revenue_test_passed = test_revenue_service()
    
    # Test chart data
    chart_test_passed = test_chart_data()
    
    print("\n" + "="*50)
    print("📝 SUMMARY:")
    print(f"Revenue Service Test: {'✅ PASSED' if revenue_test_passed else '❌ FAILED'}")
    print(f"Chart Data Test: {'✅ PASSED' if chart_test_passed else '❌ FAILED'}")
    
    if revenue_test_passed and chart_test_passed:
        print("\n🎉 All tests passed! The revenue analysis should now display charts with data.")
        print("📌 Visit: http://127.0.0.1:8000/pharmacy/revenue/statistics/")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")