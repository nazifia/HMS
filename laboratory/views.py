from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import models
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction # Ensure transaction is imported
from billing.models import Invoice, InvoiceItem, Service, ServiceCategory # Added ServiceCategory
from datetime import timedelta # For due date calculation
import datetime # Import the datetime module itself
from decimal import Decimal

from .models import (
    TestCategory, Test, TestParameter, TestRequest,
    TestResult, TestResultParameter
)
from .forms import (
    TestCategoryForm, TestForm, TestParameterForm, TestRequestForm,
    TestResultForm, TestResultParameterForm, TestSearchForm, TestRequestSearchForm,
    TestResultParameterFormSet # Import the new formset
)
from patients.models import Patient
from accounts.models import CustomUser
import os
from core.models import send_notification_email, InternalNotification

@login_required
def result_list(request):
    """Enhanced view for listing all test results with comprehensive search"""
    from .forms import TestResultSearchForm

    results_list = TestResult.objects.select_related(
        'test_request__patient', 'test', 'performed_by', 'verified_by'
    ).all().order_by('-result_date')

    # Enhanced search form
    search_form = TestResultSearchForm(request.GET or None)

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        patient_number = search_form.cleaned_data.get('patient_number')
        test_name = search_form.cleaned_data.get('test_name')
        test_category = search_form.cleaned_data.get('test_category')
        status = search_form.cleaned_data.get('status')
        performed_by = search_form.cleaned_data.get('performed_by')
        verified_by = search_form.cleaned_data.get('verified_by')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        # Enhanced patient search by name, number, or phone
        if search_query:
            results_list = results_list.filter(
                Q(test_request__patient__first_name__icontains=search_query) |
                Q(test_request__patient__last_name__icontains=search_query) |
                Q(test_request__patient__middle_name__icontains=search_query) |
                Q(test_request__patient__patient_number__icontains=search_query) |
                Q(test_request__patient__phone_number__icontains=search_query)
            )

        if patient_number:
            results_list = results_list.filter(
                Q(test_request__patient__patient_number__icontains=patient_number)
            )

        if test_name:
            results_list = results_list.filter(
                test__name__icontains=test_name
            )

        if test_category:
            results_list = results_list.filter(
                test__category=test_category
            )

        if status:
            # Map status to appropriate field filtering
            if status == 'verified':
                results_list = results_list.filter(verified_by__isnull=False)
            elif status == 'pending':
                results_list = results_list.filter(
                    performed_by__isnull=True,
                    verified_by__isnull=True
                )
            elif status == 'in_progress':
                results_list = results_list.filter(
                    performed_by__isnull=False,
                    verified_by__isnull=True
                )
            elif status == 'completed':
                results_list = results_list.filter(
                    performed_by__isnull=False
                )

        if performed_by:
            results_list = results_list.filter(performed_by=performed_by)

        if verified_by:
            results_list = results_list.filter(verified_by=verified_by)

        if date_from:
            results_list = results_list.filter(result_date__gte=date_from)

        if date_to:
            results_list = results_list.filter(result_date__lte=date_to)

    # Legacy query parameter support
    query = request.GET.get('q')
    if query and not search_form.is_valid():
        results_list = results_list.filter(
            Q(test_request__patient__first_name__icontains=query) |
            Q(test_request__patient__last_name__icontains=query) |
            Q(test__name__icontains=query) |
            Q(test_request__patient__patient_number__icontains=query)
        )

    paginator = Paginator(results_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'title': 'Test Results',
        'query': query,
    }

    return render(request, 'laboratory/result_list.html', context)

@login_required
def result_detail(request, result_id):
    """View for displaying a single test result"""
    result = get_object_or_404(
        TestResult.objects.select_related(
            'test_request__patient', 'test__category', 'performed_by', 'verified_by', 'sample_collected_by'
        ),
        id=result_id
    )
    parameters = result.parameters.select_related('parameter').all()

    context = {
        'result': result,
        'parameters': parameters,
        'title': f'Result for {result.test.name}'
    }
    return render(request, 'laboratory/result_detail.html', context)

@login_required
def edit_test_result(request, result_id):
    """View for editing a test result"""
    result = get_object_or_404(TestResult.objects.select_related('test_request'), id=result_id)
    test_request = result.test_request

    if request.method == 'POST':
        form = TestResultForm(request.POST, request.FILES, instance=result)
        if form.is_valid():
            form.save()
            messages.success(request, 'Test result updated successfully.')
            return redirect('laboratory:result_detail', result_id=result.id)
    else:
        form = TestResultForm(instance=result)

    context = {
        'form': form,
        'result': result,
        'test_request': test_request,
        'title': 'Edit Test Result'
    }
    return render(request, 'laboratory/test_result_form.html', context)

