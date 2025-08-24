"""
Comprehensive Revenue Aggregation Service for HMS
Collects revenue data from all hospital modules including pharmacy, laboratory, 
consultations, theatre, admissions, and general billing.
"""

from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

from billing.models import Invoice, Payment as BillingPayment
# from pharmacy_billing.models import Payment as PharmacyPayment
from pharmacy.models import DispensingLog
from patients.models import WalletTransaction


class RevenueAggregationService:
    """
    Service class to aggregate revenue from all hospital revenue sources
    """
    
    def __init__(self, start_date, end_date):
        """
        Initialize the service with date range
        
        Args:
            start_date: Start date for revenue calculation
            end_date: End date for revenue calculation
        """
        self.start_date = start_date
        self.end_date = end_date
        
    def get_pharmacy_revenue(self):
        """
        Calculate pharmacy revenue from both pharmacy billing payments and dispensing logs
        
        Returns:
            dict: Pharmacy revenue breakdown
        """
        # Pharmacy billing payments - Temporarily disabled
        # pharmacy_payments = PharmacyPayment.objects.filter(
        #     payment_date__range=[self.start_date, self.end_date]
        # ).aggregate(
        #     total_amount=Sum('amount'),
        #     total_payments=Count('id')
        # )
        pharmacy_payments = {'total_amount': Decimal('0.00'), 'total_payments': 0}
        
        # Dispensing logs (for direct medication sales)
        dispensing_revenue = DispensingLog.objects.filter(
            dispensed_date__date__range=[self.start_date, self.end_date]
        ).aggregate(
            total_amount=Sum('total_price_for_this_log'),
            total_dispensed=Count('id')
        )
        
        # Get prescription count
        prescription_count = DispensingLog.objects.filter(
            dispensed_date__date__range=[self.start_date, self.end_date]
        ).values('prescription_item__prescription').distinct().count()
        
        total_revenue = (
            (pharmacy_payments['total_amount'] or Decimal('0.00')) +
            (dispensing_revenue['total_amount'] or Decimal('0.00'))
        )
        
        return {
            'total_revenue': total_revenue,
            'pharmacy_billing_revenue': pharmacy_payments['total_amount'] or Decimal('0.00'),
            'dispensing_revenue': dispensing_revenue['total_amount'] or Decimal('0.00'),
            'total_prescriptions': prescription_count,
            'total_medications_dispensed': dispensing_revenue['total_dispensed'] or 0,
            'total_payments': pharmacy_payments['total_payments'] or 0
        }
    
    def get_laboratory_revenue(self):
        """
        Calculate laboratory revenue from billing invoices
        
        Returns:
            dict: Laboratory revenue breakdown
        """
        lab_payments = BillingPayment.objects.filter(
            payment_date__range=[self.start_date, self.end_date],
            invoice__source_app='laboratory'
        ).aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id')
        )
        
        # Get test count from laboratory invoices
        test_count = Invoice.objects.filter(
            invoice_date__range=[self.start_date, self.end_date],
            source_app='laboratory'
        ).count()
        
        return {
            'total_revenue': lab_payments['total_amount'] or Decimal('0.00'),
            'total_tests': test_count,
            'total_payments': lab_payments['total_payments'] or 0
        }
    
    def get_consultation_revenue(self):
        """
        Calculate consultation/appointment revenue from billing invoices
        
        Returns:
            dict: Consultation revenue breakdown
        """
        consultation_payments = BillingPayment.objects.filter(
            payment_date__range=[self.start_date, self.end_date],
            invoice__source_app='appointment'
        ).aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id')
        )
        
        # Get consultation count
        consultation_count = Invoice.objects.filter(
            invoice_date__range=[self.start_date, self.end_date],
            source_app='appointment'
        ).count()
        
        return {
            'total_revenue': consultation_payments['total_amount'] or Decimal('0.00'),
            'total_consultations': consultation_count,
            'total_payments': consultation_payments['total_payments'] or 0
        }
    
    def get_theatre_revenue(self):
        """
        Calculate theatre/surgery revenue from billing invoices
        
        Returns:
            dict: Theatre revenue breakdown
        """
        theatre_payments = BillingPayment.objects.filter(
            payment_date__range=[self.start_date, self.end_date],
            invoice__source_app='theatre'
        ).aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id')
        )
        
        # Get surgery count
        surgery_count = Invoice.objects.filter(
            invoice_date__range=[self.start_date, self.end_date],
            source_app='theatre'
        ).count()
        
        return {
            'total_revenue': theatre_payments['total_amount'] or Decimal('0.00'),
            'total_surgeries': surgery_count,
            'total_payments': theatre_payments['total_payments'] or 0
        }
    
    def get_admission_revenue(self):
        """
        Calculate admission/inpatient revenue from billing invoices
        
        Returns:
            dict: Admission revenue breakdown
        """
        admission_payments = BillingPayment.objects.filter(
            payment_date__range=[self.start_date, self.end_date],
            invoice__source_app='inpatient'
        ).aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id')
        )
        
        # Get admission count
        admission_count = Invoice.objects.filter(
            invoice_date__range=[self.start_date, self.end_date],
            source_app='inpatient'
        ).count()
        
        return {
            'total_revenue': admission_payments['total_amount'] or Decimal('0.00'),
            'total_admissions': admission_count,
            'total_payments': admission_payments['total_payments'] or 0
        }
    
    def get_general_revenue(self):
        """
        Calculate general billing revenue (other services)
        
        Returns:
            dict: General revenue breakdown
        """
        general_payments = BillingPayment.objects.filter(
            payment_date__range=[self.start_date, self.end_date],
            invoice__source_app__in=['billing', 'general']
        ).aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id')
        )
        
        # Include payments without specific source app (legacy data)
        other_payments = BillingPayment.objects.filter(
            payment_date__range=[self.start_date, self.end_date],
            invoice__source_app__isnull=True
        ).aggregate(
            total_amount=Sum('amount'),
            total_payments=Count('id')
        )
        
        total_revenue = (
            (general_payments['total_amount'] or Decimal('0.00')) +
            (other_payments['total_amount'] or Decimal('0.00'))
        )
        
        total_payments_count = (
            (general_payments['total_payments'] or 0) +
            (other_payments['total_payments'] or 0)
        )
        
        return {
            'total_revenue': total_revenue,
            'total_payments': total_payments_count
        }
    
    def get_wallet_revenue(self):
        """
        Calculate revenue from wallet transactions
        
        Returns:
            dict: Wallet revenue breakdown
        """
        # Filter wallet transactions that represent payments/revenue
        payment_transaction_types = [
            'payment', 'lab_test_payment', 'pharmacy_payment', 
            'consultation_fee', 'procedure_fee', 'admission_fee',
            'daily_admission_charge'
        ]
        
        wallet_transactions = WalletTransaction.objects.filter(
            created_at__date__range=[self.start_date, self.end_date],
            transaction_type__in=payment_transaction_types
        ).aggregate(
            total_amount=Sum('amount'),
            total_transactions=Count('id')
        )
        
        return {
            'total_revenue': wallet_transactions['total_amount'] or Decimal('0.00'),
            'total_transactions': wallet_transactions['total_transactions'] or 0
        }
    
    def get_comprehensive_revenue(self):
        """
        Get comprehensive revenue breakdown from all sources
        
        Returns:
            dict: Complete revenue breakdown
        """
        pharmacy_data = self.get_pharmacy_revenue()
        laboratory_data = self.get_laboratory_revenue()
        consultation_data = self.get_consultation_revenue()
        theatre_data = self.get_theatre_revenue()
        admission_data = self.get_admission_revenue()
        general_data = self.get_general_revenue()
        wallet_data = self.get_wallet_revenue()
        
        total_revenue = (
            pharmacy_data['total_revenue'] +
            laboratory_data['total_revenue'] +
            consultation_data['total_revenue'] +
            theatre_data['total_revenue'] +
            admission_data['total_revenue'] +
            general_data['total_revenue'] +
            wallet_data['total_revenue']
        )
        
        return {
            'total_revenue': total_revenue,
            'pharmacy_revenue': pharmacy_data,
            'laboratory_revenue': laboratory_data,
            'consultation_revenue': consultation_data,
            'theatre_revenue': theatre_data,
            'admission_revenue': admission_data,
            'general_revenue': general_data,
            'wallet_revenue': wallet_data,
            'date_range': {
                'start_date': self.start_date,
                'end_date': self.end_date
            }
        }
    
    def get_monthly_trends(self, months=12):
        """
        Get monthly revenue trends for the specified number of months
        
        Args:
            months: Number of months to include in trends (default: 12)
            
        Returns:
            list: Monthly revenue data
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30 * months)
        
        monthly_data = []
        current_date = start_date.replace(day=1)  # Start from first of the month
        
        while current_date <= end_date:
            # Calculate next month
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            
            # Get revenue for this month
            month_service = RevenueAggregationService(current_date, next_month - timedelta(days=1))
            month_revenue = month_service.get_comprehensive_revenue()
            
            monthly_data.append({
                'month': current_date.strftime('%b %Y'),
                'month_date': current_date,
                'total_revenue': month_revenue['total_revenue'],
                'pharmacy': month_revenue['pharmacy_revenue']['total_revenue'],
                'laboratory': month_revenue['laboratory_revenue']['total_revenue'],
                'consultations': month_revenue['consultation_revenue']['total_revenue'],
                'theatre': month_revenue['theatre_revenue']['total_revenue'],
                'admissions': month_revenue['admission_revenue']['total_revenue'],
                'general': month_revenue['general_revenue']['total_revenue'],
                'wallet': month_revenue['wallet_revenue']['total_revenue']
            })
            
            current_date = next_month
        
        return monthly_data
    
    def get_daily_breakdown(self):
        """
        Get daily revenue breakdown for the specified date range
        
        Returns:
            list: Daily revenue data
        """
        daily_data = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Get revenue for this day
            day_service = RevenueAggregationService(current_date, current_date)
            day_revenue = day_service.get_comprehensive_revenue()
            
            daily_data.append({
                'date': current_date,
                'date_str': current_date.strftime('%Y-%m-%d'),
                'total_revenue': day_revenue['total_revenue'],
                'pharmacy': day_revenue['pharmacy_revenue']['total_revenue'],
                'laboratory': day_revenue['laboratory_revenue']['total_revenue'],
                'consultations': day_revenue['consultation_revenue']['total_revenue'],
                'theatre': day_revenue['theatre_revenue']['total_revenue'],
                'admissions': day_revenue['admission_revenue']['total_revenue'],
                'general': day_revenue['general_revenue']['total_revenue'],
                'wallet': day_revenue['wallet_revenue']['total_revenue']
            })
            
            current_date += timedelta(days=1)
        
        return daily_data


class MonthFilterHelper:
    """
    Helper class for handling month-based filtering
    """
    
    @staticmethod
    def get_current_month():
        """Get start and end date for current month"""
        today = timezone.now().date()
        start_date = today.replace(day=1)
        next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
        end_date = next_month - timedelta(days=1)
        return start_date, end_date
    
    @staticmethod
    def get_previous_month():
        """Get start and end date for previous month"""
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        if current_month_start.month == 1:
            prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            prev_month_start = current_month_start.replace(month=current_month_start.month - 1)
        
        end_date = current_month_start - timedelta(days=1)
        return prev_month_start, end_date
    
    @staticmethod
    def get_last_n_months(n):
        """Get start and end date for last n months"""
        today = timezone.now().date()
        end_date = today
        start_date = today - timedelta(days=30 * n)
        return start_date, end_date
    
    @staticmethod
    def get_year_to_date():
        """Get start and end date for year to date"""
        today = timezone.now().date()
        start_date = today.replace(month=1, day=1)
        return start_date, today
    
    @staticmethod
    def get_specific_month(year, month):
        """Get start and end date for specific month"""
        start_date = datetime(year, month, 1).date()
        if month == 12:
            next_month = datetime(year + 1, 1, 1).date()
        else:
            next_month = datetime(year, month + 1, 1).date()
        end_date = next_month - timedelta(days=1)
        return start_date, end_date
    
    @staticmethod
    def get_filter_options():
        """Get available filter options"""
        return [
            ('current_month', 'Current Month'),
            ('previous_month', 'Previous Month'),
            ('last_3_months', 'Last 3 Months'),
            ('last_6_months', 'Last 6 Months'),
            ('last_12_months', 'Last 12 Months'),
            ('year_to_date', 'Year to Date'),
            ('custom_range', 'Custom Range'),
            ('specific_month', 'Specific Month')
        ]