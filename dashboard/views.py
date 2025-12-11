from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta

from patients.models import Patient
from appointments.models import Appointment
from pharmacy.models import Medication, Prescription, MedicationCategory, MedicationInventory
from laboratory.models import TestRequest, TestResult, Test, TestCategory
from billing.models import Invoice, Payment, Service, ServiceCategory
from consultations.models import Consultation, ConsultingRoom, Referral, WaitingList
from hr.models import Department as HRDepartment # Assuming 'Department' from hr.models is the intended HRDepartment.
from inpatient.models import Admission, Bed, Ward
from accounts.models import CustomUserProfile # Assuming UserProfile holds role and department for staff
from accounts.models import CustomUser

# Import models for new modules
from ophthalmic.models import OphthalmicRecord
from ent.models import EntRecord
from oncology.models import OncologyRecord
from scbu.models import ScbuRecord
from anc.models import AncRecord
from labor.models import LaborRecord
from icu.models import IcuRecord
from family_planning.models import Family_planningRecord
from gynae_emergency.models import Gynae_emergencyRecord


@login_required
def dashboard(request):
    """Main dashboard view - Optimized for performance with caching"""
    from django.db.models import Q, Count as CountFunc
    from django.core.cache import cache

    today = timezone.now().date()
    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)

    # Create cache key based on user and date
    cache_key = f'dashboard_data_{request.user.id}_{today}'
    cached_data = cache.get(cache_key)

    if cached_data:
        # Return cached data if available
        return render(request, 'dashboard/dashboard_modern.html', cached_data)

    # Optimize: Get basic counts in fewer queries
    total_patients = Patient.objects.filter(is_active=True).count()
    total_appointments = Appointment.objects.count()
    total_prescriptions = Prescription.objects.count()
    total_tests = TestRequest.objects.count()

    # Optimize: Get all module record counts (removed duplicate queries)
    total_ophthalmic_records = OphthalmicRecord.objects.count()
    total_ent_records = EntRecord.objects.count()
    total_oncology_records = OncologyRecord.objects.count()
    total_scbu_records = ScbuRecord.objects.count()
    total_anc_records = AncRecord.objects.count()
    total_labor_records = LaborRecord.objects.count()
    total_icu_records = IcuRecord.objects.count()
    total_family_planning_records = Family_planningRecord.objects.count()
    total_gynae_emergency_records = Gynae_emergencyRecord.objects.count()

    # Get follow-up counts for new modules
    ent_follow_up_count = EntRecord.objects.filter(follow_up_required=True).count()

    # Optimize: Get today's appointments with select_related for related objects
    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).select_related('patient', 'doctor').order_by('appointment_time')[:5]

    # Optimize: Get pending prescriptions with select_related
    pending_prescriptions = Prescription.objects.filter(
        status__in=['pending', 'processing']
    ).select_related('patient').order_by('-prescription_date')[:5]

    # Optimize: Get pending test requests with select_related
    pending_tests = TestRequest.objects.filter(
        status__in=['pending', 'collected', 'processing']
    ).select_related('patient', 'doctor').order_by('-request_date')[:5]

    # Get low stock medications (already optimized with select_related)
    low_stock_medications = MedicationInventory.objects.filter(
        stock_quantity__lte=F('reorder_level'),
        stock_quantity__gt=0
    ).select_related('medication', 'dispensary').order_by('stock_quantity')[:5]

    # Optimize: Get recent invoices with select_related
    recent_invoices = Invoice.objects.select_related('patient').order_by('-created_at')[:5]

    # Optimize: Get all revenue statistics in a single query using conditional aggregation
    revenue_stats = Payment.objects.aggregate(
        today_revenue=Sum('amount', filter=Q(payment_date=today)),
        week_revenue=Sum('amount', filter=Q(payment_date__gte=this_week_start, payment_date__lte=today)),
        month_revenue=Sum('amount', filter=Q(payment_date__gte=this_month_start, payment_date__lte=today))
    )

    today_revenue = revenue_stats['today_revenue'] or 0
    this_week_revenue = revenue_stats['week_revenue'] or 0
    this_month_revenue = revenue_stats['month_revenue'] or 0

    # Optimize: Get appointment statistics in a single query using conditional aggregation
    appointment_stats_query = Appointment.objects.aggregate(
        today=CountFunc('id', filter=Q(appointment_date=today)),
        scheduled=CountFunc('id', filter=Q(status='scheduled')),
        completed=CountFunc('id', filter=Q(status='completed')),
        cancelled=CountFunc('id', filter=Q(status='cancelled'))
    )

    appointment_stats = {
        'today': appointment_stats_query['today'],
        'scheduled': appointment_stats_query['scheduled'],
        'completed': appointment_stats_query['completed'],
        'cancelled': appointment_stats_query['cancelled'],
    }

    # Optimize: Get wallet statistics in a single query using conditional aggregation
    from patients.models import PatientWallet, WalletTransaction
    wallet_stats = PatientWallet.objects.aggregate(
        total_balance=Sum('balance'),
        positive_count=CountFunc('id', filter=Q(balance__gt=0)),
        negative_count=CountFunc('id', filter=Q(balance__lt=0)),
        zero_count=CountFunc('id', filter=Q(balance=0))
    )

    total_wallet_balance = wallet_stats['total_balance'] or 0
    positive_wallets = wallet_stats['positive_count']
    negative_wallets = wallet_stats['negative_count']
    zero_wallets = wallet_stats['zero_count']

    # Optimize: Get recent wallet transactions with select_related
    recent_wallet_transactions = WalletTransaction.objects.select_related(
        'patient_wallet__patient'
    ).order_by('-created_at')[:5]

    context = {
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'total_prescriptions': total_prescriptions,
        'total_tests': total_tests,
        'total_ophthalmic_records': total_ophthalmic_records,
        'total_ent_records': total_ent_records,
        'total_oncology_records': total_oncology_records,
        'total_scbu_records': total_scbu_records,
        'total_anc_records': total_anc_records,
        'total_labor_records': total_labor_records,
        'total_icu_records': total_icu_records,
        'total_family_planning_records': total_family_planning_records,
        'total_gynae_emergency_records': total_gynae_emergency_records,
        # Use same variables for consistency (removed duplicates)
        'ophthalmic_records_count': total_ophthalmic_records,
        'ent_records_count': total_ent_records,
        'oncology_records_count': total_oncology_records,
        'scbu_records_count': total_scbu_records,
        'anc_records_count': total_anc_records,
        'labor_records_count': total_labor_records,
        'icu_records_count': total_icu_records,
        'family_planning_records_count': total_family_planning_records,
        'gynae_emergency_records_count': total_gynae_emergency_records,
        'today_appointments': today_appointments,
        'pending_prescriptions': pending_prescriptions,
        'pending_tests': pending_tests,
        'low_stock_medications': low_stock_medications,
        'recent_invoices': recent_invoices,
        'today_revenue': today_revenue,
        'this_week_revenue': this_week_revenue,
        'this_month_revenue': this_month_revenue,
        'appointment_stats': appointment_stats,
        'ent_follow_up_count': ent_follow_up_count,
        # Wallet statistics
        'total_wallet_balance': total_wallet_balance,
        'positive_wallets': positive_wallets,
        'negative_wallets': negative_wallets,
        'zero_wallets': zero_wallets,
        'recent_wallet_transactions': recent_wallet_transactions,
    }

    # Cache the context for 5 minutes (300 seconds)
    cache.set(cache_key, context, 300)

    return render(request, 'dashboard/dashboard_modern.html', context)