# Test Management Views
@login_required
def test_list(request):
    """View for listing all tests"""
    search_form = TestSearchForm(request.GET)
    tests = Test.objects.all().order_by('name')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        category = search_form.cleaned_data.get('category')
        sample_type = search_form.cleaned_data.get('sample_type')
        is_active = search_form.cleaned_data.get('is_active')

        if search_query:
            tests = tests.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        if category:
            tests = tests.filter(category=category)

        if sample_type:
            tests = tests.filter(sample_type=sample_type)

        if is_active:
            if is_active == 'active':
                tests = tests.filter(is_active=True)
            elif is_active == 'inactive':
                tests = tests.filter(is_active=False)

    # Pagination
    paginator = Paginator(tests, 10)  # Show 10 tests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories for the filter
    categories = TestCategory.objects.all()

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'categories': categories,
        'total_tests': tests.count(),
        'active_tests': tests.filter(is_active=True).count(),
        'inactive_tests': tests.filter(is_active=False).count(),
    }

    return render(request, 'laboratory/test_list.html', context)

@login_required
def add_test(request):
    """View for adding a new test"""
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save()
            messages.success(request, f'Test {test.name} has been added successfully.')
            return redirect('laboratory:tests')
    else:
        form = TestForm()

    context = {
        'form': form,
        'title': 'Add New Test'
    }

    return render(request, 'laboratory/test_form.html', context)

@login_required
def edit_test(request, test_id):
    """View for editing a test"""
    test = get_object_or_404(Test, id=test_id)
    parameters = test.parameters.all().order_by('order')

    if request.method == 'POST' and 'add_parameter' not in request.POST:
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, f'Test {test.name} has been updated successfully.')
            return redirect('laboratory:edit_test', test_id=test.id) # Redirect to same page to see changes
    else:
        form = TestForm(instance=test)

    if request.method == 'POST' and 'add_parameter' in request.POST:
        parameter_form = TestParameterForm(request.POST, prefix="param")
        if parameter_form.is_valid():
            parameter = parameter_form.save(commit=False)
            parameter.test = test
            parameter.save()
            messages.success(request, f'Parameter {parameter.name} added to test.')
            return redirect('laboratory:edit_test', test_id=test.id)
    else:
        parameter_form = TestParameterForm(prefix="param")

    context = {
        'form': form,
        'parameter_form': parameter_form,
        'test': test,
        'parameters': parameters,
        'title': f'Edit Test: {test.name}'
    }
    return render(request, 'laboratory/test_form.html', context)

@login_required
def delete_test(request, test_id):
    """View for deleting a test (soft delete)"""
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        test.is_active = False
        test.save()
        messages.success(request, f'Test {test.name} has been deactivated.')
        return redirect('laboratory:tests')

    context = {
        'test': test
    }

    return render(request, 'laboratory/delete_test.html', context)

@login_required
def delete_parameter(request, parameter_id):
    """View for deleting a test parameter"""
    parameter = get_object_or_404(TestParameter, id=parameter_id)
    test_id = parameter.test.id

    if request.method == 'POST':
        parameter.delete()
        messages.success(request, f'Parameter {parameter.name} has been deleted.')
        return redirect('laboratory:edit_test', test_id=test_id)

    context = {
        'parameter': parameter,
        'test': parameter.test
    }

    return render(request, 'laboratory/delete_parameter.html', context)

@login_required
def manage_categories(request):
    """View for managing test categories"""
    categories = TestCategory.objects.all().order_by('name')

    if request.method == 'POST':
        form = TestCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} has been added successfully.')
            return redirect('laboratory:manage_categories')
    else:
        form = TestCategoryForm()

    context = {
        'form': form,
        'categories': categories,
        'title': 'Manage Test Categories'
    }

    return render(request, 'laboratory/manage_categories.html', context)

@login_required
def edit_category(request, category_id):
    """View for editing a test category"""
    category = get_object_or_404(TestCategory, id=category_id)

    if request.method == 'POST':
        form = TestCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category {category.name} has been updated successfully.')
            return redirect('laboratory:manage_categories')
    else:
        form = TestCategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}'
    }

    return render(request, 'laboratory/category_form.html', context)

