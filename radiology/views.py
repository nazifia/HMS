from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import RadiologyCategory, RadiologyTest, RadiologyOrder, RadiologyResult
from patients.models import Patient
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from .forms import RadiologyOrderForm, RadiologyResultForm
from core.decorators import department_access_required
from core.department_dashboard_utils import (
    get_user_department,
    build_department_dashboard_context,
    build_enhanced_dashboard_context,
    categorize_referrals,
    get_daily_trend_data,
    get_status_distribution,
    get_urgent_items,
    calculate_completion_rate,
    get_active_staff
)
import json

@login_required
def index(request):
    """Enhanced Radiology dashboard with charts, metrics, and referral integration"""
    from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DurationField
    from datetime import datetime, timedelta

    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Get user's department for referral integration
    user_department = get_user_department(request.user)

    # Superusers don't need department assignment warnings
    if not user_department and not request.user.is_superuser:
        messages.warning(request, "You are not assigned to a department. Some features may be limited.")
        user_department = None

    # Build enhanced context with charts and trends
    # Note: RadiologyOrder uses 'order_date' instead of 'created_at'
    if user_department:
        # Get chart data manually since RadiologyOrder uses 'order_date' not 'created_at'
        context = build_department_dashboard_context(
            department=user_department,
            record_model=RadiologyOrder,
            record_queryset=RadiologyOrder.objects.all()
        )

        # Add chart data with correct date field
        context['daily_trend'] = get_daily_trend_data(RadiologyOrder, days=7, date_field='order_date')
        context['status_distribution'] = get_status_distribution(RadiologyOrder, status_field='status')
        context['completion_rate'] = calculate_completion_rate(RadiologyOrder, status_field='status', completed_status='completed')
        context['urgent_items'] = get_urgent_items(RadiologyOrder, priority_field='priority')
        context['active_staff'] = get_active_staff(user_department)
    else:
        # Fallback for users without department
        context = {
            'total_records': RadiologyOrder.objects.count(),
            'recent_records': RadiologyOrder.objects.select_related('patient', 'test').order_by('-order_date')[:10]
        }

    # Get counts for dashboard cards
    pending_count = RadiologyOrder.objects.filter(status='pending').count()
    awaiting_payment = RadiologyOrder.objects.filter(status='awaiting_payment').count()
    scheduled_count = RadiologyOrder.objects.filter(status='scheduled').count()
    completed_count = RadiologyOrder.objects.filter(status='completed').count()
    total_count = RadiologyOrder.objects.count()

    # Today's statistics
    today_orders = RadiologyOrder.objects.filter(order_date__date=today).count()
    today_completed = RadiologyOrder.objects.filter(order_date__date=today, status='completed').count()

    # This week's statistics
    week_orders = RadiologyOrder.objects.filter(order_date__date__gte=week_start).count()
    week_completed = RadiologyOrder.objects.filter(order_date__date__gte=week_start, status='completed').count()

    # This month's statistics
    month_orders = RadiologyOrder.objects.filter(order_date__date__gte=month_start).count()
    month_revenue = RadiologyOrder.objects.filter(
        order_date__date__gte=month_start,
        invoice__isnull=False
    ).aggregate(total=Sum('invoice__total_amount'))['total'] or 0

    # Get urgent/emergency imaging orders
    urgent_orders = RadiologyOrder.objects.filter(
        status__in=['pending', 'scheduled', 'awaiting_payment'],
        priority__in=['urgent', 'emergency']
    ).select_related('patient', 'test', 'referring_doctor').order_by('-priority', 'order_date')[:10]

    # Get emergency orders count
    emergency_orders = RadiologyOrder.objects.filter(
        status__in=['pending', 'scheduled'],
        priority='emergency'
    ).count()

    # Calculate average reporting time (for completed orders in last 30 days)
    avg_reporting_time = RadiologyOrder.objects.filter(
        status='completed',
        created_at__gte=timezone.now() - timedelta(days=30),
        completed_date__isnull=False
    ).annotate(
        reporting_time=ExpressionWrapper(
            F('completed_date') - F('created_at'),
            output_field=DurationField()
        )
    ).aggregate(avg=Avg('reporting_time'))['avg']

    # Format reporting time
    if avg_reporting_time:
        hours = avg_reporting_time.total_seconds() / 3600
        avg_reporting_hours = round(hours, 1)
    else:
        avg_reporting_hours = 0

    # Get modality distribution (by test type)
    modality_data = RadiologyOrder.objects.values('test__name').annotate(count=Count('id')).order_by('-count')[:5]
    modality_labels = [item['test__name'] for item in modality_data]
    modality_counts = [item['count'] for item in modality_data]

    # Get results needing verification
    results_needing_verification = RadiologyResult.objects.filter(
        verified_by__isnull=True
    ).select_related('order__patient').count()

    # Get completed orders without results (for action alert)
    orders_needing_results = RadiologyOrder.objects.filter(
        status='completed',
        result__isnull=True
    ).select_related('patient', 'test').order_by('-order_date')[:10]

    # Build query with filters first
    recent_orders_query = RadiologyOrder.objects.select_related('patient', 'test', 'referring_doctor', 'result')

    # Apply filters if provided
    status_filter = request.GET.get('status')
    if status_filter:
        recent_orders_query = recent_orders_query.filter(status=status_filter)

    patient_id_filter = request.GET.get('patient_id')
    if patient_id_filter:
        recent_orders_query = recent_orders_query.filter(patient__patient_id=patient_id_filter)

    # Apply ordering after all filters are applied to ensure most recent at top
    recent_orders = recent_orders_query.order_by('-order_date', '-id')[:20]

    # Get patients with radiology orders (more relevant than all patients)
    patients = Patient.objects.filter(radiology_orders__isnull=False).distinct()[:50]
    # Add patient results page link to each patient in the dashboard context
    for patient in patients:
        patient.results_url = f"/radiology/patient/{patient.id}/results/"
        patient.order_count = patient.radiology_orders.count()

    # Add referral integration if user has a department
    pending_referrals = []
    pending_referrals_count = 0
    pending_authorizations = 0
    categorized_referrals = None

    if user_department:
        from consultations.models import Referral
        from core.department_dashboard_utils import get_pending_referrals, get_department_referral_statistics

        pending_referrals = get_pending_referrals(user_department, limit=5)
        referral_stats = get_department_referral_statistics(user_department)
        pending_referrals_count = referral_stats['pending_referrals']
        pending_authorizations = referral_stats['requiring_authorization']
        categorized_referrals = categorize_referrals(user_department)

    # Update context with new metrics
    context.update({
        'pending_count': pending_count,
        'awaiting_payment': awaiting_payment,
        'scheduled_count': scheduled_count,
        'completed_count': completed_count,
        'total_count': total_count,
        'today_orders': today_orders,
        'today_completed': today_completed,
        'week_orders': week_orders,
        'week_completed': week_completed,
        'month_orders': month_orders,
        'month_revenue': month_revenue,
        'urgent_orders': urgent_orders,
        'emergency_orders': emergency_orders,
        'avg_reporting_hours': avg_reporting_hours,
        'results_needing_verification': results_needing_verification,
        'orders_needing_results': orders_needing_results,
        'modality_labels': json.dumps(modality_labels),
        'modality_counts': json.dumps(modality_counts),
        'recent_orders': recent_orders,
        # Referral integration
        'pending_referrals': pending_referrals,
        'pending_referrals_count': pending_referrals_count,
        'pending_authorizations': pending_authorizations,
        'categorized_referrals': categorized_referrals,
        'user_department': user_department,
        'patients': patients,
        'today': today,
        'week_start': week_start,
        'month_start': month_start,
    })

    return render(request, 'radiology/index.html', context)

