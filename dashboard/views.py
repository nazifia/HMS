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
    """Main dashboard view"""
    today = timezone.now().date()

    # Get counts for various entities
    total_patients = Patient.objects.filter(is_active=True).count()
    total_appointments = Appointment.objects.count()
    total_prescriptions = Prescription.objects.count()
    total_tests = TestRequest.objects.count()
    
    # Get counts for new modules
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

    # Get today's appointments
    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).order_by('appointment_time')[:5]

    # Get pending prescriptions
    pending_prescriptions = Prescription.objects.filter(
        status__in=['pending', 'processing']
    ).order_by('-prescription_date')[:5]

    # Get pending test requests
    pending_tests = TestRequest.objects.filter(
        status__in=['pending', 'collected', 'processing']
    ).order_by('-request_date')[:5]

    # Get low stock medications
    low_stock_medications = MedicationInventory.objects.filter(
        stock_quantity__lte=F('reorder_level'),
        stock_quantity__gt=0 # Ensure it's not completely out of stock if that's a separate category
    ).select_related('medication', 'dispensary').order_by('stock_quantity')[:5]

    # Get recent invoices
    recent_invoices = Invoice.objects.order_by('-created_at')[:5]

    # Get revenue statistics
    today_revenue = Payment.objects.filter(
        payment_date=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    this_week_start = today - timedelta(days=today.weekday())
    this_week_revenue = Payment.objects.filter(
        payment_date__gte=this_week_start,
        payment_date__lte=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    this_month_start = today.replace(day=1)
    this_month_revenue = Payment.objects.filter(
        payment_date__gte=this_month_start,
        payment_date__lte=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Get appointment statistics
    appointment_stats = {
        'today': Appointment.objects.filter(appointment_date=today).count(),
        'scheduled': Appointment.objects.filter(status='scheduled').count(),
        'completed': Appointment.objects.filter(status='completed').count(),
        'cancelled': Appointment.objects.filter(status='cancelled').count(),
    }

    # Get counts for new modules (for system overview)
    ophthalmic_records_count = OphthalmicRecord.objects.count()
    ent_records_count = EntRecord.objects.count()
    oncology_records_count = OncologyRecord.objects.count()
    scbu_records_count = ScbuRecord.objects.count()
    anc_records_count = AncRecord.objects.count()
    labor_records_count = LaborRecord.objects.count()
    icu_records_count = IcuRecord.objects.count()
    family_planning_records_count = Family_planningRecord.objects.count()
    gynae_emergency_records_count = Gynae_emergencyRecord.objects.count()

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
        'ophthalmic_records_count': ophthalmic_records_count,
        'ent_records_count': ent_records_count,
        'oncology_records_count': oncology_records_count,
        'scbu_records_count': scbu_records_count,
        'anc_records_count': anc_records_count,
        'labor_records_count': labor_records_count,
        'icu_records_count': icu_records_count,
        'family_planning_records_count': family_planning_records_count,
        'gynae_emergency_records_count': gynae_emergency_records_count,
        'today_appointments': today_appointments,
        'pending_prescriptions': pending_prescriptions,
        'pending_tests': pending_tests,
        'low_stock_medications': low_stock_medications,
        'recent_invoices': recent_invoices,
        'today_revenue': today_revenue,
        'this_week_revenue': this_week_revenue,
        'this_month_revenue': this_month_revenue,
        'appointment_stats': appointment_stats,
        'ent_follow_up_count': ent_follow_up_count,  # Add this line
    }

    return render(request, 'dashboard/dashboard_modern.html', context)


@login_required
def system_overview(request):
    """View to display a system configuration and data overview."""
    context = {'title': 'System Configuration Overview'}

    # Accounts App
    context['total_users'] = CustomUser.objects.count()
    context['superuser_count'] = CustomUser.objects.filter(is_superuser=True).count()
    context['staff_count'] = CustomUser.objects.filter(is_staff=True, is_superuser=False).count()
    try:
        # Get role counts from the many-to-many relationship
        from accounts.models import Role
        context['user_roles'] = Role.objects.annotate(count=Count('customuser_roles')).values('name', 'count').order_by('-count')
    except Exception:
        context['user_roles'] = []

    # Patients App
    context['total_patients_records'] = Patient.objects.count()
    context['active_patients'] = Patient.objects.filter(is_active=True).count()

    # Appointments App
    context['total_appointments_records'] = Appointment.objects.count()
    context['scheduled_appointments'] = Appointment.objects.filter(status='scheduled').count()
    context['completed_appointments'] = Appointment.objects.filter(status='completed').count()
    context['cancelled_appointments'] = Appointment.objects.filter(status='cancelled').count()
    context['appointment_types'] = Appointment.objects.values('appointment_type').annotate(count=Count('appointment_type')).order_by('-count')

    # Laboratory App
    context['lab_test_categories'] = TestCategory.objects.count()
    context['lab_tests_defined'] = Test.objects.count()
    context['active_lab_tests'] = Test.objects.filter(is_active=True).count()
    context['total_test_requests'] = TestRequest.objects.count()
    context['pending_test_requests'] = TestRequest.objects.filter(status='pending').count()
    context['completed_test_requests'] = TestRequest.objects.filter(status='completed').count()

    # Pharmacy App
    context['medication_categories'] = MedicationCategory.objects.count()
    context['medications_in_inventory'] = Medication.objects.count()
    context['active_medications'] = Medication.objects.filter(is_active=True).count()
    context['low_stock_medications_count'] = MedicationInventory.objects.filter(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0).count()
    context['out_of_stock_medications_count'] = MedicationInventory.objects.filter(stock_quantity=0).count()
    context['total_prescriptions_issued'] = Prescription.objects.count()

    # Billing App
    context['billable_service_categories'] = ServiceCategory.objects.count()
    context['billable_services_defined'] = Service.objects.count()
    context['total_invoices'] = Invoice.objects.count()
    context['paid_invoices'] = Invoice.objects.filter(status='paid').count()
    context['pending_invoices'] = Invoice.objects.filter(status='pending').count()
    context['overdue_invoices'] = Invoice.objects.filter(status='overdue').count()
    context['total_payments_recorded'] = Payment.objects.count()
    context['total_revenue_collected'] = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0.00

    # Consultations App
    context['total_consultations'] = Consultation.objects.count()
    context['consulting_rooms'] = ConsultingRoom.objects.count()
    context['active_consulting_rooms'] = ConsultingRoom.objects.filter(is_active=True).count()
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