@login_required
def delete_category(request, category_id):
    """View for deleting a test category"""
    category = get_object_or_404(TestCategory, id=category_id)

    if request.method == 'POST':
        # Check if there are tests in this category
        if category.tests.exists():
            messages.error(request, f'Cannot delete category {category.name} because it contains tests.')
            return redirect('laboratory:manage_categories')

        category.delete()
        messages.success(request, f'Category {category.name} has been deleted.')
        return redirect('laboratory:manage_categories')

    context = {
        'category': category
    }

    return render(request, 'laboratory/delete_category.html', context)


@login_required
def lab_statistics_report(request):
    """Comprehensive laboratory statistics and reporting"""
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

    # Base queryset for test requests
    test_requests = TestRequest.objects.filter(
        request_date__gte=start_date,
        request_date__lte=end_date
    ).select_related('patient', 'doctor', 'created_by')

    # Apply filters
    if test_category_id:
        test_requests = test_requests.filter(tests__category_id=test_category_id)

    if test_id:
        test_requests = test_requests.filter(tests__id=test_id)

    if status:
        test_requests = test_requests.filter(status=status)

    if priority:
        test_requests = test_requests.filter(priority=priority)

    # Test requests by category
    category_stats = test_requests.values(
        'tests__category__name',
        'tests__category__id'
    ).annotate(
        total_requests=Count('id'),
        total_revenue=Sum('tests__price'),
        avg_price=Avg('tests__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_requests')

    # Top tests by volume
    top_tests = test_requests.values(
        'tests__name',
        'tests__id'
    ).annotate(
        total_requests=Count('id'),
        total_revenue=Sum('tests__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_requests')[:10]

    # Status distribution
    status_stats = test_requests.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Priority distribution
    priority_stats = test_requests.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')

    # Daily test volume trend
    daily_stats = test_requests.extra(
        select={'day': 'DATE(request_date)'}
    ).values('day').annotate(
        daily_requests=Count('id'),
        daily_revenue=Sum('tests__price')
    ).order_by('day')

    # Top requesting doctors
    top_doctors = test_requests.values(
        'doctor__first_name',
        'doctor__last_name',
        'doctor__id'
    ).annotate(
        total_requests=Count('id'),
        total_revenue=Sum('tests__price'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_requests')[:10]

    # Overall statistics
    overall_stats = test_requests.aggregate(
        total_requests=Count('id'),
        total_revenue=Sum('tests__price'),
        avg_revenue_per_request=Avg('tests__price'),
        unique_patients=Count('patient', distinct=True),
        unique_tests=Count('tests', distinct=True),
        unique_doctors=Count('doctor', distinct=True)
    )

    # Completion rate (completed vs total)
    completed_requests = test_requests.filter(status='completed').count()
    total_requests = test_requests.count()
    completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0

    # Get filter options
    test_categories = TestCategory.objects.all().order_by('name')
    tests = Test.objects.all().order_by('name')

    context = {
        'title': 'Laboratory Statistics and Reports',
        'start_date': start_date,
        'end_date': end_date,
        'category_stats': category_stats,
        'top_tests': top_tests,
        'top_doctors': top_doctors,
        'status_stats': status_stats,
        'priority_stats': priority_stats,
        'daily_stats': daily_stats,
        'overall_stats': overall_stats,
        'completion_rate': completion_rate,
        'test_categories': test_categories,
        'tests': tests,
        'selected_category': test_category_id,
        'selected_test': test_id,
        'selected_status': status,
        'selected_priority': priority,
    }

    return render(request, 'laboratory/reports/lab_statistics.html', context)

# Test Request and Result Views
@login_required
def test_request_list(request):
    """View for listing all test requests"""
    search_form = TestRequestSearchForm(request.GET)
    test_requests = TestRequest.objects.all().order_by('-request_date')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        status = search_form.cleaned_data.get('status')
        priority = search_form.cleaned_data.get('priority')
        doctor = search_form.cleaned_data.get('doctor')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            test_requests = test_requests.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query)
            )

        if status:
            test_requests = test_requests.filter(status=status)

        if priority:
            test_requests = test_requests.filter(priority=priority)

        if doctor:
            test_requests = test_requests.filter(doctor=doctor)

        if date_from:
            test_requests = test_requests.filter(request_date__gte=date_from)

        if date_to:
            test_requests = test_requests.filter(request_date__lte=date_to)

    # Pagination
    paginator = Paginator(test_requests, 10)  # Show 10 test requests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts for different statuses
    pending_count = TestRequest.objects.filter(status='pending').count()
    # Corrected 'collected' to 'sample_collected' to match new status in model
    collected_count = TestRequest.objects.filter(status='sample_collected').count() 
    processing_count = TestRequest.objects.filter(status='processing').count()
    completed_count = TestRequest.objects.filter(status='completed').count()
    cancelled_count = TestRequest.objects.filter(status='cancelled').count()
    awaiting_payment_count = TestRequest.objects.filter(status='awaiting_payment').count()

    # Advanced: Add role-based analytics for test requests
    role_counts = TestRequest.objects.values('doctor__first_name', 'doctor__last_name').annotate(count=models.Count('id')).order_by('-count')
    # Advanced: Add audit log and notification fetch (if models exist)
    from core.models import AuditLog, InternalNotification
    # Note: Current AuditLog model doesn't have object_type/object_id fields
    # Filtering by action that might be related to test requests
    audit_logs = AuditLog.objects.filter(
        action__icontains='test'
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='TestRequest',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_requests': test_requests.count(),
        'pending_count': pending_count,
        'collected_count': collected_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'awaiting_payment_count': awaiting_payment_count,
        'role_counts': role_counts,
        'audit_logs': audit_logs,
        'user_notifications': user_notifications,
    }

    return render(request, 'laboratory/test_request_list.html', context)

@login_required
def create_test_request(request):
    """View for creating a new test request and associated invoice."""
    if request.method == 'POST':
        # This view now primarily handles submissions from the modal on patient_detail page
        # or a dedicated TestRequestForm if you have one that includes billing initiation.
        
        patient_id = request.POST.get('patient') or request.POST.get('patient_hidden')
        doctor_id = request.POST.get('doctor') # Ensure this name matches your form/modal
        tests_ids_str = request.POST.get('tests', '')
        tests_ids = [t.strip() for t in tests_ids_str.split(',') if t.strip()] if tests_ids_str else []
        priority = request.POST.get('priority', 'normal')
        request_date_str = request.POST.get('request_date')
        notes = request.POST.get('notes', '')

        try:
            patient = Patient.objects.get(id=patient_id)
            doctor = CustomUser.objects.get(id=doctor_id)
            selected_tests = Test.objects.filter(id__in=tests_ids)

            if not selected_tests.exists():
                messages.error(request, "Please select at least one test.")
                # Redirect back to patient detail or a more appropriate page
                return redirect(request.META.get('HTTP_REFERER', 'patients:list')) 

            # Ensure request_date_str is converted to date object correctly
            if request_date_str:
                request_date = datetime.datetime.strptime(request_date_str, '%Y-%m-%d').date()
            else:
                request_date = timezone.now().date()

            with transaction.atomic():
                # 1. Create the TestRequest, initially as 'awaiting_payment'
                test_request = TestRequest.objects.create(
                    patient=patient,
                    doctor=doctor,
                    request_date=request_date,
                    status='awaiting_payment', # New initial status
                    priority=priority,
                    notes=notes,
                    created_by=request.user
                )
                test_request.tests.set(selected_tests)

                # 2. Create an Invoice for this TestRequest
                subtotal = sum(Decimal(test.price) for test in selected_tests)
                tax_amount = Decimal('0.00')
                total_amount = subtotal + tax_amount
                due_date = request_date + timedelta(days=7) # Example: due in 7 days

                invoice = Invoice.objects.create(
                    patient=patient,
                    invoice_date=request_date,
                    due_date=due_date,
                    status='pending', # Or 'draft' if it needs review before sending to patient
                    test_request=test_request, # Link to the TestRequest
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    created_by=request.user
                )

                # The OneToOneField from TestRequest to Invoice is named 'invoice'
                # The related_name from Invoice back to TestRequest is 'lab_test_request'
                # So, test_request.invoice = invoice is correct if TestRequest.invoice is the OneToOneField
                test_request.invoice = invoice 
                test_request.save()

                # 3. Create InvoiceItems for each test
                for test_item in selected_tests:
                    # Ensure a generic service for 'Lab Test' exists or create one
                    # This part assumes you might want to categorize lab tests under a generic 'Lab Test' service in billing
                    # Or, you can create specific Service objects for each Test if preferred.
                    lab_service_category, _ = ServiceCategory.objects.get_or_create(name="Laboratory Services")
                    service, _ = Service.objects.get_or_create(
                        name=f"Lab Test: {test_item.name}", 
                        category=lab_service_category,
                        defaults={'price': test_item.price, 'description': test_item.description or f"Laboratory test: {test_item.name}"}
                    )
                    if service.price != test_item.price: # Update service price if it differs from test price
                        service.price = test_item.price
                        service.save()

                    InvoiceItem.objects.create(
                        invoice=invoice,
                        service=service, 
                        description=f"Lab Test: {test_item.name}",
                        quantity=1,
                        unit_price=Decimal(test_item.price),
                        tax_percentage=service.tax_percentage, # Use tax from service if defined
                        tax_amount=(Decimal(test_item.price) * service.tax_percentage) / Decimal('100'),
                        total_amount=Decimal(test_item.price) + ((Decimal(test_item.price) * service.tax_percentage) / Decimal('100'))
                    )
                
                # Update invoice totals based on items if not handled by signals
                invoice.subtotal = sum(Decimal(item.unit_price) * item.quantity for item in invoice.items.all())
                invoice.tax_amount = sum(Decimal(item.tax_amount) for item in invoice.items.all())
                invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount_amount # Assuming discount is handled elsewhere or is 0
                invoice.save()

                messages.success(request, f'Test request for {patient.get_full_name()} created. Invoice #{invoice.invoice_number} generated and is pending payment.')
                return redirect('laboratory:test_request_detail', request_id=test_request.id)

        except Patient.DoesNotExist:
            messages.error(request, "Selected patient not found.")
        except User.DoesNotExist:
            messages.error(request, "Selected doctor not found.")
        except Test.DoesNotExist:
            messages.error(request, "One or more selected tests not found.")
        except Exception as e:
            messages.error(request, f"Error creating test request: {str(e)}")
        
        # Fallback redirect
        return redirect(request.META.get('HTTP_REFERER', 'patients:list'))

    else: # GET request for a dedicated form page
        patient_id = request.GET.get('patient')
        patient = None
        initial_data = {}

        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id)
                initial_data['patient'] = patient
                initial_data['doctor'] = request.user
                initial_data['request_date'] = timezone.now().date()
            except Patient.DoesNotExist:
                pass

        # Create form with patient preselection
        form = TestRequestForm(
            initial=initial_data,
            request=request,
            preselected_patient=patient
        )

        # Get all tests organized by category for the enhanced interface
        test_categories = TestCategory.objects.prefetch_related('tests').filter(
            tests__is_active=True
        ).distinct().order_by('name')

        # Get all tests for search functionality
        all_tests = Test.objects.filter(is_active=True).select_related('category').order_by('category__name', 'name')

    context = {
        'form': form,
        'patient': patient,
        'test_categories': test_categories,
        'all_tests': all_tests,
        'title': 'Create New Test Request'
    }
    return render(request, 'laboratory/enhanced_test_request_form.html', context)

@login_required
def test_request_detail(request, request_id):
    test_request = get_object_or_404(TestRequest, id=request_id)
    tests = test_request.tests.all()
    results = TestResult.objects.filter(test_request=test_request)
    # Access the invoice via the related name from Invoice model if TestRequest.invoice is the OneToOneField
    # Or directly if TestRequest.invoice is the field itself.
    # Based on laboratory.models.TestRequest having `invoice = OneToOneField('billing.Invoice'...)`
    invoice = test_request.invoice 

    context = {
        'test_request': test_request,
        'tests': tests,
        'results': results,
        'invoice': invoice, 
        'title': f'Test Request #{test_request.id} - {test_request.patient.get_full_name()}'
    }
    return render(request, 'laboratory/test_request_detail.html', context)

@login_required
def update_test_request_status(request, request_id):
    """View for updating test request status"""
    test_request = get_object_or_404(TestRequest, id=request_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(TestRequest.STATUS_CHOICES):
            # Add logic here: if status is moving to 'sample_collected' or 'processing',
            # ensure payment is confirmed if it was 'awaiting_payment'.
            if test_request.status == 'awaiting_payment' and status != 'cancelled':
                messages.error(request, "Cannot proceed. Payment is still pending for this test request.")
                return redirect('laboratory:test_request_detail', request_id=test_request.id)
            
            test_request.status = status
            test_request.save()
            messages.success(request, f'Test request status updated to {test_request.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status.')

        return redirect('laboratory:test_request_detail', request_id=test_request.id)

    return redirect('laboratory:test_request_detail', request_id=test_request.id)

@login_required
def create_test_result(request, request_id):
    """View for creating a new test result"""
    test_request = get_object_or_404(TestRequest, id=request_id)

    # Check if payment is confirmed before allowing result creation
    if test_request.status == 'awaiting_payment':
        messages.error(request, "Cannot add results. Payment is pending for this test request.")
        return redirect('laboratory:test_request_detail', request_id=test_request.id)
    if test_request.status == 'pending': # Should ideally be awaiting_payment or payment_confirmed
        messages.warning(request, "This test request has not been processed for payment yet.")
        # Allow to proceed but with a warning, or redirect based on stricter workflow

    # Get tests that don't have results yet
    tests_with_results = TestResult.objects.filter(test_request=test_request).values_list('test_id', flat=True)
    available_tests = test_request.tests.exclude(id__in=tests_with_results)

    if not available_tests.exists():
        messages.info(request, 'All tests in this request already have results.')
        return redirect('laboratory:test_request_detail', request_id=test_request.id)

    if request.method == 'POST':
        form = TestResultForm(request.POST, request.FILES)
        if form.is_valid():
            test_result = form.save(commit=False)
            test_result.test_request = test_request
            test_result.save()

            # Create empty result parameters for each parameter in the test
            for parameter in test_result.test.parameters.all():
                TestResultParameter.objects.create(
                    test_result=test_result,
                    parameter=parameter,
                    value='',
                    is_normal=True
                )

            # Update test request status if it was 'payment_confirmed' or 'sample_collected'
            if test_request.status in ['payment_confirmed', 'sample_collected']:
                test_request.status = 'processing' # Now that a result is being entered
                test_request.save()
            elif test_request.status == 'pending': # If it somehow skipped payment steps
                test_request.status = 'processing'
                test_request.save()

            # Notify doctor and patient
            if test_request.doctor:
                InternalNotification.objects.create(
                    user=test_request.doctor,
                    message=f"Lab result for {test_result.test.name} is now available for {test_request.patient.get_full_name()}"
                )
                # Send email notification if doctor has email
                if hasattr(test_request.doctor, 'email') and test_request.doctor.email:
                    send_notification_email(
                        subject="Lab Result Available",
                        message=f"Lab result for {test_result.test.name} is now available for {test_request.patient.get_full_name()}.",
                        recipient_list=[test_request.doctor.email]
                    )
                # SMS notification stub for doctor (if phone number is available)
                if test_request.doctor.phone_number:
                    from core.utils import send_sms_notification
                    send_sms_notification(
                        test_request.doctor.phone_number,
                        f"Lab result for {test_result.test.name} is now available for {test_request.patient.get_full_name()}"
                    )
            if hasattr(test_request.patient, 'user') and getattr(test_request.patient.user, 'email', None):
                InternalNotification.objects.create(
                    user=test_request.patient.user,
                    message=f"Your lab result for {test_result.test.name} is now available."
                )
                send_notification_email(
                    subject="Your Lab Result is Ready",
                    message=f"Your lab result for {test_result.test.name} is now available.",
                    recipient_list=[test_request.patient.user.email]
                )
                # SMS notification stub for patient (if phone number is available)
                if getattr(test_request.patient, 'phone_number', None):
                    from core.utils import send_sms_notification
                    send_sms_notification(
                        test_request.patient.phone_number,
                        f"Your lab result for {test_result.test.name} is now available."
                    )

            messages.success(request, f'Test result for {test_result.test.name} has been created successfully.')
            return redirect('laboratory:edit_test_result', result_id=test_result.id)
    else:
        initial_data = {
            'result_date': timezone.now().date(),
            'sample_collection_date': timezone.now(),
            'performed_by': request.user,
        }
        form = TestResultForm(initial=initial_data)
        form.fields['test'].queryset = available_tests

    context = {
        'form': form,
        'test_request': test_request,
        'title': 'Create New Test Result'
    }

    return render(request, 'laboratory/test_result_form.html', context)

@login_required
def result_list(request):
    """View for listing all test results"""
    results = TestResult.objects.all().order_by('-result_date')

    # Pagination
    paginator = Paginator(results, 10)  # Show 10 results per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }

    return render(request, 'laboratory/result_list.html', context)

@login_required
def result_detail(request, result_id):
    """View for displaying test result details"""
    result = get_object_or_404(TestResult, id=result_id)
    parameters = result.parameters.all().order_by('parameter__order')

    context = {
        'result': result,
        'parameters': parameters,
    }

    return render(request, 'laboratory/result_detail.html', context)

@login_required
def edit_test_result(request, result_id):
    """View for editing a test result and its parameters."""
    result = get_object_or_404(TestResult, id=result_id)
    # parameters = result.parameters.all().order_by('parameter__order') # No longer needed directly like this

    if request.method == 'POST':
        form = TestResultForm(request.POST, request.FILES, instance=result)
        # Initialize formset with POST data and the instance of the parent TestResult
        parameter_formset = TestResultParameterFormSet(request.POST, instance=result, prefix='parameters')

        if form.is_valid() and parameter_formset.is_valid():
            form.save()
            parameter_formset.save() # This will save changes to all TestResultParameter instances

            # Update test request status if needed
            test_request = result.test_request
            if test_request.status in ['pending', 'sample_collected', 'processing', 'payment_confirmed']:
                # Consider if all results for the request are in before changing to 'processing' or 'completed'
                # This simple logic just updates if not already completed.
                # A more complex check would see if all Test objects in test_request.tests.all() have a TestResult.
                is_request_complete = not TestResult.objects.filter(test_request=test_request, verified_by__isnull=True).exists() and \
                                      test_request.tests.count() == TestResult.objects.filter(test_request=test_request).count()
                if is_request_complete and all(res.verified_by for res in test_request.results.all()):
                    test_request.status = 'completed'
                else:
                    test_request.status = 'processing'
                test_request.save()

            messages.success(request, f'Test result for {result.test.name} has been updated successfully.')
            return redirect('laboratory:result_detail', result_id=result.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TestResultForm(instance=result)
        # Initialize formset with the instance of the parent TestResult for GET request
        parameter_formset = TestResultParameterFormSet(instance=result, prefix='parameters')

    context = {
        'form': form,
        'parameter_formset': parameter_formset, # Pass the formset to the template
        'result': result,
        # 'parameters': parameters, # Not needed if using formset directly for rendering
        'title': f'Edit Test Result: {result.test.name} - {result.test_request.patient.get_full_name()}'
    }

    return render(request, 'laboratory/edit_test_result.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_result_parameter(request, result_id):
    """View for manually adding a new parameter to an existing test result"""
    result = get_object_or_404(TestResult, id=result_id)

    if request.method == 'POST':
        # Handle AJAX request for adding parameter
        parameter_name = request.POST.get('parameter_name')
        parameter_value = request.POST.get('parameter_value')
        parameter_unit = request.POST.get('parameter_unit', '')
        parameter_range = request.POST.get('parameter_range', '')
        is_normal = request.POST.get('is_normal') == 'true'
        notes = request.POST.get('notes', '')

        if parameter_name and parameter_value:
            try:
                with transaction.atomic():
                    # Create or get the test parameter
                    test_parameter, created = TestParameter.objects.get_or_create(
                        test=result.test,
                        name=parameter_name,
                        defaults={
                            'unit': parameter_unit,
                            'normal_range': parameter_range,
                            'order': TestParameter.objects.filter(test=result.test).count() + 1
                        }
                    )

                    # Create the test result parameter
                    result_parameter = TestResultParameter.objects.create(
                        test_result=result,
                        parameter=test_parameter,
                        value=parameter_value,
                        is_normal=is_normal,
                        notes=notes
                    )

                    messages.success(request, f'Parameter "{parameter_name}" added successfully.')

                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': f'Parameter "{parameter_name}" added successfully.',
                            'parameter_id': result_parameter.id
                        })
                    else:
                        return redirect('laboratory:edit_test_result', result_id=result.id)

            except Exception as e:
                error_message = f'Error adding parameter: {str(e)}'
                messages.error(request, error_message)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': error_message
                    })
                else:
                    return redirect('laboratory:edit_test_result', result_id=result.id)
        else:
            error_message = 'Parameter name and value are required.'
            messages.error(request, error_message)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            else:
                return redirect('laboratory:edit_test_result', result_id=result.id)

    # GET request - show the add parameter form
    context = {
        'result': result,
        'title': f'Add Parameter to {result.test.name}'
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'laboratory/add_parameter_modal.html', context)
    else:
        return render(request, 'laboratory/add_parameter.html', context)