@login_required
def order_radiology(request, patient_id=None):
    """View to create a new radiology order"""
    from .models import RadiologyTest  # ensure import
    from decimal import Decimal
    from billing.models import Invoice, InvoiceItem, Service, ServiceCategory
    from django.db import transaction
    from datetime import timedelta
    
    selected_patient = None
    initial = {}
    if patient_id:
        selected_patient = get_object_or_404(Patient, pk=patient_id)
        initial['patient'] = selected_patient.id
    patients = Patient.objects.all()
    tests = RadiologyTest.objects.filter(is_active=True)
    if request.method == 'POST':
        form = RadiologyOrderForm(request.POST, request=request)
        if form.is_valid():
            # Get authorization code if provided
            authorization_code_id = request.POST.get('authorization_code')
            authorization_code = None
            if authorization_code_id:
                try:
                    from nhia.models import AuthorizationCode
                    authorization_code = AuthorizationCode.objects.get(id=authorization_code_id)
                    # Verify the authorization code is valid
                    if not authorization_code.is_valid():
                        messages.error(request, "The provided authorization code is not valid.")
                        return redirect('radiology:order_radiology', patient_id=patient_id) if patient_id else redirect('radiology:order_radiology')
                    # Verify the authorization code is for this patient
                    if authorization_code.patient != selected_patient:
                        messages.error(request, "The provided authorization code is not for this patient.")
                        return redirect('radiology:order_radiology', patient_id=patient_id) if patient_id else redirect('radiology:order_radiology')
                except AuthorizationCode.DoesNotExist:
                    messages.error(request, "The provided authorization code does not exist.")
                    return redirect('radiology:order_radiology', patient_id=patient_id) if patient_id else redirect('radiology:order_radiology')
            
            with transaction.atomic():
                order = form.save(commit=False)
                if not order.referring_doctor_id:
                    order.referring_doctor = request.user
                order.status = 'pending'
                order.order_date = timezone.now()
                order.authorization_code = authorization_code  # Set authorization code if provided
                order.save()
                
                # Create an invoice for this radiology order
                subtotal = Decimal(order.test.price)
                tax_amount = Decimal('0.00')
                total_amount = subtotal + tax_amount
                due_date = order.order_date.date() + timedelta(days=7) # Example: due in 7 days

                # If authorization code is provided, mark as paid
                invoice_status = 'paid' if authorization_code else 'pending'
                payment_method = 'insurance' if authorization_code else None
                payment_date = timezone.now().date() if authorization_code else None

                invoice = Invoice.objects.create(
                    patient=order.patient,
                    invoice_date=order.order_date.date(),
                    due_date=due_date,
                    status=invoice_status, # Mark as paid if authorization code is used
                    radiology_order=order, # Link to the RadiologyOrder
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    amount_paid=total_amount if authorization_code else Decimal('0.00'),
                    payment_method=payment_method,
                    payment_date=payment_date,
                    created_by=request.user,
                    source_app='radiology'
                )
                
                # Update order with invoice
                order.invoice = invoice
                order.status = 'payment_confirmed' if authorization_code else 'pending'
                order.save()
                
                # Create InvoiceItem for the radiology test
                radiology_service_category, _ = ServiceCategory.objects.get_or_create(name="Radiology Services")
                service, _ = Service.objects.get_or_create(
                    name=f"Radiology Test: {order.test.name}", 
                    category=radiology_service_category,
                    defaults={'price': order.test.price, 'description': order.test.description or f"Radiology test: {order.test.name}"}
                )
                if service.price != order.test.price: # Update service price if it differs from test price
                    service.price = order.test.price
                    service.save()

                InvoiceItem.objects.create(
                    invoice=invoice,
                    service=service, 
                    description=f"Radiology Test: {order.test.name}",
                    quantity=1,
                    unit_price=Decimal(order.test.price),
                    tax_percentage=service.tax_percentage, # Use tax from service if defined
                    tax_amount=(Decimal(order.test.price) * service.tax_percentage) / Decimal('100'),
                    total_amount=Decimal(order.test.price) + ((Decimal(order.test.price) * service.tax_percentage) / Decimal('100'))
                )
                
                # If authorization code was used, mark it as used
                if authorization_code:
                    authorization_code.mark_as_used(f"Radiology Order #{order.id}")
            
            messages.success(request, f'Radiology order created successfully. Invoice #{invoice.invoice_number} generated and is {"paid via authorization code" if authorization_code else "pending payment"}.')
            return redirect('radiology:order_detail', order_id=order.id)
    else:
        form = RadiologyOrderForm(initial=initial, request=request)
    context = {
        'form': form,
        'selected_patient': selected_patient,
        'patients': patients,
        'tests': tests,
    }
    return render(request, 'radiology/order_form.html', context)

