"""
Department-Specific Revenue Calculation Utilities for HMS
Provides specialized revenue calculation methods for each department
while maintaining integration with existing revenue logic.
"""

from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

from billing.models import Invoice, Payment as BillingPayment, InvoiceItem, Service
# from pharmacy_billing.models import Payment as PharmacyPayment
from pharmacy.models import DispensingLog, Medication, PrescriptionItem
from patients.models import WalletTransaction, Patient
from appointments.models import Appointment
from consultations.models import Consultation

try:
    # Import department models
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
    from laboratory.models import TestRequest
    from inpatient.models import Admission, Ward
except ImportError:
    pass


class DepartmentRevenueCalculator:
    """
    Specialized calculator for department-specific revenue analysis
    """
    
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
    
    def get_pharmacy_detailed_revenue(self):
        """
        Enhanced pharmacy revenue calculation with medication breakdown
        """
        try:
            # Base pharmacy revenue (existing logic) - Temporarily disabled
            # pharmacy_payments = PharmacyPayment.objects.filter(
            #     payment_date__range=[self.start_date, self.end_date]
            # ).aggregate(
            #     total_amount=Sum('amount'),
            #     total_payments=Count('id')
            # )
            pharmacy_payments = {'total_amount': Decimal('0.00'), 'total_payments': 0}
            
            dispensing_revenue = DispensingLog.objects.filter(
                dispensed_date__date__range=[self.start_date, self.end_date]
            ).aggregate(
                total_amount=Sum('total_price_for_this_log'),
                total_dispensed=Count('id')
            )
            
            # Enhanced analysis
            # Top medications by revenue
            top_medications = DispensingLog.objects.filter(
                dispensed_date__date__range=[self.start_date, self.end_date]
            ).values(
                'medication__name',
                'medication__category'
            ).annotate(
                total_revenue=Sum('total_price_for_this_log'),
                total_quantity=Sum('quantity_dispensed'),
                total_prescriptions=Count('prescription_item__prescription', distinct=True)
            ).order_by('-total_revenue')[:10]
            
            # Prescription types breakdown
            prescription_types = PrescriptionItem.objects.filter(
                dispensing_logs__dispensed_date__date__range=[self.start_date, self.end_date]
            ).values(
                'prescription__prescribed_by__profile__specialization'
            ).annotate(
                total_revenue=Sum('dispensing_logs__total_price_for_this_log'),
                total_items=Count('id')
            ).order_by('-total_revenue')
            
            # Daily dispensing trends
            daily_dispensing = DispensingLog.objects.filter(
                dispensed_date__date__range=[self.start_date, self.end_date]
            ).extra(
                select={'day': 'DATE(dispensed_date)'}
            ).values('day').annotate(
                daily_revenue=Sum('total_price_for_this_log'),
                daily_prescriptions=Count('prescription_item__prescription', distinct=True)
            ).order_by('day')
            
            total_revenue = (
                (pharmacy_payments['total_amount'] or Decimal('0.00')) +
                (dispensing_revenue['total_amount'] or Decimal('0.00'))
            )
            
            return {
                'total_revenue': total_revenue,
                'pharmacy_billing_revenue': pharmacy_payments['total_amount'] or Decimal('0.00'),
                'dispensing_revenue': dispensing_revenue['total_amount'] or Decimal('0.00'),
                'total_payments': pharmacy_payments['total_payments'] or 0,
                'total_dispensed': dispensing_revenue['total_dispensed'] or 0,
                'top_medications': list(top_medications),
                'prescription_types': list(prescription_types),
                'daily_trends': list(daily_dispensing),
                'avg_prescription_value': self._calculate_average(
                    dispensing_revenue['total_amount'], 
                    dispensing_revenue['total_dispensed']
                )
            }
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def get_laboratory_detailed_revenue(self):
        """
        Enhanced laboratory revenue calculation with test breakdown
        """
        try:
            # Base laboratory revenue
            lab_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app='laboratory'
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Enhanced analysis
            # Top tests by revenue
            top_tests = InvoiceItem.objects.filter(
                invoice__invoice_date__range=[self.start_date, self.end_date],
                invoice__source_app='laboratory'
            ).values(
                'service__name',
                'service__category__name'
            ).annotate(
                total_revenue=Sum('total_amount'),
                total_quantity=Sum('quantity'),
                avg_price=Avg('unit_price')
            ).order_by('-total_revenue')[:10]
            
            # Test requests analysis
            test_requests = TestRequest.objects.filter(
                created_at__date__range=[self.start_date, self.end_date]
            ).aggregate(
                total_requests=Count('id'),
                completed_requests=Count('id', filter=Q(status='completed')),
                avg_turnaround_time=Avg(
                    F('updated_at') - F('created_at'),
                    filter=Q(status='completed')
                )
            )
            
            # Department referral analysis
            referral_analysis = TestRequest.objects.filter(
                created_at__date__range=[self.start_date, self.end_date]
            ).values(
                'requested_by__profile__specialization'
            ).annotate(
                total_requests=Count('id'),
                total_revenue=Sum('invoice_record__payments__amount')
            ).order_by('-total_requests')
            
            return {
                'total_revenue': lab_payments['total_amount'] or Decimal('0.00'),
                'total_payments': lab_payments['total_payments'] or 0,
                'total_requests': test_requests['total_requests'] or 0,
                'completed_requests': test_requests['completed_requests'] or 0,
                'completion_rate': self._calculate_percentage(
                    test_requests['completed_requests'],
                    test_requests['total_requests']
                ),
                'avg_turnaround_hours': self._calculate_hours(
                    test_requests['avg_turnaround_time']
                ),
                'top_tests': list(top_tests),
                'referral_analysis': list(referral_analysis),
                'avg_test_value': self._calculate_average(
                    lab_payments['total_amount'],
                    test_requests['total_requests']
                )
            }
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def get_consultation_detailed_revenue(self):
        """
        Enhanced consultation revenue calculation with doctor breakdown
        """
        try:
            # Base consultation revenue
            consultation_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app='appointment'
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Doctor performance analysis
            doctor_revenue = Appointment.objects.filter(
                appointment_date__range=[self.start_date, self.end_date],
                status='completed'
            ).values(
                'doctor__user__first_name',
                'doctor__user__last_name',
                'doctor__specialization'
            ).annotate(
                total_consultations=Count('id'),
                total_revenue=Sum('invoices__payments__amount'),
                avg_consultation_fee=Avg('invoices__total_amount')
            ).order_by('-total_revenue')[:10]
            
            # Appointment type analysis
            appointment_types = Consultation.objects.filter(
                created_at__date__range=[self.start_date, self.end_date]
            ).values(
                'appointment_type'
            ).annotate(
                total_consultations=Count('id'),
                avg_duration=Avg('duration_minutes')
            ).order_by('-total_consultations')
            
            # Time slot analysis
            time_analysis = Appointment.objects.filter(
                appointment_date__range=[self.start_date, self.end_date]
            ).extra(
                select={'hour': 'EXTRACT(hour FROM appointment_time)'}
            ).values('hour').annotate(
                total_appointments=Count('id'),
                total_revenue=Sum('invoices__payments__amount')
            ).order_by('hour')
            
            return {
                'total_revenue': consultation_payments['total_amount'] or Decimal('0.00'),
                'total_payments': consultation_payments['total_payments'] or 0,
                'doctor_performance': list(doctor_revenue),
                'appointment_types': list(appointment_types),
                'time_distribution': list(time_analysis),
                'avg_consultation_fee': self._calculate_average(
                    consultation_payments['total_amount'],
                    consultation_payments['total_payments']
                )
            }
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def get_theatre_detailed_revenue(self):
        """
        Enhanced theatre revenue calculation with surgery breakdown
        """
        try:
            # Base theatre revenue
            theatre_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app='theatre'
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Surgery type analysis
            surgery_types = Surgery.objects.filter(
                surgery_date__range=[self.start_date, self.end_date]
            ).values(
                'surgery_type',
                'urgency_level'
            ).annotate(
                total_surgeries=Count('id'),
                total_revenue=Sum('invoice__payments__amount'),
                avg_duration=Avg('duration_minutes')
            ).order_by('-total_revenue')
            
            # Surgeon performance
            surgeon_performance = Surgery.objects.filter(
                surgery_date__range=[self.start_date, self.end_date]
            ).values(
                'primary_surgeon__user__first_name',
                'primary_surgeon__user__last_name',
                'primary_surgeon__specialization'
            ).annotate(
                total_surgeries=Count('id'),
                total_revenue=Sum('invoice__payments__amount'),
                avg_surgery_fee=Avg('invoice__total_amount')
            ).order_by('-total_surgeries')[:10]
            
            # Theatre utilization
            theatre_utilization = Surgery.objects.filter(
                surgery_date__range=[self.start_date, self.end_date]
            ).values(
                'theatre_room'
            ).annotate(
                total_surgeries=Count('id'),
                total_hours=Sum('duration_minutes') / 60,
                total_revenue=Sum('invoice__payments__amount')
            ).order_by('-total_surgeries')
            
            return {
                'total_revenue': theatre_payments['total_amount'] or Decimal('0.00'),
                'total_payments': theatre_payments['total_payments'] or 0,
                'surgery_types': list(surgery_types),
                'surgeon_performance': list(surgeon_performance),
                'theatre_utilization': list(theatre_utilization),
                'avg_surgery_fee': self._calculate_average(
                    theatre_payments['total_amount'],
                    theatre_payments['total_payments']
                )
            }
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def get_inpatient_detailed_revenue(self):
        """
        Enhanced inpatient revenue calculation with ward breakdown
        """
        try:
            # Base admission revenue
            admission_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app='inpatient'
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Daily charges revenue
            daily_charges = WalletTransaction.objects.filter(
                created_at__date__range=[self.start_date, self.end_date],
                transaction_type='daily_admission_charge'
            ).aggregate(
                total_amount=Sum('amount'),
                total_transactions=Count('id')
            )
            
            # Ward analysis
            ward_analysis = Admission.objects.filter(
                admission_date__range=[self.start_date, self.end_date]
            ).values(
                'bed__ward__name',
                'bed__ward__ward_type',
                'bed__ward__charge_per_day'
            ).annotate(
                total_admissions=Count('id'),
                total_patient_days=Sum(
                    F('discharge_date') - F('admission_date'),
                    filter=Q(discharge_date__isnull=False)
                ),
                avg_stay_duration=Avg(
                    F('discharge_date') - F('admission_date'),
                    filter=Q(discharge_date__isnull=False)
                ),
                total_revenue=Sum('invoices__payments__amount')
            ).order_by('-total_admissions')
            
            # Discharge analysis
            discharge_analysis = Admission.objects.filter(
                discharge_date__range=[self.start_date, self.end_date]
            ).values(
                'discharge_condition'
            ).annotate(
                total_discharges=Count('id'),
                avg_stay_days=Avg(
                    F('discharge_date') - F('admission_date')
                )
            ).order_by('-total_discharges')
            
            total_revenue = (
                (admission_payments['total_amount'] or Decimal('0.00')) +
                (daily_charges['total_amount'] or Decimal('0.00'))
            )
            
            return {
                'total_revenue': total_revenue,
                'admission_revenue': admission_payments['total_amount'] or Decimal('0.00'),
                'daily_charges_revenue': daily_charges['total_amount'] or Decimal('0.00'),
                'total_payments': admission_payments['total_payments'] or 0,
                'total_patient_days': daily_charges['total_transactions'] or 0,
                'ward_analysis': list(ward_analysis),
                'discharge_analysis': list(discharge_analysis),
                'avg_daily_charge': self._calculate_average(
                    daily_charges['total_amount'],
                    daily_charges['total_transactions']
                )
            }
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def get_specialty_department_detailed_revenue(self, department):
        """
        Enhanced specialty department revenue calculation
        """
        department_configs = {
            'anc': {
                'model': 'AncRecord',
                'display_name': 'Antenatal Care',
                'key_fields': ['gravida', 'para', 'edd']
            },
            'dental': {
                'model': 'DentalRecord', 
                'display_name': 'Dental Services',
                'key_fields': ['procedure_type', 'tooth_number']
            },
            'ent': {
                'model': 'EntRecord',
                'display_name': 'ENT Services', 
                'key_fields': ['ear_examination', 'throat_examination']
            },
            'icu': {
                'model': 'IcuRecord',
                'display_name': 'Intensive Care Unit',
                'key_fields': ['glasgow_coma_scale', 'mechanical_ventilation']
            },
            'oncology': {
                'model': 'OncologyRecord',
                'display_name': 'Oncology',
                'key_fields': ['cancer_type', 'cancer_stage']
            }
        }
        
        if department not in department_configs:
            return {'total_revenue': Decimal('0.00'), 'error': 'Department not found'}
        
        try:
            config = department_configs[department]
            
            # Base revenue calculation
            dept_payments = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date],
                invoice__source_app=department
            ).aggregate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            )
            
            # Wallet transactions
            dept_wallet = WalletTransaction.objects.filter(
                created_at__date__range=[self.start_date, self.end_date],
                description__icontains=department
            ).aggregate(
                wallet_amount=Sum('amount'),
                wallet_transactions=Count('id')
            )
            
            # Record statistics
            try:
                model_class = globals().get(config['model'])
                if model_class:
                    record_stats = model_class.objects.filter(
                        created_at__date__range=[self.start_date, self.end_date]
                    ).aggregate(
                        total_records=Count('id')
                    )
                    
                    # Monthly trend
                    monthly_records = model_class.objects.filter(
                        created_at__date__range=[self.start_date, self.end_date]
                    ).extra(
                        select={'month': 'DATE_FORMAT(created_at, "%%Y-%%m")'}
                    ).values('month').annotate(
                        monthly_count=Count('id')
                    ).order_by('month')
                else:
                    record_stats = {'total_records': 0}
                    monthly_records = []
            except:
                record_stats = {'total_records': 0}
                monthly_records = []
            
            # Services provided analysis
            service_analysis = InvoiceItem.objects.filter(
                invoice__invoice_date__range=[self.start_date, self.end_date],
                invoice__source_app=department
            ).values(
                'service__name'
            ).annotate(
                total_revenue=Sum('total_amount'),
                total_quantity=Sum('quantity')
            ).order_by('-total_revenue')[:5]
            
            total_revenue = (
                (dept_payments['total_amount'] or Decimal('0.00')) +
                (dept_wallet['wallet_amount'] or Decimal('0.00'))
            )
            
            return {
                'department_name': config['display_name'],
                'total_revenue': total_revenue,
                'invoice_revenue': dept_payments['total_amount'] or Decimal('0.00'),
                'wallet_revenue': dept_wallet['wallet_amount'] or Decimal('0.00'),
                'total_payments': (dept_payments['total_payments'] or 0) + (dept_wallet['wallet_transactions'] or 0),
                'total_records': record_stats['total_records'],
                'monthly_records': list(monthly_records),
                'top_services': list(service_analysis),
                'avg_revenue_per_record': self._calculate_average(
                    total_revenue,
                    record_stats['total_records']
                )
            }
            
        except Exception as e:
            return {
                'total_revenue': Decimal('0.00'),
                'error': str(e)
            }
    
    def get_patient_revenue_analysis(self, patient_id=None):
        """
        Patient-specific revenue analysis
        """
        try:
            patient_filter = Q()
            if patient_id:
                patient_filter = Q(invoice__patient_id=patient_id)
            
            # Patient revenue breakdown
            patient_revenue = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date]
            ).filter(patient_filter).values(
                'invoice__patient__patient_id',
                'invoice__patient__user__first_name',
                'invoice__patient__user__last_name'
            ).annotate(
                total_revenue=Sum('amount'),
                total_visits=Count('invoice', distinct=True),
                avg_visit_value=Avg('amount')
            ).order_by('-total_revenue')[:20]
            
            # Payment method preferences
            payment_preferences = BillingPayment.objects.filter(
                payment_date__range=[self.start_date, self.end_date]
            ).filter(patient_filter).values(
                'payment_method'
            ).annotate(
                total_amount=Sum('amount'),
                total_payments=Count('id')
            ).order_by('-total_amount')
            
            return {
                'top_patients': list(patient_revenue),
                'payment_preferences': list(payment_preferences)
            }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    def _calculate_average(self, total, count):
        """Calculate average safely"""
        if count and count > 0:
            return total / count
        return Decimal('0.00')
    
    def _calculate_percentage(self, part, total):
        """Calculate percentage safely"""
        if total and total > 0:
            return round((part / total) * 100, 2)
        return 0.00
    
    def _calculate_hours(self, timedelta_avg):
        """Convert timedelta to hours"""
        if timedelta_avg:
            return round(timedelta_avg.total_seconds() / 3600, 2)
        return 0.00