@login_required
def get_test_parameters(request, test_id):
    """
    AJAX endpoint to get predefined parameters for a test
    """
    test = get_object_or_404(Test, id=test_id)
    parameters = test.parameters.all().order_by('order')

    parameter_data = []
    for param in parameters:
        parameter_data.append({
            'id': param.id,
            'name': param.name,
            'unit': param.unit or '',
            'normal_range': param.normal_range or '',
            'order': param.order
        })

    return JsonResponse({
        'parameters': parameter_data,
        'test_info': {
            'name': test.name,
            'category': test.category.name if test.category else '',
            'sample_type': test.sample_type or '',
            'normal_range': test.normal_range or '',
            'preparation_instructions': test.preparation_instructions or ''
        }
    })

@login_required
def print_result(request, result_id):
    """View for printing a test result"""
    result = get_object_or_404(TestResult, id=result_id)
    parameters = result.parameters.all().order_by('parameter__order')

    context = {
        'result': result,
        'parameters': parameters,
        'hospital_name': settings.HOSPITAL_NAME,
        'hospital_address': settings.HOSPITAL_ADDRESS,
        'hospital_phone': settings.HOSPITAL_PHONE,
        'hospital_email': settings.HOSPITAL_EMAIL,
        'print_date': timezone.now(),
    }

    return render(request, 'laboratory/print_result.html', context)