@login_required
def order_detail(request, order_id):
    """View to show radiology order details"""
    order = None
    result = None
    try:
        order = RadiologyOrder.objects.get(pk=order_id)
    except RadiologyOrder.DoesNotExist:
        order = None
    if order:
        try:
            result = order.result
        except RadiologyResult.DoesNotExist:
            result = None
    context = {
        'order': order,
        'order_id': order_id,
        'result': result,
    }
    return render(request, 'radiology/order_detail.html', context)

@login_required
def edit_order(request, order_id):
    order = get_object_or_404(RadiologyOrder, pk=order_id)
    if request.method == 'POST':
        form = RadiologyOrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, 'Order updated successfully.')
            return redirect('radiology:order_detail', order_id=order.id)
    else:
        form = RadiologyOrderForm(instance=order)
    return render(request, 'radiology/order_form.html', {'form': form, 'order': order, 'selected_patient': order.patient})

@login_required
@require_POST
def schedule_order(request, order_id):
    order = get_object_or_404(RadiologyOrder, pk=order_id)

    # Check authorization requirement before scheduling
    can_process, message = order.can_be_processed()
    if not can_process:
        messages.error(request, message)
        return redirect('radiology:order_detail', order_id=order.id)

    order.status = 'scheduled'
    order.scheduled_date = timezone.now()
    order.save()
    messages.success(request, 'Order scheduled.')
    return redirect('radiology:order_detail', order_id=order.id)

