"""
Comprehensive Revenue Point Breakdown Analysis Service for HMS
Extends existing revenue logic to provide detailed revenue point analysis
while maintaining backward compatibility with existing systems.
"""

from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import calendar

# Existing imports maintained for compatibility
from billing.models import Invoice, Payment as BillingPayment, InvoiceItem
from pharmacy_billing.models import Payment as PharmacyPayment
from pharmacy.models import DispensingLog
from patients.models import WalletTransaction

# Import existing service to maintain compatibility
from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper

try:
    # Import specialty department models if they exist
    from anc.models import AncRecord
    from dental.models import DentalRecord
    from ent.models import EntRecord
    from family_planning.models import FamilyPlanningRecord
    from gynae_emergency.models import GynaeEmergencyRecord
    from icu.models import IcuRecord
    from labor.models import LaborRecord
    from oncology.models import OncologyRecord
    from ophthalmic.models import OphthalmicRecord
    from scbu.models import ScbuRecord
    from theatre.models import Surgery
    from radiology.models import RadiologyOrder
except ImportError:
    # Handle missing models gracefully
    pass


class RevenuePointBreakdownAnalyzer(RevenueAggregationService):
    """
    Extended Revenue Analysis Service providing detailed revenue point breakdown
    Inherits from existing RevenueAggregationService to maintain compatibility
    """
    
    def __init__(self, start_date, end_date):
        """
        Initialize the analyzer with date range
        Calls parent constructor to maintain existing functionality
        """
        super().__init__(start_date, end_date)
        self.revenue_points = self._initialize_revenue_points()
    
    def _initialize_revenue_points(self):
        """
        Initialize revenue point categories based on system analysis
        """
        return {
            'clinical_services': {
                'consultation': 'Consultation Services',
                'pharmacy': 'Pharmacy Services', 
                'laboratory': 'Laboratory Services',
                'radiology': 'Radiology Services',
                'theatre': 'Theatre/Surgery Services',
                'specialties': 'Medical Specialties'
            },
            'support_services': {
                'admission': 'Admission Services',
                'inpatient': 'Inpatient Services',
                'emergency': 'Emergency Services'
            },
            'administrative_services': {
                'general_billing': 'General Billing',
                'insurance': 'Insurance Claims',
                'wallet': 'Wallet Services'
            },
            'specialty_departments': {
                'anc': 'Antenatal Care',
                'dental': 'Dental Services',
                'ent': 'ENT Services',
                'family_planning': 'Family Planning',
                'gynae_emergency': 'Gynae Emergency',
                'icu': 'Intensive Care Unit',
                'labor': 'Labor Ward',
                'oncology': 'Oncology',
                'ophthalmic': 'Ophthalmology',
                'scbu': 'Special Care Baby Unit'
            }
        }
    
    def get_revenue_point_breakdown(self, include_trends=False):
        """
        Get comprehensive revenue breakdown by point
        Maintains existing logic while adding detailed breakdown
        
        Args:
            include_trends: Whether to include trend analysis
            
        Returns:
            dict: Comprehensive revenue point breakdown
        """
        # Get base revenue data using existing methods
        base_revenue = self.get_comprehensive_revenue()
        
        # Enhance with detailed point breakdown
        point_breakdown = {
            'total_revenue': base_revenue['total_revenue'],
            'date_range': base_revenue['date_range'],
            'clinical_services': self._get_clinical_services_breakdown(),
            'support_services': self._get_support_services_breakdown(),
            'administrative_services': self._get_administrative_services_breakdown(),
            'specialty_departments': self._get_specialty_departments_breakdown(),
            'summary_by_category': self._get_category_summary(),
            'payment_method_breakdown': self._get_payment_method_breakdown(),
            'service_utilization': self._get_service_utilization_stats()
        }
        
        if include_trends:
            point_breakdown['trends'] = self._get_revenue_point_trends()
        
        return point_breakdown
    
    def _get_clinical_services_breakdown(self):
        """
        Detailed breakdown of clinical services revenue
        Uses existing methods while adding granular analysis
        """
        # Use existing methods to maintain compatibility
        consultation_data = self.get_consultation_revenue()
        pharmacy_data = self.get_pharmacy_revenue()
        laboratory_data = self.get_laboratory_revenue()
        theatre_data = self.get_theatre_revenue()
        
        # Enhanced radiology revenue calculation
        radiology_data = self._get_radiology_revenue()
        
        return {
            'consultation': {
                'revenue': consultation_data['total_revenue'],
                'transactions': consultation_data['total_payments'],
                'services': consultation_data['total_consultations'],
                'avg_transaction': self._calculate_average(
                    consultation_data['total_revenue'], 
                    consultation_data['total_payments']
                ),
                'details': consultation_data
            },
            'pharmacy': {
                'revenue': pharmacy_data['total_revenue'],
                'transactions': pharmacy_data['total_payments'],
                'prescriptions': pharmacy_data['total_prescriptions'],
                'medications_dispensed': pharmacy_data['total_medications_dispensed'],
                'avg_transaction': self._calculate_average(
                    pharmacy_data['total_revenue'], 
                    pharmacy_data['total_payments']
                ),
                'breakdown': {
                    'billing_revenue': pharmacy_data['pharmacy_billing_revenue'],
                    'dispensing_revenue': pharmacy_data['dispensing_revenue']
                },
                'details': pharmacy_data
            },
            'laboratory': {
                'revenue': laboratory_data['total_revenue'],
                'transactions': laboratory_data['total_payments'],
                'tests': laboratory_data['total_tests'],
                'avg_transaction': self._calculate_average(
                    laboratory_data['total_revenue'], 
                    laboratory_data['total_payments']
                ),
                'details': laboratory_data
            },
            'radiology': {
                'revenue': radiology_data['total_revenue'],
                'transactions': radiology_data['total_payments'],
                'orders': radiology_data['total_orders'],
                'avg_transaction': self._calculate_average(
                    radiology_data['total_revenue'], 
                    radiology_data['total_payments']
                ),
                'details': radiology_data
            },
            'theatre': {
                'revenue': theatre_data['total_revenue'],
                'transactions': theatre_data['total_payments'],
                'surgeries': theatre_data['total_surgeries'],
                'avg_transaction': self._calculate_average(
                    theatre_data['total_revenue'], 
                    theatre_data['total_payments']
                ),
                'details': theatre_data
            }
        }
    
    def _get_support_services_breakdown(self):
        """
        Detailed breakdown of support services revenue
        """
        # Use existing admission method
        admission_data = self.get_admission_revenue()
        
        # Enhanced inpatient and emergency revenue
        inpatient_data = self._get_inpatient_revenue()
        emergency_data = self._get_emergency_revenue()
        
        return {
            'admission': {
                'revenue': admission_data['total_revenue'],
                'transactions': admission_data['total_payments'],
                'admissions': admission_data['total_admissions'],
                'avg_transaction': self._calculate_average(
                    admission_data['total_revenue'], 
                    admission_data['total_payments']
                ),
                'details': admission_data
            },
            'inpatient': {
                'revenue': inpatient_data['total_revenue'],
                'transactions': inpatient_data['total_payments'],
                'patient_days': inpatient_data['total_patient_days'],
                'avg_daily_charge': self._calculate_average(
                    inpatient_data['total_revenue'], 
                    inpatient_data['total_patient_days']
                ),
                'details': inpatient_data
            },
            'emergency': {
                'revenue': emergency_data['total_revenue'],
                'transactions': emergency_data['total_payments'],
                'cases': emergency_data['total_cases'],
                'avg_transaction': self._calculate_average(
                    emergency_data['total_revenue'], 
                    emergency_data['total_payments']
                ),
                'details': emergency_data
            }
        }
    
    def _get_administrative_services_breakdown(self):
        """
        Detailed breakdown of administrative services revenue
        """
        # Use existing methods
        general_data = self.get_general_revenue()
        wallet_data = self.get_wallet_revenue()
        
        # Enhanced insurance revenue
        insurance_data = self._get_insurance_revenue()
        
        return {
            'general_billing': {
                'revenue': general_data['total_revenue'],
                'transactions': general_data['total_payments'],
                'avg_transaction': self._calculate_average(
                    general_data['total_revenue'], 
                    general_data['total_payments']
                ),
                'details': general_data
            },
            'wallet': {
                'revenue': wallet_data['total_revenue'],
                'transactions': wallet_data['total_transactions'],
                'avg_transaction': self._calculate_average(
                    wallet_data['total_revenue'], 
                    wallet_data['total_transactions']
                ),
                'details': wallet_data
            },
            'insurance': {
                'revenue': insurance_data['total_revenue'],
                'claims': insurance_data['total_claims'],
                'avg_claim': self._calculate_average(
                    insurance_data['total_revenue'], 
                    insurance_data['total_claims']
                ),
                'details': insurance_data
            }
        }
    
    def _get_specialty_departments_breakdown(self):
        """
        Detailed breakdown of specialty department revenue
        """
        specialty_breakdown = {}
        
        specialty_departments = [
            ('anc', 'AncRecord'),
            ('dental', 'DentalRecord'),
            ('ent', 'EntRecord'),
            ('family_planning', 'FamilyPlanningRecord'),
            ('gynae_emergency', 'GynaeEmergencyRecord'),
            ('icu', 'IcuRecord'),
            ('labor', 'LaborRecord'),
            ('oncology', 'OncologyRecord'),
            ('ophthalmic', 'OphthalmicRecord'),
            ('scbu', 'ScbuRecord')
        ]
        
        for dept_name, model_name in specialty_departments:
            dept_data = self._get_specialty_revenue(dept_name, model_name)
            specialty_breakdown[dept_name] = {
                'revenue': dept_data['total_revenue'],
                'transactions': dept_data['total_payments'],
                'records': dept_data['total_records'],
                'avg_transaction': self._calculate_average(
                    dept_data['total_revenue'], 
                    dept_data['total_payments']
                ),
                'details': dept_data
            }
        
        return specialty_breakdown
    
    def _get_specialty_revenue(self, department, model_name):
        """
        Calculate revenue for specialty departments
        """
        try:
            # Get revenue from invoices linked to department
            dept_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app=department
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Get record count if model exists
            record_count = 0
            try:
                model_class = globals().get(model_name)
                if model_class:
                    record_count = model_class.objects.filter(
                        created_at__date__range=[self.start_date, self.end_date]
                    ).count()
            except:
                pass
            
            # Get wallet transactions for department
            dept_wallet = WalletTransaction.objects.filter(
                created_at__date__range=[self.start_date, self.end_date],
                description__icontains=department
            ).aggregate(
                wallet_amount=Sum('amount'),
                wallet_transactions=Count('id')
            )
            
            total_revenue = (
                (dept_payments['total_amount'] or Decimal('0.00')) +
                (dept_wallet['wallet_amount'] or Decimal('0.00'))
            )
            
            total_payments = (
                (dept_payments['total_payments'] or 0) +
                (dept_wallet['wallet_transactions'] or 0)
            )
            
            return {
                'total_revenue': total_revenue,
                'total_payments': total_payments,
                'total_records': record_count,
                'invoice_revenue': dept_payments['total_amount'] or Decimal('0.00'),
                'wallet_revenue': dept_wallet['wallet_amount'] or Decimal('0.00')
            }
            
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'total_payments': 0,
                'total_records': 0,
                'invoice_revenue': Decimal('0.00'),
                'wallet_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def _get_radiology_revenue(self):
        """
        Calculate radiology revenue
        """
        try:
            radiology_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app='radiology'
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Get radiology order count
            order_count = Invoice.objects.filter(
                invoice_date__range=[self.start_date, self.end_date],
                source_app='radiology'
            ).count()
            
            return {
                'total_revenue': radiology_payments['total_amount'] or Decimal('0.00'),
                'total_payments': radiology_payments['total_payments'] or 0,
                'total_orders': order_count
            }
        except:
            return {
                'total_revenue': Decimal('0.00'),
                'total_payments': 0,
                'total_orders': 0
            }
    
    def _get_inpatient_revenue(self):
        """
        Calculate detailed inpatient revenue including daily charges
        """
        try:
            # Get daily admission charges from wallet transactions
            daily_charges = WalletTransaction.objects.filter(
                created_at__date__range=[self.start_date, self.end_date],
                transaction_type='daily_admission_charge'
            ).aggregate(
                total_amount=Sum('amount'),
                total_transactions=Count('id')
            )
            
            # Combine with existing admission revenue
            admission_data = self.get_admission_revenue()
            
            total_revenue = (
                admission_data['total_revenue'] +
                (daily_charges['total_amount'] or Decimal('0.00'))
            )
            
            total_payments = (
                admission_data['total_payments'] +
                (daily_charges['total_transactions'] or 0)
            )
            
            return {
                'total_revenue': total_revenue,
                'total_payments': total_payments,
                'total_patient_days': daily_charges['total_transactions'] or 0,
                'admission_revenue': admission_data['total_revenue'],
                'daily_charges_revenue': daily_charges['total_amount'] or Decimal('0.00')
            }
        except:
            return {
                'total_revenue': Decimal('0.00'),
                'total_payments': 0,
                'total_patient_days': 0
            }
    
    def _get_emergency_revenue(self):
        """
        Calculate emergency services revenue
        """
        try:
            # Emergency services might be under different source apps
            emergency_sources = ['emergency', 'gynae_emergency', 'a_and_e']
            
            emergency_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app__in=emergency_sources
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            case_count = Invoice.objects.filter(
                invoice_date__range=[self.start_date, self.end_date],
                source_app__in=emergency_sources
            ).count()
            
            return {
                'total_revenue': emergency_payments['total_amount'] or Decimal('0.00'),
                'total_payments': emergency_payments['total_payments'] or 0,
                'total_cases': case_count
            }
        except:
            return {
                'total_revenue': Decimal('0.00'),
                'total_payments': 0,
                'total_cases': 0
            }
    
    def _get_insurance_revenue(self):
        """
        Calculate insurance claims revenue
        """
        try:
            insurance_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                payment_method='insurance'
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Also check wallet transactions for insurance
            insurance_wallet = WalletTransaction.objects.filter(
                created_at__date__range=[self.start_date, self.end_date],
                transaction_type='insurance_claim'
            ).aggregate(
                wallet_amount=Sum('amount'),
                wallet_transactions=Count('id')
            )
            
            total_revenue = (
                (insurance_payments['total_amount'] or Decimal('0.00')) +
                (insurance_wallet['wallet_amount'] or Decimal('0.00'))
            )
            
            total_claims = (
                (insurance_payments['total_payments'] or 0) +
                (insurance_wallet['wallet_transactions'] or 0)
            )
            
            return {
                'total_revenue': total_revenue,
                'total_claims': total_claims,
                'direct_payments': insurance_payments['total_amount'] or Decimal('0.00'),
                'wallet_claims': insurance_wallet['wallet_amount'] or Decimal('0.00')
            }
        except:
            return {
                'total_revenue': Decimal('0.00'),
                'total_claims': 0
            }
    
    def _get_category_summary(self):
        """
        Get summary statistics by category
        """
        clinical = self._get_clinical_services_breakdown()
        support = self._get_support_services_breakdown()
        administrative = self._get_administrative_services_breakdown()
        specialty = self._get_specialty_departments_breakdown()
        
        clinical_total = sum([service['revenue'] for service in clinical.values()])
        support_total = sum([service['revenue'] for service in support.values()])
        administrative_total = sum([service['revenue'] for service in administrative.values()])
        specialty_total = sum([dept['revenue'] for dept in specialty.values()])
        
        grand_total = clinical_total + support_total + administrative_total + specialty_total
        
        return {
            'clinical_services': {
                'revenue': clinical_total,
                'percentage': self._calculate_percentage(clinical_total, grand_total)
            },
            'support_services': {
                'revenue': support_total,
                'percentage': self._calculate_percentage(support_total, grand_total)
            },
            'administrative_services': {
                'revenue': administrative_total,
                'percentage': self._calculate_percentage(administrative_total, grand_total)
            },
            'specialty_departments': {
                'revenue': specialty_total,
                'percentage': self._calculate_percentage(specialty_total, grand_total)
            },
            'grand_total': grand_total
        }
    
    def _get_payment_method_breakdown(self):
        """
        Get revenue breakdown by payment method
        """
        try:
            payment_methods = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date]
            ).values('payment_method').annotate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            ).order_by('-total_amount')
            
            # Also get pharmacy payment methods
            pharmacy_methods = PharmacyPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date]
            ).values('payment_method').annotate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Combine and aggregate
            method_totals = defaultdict(lambda: {'amount': Decimal('0.00'), 'count': 0})
            
            for pm in payment_methods:
                method = pm['payment_method'] or 'unknown'
                method_totals[method]['amount'] += pm['total_amount'] or Decimal('0.00')
                method_totals[method]['count'] += pm['total_payments'] or 0
            
            for pm in pharmacy_methods:
                method = pm['payment_method'] or 'unknown'
                method_totals[method]['amount'] += pm['total_amount'] or Decimal('0.00')
                method_totals[method]['count'] += pm['total_payments'] or 0
            
            return dict(method_totals)
        except:
            return {}
    
    def _get_service_utilization_stats(self):
        """
        Get service utilization statistics
        """
        try:
            # Top services by revenue
            top_services = InvoiceItem.objects.filter(
                invoice__invoice_date__range=[self.start_date, self.end_date]
            ).values('service__name').annotate(
                total_revenue=Sum('total_amount'),
                total_quantity=Sum('quantity')
            ).order_by('-total_revenue')[:10]
            
            # Service categories by revenue
            service_categories = InvoiceItem.objects.filter(
                invoice__invoice_date__range=[self.start_date, self.end_date]
            ).values('service__category__name').annotate(
                total_revenue=Sum('total_amount'),
                total_services=Count('service', distinct=True)
            ).order_by('-total_revenue')
            
            return {
                'top_services': list(top_services),
                'service_categories': list(service_categories)
            }
        except:
            return {
                'top_services': [],
                'service_categories': []
            }
    
    def _get_revenue_point_trends(self, months=6):
        """
        Get revenue trends by point over specified months
        """
        trends = {}
        
        for i in range(months):
            # Calculate date range for each month
            end_date = timezone.now().date().replace(day=1) - timedelta(days=30*i)
            start_date = end_date.replace(day=1)
            if end_date.month == 12:
                end_date = end_date.replace(year=end_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = end_date.replace(month=end_date.month + 1, day=1) - timedelta(days=1)
            
            # Create analyzer for this month
            month_analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
            monthly_data = month_analyzer.get_revenue_point_breakdown(include_trends=False)
            
            month_key = start_date.strftime('%Y-%m')
            trends[month_key] = {
                'date': start_date,
                'clinical_total': sum([s['revenue'] for s in monthly_data['clinical_services'].values()]),
                'support_total': sum([s['revenue'] for s in monthly_data['support_services'].values()]),
                'administrative_total': sum([s['revenue'] for s in monthly_data['administrative_services'].values()]),
                'specialty_total': sum([s['revenue'] for s in monthly_data['specialty_departments'].values()]),
                'grand_total': monthly_data['total_revenue']
            }
        
        return OrderedDict(sorted(trends.items()))
    
    def _calculate_average(self, total, count):
        """
        Calculate average safely handling zero division
        """
        if count and count > 0:
            return total / count
        return Decimal('0.00')
    
    def _calculate_percentage(self, part, total):
        """
        Calculate percentage safely handling zero division
        """
        if total and total > 0:
            return round((part / total) * 100, 2)
        return 0.00
    
    def export_revenue_breakdown_csv(self):
        """
        Export revenue breakdown data as CSV format
        """
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Get breakdown data
        breakdown = self.get_revenue_point_breakdown()
        
        # Write headers
        writer.writerow(['Revenue Point Breakdown Analysis'])
        writer.writerow(['Date Range', f"{self.start_date} to {self.end_date}"])
        writer.writerow(['Generated', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Clinical Services
        writer.writerow(['Clinical Services'])
        writer.writerow(['Service', 'Revenue', 'Transactions', 'Average Transaction'])
        for service, data in breakdown['clinical_services'].items():
            writer.writerow([
                service.title(),
                f"₦{data['revenue']:,.2f}",
                data['transactions'],
                f"₦{data['avg_transaction']:,.2f}"
            ])
        
        writer.writerow([])
        
        # Category Summary
        writer.writerow(['Category Summary'])
        writer.writerow(['Category', 'Revenue', 'Percentage'])
        for category, data in breakdown['summary_by_category'].items():
            if category != 'grand_total':
                writer.writerow([
                    category.replace('_', ' ').title(),
                    f"₦{data['revenue']:,.2f}",
                    f"{data['percentage']}%"
                ])
        
        return output.getvalue()


class RevenuePointFilterHelper(MonthFilterHelper):
    """
    Extended filter helper for revenue point analysis
    Inherits from existing MonthFilterHelper to maintain compatibility
    """
    
    @staticmethod
    def get_department_filter_options():
        """Get available department filter options"""
        return [
            ('all', 'All Departments'),
            ('clinical', 'Clinical Services'),
            ('support', 'Support Services'),
            ('administrative', 'Administrative Services'),
            ('specialty', 'Specialty Departments'),
            ('consultation', 'Consultation'),
            ('pharmacy', 'Pharmacy'),
            ('laboratory', 'Laboratory'),
            ('radiology', 'Radiology'),
            ('theatre', 'Theatre'),
            ('admission', 'Admission'),
            ('inpatient', 'Inpatient'),
            ('emergency', 'Emergency'),
            ('anc', 'ANC'),
            ('dental', 'Dental'),
            ('ent', 'ENT'),
            ('icu', 'ICU'),
            ('oncology', 'Oncology')
        ]
    
    @staticmethod
    def get_payment_method_options():
        """Get available payment method filter options"""
        return [
            ('all', 'All Payment Methods'),
            ('cash', 'Cash'),
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('upi', 'UPI'),
            ('net_banking', 'Net Banking'),
            ('insurance', 'Insurance'),
            ('wallet', 'Wallet'),
            ('other', 'Other')
        ]
    
    @staticmethod
    def get_export_format_options():
        """Get available export format options"""
        return [
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('pdf', 'PDF')
        ]