@login_required
def verify_test_result(request, result_id):
    """View for verifying a test result"""
    result = get_object_or_404(TestResult, id=result_id)

    # Check if result is already verified
    if result.verified_by:
        messages.info(request, f'This result has already been verified by {result.verified_by.get_full_name()} on {result.verified_date}.')
        return redirect('laboratory:result_detail', result_id=result.id)

    if request.method == 'POST':
        # Verify the result
        result.verified_by = request.user
        result.verified_date = timezone.now()
        result.save()

        # Update test request status if all results are verified
        test_request = result.test_request
        all_results_verified = True

        # Check if all tests in the request have verified results
        for test in test_request.tests.all():
            try:
                test_result = TestResult.objects.get(test_request=test_request, test=test)
                if not test_result.verified_by:
                    all_results_verified = False
                    break
            except TestResult.DoesNotExist:
                all_results_verified = False
                break

        if all_results_verified:
            test_request.status = 'completed'
            test_request.save()

        messages.success(request, f'Test result for {result.test.name} has been verified successfully.')
        return redirect('laboratory:result_detail', result_id=result.id)

    context = {
        'result': result,
        'title': f'Verify Test Result: {result.test.name}'
    }

    return render(request, 'laboratory/verify_test_result.html', context)

@login_required
def patient_tests(request, patient_id):
    """View for displaying tests for a specific patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    test_requests = TestRequest.objects.filter(patient=patient).order_by('-request_date')

    context = {
        'patient': patient,
        'test_requests': test_requests,
    }

    return render(request, 'laboratory/patient_tests.html', context)

@login_required
def test_api(request):
    """API view for getting test information"""
    tests = Test.objects.filter(is_active=True).select_related('category')

    results = []
    for test in tests:
        results.append({
            'id': test.id,
            'name': test.name,
            'category': test.category.name if test.category else 'Uncategorized',
            'price': float(test.price),
            'description': test.description
        })

    return JsonResponse(results, safe=False)

@login_required
def laboratory_sales_report(request):
    """View for daily tests by doctor and total monthly lab revenue."""
    from django.db.models import Sum, Count
    today = timezone.now().date()
    month_start = today.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month - timezone.timedelta(days=1)

    # Daily tests by doctor (doctor field)
    daily_tests = (
        TestRequest.objects.filter(request_date=today)
        .values('doctor__id', 'doctor__first_name', 'doctor__last_name')
        .annotate(total_tests=Count('id'), total_revenue=Sum('invoice__total_amount'))
        .order_by('-total_tests')
    )

    # Total monthly revenue
    monthly_revenue = (
        TestRequest.objects.filter(request_date__gte=month_start, request_date__lte=month_end)
        .aggregate(total=Sum('invoice__total_amount'))['total'] or 0
    )

    context = {
        'daily_tests': daily_tests,
        'monthly_revenue': monthly_revenue,
        'today': today,
        'month_start': month_start,
        'month_end': month_end,
        'title': 'Laboratory Report Dashboard',
    }
    return render(request, 'laboratory/sales_report.html', context)


@login_required
def radiology_sales_report(request):
    """View for daily radiology tests by user and total monthly radiology revenue."""
    from radiology.models import RadiologyOrder
    from django.db.models import Sum, F
    from django.utils import timezone
    # from django.contrib.auth.models import User  # Using CustomUser instead

    today = timezone.now().date()
    month_start = today.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month - timezone.timedelta(days=1)

    # Daily radiology tests by user (ordered_by)
    daily_tests = (
        RadiologyOrder.objects.filter(ordered_at__date=today)
        .values('ordered_by__id', 'ordered_by__first_name', 'ordered_by__last_name')
        .annotate(total_tests=Count('id'), total_revenue=Sum('total_price'))
        .order_by('-total_tests')
    )

    # Total monthly revenue
    monthly_revenue = (
        RadiologyOrder.objects.filter(ordered_at__date__gte=month_start, ordered_at__date__lte=month_end)
        .aggregate(total=Sum('total_price'))['total'] or 0
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