@login_required
@require_POST
def mark_completed(request, order_id):
    order = get_object_or_404(RadiologyOrder, pk=order_id)

    # Check authorization requirement before marking as completed
    can_process, message = order.can_be_processed()
    if not can_process:
        messages.error(request, message)
        return redirect('radiology:order_detail', order_id=order.id)

    order.status = 'completed'
    order.completed_date = timezone.now()
    order.save()
    messages.success(request, 'Order marked as completed.')
    return redirect('radiology:order_detail', order_id=order.id)

@login_required
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(RadiologyOrder, pk=order_id)
    order.status = 'cancelled'
    order.save()
    messages.success(request, 'Order cancelled.')
    return redirect('radiology:order_detail', order_id=order.id)

@login_required
def add_result(request, order_id):
    order = get_object_or_404(RadiologyOrder, pk=order_id)

    # Check if result can be added to this order
    can_add, message = order.can_add_result()
    if not can_add:
        messages.error(request, message)
        return redirect('radiology:order_detail', order_id=order.id)

    try:
        result = order.result
    except RadiologyResult.DoesNotExist:
        result = None
    if request.method == 'POST':
        form = RadiologyResultForm(request.POST, request.FILES, instance=result)
        if form.is_valid():
            result_obj = form.save(commit=False)
            result_obj.order = order
            result_obj.performed_by = request.user
            # Set default values for new fields
            if not result_obj.result_status:
                result_obj.result_status = 'submitted'
            if not result_obj.study_date:
                result_obj.study_date = timezone.now().date()
            if not result_obj.study_time:
                result_obj.study_time = timezone.now().time()
            result_obj.save()
            messages.success(request, 'Result saved successfully.')
            return redirect('radiology:order_detail', order_id=order.id)
    else:
        form = RadiologyResultForm(instance=result)
    return render(request, 'radiology/result_form.html', {'form': form, 'order': order, 'result': result})

@login_required
def radiology_sales_report(request):
    """View for daily radiology tests by technician and total monthly radiology revenue."""
    from django.db.models import Sum, Count
    today = timezone.now().date()
    month_start = today.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month - timezone.timedelta(days=1)

    # Daily radiology tests by technician (if technician is set)
    daily_tests = (
        RadiologyOrder.objects.filter(order_date__date=today, technician__isnull=False)
        .values('technician__id', 'technician__first_name', 'technician__last_name')
        .annotate(total_tests=Count('id'), total_revenue=Sum('invoice__total_amount'))
        .order_by('-total_tests')
    )

    # Total monthly revenue
    monthly_revenue = (
        RadiologyOrder.objects.filter(order_date__date__gte=month_start, order_date__date__lte=month_end)
        .aggregate(total=Sum('invoice__total_amount'))['total'] or 0
    )

    context = {
        'daily_tests': daily_tests,
        'monthly_revenue': monthly_revenue,
        'today': today,
        'month_start': month_start,
        'month_end': month_end,
        'title': 'Radiology Report Dashboard',
    }
    return render(request, 'radiology/sales_report.html', context)

@login_required
def patient_radiology_results(request, patient_id):
    """View all radiology results for a given patient."""
    patient = get_object_or_404(Patient, pk=patient_id)
    # Get all completed radiology orders with results for this patient
    orders_with_results = RadiologyOrder.objects.filter(patient=patient, status='completed').select_related('test', 'result').order_by('-order_date')
    results = RadiologyResult.objects.filter(order__in=orders_with_results).select_related('order', 'performed_by')

    context = {
        'patient': patient,
        'results': results,
        'orders_with_results': orders_with_results,
        'results': results,
        'title': f'Radiology Results for {patient.get_full_name()}',
    }
    return render(request, 'radiology/patient_results.html', context)


