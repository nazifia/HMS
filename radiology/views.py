from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import RadiologyCategory, RadiologyTest, RadiologyOrder, RadiologyResult
from patients.models import Patient
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from .forms import RadiologyOrderForm, RadiologyResultForm

@login_required
def index(request):
    """Radiology dashboard view"""
    # Get counts for dashboard cards
    pending_count = RadiologyOrder.objects.filter(status='pending').count()
    scheduled_count = RadiologyOrder.objects.filter(status='scheduled').count()
    completed_count = RadiologyOrder.objects.filter(status='completed').count()
    total_count = RadiologyOrder.objects.count()

    # Get recent orders for the table
    recent_orders = RadiologyOrder.objects.all().order_by('-order_date')[:10]

    # Get all active patients for the dashboard
    patients = Patient.objects.all()
    # Add patient results page link to each patient in the dashboard context
    for patient in patients:
        patient.results_url = f"/radiology/patient/{patient.id}/results/"

    context = {
        'pending_count': pending_count,
        'scheduled_count': scheduled_count,
        'completed_count': completed_count,
        'total_count': total_count,
        'recent_orders': recent_orders,
        'patients': patients,  # Add patients to context
    }

    return render(request, 'radiology/index.html', context)

@login_required
def order_radiology(request, patient_id=None):
    """View to create a new radiology order"""
    from .models import RadiologyTest  # ensure import
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
            order = form.save(commit=False)
            if not order.referring_doctor_id:
                order.referring_doctor = request.user
            order.status = 'pending'
            order.order_date = timezone.now()
            order.save()
            messages.success(request, 'Radiology order created successfully')
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
    order.status = 'scheduled'
    order.scheduled_date = timezone.now()
    order.save()
    messages.success(request, 'Order scheduled.')
    return redirect('radiology:order_detail', order_id=order.id)

@login_required
@require_POST
def mark_completed(request, order_id):
    order = get_object_or_404(RadiologyOrder, pk=order_id)
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
        'orders_with_results': orders_with_results,
        'results': results,
        'title': f'Radiology Results for {patient.get_full_name()}',
    }
    return render(request, 'radiology/patient_results.html', context)
