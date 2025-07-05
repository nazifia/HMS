from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta

from patients.models import Patient
from appointments.models import Appointment
from pharmacy.models import Medication, Prescription, MedicationCategory
from laboratory.models import TestRequest, TestResult, Test, TestCategory
from billing.models import Invoice, Payment, Service, ServiceCategory
from consultations.models import Consultation, ConsultingRoom, Referral, WaitingList
from hr.models import Department as HRDepartment # Assuming 'Department' from hr.models is the intended HRDepartment.
from inpatient.models import Admission, Bed, Ward
from accounts.models import CustomUserProfile # Assuming UserProfile holds role and department for staff
from django.contrib.auth.models import User

@login_required
def dashboard(request):
    """Main dashboard view"""
    today = timezone.now().date()

    # Get counts for various entities
    total_patients = Patient.objects.filter(is_active=True).count()
    total_appointments = Appointment.objects.count()
    total_prescriptions = Prescription.objects.count()
    total_tests = TestRequest.objects.count()

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
    low_stock_medications = Medication.objects.filter(
        is_active=True,
        stock_quantity__lte=F('reorder_level'),
        stock_quantity__gt=0 # Ensure it's not completely out of stock if that's a separate category
    ).order_by('stock_quantity')[:5]

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

    context = {
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'total_prescriptions': total_prescriptions,
        'total_tests': total_tests,
        'today_appointments': today_appointments,
        'pending_prescriptions': pending_prescriptions,
        'pending_tests': pending_tests,
        'low_stock_medications': low_stock_medications,
        'recent_invoices': recent_invoices,
        'today_revenue': today_revenue,
        'this_week_revenue': this_week_revenue,
        'this_month_revenue': this_month_revenue,
        'appointment_stats': appointment_stats,
    }

    return render(request, 'dashboard/dashboard_modern.html', context)

@login_required
def system_overview(request):
    """View to display a system configuration and data overview."""
    context = {'title': 'System Configuration Overview'}

    # Accounts App
    context['total_users'] = User.objects.count()
    context['superuser_count'] = User.objects.filter(is_superuser=True).count()
    context['staff_count'] = User.objects.filter(is_staff=True, is_superuser=False).count()
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
    context['low_stock_medications_count'] = Medication.objects.filter(is_active=True, stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0).count()
    context['out_of_stock_medications_count'] = Medication.objects.filter(is_active=True, stock_quantity=0).count()
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
    context['total_employees'] = User.objects.filter(is_staff=True).count()
    context['active_employees'] = User.objects.filter(is_staff=True, is_active=True).count()

    # Inpatient App
    context['total_wards'] = Ward.objects.count()
    context['total_beds'] = Bed.objects.count()
    context['occupied_beds'] = Bed.objects.filter(is_occupied=True).count()
    context['available_beds'] = Bed.objects.filter(is_occupied=False, is_active=True).count()
    context['total_admissions'] = Admission.objects.count()
    context['current_admissions'] = Admission.objects.filter(discharge_date__isnull=True).count()

    return render(request, 'dashboard/system_overview.html', context)