@login_required
def radiology_statistics_report(request):
    """Comprehensive radiology statistics and reporting"""
    from django.db.models import Q, Sum, Count, Avg
    from datetime import datetime, timedelta
    from decimal import Decimal

    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    test_category_id = request.GET.get('test_category')
    test_id = request.GET.get('test')
    status = request.GET.get('status')
    priority = request.GET.get('priority')

    # Default date range (last 30 days)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Base queryset for radiology orders
    radiology_orders = RadiologyOrder.objects.filter(
        order_date__date__gte=start_date,
        order_date__date__lte=end_date
    ).select_related('patient', 'test', 'referring_doctor', 'technician')

    # Apply filters
    if test_category_id:
        radiology_orders = radiology_orders.filter(test__category_id=test_category_id)

    if test_id:
        radiology_orders = radiology_orders.filter(test_id=test_id)

    if status:
        radiology_orders = radiology_orders.filter(status=status)

    if priority:
        radiology_orders = radiology_orders.filter(priority=priority)

    # Orders by category
    category_stats = radiology_orders.values(
        'test__category__name',
        'test__category__id'
    ).annotate(
        total_orders=Count('id'),
        total_revenue=Sum('test__price'),
        avg_price=Avg('test__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_orders')

    # Top tests by volume
    top_tests = radiology_orders.values(
        'test__name',
        'test__id'
    ).annotate(
        total_orders=Count('id'),
        total_revenue=Sum('test__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_orders')[:10]

    # Status distribution
    status_stats = radiology_orders.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Priority distribution
    priority_stats = radiology_orders.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')

    # Daily order volume trend
    daily_stats = radiology_orders.extra(
        select={'day': 'DATE(order_date)'}
    ).values('day').annotate(
        daily_orders=Count('id'),
        daily_revenue=Sum('test__price')
    ).order_by('day')

    # Top referring doctors
    top_doctors = radiology_orders.values(
        'referring_doctor__first_name',
        'referring_doctor__last_name',
        'referring_doctor__id'
    ).annotate(
        total_orders=Count('id'),
        total_revenue=Sum('test__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_orders')[:10]

    # Top technicians
    top_technicians = radiology_orders.filter(
        technician__isnull=False
    ).values(
        'technician__first_name',
        'technician__last_name',
        'technician__id'
    ).annotate(
        total_orders=Count('id'),
        total_revenue=Sum('test__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_orders')[:10]

    # Overall statistics
    overall_stats = radiology_orders.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('test__price'),
        avg_revenue_per_order=Avg('test__price'),
        unique_patients=Count('patient', distinct=True),
        unique_tests=Count('test', distinct=True),
        unique_doctors=Count('referring_doctor', distinct=True)
    )

    # Completion rate (completed vs total)
    completed_orders = radiology_orders.filter(status='completed').count()
    total_orders = radiology_orders.count()
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

    # Average turnaround time for completed orders
    completed_with_times = radiology_orders.filter(
        status='completed',
        completed_date__isnull=False
    )

    turnaround_times = []
    for order in completed_with_times:
        if order.completed_date and order.order_date:
            delta = order.completed_date - order.order_date
            turnaround_times.append(delta.total_seconds() / 3600)  # Convert to hours

    avg_turnaround_hours = sum(turnaround_times) / len(turnaround_times) if turnaround_times else 0

    # Get filter options
    test_categories = RadiologyCategory.objects.all().order_by('name')
    tests = RadiologyTest.objects.filter(is_active=True).order_by('name')

    context = {
        'title': 'Radiology Statistics and Reports',
        'start_date': start_date,
        'end_date': end_date,
        'category_stats': category_stats,
        'top_tests': top_tests,
        'top_doctors': top_doctors,
        'top_technicians': top_technicians,
        'status_stats': status_stats,
        'priority_stats': priority_stats,
        'daily_stats': daily_stats,
        'overall_stats': overall_stats,
        'completion_rate': completion_rate,
        'avg_turnaround_hours': avg_turnaround_hours,
        'test_categories': test_categories,
        'tests': tests,
        'selected_category': test_category_id,
        'selected_test': test_id,
        'selected_status': status,
        'selected_priority': priority,
    }

    return render(request, 'radiology/reports/radiology_statistics.html', context)