class RevenueComparisonAnalyzer:
    """
    Analyzer for comparing revenue across different periods and departments
    """
    
    def __init__(self, current_start, current_end, previous_start, previous_end):
        self.current_period = DepartmentRevenueCalculator(current_start, current_end)
        self.previous_period = DepartmentRevenueCalculator(previous_start, previous_end)
    
    def get_period_comparison(self):
        """
        Compare revenue between current and previous periods
        """
        current_total = self._get_total_revenue(self.current_period)
        previous_total = self._get_total_revenue(self.previous_period)
        
        growth_rate = self._calculate_growth_rate(current_total, previous_total)
        
        return {
            'current_period': {
                'total_revenue': current_total,
                'start_date': self.current_period.start_date,
                'end_date': self.current_period.end_date
            },
            'previous_period': {
                'total_revenue': previous_total,
                'start_date': self.previous_period.start_date,
                'end_date': self.previous_period.end_date
            },
            'growth_rate': growth_rate,
            'revenue_change': current_total - previous_total
        }
    
    def _get_total_revenue(self, calculator):
        """Get total revenue for a period"""
        try:
            pharmacy = calculator.get_pharmacy_detailed_revenue()
            laboratory = calculator.get_laboratory_detailed_revenue()
            consultation = calculator.get_consultation_detailed_revenue()
            theatre = calculator.get_theatre_detailed_revenue()
            inpatient = calculator.get_inpatient_detailed_revenue()
            
            return (
                pharmacy['total_revenue'] +
                laboratory['total_revenue'] +
                consultation['total_revenue'] +
                theatre['total_revenue'] +
                inpatient['total_revenue']
            )
        except:
            return Decimal('0.00')
    
    def _calculate_growth_rate(self, current, previous):
        """Calculate growth rate between periods"""
        if previous and previous > 0:
            return round(((current - previous) / previous) * 100, 2)
        return 0.00