@login_required
def system_overview(request):
    """View to display a system configuration and data overview - Optimized"""
    from django.db.models import Q, Count as CountFunc

    context = {'title': 'System Configuration Overview'}

    # Optimize: Accounts App - Get user stats in a single query
    user_stats = CustomUser.objects.aggregate(
        total=CountFunc('id'),
        superusers=CountFunc('id', filter=Q(is_superuser=True)),
        staff=CountFunc('id', filter=Q(is_staff=True, is_superuser=False))
    )
    context['total_users'] = user_stats['total']
    context['superuser_count'] = user_stats['superusers']
    context['staff_count'] = user_stats['staff']

    try:
        # Get role counts from the many-to-many relationship
        from accounts.models import Role
        context['user_roles'] = Role.objects.annotate(count=Count('customuser_roles')).values('name', 'count').order_by('-count')
    except Exception:
        context['user_roles'] = []

    # Optimize: Patients App - Get patient stats in a single query
    patient_stats = Patient.objects.aggregate(
        total=CountFunc('id'),
        active=CountFunc('id', filter=Q(is_active=True))
    )
    context['total_patients_records'] = patient_stats['total']
    context['active_patients'] = patient_stats['active']

    # Optimize: Appointments App - Get appointment stats in a single query
    appointment_stats = Appointment.objects.aggregate(
        total=CountFunc('id'),
        scheduled=CountFunc('id', filter=Q(status='scheduled')),
        completed=CountFunc('id', filter=Q(status='completed')),
        cancelled=CountFunc('id', filter=Q(status='cancelled'))
    )
    context['total_appointments_records'] = appointment_stats['total']
    context['scheduled_appointments'] = appointment_stats['scheduled']
    context['completed_appointments'] = appointment_stats['completed']
    context['cancelled_appointments'] = appointment_stats['cancelled']
    context['appointment_types'] = Appointment.objects.values('priority').annotate(count=Count('priority')).order_by('-count')

    # Optimize: Laboratory App - Get lab stats in fewer queries
    lab_stats = Test.objects.aggregate(
        total=CountFunc('id'),
        active=CountFunc('id', filter=Q(is_active=True))
    )
    test_request_stats = TestRequest.objects.aggregate(
        total=CountFunc('id'),
        pending=CountFunc('id', filter=Q(status='pending')),
        completed=CountFunc('id', filter=Q(status='completed'))
    )
    context['lab_test_categories'] = TestCategory.objects.count()
    context['lab_tests_defined'] = lab_stats['total']
    context['active_lab_tests'] = lab_stats['active']
    context['total_test_requests'] = test_request_stats['total']
    context['pending_test_requests'] = test_request_stats['pending']
    context['completed_test_requests'] = test_request_stats['completed']

    # Optimize: Pharmacy App - Get pharmacy stats in fewer queries
    medication_stats = Medication.objects.aggregate(
        total=CountFunc('id'),
        active=CountFunc('id', filter=Q(is_active=True))
    )
    inventory_stats = MedicationInventory.objects.aggregate(
        low_stock=CountFunc('id', filter=Q(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0)),
        out_of_stock=CountFunc('id', filter=Q(stock_quantity=0))
    )
    context['medication_categories'] = MedicationCategory.objects.count()
    context['medications_in_inventory'] = medication_stats['total']
    context['active_medications'] = medication_stats['active']
    context['low_stock_medications_count'] = inventory_stats['low_stock']
    context['out_of_stock_medications_count'] = inventory_stats['out_of_stock']
    context['total_prescriptions_issued'] = Prescription.objects.count()

    # Optimize: Billing App - Get billing stats in fewer queries
    invoice_stats = Invoice.objects.aggregate(
        total=CountFunc('id'),
        paid=CountFunc('id', filter=Q(status='paid')),
        pending=CountFunc('id', filter=Q(status='pending')),
        overdue=CountFunc('id', filter=Q(status='overdue'))
    )
    payment_stats = Payment.objects.aggregate(
        total_count=CountFunc('id'),
        total_revenue=Sum('amount')
    )
    context['billable_service_categories'] = ServiceCategory.objects.count()
    context['billable_services_defined'] = Service.objects.count()
    context['total_invoices'] = invoice_stats['total']
    context['paid_invoices'] = invoice_stats['paid']
    context['pending_invoices'] = invoice_stats['pending']
    context['overdue_invoices'] = invoice_stats['overdue']
    context['total_payments_recorded'] = payment_stats['total_count']
    context['total_revenue_collected'] = payment_stats['total_revenue'] or 0.00

    # Optimize: Consultations App - Get consultation stats in a single query
    consulting_room_stats = ConsultingRoom.objects.aggregate(
        total=CountFunc('id'),
        active=CountFunc('id', filter=Q(is_active=True))
    )
    context['total_consultations'] = Consultation.objects.count()
    context['consulting_rooms'] = consulting_room_stats['total']
    context['active_consulting_rooms'] = consulting_room_stats['active']
    context['total_referrals'] = Referral.objects.count()
    context['patients_in_waiting_list'] = WaitingList.objects.filter(status__in=['waiting', 'in_progress']).count()

    # HR App (Human Resources)
    context['hr_departments'] = HRDepartment.objects.count()
    context['total_employees'] = CustomUser.objects.filter(is_staff=True).count()
    context['active_employees'] = CustomUser.objects.filter(is_staff=True, is_active=True).count()

    # Inpatient App
    context['total_wards'] = Ward.objects.count()
    context['total_beds'] = Bed.objects.count()
    context['occupied_beds'] = Bed.objects.filter(is_occupied=True).count()
    context['available_beds'] = Bed.objects.filter(is_occupied=False, is_active=True).count()
    context['total_admissions'] = Admission.objects.count()
    context['current_admissions'] = Admission.objects.filter(discharge_date__isnull=True).count()

    # New Modules
    context['ophthalmic_records_count'] = OphthalmicRecord.objects.count()
    context['ent_records_count'] = EntRecord.objects.count()
    context['oncology_records_count'] = OncologyRecord.objects.count()
    context['scbu_records_count'] = ScbuRecord.objects.count()
    context['anc_records_count'] = AncRecord.objects.count()
    context['labor_records_count'] = LaborRecord.objects.count()
    context['icu_records_count'] = IcuRecord.objects.count()
    context['family_planning_records_count'] = Family_planningRecord.objects.count()
    context['gynae_emergency_records_count'] = Gynae_emergencyRecord.objects.count()
    
    # Authorization code statistics
    from nhia.models import AuthorizationCode
    context['active_authorization_codes'] = AuthorizationCode.objects.filter(status='active').count()
    context['used_authorization_codes'] = AuthorizationCode.objects.filter(status='used').count()
    context['expired_authorization_codes'] = AuthorizationCode.objects.filter(status='expired').count()

    return render(request, 'dashboard/system_overview.html', context)