from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F, Count
from django.db import models, transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import (
    Medication, MedicationCategory, Supplier, Purchase, PurchaseItem,
    Prescription, PrescriptionItem, Dispensary, ActiveStore, ActiveStoreInventory, MedicationInventory,
    BulkStore, BulkStoreInventory, MedicationTransfer, DispensaryTransfer, DispensingLog,
    MedicalPack, PackItem, PackOrder
)
from accounts.models import CustomUser
from patients.models import Patient
from .forms import (
    MedicationForm, MedicationCategoryForm, SupplierForm, PurchaseForm, PurchaseItemForm,
    PrescriptionForm, PrescriptionItemForm, DispensaryForm,
    MedicationInventoryForm, ActiveStoreInventoryForm, PrescriptionSearchForm,
    MedicationSearchForm  # Add this import
)
from reporting.forms import PharmacySalesReportForm
from django.forms import formset_factory
from .forms import DispenseItemForm, BaseDispenseItemFormSet
from decimal import Decimal
from billing.models import Invoice, InvoiceItem, Service, ServiceCategory


@login_required
def pharmacy_dashboard(request):
    """View for the pharmacy dashboard"""
    # Get pharmacy statistics
    total_medications = Medication.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    total_dispensaries = Dispensary.objects.filter(is_active=True).count()
    
    # Get low stock items
    low_stock_items = ActiveStoreInventory.objects.filter(
        stock_quantity__lte=models.F('reorder_level')
    ).select_related('medication', 'active_store__dispensary')[:5]
    
    # Get recent purchases
    recent_purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')[:5]
    
    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.select_related('patient', 'doctor').order_by('-prescription_date')[:5]
    
    context = {
        'total_medications': total_medications,
        'total_suppliers': total_suppliers,
        'total_dispensaries': total_dispensaries,
        'low_stock_items': low_stock_items,
        'recent_purchases': recent_purchases,
        'recent_prescriptions': recent_prescriptions,
        'page_title': 'Pharmacy Dashboard',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/dashboard.html', context)


@login_required
def features_showcase(request):
    """View for showcasing pharmacy features"""
    return render(request, 'pharmacy/features.html')


@login_required
def inventory_list(request):
    """View for listing pharmacy inventory"""
    # Get all medications
    medications = Medication.objects.filter(is_active=True).select_related('category')
    
    # Initialize the search form
    form = MedicationSearchForm(request.GET or None)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        medications = medications.filter(
            Q(name__icontains=search_query) |
            Q(generic_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        medications = medications.filter(category_id=category_id)
    
    # Filter by active status
    is_active = request.GET.get('is_active', '')
    if is_active == 'active':
        medications = medications.filter(is_active=True)
    elif is_active == 'inactive':
        medications = medications.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(medications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = MedicationCategory.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'form': form,  # Pass the form to the template
        'search_query': search_query,
        'category_id': category_id,
        'page_title': 'Pharmacy Inventory',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/inventory_list.html', context)


@login_required
def add_medication(request):
    """View for adding a new medication"""
    if request.method == 'POST':
        form = MedicationForm(request.POST)
        if form.is_valid():
            medication = form.save()
            messages.success(request, f'Medication {medication.name} added successfully.')
            return redirect('pharmacy:inventory')
    else:
        form = MedicationForm()
    
    context = {
        'form': form,
        'page_title': 'Add Medication',
        'active_nav': 'pharmacy',
        'title': 'Add Medication'  # Add title for the template
    }
    
    return render(request, 'pharmacy/add_edit_medication.html', context)


@login_required
def medication_detail(request, medication_id):
    """View for displaying medication details"""
    medication = get_object_or_404(Medication, id=medication_id)
    
    # Get inventory information
    inventory_items = ActiveStoreInventory.objects.filter(
        medication=medication
    ).select_related('active_store__dispensary')
    
    context = {
        'medication': medication,
        'inventory_items': inventory_items,
        'page_title': f'Medication Details - {medication.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medication_detail.html', context)


@login_required
def edit_medication(request, medication_id):
    """View for editing medication information"""
    medication = get_object_or_404(Medication, id=medication_id)
    
    if request.method == 'POST':
        form = MedicationForm(request.POST, instance=medication)
        if form.is_valid():
            medication = form.save()
            messages.success(request, f'Medication {medication.name} updated successfully.')
            return redirect('pharmacy:medication_detail', medication_id=medication.id)
    else:
        form = MedicationForm(instance=medication)
    
    context = {
        'form': form,
        'medication': medication,
        'page_title': f'Edit Medication - {medication.name}',
        'active_nav': 'pharmacy',
        'title': f'Edit Medication - {medication.name}'  # Add title for the template
    }
    
    return render(request, 'pharmacy/add_edit_medication.html', context)


@login_required
def delete_medication(request, medication_id):
    """View for deleting a medication"""
    medication = get_object_or_404(Medication, id=medication_id)
    
    if request.method == 'POST':
        medication.is_active = False
        medication.save()
        messages.success(request, f'Medication {medication.name} deactivated successfully.')
        return redirect('pharmacy:inventory')
    
    context = {
        'medication': medication,
        'page_title': f'Delete Medication - {medication.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/delete_medication.html', context)


@login_required
def manage_categories(request):
    """View for managing medication categories"""
    categories = MedicationCategory.objects.all().order_by('name')
    
    if request.method == 'POST':
        form = MedicationCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} created successfully.')
            return redirect('pharmacy:manage_categories')
    else:
        form = MedicationCategoryForm()
    
    context = {
        'categories': categories,
        'form': form,
    }
    
    return render(request, 'pharmacy/manage_categories.html', context)


@login_required
def patient_prescriptions(request, patient_id):
    """View for listing prescriptions for a patient"""
    # Get the patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=patient).select_related('doctor').order_by('-prescription_date')
    
    # Pagination
    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'patient': patient,
        'page_obj': page_obj,
        'page_title': f'Prescriptions for {patient.get_full_name()}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/prescription_list.html', context)


@login_required
def create_prescription(request, patient_id=None):
    """View for creating a prescription"""
    if request.method == 'POST':
        # Handle patient context ID from form submission
        patient_context_id = request.POST.get('patient_context_id')

        # If patient context ID is provided, use it to preselect patient
        if patient_context_id:
            try:
                preselected_patient = Patient.objects.get(id=patient_context_id)
                form = PrescriptionForm(request.POST, request=request, preselected_patient=preselected_patient)
            except Patient.DoesNotExist:
                form = PrescriptionForm(request.POST, request=request)
        else:
            form = PrescriptionForm(request.POST, request=request)

        if form.is_valid():
            prescription = form.save()
            messages.success(request, f'Prescription #{prescription.id} created successfully.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    else:
        # Preselect patient from multiple sources with priority:
        # 1. URL parameter (patient_id)
        # 2. Current patient context from session
        # 3. None (user will select manually)
        preselected_patient = None

        # First check URL parameter
        if patient_id:
            try:
                preselected_patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                preselected_patient = None

        # If no URL parameter, check current patient context from session
        elif hasattr(request, 'current_patient') and request.current_patient:
            try:
                preselected_patient = Patient.objects.get(id=request.current_patient['id'])
            except (Patient.DoesNotExist, KeyError):
                preselected_patient = None

        form = PrescriptionForm(request=request, preselected_patient=preselected_patient)

    context = {
        'form': form,
        'title': 'Create Prescription',
        'active_nav': 'pharmacy',
        'current_patient': getattr(request, 'current_patient', None),
        'has_current_patient': hasattr(request, 'has_current_patient') and request.has_current_patient,
    }

    return render(request, 'pharmacy/prescription_form.html', context)


@login_required
def pharmacy_create_prescription(request, patient_id=None):
    """View for pharmacy creating a prescription"""
    # This is the same as create_prescription but might have different permissions or workflow
    if request.method == 'POST':
        # Handle patient context ID from form submission
        patient_context_id = request.POST.get('patient_context_id')

        # If patient context ID is provided, use it to preselect patient
        if patient_context_id:
            try:
                preselected_patient = Patient.objects.get(id=patient_context_id)
                form = PrescriptionForm(request.POST, request=request, preselected_patient=preselected_patient)
            except Patient.DoesNotExist:
                form = PrescriptionForm(request.POST, request=request)
        else:
            form = PrescriptionForm(request.POST, request=request)

        if form.is_valid():
            prescription = form.save()
            messages.success(request, f'Prescription #{prescription.id} created successfully.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    else:
        # Preselect patient from multiple sources with priority:
        # 1. URL parameter (patient_id)
        # 2. Current patient context from session
        # 3. None (user will select manually)
        preselected_patient = None

        # First check URL parameter
        if patient_id:
            try:
                preselected_patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                preselected_patient = None

        # If no URL parameter, check current patient context from session
        elif hasattr(request, 'current_patient') and request.current_patient:
            try:
                preselected_patient = Patient.objects.get(id=request.current_patient['id'])
            except (Patient.DoesNotExist, KeyError):
                preselected_patient = None

        form = PrescriptionForm(request=request, preselected_patient=preselected_patient)

    context = {
        'form': form,
        'title': 'Create Prescription (Pharmacy)',
        'active_nav': 'pharmacy',
        'patient': preselected_patient,  # Add patient to context for template
        'selected_patient': preselected_patient,  # Also add selected_patient for template compatibility
        'current_patient': getattr(request, 'current_patient', None),
        'has_current_patient': hasattr(request, 'has_current_patient') and request.has_current_patient,
    }

    return render(request, 'pharmacy/pharmacy_create_prescription.html', context)


@login_required
def create_procurement_request(request, medication_id):
    """View for creating a procurement request"""
    medication = get_object_or_404(Medication, id=medication_id)
    
    # Get suppliers who have supplied this medication before
    suppliers = Supplier.objects.filter(
        purchases__items__medication=medication,
        is_active=True
    ).distinct()
    
    context = {
        'medication': medication,
        'suppliers': suppliers,
        'page_title': f'Procurement Request - {medication.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/create_procurement_request.html', context)

@login_required
def edit_category(request, category_id):
    """View for editing a medication category"""
    category = get_object_or_404(MedicationCategory, id=category_id)
    
    if request.method == 'POST':
        form = MedicationCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} updated successfully.')
            return redirect('pharmacy:manage_categories')
    else:
        form = MedicationCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'page_title': f'Edit Category - {category.name}',
        'active_nav': 'pharmacy',
        'title': f'Edit Category - {category.name}'  # Add title for the template
    }
    
    return render(request, 'pharmacy/add_edit_category.html', context)


@login_required
def delete_category(request, category_id):
    """View for deleting a medication category"""
    category = get_object_or_404(MedicationCategory, id=category_id)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, f'Category {category.name} deleted successfully.')
        return redirect('pharmacy:manage_categories')
    
    context = {
        'category': category,
        'page_title': f'Delete Category - {category.name}',
        'active_nav': 'pharmacy',
        'title': f'Delete Category - {category.name}'  # Add title for the template
    }
    
    return render(request, 'pharmacy/confirm_delete_category.html', context)


@login_required
def manage_suppliers(request):
    """View for managing suppliers"""
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier {supplier.name} created successfully.')
            return redirect('pharmacy:manage_suppliers')
    else:
        form = SupplierForm()
    
    context = {
        'suppliers': suppliers,
        'form': form,
        'page_title': 'Manage Suppliers',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/manage_suppliers.html', context)


@login_required
def supplier_list(request):
    """View for listing suppliers"""
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(suppliers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'page_title': 'Supplier List',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/supplier_list.html', context)


@login_required
def supplier_detail(request, supplier_id):
    """View for displaying supplier details"""
    supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
    
    # Get recent purchases from this supplier
    recent_purchases = Purchase.objects.filter(
        supplier=supplier
    ).order_by('-purchase_date')[:10]
    
    context = {
        'supplier': supplier,
        'recent_purchases': recent_purchases,
        'page_title': f'Supplier Details - {supplier.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/supplier_detail.html', context)


@login_required
def edit_supplier(request, supplier_id):
    """View for editing supplier information"""
    supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier {supplier.name} updated successfully.')
            return redirect('pharmacy:supplier_detail', supplier_id=supplier.id)
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'form': form,
        'supplier': supplier,
        'page_title': f'Edit Supplier - {supplier.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/edit_supplier.html', context)


@login_required
def delete_supplier(request, supplier_id):
    """View for deleting a supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
    
    if request.method == 'POST':
        supplier.is_active = False
        supplier.save()
        messages.success(request, f'Supplier {supplier.name} deactivated successfully.')
        return redirect('pharmacy:manage_suppliers')
    
    context = {
        'supplier': supplier,
        'page_title': f'Delete Supplier - {supplier.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/delete_supplier.html', context)


@login_required
def quick_procurement(request, supplier_id):
    """View for deleting a supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
    context = {
        'supplier': supplier,
        'page_title': f'Delete Supplier - {supplier.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/delete_supplier.html', context)


@login_required
def quick_procurement(request, supplier_id):
    """View for quick procurement from a supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
    
    # Get frequently ordered medications from this supplier
    frequently_ordered = PurchaseItem.objects.filter(
        purchase__supplier=supplier
    ).values(
        'medication_id', 'medication__name'
    ).annotate(
        order_count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-order_count')[:10]
    
    context = {
        'supplier': supplier,
        'frequently_ordered': frequently_ordered,
        'page_title': f'Quick Procurement - {supplier.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/quick_procurement.html', context)


@login_required
def procurement_dashboard(request):
    """View for the procurement dashboard"""
    # Get procurement statistics
    total_purchases = Purchase.objects.count()
    pending_purchases = Purchase.objects.filter(approval_status='pending').count()
    approved_purchases = Purchase.objects.filter(approval_status='approved').count()
    
    # Get recent purchases
    recent_purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')[:10]
    
    context = {
        'total_purchases': total_purchases,
        'pending_purchases': pending_purchases,
        'approved_purchases': approved_purchases,
        'recent_purchases': recent_purchases,
        'page_title': 'Procurement Dashboard',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/procurement_dashboard.html', context)

@login_required
def procurement_analytics(request):
    """View for procurement analytics"""
    # Implementation for procurement analytics

    # Get purchase data for analytics
    purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')[:50]
    
    # Calculate procurement statistics
    total_purchases = Purchase.objects.count()
    total_purchase_value = Purchase.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Get supplier-wise purchase data
    supplier_stats = Purchase.objects.values(
        'supplier__name'
    ).annotate(
        total_purchases=Count('id'),
        total_value=Sum('total_amount')
    ).order_by('-total_value')[:10]
    
    context = {
        'purchases': purchases,
        'total_purchases': total_purchases,
        'total_purchase_value': total_purchase_value,
        'supplier_stats': supplier_stats,
        'page_title': 'Procurement Analytics',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/procurement_analytics.html', context)


@login_required
def automated_reorder_suggestions(request):
    """View for automated reorder suggestions"""
    # Implementation for automated reorder suggestions
    # Get medications that are below reorder level
    low_stock_items = ActiveStoreInventory.objects.filter(
        stock_quantity__lte=F('reorder_level')
    ).select_related('medication', 'active_store__dispensary')
    
    # Get items that need reordering based on usage patterns
    # This is a simplified implementation - in a real system, you might use more complex algorithms
    reorder_suggestions = []
    for item in low_stock_items:
        # Calculate average monthly usage (simplified)
        avg_monthly_usage = item.stock_quantity * 0.3  # Placeholder calculation
        suggested_order_qty = max(
            item.reorder_level,  # Using reorder_level instead of reorder_quantity
            (avg_monthly_usage * 3) - item.stock_quantity  # 3 months supply minus current stock
        )
        
        reorder_suggestions.append({
            'inventory_item': item,
            'current_stock': item.stock_quantity,
            'reorder_level': item.reorder_level,
            'suggested_quantity': suggested_order_qty,
        })
    
    context = {
        'reorder_suggestions': reorder_suggestions,
        'page_title': 'Reorder Suggestions',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/reorder_suggestions.html', context)


@login_required
def revenue_analysis(request):
    """View for revenue analysis"""
    # Backwards-compatibility redirect: the comprehensive implementation
    # was replaced with `simple_revenue_statistics` (path: /pharmacy/revenue/statistics/).
    # Preserve any query parameters when redirecting.
    from django.shortcuts import redirect
    from django.urls import reverse

    target = reverse('pharmacy:simple_revenue_statistics')
    query = request.META.get('QUERY_STRING', '')
    if query:
        return redirect(f"{target}?{query}")
    return redirect(target)


@login_required
def expense_analysis(request):
    """View for expense analysis"""
    # Implementation for expense analysis
    # Get expense data
    purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')[:50]
    
    # Calculate expense statistics
    total_expenses = Purchase.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Get category-wise expense data
    category_expenses = PurchaseItem.objects.values(
        'medication__category__name'
    ).annotate(
        total_value=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_value')[:10]
    
    context = {
        'purchases': purchases,
        'total_expenses': total_expenses,
        'category_expenses': category_expenses,
        'page_title': 'Expense Analysis',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/expense_analysis.html', context)
import json
from datetime import datetime
from django.utils import timezone


def test_revenue_charts_public(request):
    """Temporary public view to test revenue charts without authentication"""
    from .revenue_service import RevenueAggregationService, MonthFilterHelper
    import json
    
    # Get current month date range
    start_date, end_date = MonthFilterHelper.get_current_month()
    
    # Initialize revenue aggregation service
    revenue_service = RevenueAggregationService(start_date, end_date)
    
    # Get comprehensive revenue data
    comprehensive_data = revenue_service.get_comprehensive_revenue()
    
    # Get monthly trends (last 12 months)
    monthly_trends = revenue_service.get_monthly_trends(12)
    
    # Prepare chart data for monthly trends
    chart_months = [trend['month'] for trend in monthly_trends]
    chart_data = {
        'months': json.dumps(chart_months),
        'pharmacy': json.dumps([float(trend['pharmacy']) for trend in monthly_trends]),
        'laboratory': json.dumps([float(trend['laboratory']) for trend in monthly_trends]),
        'consultations': json.dumps([float(trend['consultations']) for trend in monthly_trends]),
        'theatre': json.dumps([float(trend['theatre']) for trend in monthly_trends]),
        'admissions': json.dumps([float(trend['admissions']) for trend in monthly_trends]),
        'general': json.dumps([float(trend['general']) for trend in monthly_trends]),
        'wallet': json.dumps([float(trend['wallet']) for trend in monthly_trends]),
        'total': json.dumps([float(trend['total_revenue']) for trend in monthly_trends])
    }
    
    # Top revenue sources analysis
    revenue_sources = [
        {'name': 'Pharmacy', 'revenue': comprehensive_data['pharmacy_revenue']['total_revenue'], 'icon': 'fas fa-pills', 'color': 'primary'},
        {'name': 'Laboratory', 'revenue': comprehensive_data['laboratory_revenue']['total_revenue'], 'icon': 'fas fa-microscope', 'color': 'success'},
        {'name': 'Consultations', 'revenue': comprehensive_data['consultation_revenue']['total_revenue'], 'icon': 'fas fa-stethoscope', 'color': 'info'},
        {'name': 'Theatre', 'revenue': comprehensive_data['theatre_revenue']['total_revenue'], 'icon': 'fas fa-procedures', 'color': 'warning'},
        {'name': 'Admissions', 'revenue': comprehensive_data['admission_revenue']['total_revenue'], 'icon': 'fas fa-bed', 'color': 'danger'},
        {'name': 'General & Others', 'revenue': comprehensive_data['general_revenue']['total_revenue'], 'icon': 'fas fa-receipt', 'color': 'secondary'},
        {'name': 'Wallet', 'revenue': comprehensive_data['wallet_revenue']['total_revenue'], 'icon': 'fas fa-wallet', 'color': 'dark'}
    ]
    
    # Sort by revenue (highest first)
    revenue_sources.sort(key=lambda x: x['revenue'], reverse=True)
    
    # Performance metrics
    total_revenue = comprehensive_data['total_revenue']
    performance_metrics = {
        'total_transactions': sum([
            comprehensive_data['pharmacy_revenue']['total_payments'],
            comprehensive_data['laboratory_revenue']['total_payments'],
            comprehensive_data['consultation_revenue']['total_payments'],
            comprehensive_data['theatre_revenue']['total_payments'],
            comprehensive_data['admission_revenue']['total_payments'],
            comprehensive_data['general_revenue']['total_payments'],
            comprehensive_data['wallet_revenue']['total_transactions']
        ]),
        'average_transaction_value': total_revenue / max(1, sum([
            comprehensive_data['pharmacy_revenue']['total_payments'],
            comprehensive_data['laboratory_revenue']['total_payments'],
            comprehensive_data['consultation_revenue']['total_payments'],
            comprehensive_data['theatre_revenue']['total_payments'],
            comprehensive_data['admission_revenue']['total_payments'],
            comprehensive_data['general_revenue']['total_payments'],
            comprehensive_data['wallet_revenue']['total_transactions']
        ])),
        'days_in_period': (end_date - start_date).days + 1,
        'daily_average': total_revenue / max(1, (end_date - start_date).days + 1)
    }
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'comprehensive_data': comprehensive_data,
        'monthly_trends': monthly_trends,
        'daily_breakdown': [],
        'chart_data': chart_data,
        'revenue_sources': revenue_sources,
        'performance_metrics': performance_metrics,
        'include_daily_breakdown': False,
        'selected_departments': [],
        'page_title': 'Revenue Charts Test',
        'active_nav': 'pharmacy',
        
        # Individual department data for backward compatibility with template
        'pharmacy_revenue': comprehensive_data['pharmacy_revenue'],
        'lab_revenue': comprehensive_data['laboratory_revenue'],
        'consultation_revenue': comprehensive_data['consultation_revenue'],
        'theatre_revenue': comprehensive_data['theatre_revenue'],
        'admission_revenue': comprehensive_data['admission_revenue'],
        'general_revenue': comprehensive_data['general_revenue'],
        'wallet_revenue': comprehensive_data['wallet_revenue'],
    }
    
    return render(request, 'pharmacy/simple_revenue_statistics.html', context)


@login_required
def _add_pack_to_patient_billing(patient, pack_order, source_context='pharmacy'):
    """Helper function to add pack costs to patient billing"""
    
    # Create or get invoice for patient
    invoice, created = Invoice.objects.get_or_create(
        patient=patient,
        status='pending',
        source_app='pharmacy',  # Using pharmacy as the source for pack orders
        defaults={
            'invoice_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=7),
            'subtotal': Decimal('0.00'),
            'tax_amount': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'created_by': pack_order.ordered_by,
        }
    )
    
    # Create or get medical pack service category
    pack_service_category, _ = ServiceCategory.objects.get_or_create(
        name="Medical Packs",
        defaults={'description': 'Pre-packaged medical supplies and medications'}
    )
    
    # Create or get service for this specific pack
    service, _ = Service.objects.get_or_create(
        name=f"Medical Pack: {pack_order.pack.name}",
        category=pack_service_category,
        defaults={
            'price': pack_order.pack.get_total_cost(),
            'description': f"Medical pack for {pack_order.pack.get_pack_type_display()}: {pack_order.pack.name}",
            'tax_percentage': Decimal('0.00')  # Assuming no tax on medical packs
        }
    )
    
    # Add invoice item for the pack
    pack_cost = pack_order.pack.get_total_cost()
    invoice_item = InvoiceItem.objects.create(
        invoice=invoice,
        service=service,
        description=f"Medical Pack: {pack_order.pack.name} (Order #{pack_order.id}) - {source_context.title()}",
        quantity=1,
        unit_price=pack_cost,
        tax_percentage=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        total_amount=pack_cost
    )
    
    # Update invoice totals
    invoice.subtotal = invoice.items.aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0.00')
    invoice.tax_amount = invoice.items.aggregate(
        total=models.Sum('tax_amount')
    )['total'] or Decimal('0.00')
    invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount_amount
    invoice.save()
    
    return invoice_item


@login_required
def simple_revenue_statistics(request):
    """Simple revenue statistics view showing department-wise revenue in a table and chart"""
    from .revenue_service import RevenueAggregationService, MonthFilterHelper
    import json
    from datetime import datetime
    from django.utils import timezone

    # Handle search parameters
    search_query = request.GET.get('search', '').strip().lower()
    
    # Handle date range parameters
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    # Parse dates if provided, otherwise use current month
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            # Get first day of current month
            today = timezone.now().date()
            start_date = today.replace(day=1)
    except ValueError:
        # Fallback to current month if invalid date
        today = timezone.now().date()
        start_date = today.replace(day=1)
    
    try:
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Get last day of current month
            today = timezone.now().date()
            if today.month == 12:
                end_date = today.replace(day=31, month=12)
            else:
                # Get the last day of the current month
                next_month = today.replace(day=28) + timezone.timedelta(days=4)
                end_date = next_month - timezone.timedelta(days=next_month.day)
    except ValueError:
        # Fallback to last day of current month if invalid date
        today = timezone.now().date()
        if today.month == 12:
            end_date = today.replace(day=31, month=12)
        else:
            next_month = today.replace(day=28) + timezone.timedelta(days=4)
            end_date = next_month - timezone.timedelta(days=next_month.day)
    
    # Ensure start_date is not after end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Initialize revenue aggregation service with the specified date range
    revenue_service = RevenueAggregationService(start_date, end_date)
    
    # Get comprehensive revenue data
    comprehensive_data = revenue_service.get_comprehensive_revenue()
    
    # Get monthly trends (last 12 months)
    monthly_trends = revenue_service.get_monthly_trends(12)
    
    # Calculate total revenue
    total_revenue = comprehensive_data['total_revenue']
    
    # Prepare chart data for monthly trends
    chart_months = [trend['month'] for trend in monthly_trends]
    chart_data = {
        'months': json.dumps(chart_months),
        'pharmacy': json.dumps([float(trend['pharmacy']) for trend in monthly_trends]),
        'laboratory': json.dumps([float(trend['laboratory']) for trend in monthly_trends]),
        'consultations': json.dumps([float(trend['consultations']) for trend in monthly_trends]),
        'theatre': json.dumps([float(trend['theatre']) for trend in monthly_trends]),
        'admissions': json.dumps([float(trend['admissions']) for trend in monthly_trends]),
        'general': json.dumps([float(trend['general']) for trend in monthly_trends]),
        'wallet': json.dumps([float(trend['wallet']) for trend in monthly_trends]),
        'total': json.dumps([float(trend['total_revenue']) for trend in monthly_trends])
    }
    
    # Revenue sources for table
    all_revenue_sources = [
        {'name': 'Pharmacy', 'revenue': comprehensive_data['pharmacy_revenue']['total_revenue'], 'icon': 'fas fa-pills', 'color': 'primary', 'transactions': comprehensive_data['pharmacy_revenue']['total_payments']},
        {'name': 'Laboratory', 'revenue': comprehensive_data['laboratory_revenue']['total_revenue'], 'icon': 'fas fa-microscope', 'color': 'success', 'transactions': comprehensive_data['laboratory_revenue']['total_payments']},
        {'name': 'Consultations', 'revenue': comprehensive_data['consultation_revenue']['total_revenue'], 'icon': 'fas fa-stethoscope', 'color': 'info', 'transactions': comprehensive_data['consultation_revenue']['total_payments']},
        {'name': 'Theatre', 'revenue': comprehensive_data['theatre_revenue']['total_revenue'], 'icon': 'fas fa-procedures', 'color': 'warning', 'transactions': comprehensive_data['theatre_revenue']['total_payments']},
        {'name': 'Admissions', 'revenue': comprehensive_data['admission_revenue']['total_revenue'], 'icon': 'fas fa-bed', 'color': 'danger', 'transactions': comprehensive_data['admission_revenue']['total_payments']},
        {'name': 'General & Others', 'revenue': comprehensive_data['general_revenue']['total_revenue'], 'icon': 'fas fa-receipt', 'color': 'secondary', 'transactions': comprehensive_data['general_revenue']['total_payments']},
        {'name': 'Wallet', 'revenue': comprehensive_data['wallet_revenue']['total_revenue'], 'icon': 'fas fa-wallet', 'color': 'dark', 'transactions': comprehensive_data['wallet_revenue']['total_transactions']},
    ]
    
    # Filter revenue sources based on search query
    if search_query:
        revenue_sources = [source for source in all_revenue_sources 
                          if search_query in source['name'].lower()]
    else:
        revenue_sources = all_revenue_sources
    
    # Recalculate total revenue based on filtered sources
    if search_query:
        total_revenue = sum(source['revenue'] for source in revenue_sources)
    
    # Performance metrics
    performance_metrics = {
        'total_transactions': sum([
            comprehensive_data['pharmacy_revenue']['total_payments'],
            comprehensive_data['laboratory_revenue']['total_payments'],
            comprehensive_data['consultation_revenue']['total_payments'],
            comprehensive_data['theatre_revenue']['total_payments'],
            comprehensive_data['admission_revenue']['total_payments'],
            comprehensive_data['general_revenue']['total_payments'],
            comprehensive_data['wallet_revenue']['total_transactions']
        ]),
        'average_transaction_value': total_revenue / max(1, sum([
            comprehensive_data['pharmacy_revenue']['total_payments'],
            comprehensive_data['laboratory_revenue']['total_payments'],
            comprehensive_data['consultation_revenue']['total_payments'],
            comprehensive_data['theatre_revenue']['total_payments'],
            comprehensive_data['admission_revenue']['total_payments'],
            comprehensive_data['general_revenue']['total_payments'],
            comprehensive_data['wallet_revenue']['total_transactions']
        ])),
        'days_in_period': (end_date - start_date).days + 1,
        'daily_average': total_revenue / max(1, (end_date - start_date).days + 1)
    }
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'revenue_sources': revenue_sources,
        'chart_data': chart_data,
        'performance_metrics': performance_metrics,
        'page_title': 'Revenue Statistics',
        'active_nav': 'pharmacy',
        'search_query': search_query,  # Add search query to context
        'start_date_str': start_date_str,  # Add date strings to context
        'end_date_str': end_date_str,
        
        # Individual department data for backward compatibility with template
        'pharmacy_revenue': comprehensive_data['pharmacy_revenue'],
        'lab_revenue': comprehensive_data['laboratory_revenue'],
        'consultation_revenue': comprehensive_data['consultation_revenue'],
        'theatre_revenue': comprehensive_data['theatre_revenue'],
        'admission_revenue': comprehensive_data['admission_revenue'],
        'general_revenue': comprehensive_data['general_revenue'],
        'wallet_revenue': comprehensive_data['wallet_revenue'],
    }
    
    return render(request, 'pharmacy/simple_revenue_statistics.html', context)

def comprehensive_revenue_analysis_debug(request):
    """Legacy debug route - redirect to the canonical simple revenue statistics view."""
    from django.shortcuts import redirect
    from django.urls import reverse

    target = reverse('pharmacy:simple_revenue_statistics')
    query = request.META.get('QUERY_STRING', '')
    if query:
        return redirect(f"{target}?{query}")
    return redirect(target)
@login_required
def create_procurement_request(request, medication_id):
    """View for creating a procurement request"""
    medication = get_object_or_404(Medication, id=medication_id)
    # Implementation for creating procurement request
    pass


@login_required
def api_suppliers(request):
    """API endpoint for suppliers"""
    suppliers = Supplier.objects.filter(is_active=True).values('id', 'name')
    return JsonResponse(list(suppliers), safe=False)


@login_required
def bulk_store_dashboard(request):
    """View for the bulk store dashboard"""
    # Get bulk store information
    bulk_stores = BulkStore.objects.filter(is_active=True)
    
    context = {
        'bulk_stores': bulk_stores,
        'page_title': 'Bulk Store Dashboard',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/bulk_store_dashboard.html', context)


@login_required
def active_store_detail(request, dispensary_id):
    """View for displaying active store details"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    active_store = getattr(dispensary, 'active_store', None)
    
    if not active_store:
        messages.error(request, f'No active store found for {dispensary.name}.')
        return redirect('pharmacy:dispensary_list')
    
    # Get inventory items in the active store
    inventory_items = ActiveStoreInventory.objects.filter(
        active_store=active_store
    ).select_related('medication', 'active_store')
    
    context = {
        'active_store': active_store,
        'dispensary': dispensary,
        'inventory_items': inventory_items,
        'page_title': f'Active Store - {active_store.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/active_store_detail.html', context)


@login_required
def request_medication_transfer(request):
    """View for requesting medication transfer from bulk store to active store"""
    if request.method == 'POST':
        # Handle transfer request
        try:
            medication_id = request.POST.get('medication')
            bulk_store_id = request.POST.get('bulk_store')
            active_store_id = request.POST.get('active_store')
            quantity = int(request.POST.get('quantity'))
            batch_number = request.POST.get('batch_number')
            
            medication = get_object_or_404(Medication, id=medication_id)
            bulk_store = get_object_or_404(BulkStore, id=bulk_store_id)
            active_store = get_object_or_404(ActiveStore, id=active_store_id)
            
            # Check if bulk store has sufficient quantity
            bulk_inventory = BulkStoreInventory.objects.filter(
                medication=medication,
                bulk_store=bulk_store,
                batch_number=batch_number,
                stock_quantity__gte=quantity
            ).first()
            
            if not bulk_inventory:
                messages.error(request, f'Insufficient stock in bulk store for {medication.name}.')
                return redirect('pharmacy:request_medication_transfer')
            
            # Create transfer request
            transfer = MedicationTransfer.objects.create(
                medication=medication,
                from_bulk_store=bulk_store,
                to_active_store=active_store,
                quantity=quantity,
                batch_number=batch_number,
                expiry_date=bulk_inventory.expiry_date,
                unit_cost=bulk_inventory.unit_cost,
                status='pending',
                requested_by=request.user
            )
            
            messages.success(request, f'Transfer request #{transfer.id} created successfully.')
            return redirect('pharmacy:bulk_store_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error creating transfer request: {str(e)}')
            return redirect('pharmacy:request_medication_transfer')
    
    # GET request - show form
    medications = Medication.objects.filter(is_active=True).order_by('name')
    bulk_stores = BulkStore.objects.filter(is_active=True)
    active_stores = ActiveStore.objects.filter(is_active=True)
    
    context = {
        'medications': medications,
        'bulk_stores': bulk_stores,
        'active_stores': active_stores,
        'page_title': 'Request Medication Transfer',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/request_transfer.html', context)


@login_required
def approve_medication_transfer(request, transfer_id):
    """View for approving a medication transfer"""
    transfer = get_object_or_404(MedicationTransfer, id=transfer_id)
    
    if request.method == 'POST':
        try:
            if not transfer.can_approve():
                messages.error(request, 'Transfer cannot be approved in current status.')
                return redirect('pharmacy:bulk_store_dashboard')
            
            # Approve the transfer
            transfer.approved_by = request.user
            transfer.approved_at = timezone.now()
            transfer.status = 'in_transit'
            transfer.save()
            
            messages.success(request, f'Transfer #{transfer.id} approved successfully.')
            return redirect('pharmacy:bulk_store_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error approving transfer: {str(e)}')
            return redirect('pharmacy:bulk_store_dashboard')
    
    context = {
        'transfer': transfer,
        'page_title': f'Approve Transfer #{transfer.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/approve_transfer.html', context)


@login_required
def execute_medication_transfer(request, transfer_id):
    """View for executing a medication transfer"""
    transfer = get_object_or_404(MedicationTransfer, id=transfer_id)
    
    if request.method == 'POST':
        try:
            if not transfer.can_execute():
                messages.error(request, 'Transfer cannot be executed in current status.')
                return redirect('pharmacy:bulk_store_dashboard')
            
            # Execute the transfer
            transfer.execute_transfer(request.user)
            
            messages.success(request, f'Transfer #{transfer.id} executed successfully.')
            return redirect('pharmacy:bulk_store_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error executing transfer: {str(e)}')
            return redirect('pharmacy:bulk_store_dashboard')
    
    context = {
        'transfer': transfer,
        'page_title': f'Execute Transfer #{transfer.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/execute_transfer.html', context)


@login_required
def manage_transfers(request):
    """View for managing all types of transfers"""
    # Get data for bulk store to active store transfers
    medications = Medication.objects.filter(is_active=True).order_by('name')
    bulk_stores = BulkStore.objects.filter(is_active=True)
    active_stores = ActiveStore.objects.filter(is_active=True)
    dispensaries = Dispensary.objects.filter(is_active=True)
    
    # Get pending transfers
    pending_bulk_transfers = MedicationTransfer.objects.filter(status='pending').select_related(
        'medication', 'from_bulk_store', 'to_active_store', 'requested_by'
    )
    
    # Get transfer history
    medication_transfers = MedicationTransfer.objects.all().select_related(
        'medication', 'from_bulk_store', 'to_active_store', 'requested_by'
    )
    dispensary_transfers = DispensaryTransfer.objects.all().select_related(
        'medication', 'from_active_store', 'to_dispensary', 'requested_by'
    )
    
    # Combine and sort transfers by date
    all_transfers = list(medication_transfers) + list(dispensary_transfers)
    all_transfers.sort(key=lambda x: x.requested_at, reverse=True)
    
    context = {
        'medications': medications,
        'bulk_stores': bulk_stores,
        'active_stores': active_stores,
        'dispensaries': dispensaries,
        'pending_bulk_transfers': pending_bulk_transfers,
        'all_transfers': all_transfers[:50],  # Limit to last 50 transfers
        'page_title': 'Manage Transfers',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/manage_transfers.html', context)


@login_required
def transfer_to_dispensary(request, dispensary_id):
    """View for transferring medications from active store to dispensary"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    active_store = getattr(dispensary, 'active_store', None)
    
    if not active_store:
        messages.error(request, f'No active store found for {dispensary.name}.')
        return redirect('pharmacy:dispensary_list')
    
    if request.method == 'POST':
        try:
            # Get form data
            medication_id = request.POST.get('medication_id')
            batch_number = request.POST.get('batch_number')
            quantity = int(request.POST.get('quantity'))
            
            # Get the medication
            medication = get_object_or_404(Medication, id=medication_id)
            
            # Check if active store has sufficient quantity
            active_inventory = ActiveStoreInventory.objects.filter(
                medication=medication,
                active_store=active_store,
                batch_number=batch_number,
                stock_quantity__gte=quantity
            ).first()
            
            if not active_inventory:
                messages.error(request, f'Insufficient stock in active store for {medication.name}.')
                return redirect('pharmacy:active_store_detail', dispensary_id=dispensary_id)
            
            # Create dispensary transfer
            dispensary_transfer = DispensaryTransfer.objects.create(
                medication=medication,
                from_active_store=active_store,
                to_dispensary=dispensary,
                quantity=quantity,
                batch_number=batch_number,
                expiry_date=active_inventory.expiry_date,
                unit_cost=active_inventory.unit_cost,
                status='pending',
                requested_by=request.user
            )
            
            # Approve and execute transfer immediately
            dispensary_transfer.approved_by = request.user
            dispensary_transfer.approved_at = timezone.now()
            dispensary_transfer.status = 'in_transit'
            dispensary_transfer.save()
            
            try:
                dispensary_transfer.execute_transfer(request.user)
                messages.success(request, f'Successfully transferred {quantity} units of {medication.name} to {dispensary.name}.')
            except Exception as e:
                messages.error(request, f'Error executing transfer: {str(e)}')
                
        except Exception as e:
            messages.error(request, f'Error processing transfer: {str(e)}')
        
        return redirect('pharmacy:active_store_detail', dispensary_id=dispensary_id)
    
    # GET request - redirect to active store detail
    return redirect('pharmacy:active_store_detail', dispensary_id=dispensary_id)


@login_required
def active_store_inventory_ajax(request, dispensary_id):
    """AJAX endpoint for getting active store inventory for a dispensary"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
            active_store = getattr(dispensary, 'active_store', None)
            
            if not active_store:
                return JsonResponse({'success': False, 'error': 'No active store found for this dispensary.'})
            
            # Get inventory items in the active store
            inventory_items = ActiveStoreInventory.objects.filter(
                active_store=active_store
            ).select_related('medication')
            
            inventory_data = []
            for item in inventory_items:
                inventory_data.append({
                    'medication_id': item.medication.id,
                    'medication_name': item.medication.name,
                    'batch_number': item.batch_number,
                    'expiry_date': item.expiry_date.strftime('%Y-%m-%d') if item.expiry_date else '',
                    'stock_quantity': item.stock_quantity,
                })
            
            return JsonResponse({'success': True, 'inventory': inventory_data})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # If not AJAX request, redirect to dispensary list
    return redirect('pharmacy:dispensary_list')


@login_required
def manage_purchases(request):
    """View for managing purchases"""
    # Get all purchases
    purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        purchases = purchases.filter(
            Q(invoice_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        purchases = purchases.filter(approval_status=status)
    
    # Pagination
    paginator = Paginator(purchases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status': status,
        'page_title': 'Manage Purchases',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/manage_purchases.html', context)


@login_required
def add_purchase(request):
    """View for adding a new purchase"""
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            # Save with commit=False so required fields added by the model (total_amount)
            # can be populated before hitting DB constraints.
            purchase = form.save(commit=False)
            # Ensure total_amount is set to a safe initial value (items will update it)
            from decimal import Decimal
            purchase.total_amount = Decimal('0.00')
            # Set creator if available
            if hasattr(request, 'user') and request.user.is_authenticated:
                purchase.created_by = request.user
            purchase.save()
            # If any items are created immediately afterwards they will call update_total_amount()
            messages.success(request, f'Purchase #{purchase.invoice_number} created successfully.')
            return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    else:
        form = PurchaseForm()
    
    context = {
        'form': form,
        'page_title': 'Add Purchase',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/add_purchase.html', context)


@login_required
def purchase_detail(request, purchase_id):
    """View for displaying purchase details"""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    
    # Get purchase items
    purchase_items = purchase.items.select_related('medication')
    
    context = {
        'purchase': purchase,
        'purchase_items': purchase_items,
        'page_title': f'Purchase Details - #{purchase.invoice_number}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/purchase_detail.html', context)


from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from pharmacy.forms import PrescriptionForm, PrescriptionSearchForm
from pharmacy.models import Patient, Prescription, PrescriptionItem, Purchase


@login_required
def process_purchase_payment(request, purchase_id):
    """View for processing purchase payment"""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for processing purchase payment
    pass


@login_required
def delete_purchase_item(request, item_id):
    """View for deleting a purchase item"""
    item = get_object_or_404(PurchaseItem, id=item_id)
    # Implementation for deleting purchase item
    pass


@login_required
def submit_purchase_for_approval(request, purchase_id):
    """View for submitting purchase for approval"""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for submitting purchase for approval
    pass


@login_required
def approve_purchase(request, purchase_id):
    """View for approving a purchase"""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for approving purchase
    pass


@login_required
def reject_purchase(request, purchase_id):
    """View for rejecting a purchase"""
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for rejecting purchase
    pass


@login_required
def prescription_list(request):
    """View for listing prescriptions with enhanced search and filtering"""
    # Get all prescriptions with prefetch for efficient dispensing status calculation
    prescriptions = Prescription.objects.select_related('patient', 'doctor').prefetch_related('items').order_by('-created_at')
    
    # Initialize the search form
    search_form = PrescriptionSearchForm(request.GET)
    
    # Apply filters if form is valid
    if search_form.is_valid():
        # Get cleaned data from form
        search_query = search_form.cleaned_data.get('search')
        patient_number = search_form.cleaned_data.get('patient_number')
        medication_name = search_form.cleaned_data.get('medication_name')
        status = search_form.cleaned_data.get('status')
        payment_status = search_form.cleaned_data.get('payment_status')
        doctor = search_form.cleaned_data.get('doctor')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        # Apply search filter
        if search_query:
            prescriptions = prescriptions.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(doctor__first_name__icontains=search_query) |
                Q(doctor__last_name__icontains=search_query) |
                Q(diagnosis__icontains=search_query)
            )
        
        # Apply patient number filter
        if patient_number:
            prescriptions = prescriptions.filter(patient__patient_id__icontains=patient_number)
        
        # Apply medication name filter
        if medication_name:
            prescriptions = prescriptions.filter(items__medication__name__icontains=medication_name)
        
        # Apply status filter
        if status:
            prescriptions = prescriptions.filter(status=status)
        
        # Apply payment status filter
        if payment_status:
            prescriptions = prescriptions.filter(payment_status=payment_status)
        
        # Apply doctor filter
        if doctor:
            prescriptions = prescriptions.filter(doctor=doctor)
        
        # Apply date range filters
        if date_from:
            prescriptions = prescriptions.filter(prescription_date__gte=date_from)
        if date_to:
            prescriptions = prescriptions.filter(prescription_date__lte=date_to)
    
    # Get statistics for the dashboard cards
    total_prescriptions = prescriptions.count()
    pending_count = prescriptions.filter(status='pending').count()
    processing_count = prescriptions.filter(status__in=['approved', 'partially_dispensed']).count()
    completed_count = prescriptions.filter(status='dispensed').count()
    
    # Add dispensing statistics
    prescriptions_list = list(prescriptions.distinct())
    dispensing_stats = {
        'fully_dispensed': 0,
        'partially_dispensed': 0,
        'not_dispensed': 0
    }
    
    for prescription in prescriptions_list:
        dispensing_status = prescription.get_dispensing_status()
        if dispensing_status == 'fully_dispensed':
            dispensing_stats['fully_dispensed'] += 1
        elif dispensing_status == 'partially_dispensed':
            dispensing_stats['partially_dispensed'] += 1
        else:
            dispensing_stats['not_dispensed'] += 1
    
    # Pagination
    paginator = Paginator(prescriptions_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add title to context for template
    title = "Prescription Management"
    
    context = {
        'page_obj': page_obj,
        'form': search_form,
        'total_prescriptions': total_prescriptions,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'dispensing_stats': dispensing_stats,
        'page_title': 'Prescription List',
        'active_nav': 'pharmacy',
        'title': title,
    }
    
    return render(request, 'pharmacy/prescription_list.html', context)
import datetime

from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Patient, Prescription


@login_required
def patient_prescriptions(request, patient_id):
    """View for listing prescriptions for a patient"""
    # Get the patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'patient': patient,
        'page_obj': page_obj,
        'page_title': f'Prescriptions for {patient.get_full_name()}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/prescription_list.html', context)


@login_required
def create_prescription(request, patient_id=None):
    """View for creating a prescription"""
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request=request)
        if form.is_valid():
            prescription = form.save()
            messages.success(request, f'Prescription #{prescription.id} created successfully.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    else:
        # Preselect patient if patient_id is provided
        initial_data = {}
        if patient_id:
            initial_data['patient'] = patient_id
        form = PrescriptionForm(request=request, initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Create Prescription',
        'active_nav': 'pharmacy',
        # Ensure templates have access to the patient when preselected
        'selected_patient': getattr(form.fields.get('patient'), 'initial', None),
        'patient': getattr(form.fields.get('patient'), 'initial', None),
    }

    return render(request, 'pharmacy/prescription_form.html', context)


@login_required
def pharmacy_create_prescription(request, patient_id=None):
    """View for pharmacy creating a prescription"""
    # Initialize preselected_patient at the beginning to avoid UnboundLocalError
    preselected_patient = None
    if patient_id:
        try:
            preselected_patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            preselected_patient = None
    
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request=request, current_user=request.user)
        if form.is_valid():
            prescription = form.save(commit=False)
            # Set the current user as the doctor/prescriber
            prescription.doctor = request.user
            prescription.save()
            form.save_m2m()  # Save many-to-many relationships if any
            messages.success(request, f'Prescription #{prescription.id} created successfully.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        # If form is not valid, we need to reinitialize it with the same parameters
        # to ensure the hidden fields and patient selection are preserved
        else:
            # Add detailed error messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            # Re-create the form with the same initialization parameters for error display
            form = PrescriptionForm(
                request.POST, 
                request=request, 
                current_user=request.user, 
                preselected_patient=preselected_patient
            )
    else:
        # Preselect patient if patient_id is provided
        initial_data = {'doctor': request.user}  # Set current user as doctor
        if preselected_patient:
            initial_data['patient'] = preselected_patient
        elif patient_id:
            initial_data['patient'] = patient_id
        form = PrescriptionForm(request=request, initial=initial_data, preselected_patient=preselected_patient, current_user=request.user)

    context = {
        'form': form,
        'title': 'Create Prescription (Pharmacy)',
        'active_nav': 'pharmacy',
        'selected_patient': preselected_patient,
        'patient': preselected_patient,
        'current_user': request.user,  # Add current user to context
    }

    return render(request, 'pharmacy/prescription_form.html', context)


@login_required
def prescription_detail(request, prescription_id):
    """View for displaying prescription details with enhanced NHIA pricing breakdown"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get prescription items
    prescription_items = prescription.items.select_related('medication')
    # Provide an empty form for the "Add Medication" modal
    item_form = PrescriptionItemForm()
    
    # Get pharmacy invoice if exists
    pharmacy_invoice = None
    try:
        from pharmacy_billing.models import Invoice as PharmacyInvoice
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        pharmacy_invoice = None

    # Get active or paid cart for quick access
    from pharmacy.cart_models import PrescriptionCart
    active_cart = PrescriptionCart.objects.filter(
        prescription=prescription,
        status__in=['active', 'invoiced', 'paid', 'partially_dispensed']
    ).order_by('-created_at').first()

    # Enhanced NHIA pricing breakdown
    pricing_breakdown = prescription.get_pricing_breakdown()
    
    # Calculate detailed item-level pricing for NHIA display
    items_with_pricing = []
    total_patient_pays = Decimal('0.00')
    total_nhia_covers = Decimal('0.00')
    total_medication_cost = Decimal('0.00')
    
    for item in prescription_items:
        item_total_cost = item.medication.price * item.quantity
        total_medication_cost += item_total_cost
        
        if pricing_breakdown['is_nhia_patient']:
            item_patient_pays = item_total_cost * Decimal('0.10')  # 10% patient portion
            item_nhia_covers = item_total_cost * Decimal('0.90')   # 90% NHIA portion
        else:
            item_patient_pays = item_total_cost  # 100% patient pays
            item_nhia_covers = Decimal('0.00')   # NHIA covers nothing
        
        total_patient_pays += item_patient_pays
        total_nhia_covers += item_nhia_covers
        
        items_with_pricing.append({
            'item': item,
            'total_cost': item_total_cost,
            'patient_pays': item_patient_pays,
            'nhia_covers': item_nhia_covers,
            'patient_percentage': '10%' if pricing_breakdown['is_nhia_patient'] else '100%',
            'nhia_percentage': '90%' if pricing_breakdown['is_nhia_patient'] else '0%',
        })

    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'item_form': item_form,
        'pharmacy_invoice': pharmacy_invoice,
        'active_cart': active_cart,  # Add cart for quick access
        'page_title': f'Prescription Details - #{prescription.id}',
        'active_nav': 'pharmacy',
        # Enhanced NHIA context
        'pricing_breakdown': pricing_breakdown,
        'items_with_pricing': items_with_pricing,
        'total_medication_cost': total_medication_cost,
        'total_patient_pays': total_patient_pays,
        'total_nhia_covers': total_nhia_covers,
        'is_nhia_patient': pricing_breakdown['is_nhia_patient'],
        'patient_percentage': '10%' if pricing_breakdown['is_nhia_patient'] else '100%',
        'nhia_percentage': '90%' if pricing_breakdown['is_nhia_patient'] else '0%',
    }
    
    return render(request, 'pharmacy/prescription_detail.html', context)


@login_required
def update_prescription_status(request, prescription_id):
    """View for updating prescription status"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        # Validate status
        valid_statuses = dict(Prescription.STATUS_CHOICES).keys()
        if new_status in valid_statuses:
            prescription.status = new_status
            prescription.save()
            messages.success(request, f'Prescription status updated to {prescription.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # For GET requests, show the update form
    status_choices = Prescription.STATUS_CHOICES
    
    context = {
        'prescription': prescription,
        'status_choices': status_choices,
        'title': f'Update Status for Prescription #{prescription.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/update_prescription_status.html', context)


@login_required
def dispense_prescription(request, prescription_id):
    """View for dispensing a prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check authorization requirement BEFORE allowing dispensing
    can_dispense, message = prescription.can_be_dispensed()
    if not can_dispense:
        messages.error(request, message)
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Prepare prescription items for dispensing
    prescription_items = list(prescription.items.select_related('medication'))

    # Build a formset class that uses our BaseDispenseItemFormSet
    DispenseFormSet = formset_factory(DispenseItemForm, formset=BaseDispenseItemFormSet, extra=0)

    # Selected dispensary handling (optional pre-selection)
    selected_dispensary = None
    dispensary_id = None

    # Check if a dispensary was selected
    if request.method == 'POST':
        dispensary_id = request.POST.get('dispensary_select') or request.POST.get('dispensary_id') or request.POST.get('selected_dispensary')
        if dispensary_id:
            try:
                selected_dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
            except (Dispensary.DoesNotExist, ValueError):
                selected_dispensary = None
    else:
        # Check GET parameters for dispensary_id
        dispensary_id = request.GET.get('dispensary_id')
        if dispensary_id:
            try:
                selected_dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
            except (Dispensary.DoesNotExist, ValueError):
                selected_dispensary = None

    # Check if this is just a form refresh (not a dispense action)
    if request.method == 'POST' and 'refresh_form' in request.POST:
        # Just refresh the form with the selected dispensary
        initial_data = []
        for p_item in prescription_items:
            initial_data.append({
                'item_id': p_item.id,
                'dispense_this_item': False,
                'quantity_to_dispense': 0,
                'dispensary': selected_dispensary.id if selected_dispensary else None,
                'stock_quantity_display': ''
            })

        formset = DispenseFormSet(initial=initial_data, prefix='form', prescription_items_qs=prescription_items, form_kwargs={'selected_dispensary': selected_dispensary})

        # Enhanced NHIA pricing breakdown
        pricing_breakdown = prescription.get_pricing_breakdown()

        # Calculate detailed item-level pricing for NHIA display
        items_with_pricing = []
        total_patient_pays = Decimal('0.00')
        total_nhia_covers = Decimal('0.00')
        total_medication_cost = Decimal('0.00')

        for item in prescription_items:
            item_total_cost = item.medication.price * item.quantity
            total_medication_cost += item_total_cost

            if pricing_breakdown['is_nhia_patient']:
                item_patient_pays = item_total_cost * Decimal('0.10')
                item_nhia_covers = item_total_cost * Decimal('0.90')
            else:
                item_patient_pays = item_total_cost
                item_nhia_covers = Decimal('0.00')

            total_patient_pays += item_patient_pays
            total_nhia_covers += item_nhia_covers

            items_with_pricing.append({
                'item': item,
                'total_cost': item_total_cost,
                'patient_pays': item_patient_pays,
                'nhia_covers': item_nhia_covers,
            })

        context = {
            'prescription': prescription,
            'page_title': f'Dispense Prescription - #{prescription.id}',
            'title': f'Dispense Prescription - #{prescription.id}',
            'dispensaries': Dispensary.objects.filter(is_active=True),
            'formset': formset,
            'selected_dispensary': selected_dispensary,
            'dispensary_id': dispensary_id,
            'pricing_breakdown': pricing_breakdown,
            'items_with_pricing': items_with_pricing,
            'total_medication_cost': total_medication_cost,
            'total_patient_pays': total_patient_pays,
            'total_nhia_covers': total_nhia_covers,
            'is_nhia_patient': pricing_breakdown['is_nhia_patient'],
        }
        return render(request, 'pharmacy/dispense_prescription.html', context)

    if request.method == 'POST':
        # Instantiate formset with POST data and bind prescription items
        formset = DispenseFormSet(request.POST, prefix='form', prescription_items_qs=prescription_items, form_kwargs={'selected_dispensary': selected_dispensary})

        # If user attempted to dispense items but didn't pick a dispensary, show a clear message
        any_checked = any(request.POST.get(f'form-{i}-dispense_this_item') in ['on', 'True', 'true', '1'] for i in range(len(prescription_items)))
        if not selected_dispensary and any_checked:
            messages.error(request, 'Please select a dispensary before dispensing items.')

            # Enhanced NHIA pricing breakdown
            pricing_breakdown = prescription.get_pricing_breakdown()

            # Calculate detailed item-level pricing for NHIA display
            items_with_pricing = []
            total_patient_pays = Decimal('0.00')
            total_nhia_covers = Decimal('0.00')
            total_medication_cost = Decimal('0.00')

            for item in prescription_items:
                item_total_cost = item.medication.price * item.quantity
                total_medication_cost += item_total_cost

                if pricing_breakdown['is_nhia_patient']:
                    item_patient_pays = item_total_cost * Decimal('0.10')
                    item_nhia_covers = item_total_cost * Decimal('0.90')
                else:
                    item_patient_pays = item_total_cost
                    item_nhia_covers = Decimal('0.00')

                total_patient_pays += item_patient_pays
                total_nhia_covers += item_nhia_covers

                items_with_pricing.append({
                    'item': item,
                    'total_cost': item_total_cost,
                    'patient_pays': item_patient_pays,
                    'nhia_covers': item_nhia_covers,
                })

            context = {
                'prescription': prescription,
                'page_title': f'Dispense Prescription - #{prescription.id}',
                'title': f'Dispense Prescription - #{prescription.id}',
                'dispensaries': Dispensary.objects.filter(is_active=True),
                'formset': formset,
                'selected_dispensary': selected_dispensary,
                'dispensary_id': dispensary_id,
                'pricing_breakdown': pricing_breakdown,
                'items_with_pricing': items_with_pricing,
                'total_medication_cost': total_medication_cost,
                'total_patient_pays': total_patient_pays,
                'total_nhia_covers': total_nhia_covers,
                'is_nhia_patient': pricing_breakdown['is_nhia_patient'],
            }
            return render(request, 'pharmacy/dispense_prescription.html', context)

        # The selected dispensary will be handled in form validation
        # No need to modify form data here as it can cause AttributeError

        if formset.is_valid():
            # Process each selected form
            any_dispensed = False
            skipped_items = []
            for form in formset:
                # Check if form has cleaned_data attribute before accessing it
                if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                    continue
                dispense = form.cleaned_data.get('dispense_this_item')
                qty = form.cleaned_data.get('quantity_to_dispense') or 0
                dispensary = form.cleaned_data.get('dispensary') or selected_dispensary

                # Ensure we have a dispensary for dispensing
                if dispense and qty > 0:
                    if not dispensary:
                        messages.error(request, f'No dispensary selected for medication item.')
                        continue

                    # Continue with dispensing logic
                    prescription_item = form.prescription_item
                    medication = prescription_item.medication

                    # Prevent redispensing items that are already fully dispensed
                    if prescription_item.is_dispensed or prescription_item.remaining_quantity_to_dispense <= 0:
                        # Collect for a single warning later
                        skipped_items.append(prescription_item)
                        continue

                    # Validate quantity
                    if qty <= 0:
                        messages.error(request, f'Quantity for {medication.name} must be greater than zero.')
                        continue

                    if qty > prescription_item.remaining_quantity_to_dispense:
                        messages.error(request, f'Cannot dispense more than remaining quantity ({prescription_item.remaining_quantity_to_dispense} units) for {medication.name}.')
                        continue

                    # Check inventory in the selected dispensary
                    # First check ActiveStoreInventory (new system)
                    med_inventory = None
                    try:
                        active_store = getattr(dispensary, 'active_store', None)
                        if active_store:
                            # Handle multiple inventory records by getting the first one with sufficient stock
                            med_inventory = ActiveStoreInventory.objects.filter(
                                medication=medication,
                                active_store=active_store,
                                stock_quantity__gte=qty
                            ).first()
                    except Exception as e:
                        pass  # Continue to legacy inventory check
                    
                    # If not found in active store, try legacy MedicationInventory (backward compatibility)
                    if med_inventory is None:
                        try:
                            med_inventory = MedicationInventory.objects.filter(
                                medication=medication,
                                dispensary=dispensary,
                                stock_quantity__gte=qty
                            ).first()
                        except Exception as e:
                            pass  # med_inventory remains None
                    
                    # If no inventory found with sufficient stock, show error and continue
                    if med_inventory is None:
                        messages.error(request, f'Insufficient stock for {medication.name} at {dispensary.name}.')
                        continue

                    # Create dispensing log
                    unit_price = medication.price or Decimal('0.00')
                    total_price = unit_price * qty
                    dispensing_log = DispensingLog.objects.create(
                        prescription_item=prescription_item,
                        dispensed_by=request.user,
                        dispensed_quantity=qty,
                        unit_price_at_dispense=unit_price,
                        total_price_for_this_log=total_price,
                        dispensary=dispensary
                    )

                    # Update inventory (update the correct inventory model)
                    if med_inventory is not None:
                        # Ensure we have sufficient stock before deducting
                        if hasattr(med_inventory, 'stock_quantity') and med_inventory.stock_quantity >= qty:
                            if isinstance(med_inventory, ActiveStoreInventory):
                                # Update active store inventory
                                med_inventory.stock_quantity -= qty
                                med_inventory.save()
                            else:
                                # Update legacy medication inventory
                                med_inventory.stock_quantity -= qty
                                med_inventory.save()
                        else:
                            messages.error(request, f'Insufficient stock for {medication.name}. Available: {getattr(med_inventory, "stock_quantity", 0)}, Required: {qty}')
                            continue
                    else:
                        messages.error(request, f'No inventory record found for {medication.name} at {dispensary.name}.')
                        continue

                    # Update prescription item quantities
                    prescription_item.quantity_dispensed_so_far += qty
                    if prescription_item.quantity_dispensed_so_far >= prescription_item.quantity:
                        prescription_item.is_dispensed = True
                        prescription_item.dispensed_date = timezone.now()
                        prescription_item.dispensed_by = request.user
                    prescription_item.save()

                    any_dispensed = True

            if any_dispensed:
                # Update prescription status based on dispensing progress
                total_items = prescription.items.count()
                fully_dispensed_items = prescription.items.filter(is_dispensed=True).count()
                partially_dispensed_items = prescription.items.filter(
                    is_dispensed=False,
                    quantity_dispensed_so_far__gt=0
                ).count()

                # Determine the correct status
                if fully_dispensed_items == total_items:
                    # All items fully dispensed
                    prescription.status = 'dispensed'
                    prescription.save(update_fields=['status'])
                    messages.success(request, f'All medications dispensed successfully. Prescription marked as fully dispensed.')
                elif fully_dispensed_items > 0 or partially_dispensed_items > 0:
                    # Some items dispensed (fully or partially)
                    prescription.status = 'partially_dispensed'
                    prescription.save(update_fields=['status'])
                    messages.success(request, f'Selected medications dispensed successfully. {fully_dispensed_items} of {total_items} items fully dispensed.')
                else:
                    # This shouldn't happen if any_dispensed is True, but handle it
                    messages.success(request, 'Selected medications dispensed successfully.')

                if skipped_items:
                    names = ', '.join([s.medication.name for s in skipped_items])
                    messages.warning(request, f'Some items were skipped because they are already fully dispensed: {names}')

                # Create invoice based on dispensed quantities
                from pharmacy_billing.models import Invoice as PharmacyInvoice
                from pharmacy_billing.utils import create_pharmacy_invoice

                # Check if invoice already exists
                try:
                    pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
                    messages.info(request, 'Invoice already exists for this prescription.')
                except PharmacyInvoice.DoesNotExist:
                    # Calculate total based on dispensed quantities
                    dispensed_total = Decimal('0.00')
                    for log in DispensingLog.objects.filter(prescription_item__prescription=prescription):
                        dispensed_total += log.total_price_for_this_log

                    # Apply NHIA discount if applicable
                    if prescription.patient.is_nhia_patient():
                        # Patient pays 10%, NHIA covers 90%
                        patient_payable = dispensed_total * Decimal('0.10')
                    else:
                        # Patient pays 100%
                        patient_payable = dispensed_total

                    # Create invoice
                    pharmacy_invoice = create_pharmacy_invoice(request, prescription, patient_payable)

                    if pharmacy_invoice:
                        messages.success(request, f'Invoice created successfully. Total: ₦{patient_payable:.2f}')
                    else:
                        messages.error(request, 'Failed to create invoice. Please contact billing.')

                # Redirect to payment page
                return redirect('pharmacy:prescription_payment', prescription_id=prescription.id)
            else:
                messages.warning(request, 'No medications were selected for dispensing.')
        else:
            # Collect detailed form/formset errors for display
            form_errors = []
            if hasattr(formset, 'non_form_errors') and formset.non_form_errors():
                form_errors.append(formset.non_form_errors())
            for idx, form in enumerate(formset.forms):
                if form.errors:
                    form_errors.append({f'form_index_{idx}': form.errors})

            # Add messages for each error bundle
            messages.error(request, 'Please correct the errors in the form.')
            for err in form_errors:
                messages.error(request, str(err))

            # Make sure to pass the selected dispensary to the context when there are form errors
            # Enhanced NHIA pricing breakdown
            pricing_breakdown = prescription.get_pricing_breakdown()

            # Calculate detailed item-level pricing for NHIA display
            items_with_pricing = []
            total_patient_pays = Decimal('0.00')
            total_nhia_covers = Decimal('0.00')
            total_medication_cost = Decimal('0.00')

            for item in prescription_items:
                item_total_cost = item.medication.price * item.quantity
                total_medication_cost += item_total_cost

                if pricing_breakdown['is_nhia_patient']:
                    item_patient_pays = item_total_cost * Decimal('0.10')
                    item_nhia_covers = item_total_cost * Decimal('0.90')
                else:
                    item_patient_pays = item_total_cost
                    item_nhia_covers = Decimal('0.00')

                total_patient_pays += item_patient_pays
                total_nhia_covers += item_nhia_covers

                items_with_pricing.append({
                    'item': item,
                    'total_cost': item_total_cost,
                    'patient_pays': item_patient_pays,
                    'nhia_covers': item_nhia_covers,
                })

            context = {
                'prescription': prescription,
                'page_title': f'Dispense Prescription - #{prescription.id}',
                'title': f'Dispense Prescription - #{prescription.id}',
                'dispensaries': Dispensary.objects.filter(is_active=True),
                'formset': formset,
                'selected_dispensary': selected_dispensary,
                'dispensary_id': dispensary_id,
                'pricing_breakdown': pricing_breakdown,
                'items_with_pricing': items_with_pricing,
                'total_medication_cost': total_medication_cost,
                'total_patient_pays': total_patient_pays,
                'total_nhia_covers': total_nhia_covers,
                'is_nhia_patient': pricing_breakdown['is_nhia_patient'],
            }
            return render(request, 'pharmacy/dispense_prescription.html', context)

    else:
        # GET request - build empty formset with initial data bound to prescription items
        initial_data = []
        for p_item in prescription_items:
            initial_data.append({
                'item_id': p_item.id,
                'dispense_this_item': False,
                'quantity_to_dispense': 0,
                'dispensary': selected_dispensary.id if selected_dispensary else None,
                'stock_quantity_display': ''
            })

        formset = DispenseFormSet(initial=initial_data, prefix='form', prescription_items_qs=prescription_items, form_kwargs={'selected_dispensary': selected_dispensary})

    # Enhanced NHIA pricing breakdown
    pricing_breakdown = prescription.get_pricing_breakdown()

    # Calculate detailed item-level pricing for NHIA display
    items_with_pricing = []
    total_patient_pays = Decimal('0.00')
    total_nhia_covers = Decimal('0.00')
    total_medication_cost = Decimal('0.00')

    for item in prescription_items:
        item_total_cost = item.medication.price * item.quantity
        total_medication_cost += item_total_cost

        if pricing_breakdown['is_nhia_patient']:
            item_patient_pays = item_total_cost * Decimal('0.10')  # 10% patient portion
            item_nhia_covers = item_total_cost * Decimal('0.90')   # 90% NHIA portion
        else:
            item_patient_pays = item_total_cost  # 100% patient pays
            item_nhia_covers = Decimal('0.00')   # NHIA covers nothing

        total_patient_pays += item_patient_pays
        total_nhia_covers += item_nhia_covers

        items_with_pricing.append({
            'item': item,
            'total_cost': item_total_cost,
            'patient_pays': item_patient_pays,
            'nhia_covers': item_nhia_covers,
            'patient_percentage': '10%' if pricing_breakdown['is_nhia_patient'] else '100%',
            'nhia_percentage': '90%' if pricing_breakdown['is_nhia_patient'] else '0%',
        })

    context = {
        'prescription': prescription,
        'page_title': f'Dispense Prescription - #{prescription.id}',
        'title': f'Dispense Prescription - #{prescription.id}',
        'dispensaries': Dispensary.objects.filter(is_active=True),
        'formset': formset,
        'selected_dispensary': selected_dispensary,
        'dispensary_id': dispensary_id,
        # Enhanced NHIA context
        'pricing_breakdown': pricing_breakdown,
        'items_with_pricing': items_with_pricing,
        'total_medication_cost': total_medication_cost,
        'total_patient_pays': total_patient_pays,
        'total_nhia_covers': total_nhia_covers,
        'is_nhia_patient': pricing_breakdown['is_nhia_patient'],
        'patient_percentage': '10%' if pricing_breakdown['is_nhia_patient'] else '100%',
        'nhia_percentage': '90%' if pricing_breakdown['is_nhia_patient'] else '0%',
    }
    return render(request, 'pharmacy/dispense_prescription.html', context)


@login_required
def dispense_prescription_original(request, prescription_id):
    """View for dispensing a prescription (original)"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Implementation for dispensing prescription (original)
    pass


@login_required
def debug_dispense_prescription(request, prescription_id):
    """View for debugging prescription dispensing"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get all dispensaries
    dispensaries = Dispensary.objects.filter(is_active=True)
    
    # Check inventory for each dispensary
    inventory_info = []
    for dispensary in dispensaries:
        dispensary_info = {
            'dispensary': dispensary,
            'medications': []
        }
        
        # Check inventory for each medication in the prescription
        for item in prescription.items.all():
            try:
                inventory = MedicationInventory.objects.get(
                    medication=item.medication,
                    dispensary=dispensary
                )
                dispensary_info['medications'].append({
                    'medication': item.medication,
                    'in_inventory': True,
                    'stock_quantity': inventory.stock_quantity,
                    'reorder_level': inventory.reorder_level
                })
            except MedicationInventory.DoesNotExist:
                dispensary_info['medications'].append({
                    'medication': item.medication,
                    'in_inventory': False,
                    'stock_quantity': 0,
                    'reorder_level': 0
                })
        
        inventory_info.append(dispensary_info)
    
    context = {
        'prescription': prescription,
        'inventory_info': inventory_info,
        'page_title': f'Debug Dispense Prescription - #{prescription.id}'
    }
    
    return render(request, 'pharmacy/debug_dispense_prescription.html', context)


@login_required
def prescription_dispensing_history(request, prescription_id):
    """View for prescription dispensing history"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get all dispensing logs for this prescription's items
    dispensing_logs = DispensingLog.objects.filter(
        prescription_item__prescription=prescription
    ).select_related(
        'prescription_item__medication',
        'dispensed_by',
        'dispensary'
    ).order_by('-dispensed_date')
    
    context = {
        'prescription': prescription,
        'dispensing_logs': dispensing_logs,
        'page_title': f'Dispensing History - Prescription #{prescription.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/prescription_dispensing_history.html', context)


@login_required
def add_prescription_item(request, prescription_id):
    """View for adding a prescription item"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Handle POST from the modal form. On success redirect back to the prescription detail.
    if request.method == 'POST':
        form = PrescriptionItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            # Associate with the prescription
            item.prescription = prescription
            # Set default quantity to 1 (will be adjusted at cart/dispensing level)
            if not item.quantity:
                item.quantity = 1
            # Initialize quantity_dispensed_so_far to 0 for new items
            # This field may not be in the model but is expected by the database
            if hasattr(item, 'quantity_dispensed_so_far'):
                item.quantity_dispensed_so_far = 0
            item.save()
            messages.success(request, 'Medication added to prescription.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        else:
            # Re-render the prescription detail with form errors so the modal can show feedback
            prescription_items = prescription.items.select_related('medication')
            context = {
                'prescription': prescription,
                'prescription_items': prescription_items,
                'item_form': form,
                'page_title': f'Prescription Details - #{prescription.id}',
                'active_nav': 'pharmacy',
            }
            return render(request, 'pharmacy/prescription_detail.html', context)

    # For non-POST requests, send user back to the prescription detail
    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)


@login_required
def delete_prescription_item(request, item_id):
    """View for deleting a prescription item"""
    item = get_object_or_404(PrescriptionItem, id=item_id)
    prescription = item.prescription
    
    if request.method == 'POST':
        # Check if the item has been dispensed (only on POST to allow viewing confirmation)
        if item.is_dispensed or item.quantity_dispensed_so_far > 0:
            messages.error(request, f'Cannot delete {item.medication.name} - it has already been dispensed.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        
        # Safe to delete
        medication_name = item.medication.name
        item.delete()
        messages.success(request, f'Successfully removed {medication_name} from prescription.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # For GET requests, always show confirmation page (with warnings if applicable)
    context = {
        'item': item,
        'prescription': prescription,
        'title': f'Delete Prescription Item - {item.medication.name}',
        'active_nav': 'pharmacy',
        'can_delete': not item.is_dispensed and item.quantity_dispensed_so_far == 0,
    }
    
    return render(request, 'pharmacy/delete_prescription_item.html', context)


@login_required
def prescription_payment(request, prescription_id):
    """View for prescription payment - patient wallet focused"""
    from pharmacy_billing.models import Invoice as PharmacyInvoice, Payment as PharmacyPayment
    from pharmacy_billing.utils import create_pharmacy_invoice
    from patients.models import PatientWallet
    from .forms import PrescriptionPaymentForm
    from django.db import transaction
    from core.audit_utils import log_audit_action
    from core.models import InternalNotification
    
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get or create pharmacy invoice
    pharmacy_invoice = None
    try:
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        # Create invoice using the utility function
        total_price = prescription.get_total_prescribed_price()
        pharmacy_invoice = create_pharmacy_invoice(request, prescription, total_price)
        if not pharmacy_invoice:
            messages.error(request, 'Failed to create invoice for this prescription.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # Get patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=prescription.patient)
    except PatientWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        patient_wallet = PatientWallet.objects.create(
            patient=prescription.patient,
            balance=0
        )
    
    remaining_amount = pharmacy_invoice.get_balance()
    
    if remaining_amount <= 0:
        messages.info(request, 'This prescription has already been fully paid.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    if request.method == 'POST':
        form = PrescriptionPaymentForm(
            request.POST,
            invoice=pharmacy_invoice,
            prescription=prescription,
            patient_wallet=patient_wallet
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Use .get() method instead of direct dictionary access to avoid KeyError
                    amount = form.cleaned_data.get('amount', 0)
                    payment_method = form.cleaned_data.get('payment_method', '')
                    payment_source = form.cleaned_data.get('payment_source', '')
                    transaction_id = form.cleaned_data.get('transaction_id', '')
                    notes = form.cleaned_data.get('notes', '')
                    
                    # Create payment record using pharmacy billing system
                    payment = PharmacyPayment.objects.create(
                        invoice=pharmacy_invoice,
                        amount=amount,
                        payment_method=payment_method,
                        transaction_id=transaction_id,
                        notes=notes + f' (Payment source: {payment_source})',
                        received_by=request.user
                    )
                    
                    # Handle wallet payment
                    if payment_source == 'patient_wallet':
                        # Use wallet's debit method to ensure proper transaction creation
                        patient_wallet.debit(
                            amount=amount,
                            description=f'Payment for prescription #{prescription.id}',
                            transaction_type='pharmacy_payment',
                            user=request.user
                        )
                    
                    # Update invoice
                    pharmacy_invoice.amount_paid += amount
                    if pharmacy_invoice.amount_paid >= pharmacy_invoice.total_amount:
                        pharmacy_invoice.status = 'paid'
                        prescription.payment_status = 'paid'
                        prescription.save(update_fields=['payment_status'])

                        # Update cart status to 'paid' if invoice is fully paid
                        from pharmacy.cart_models import PrescriptionCart
                        carts = PrescriptionCart.objects.filter(
                            invoice=pharmacy_invoice,
                            status='invoiced'
                        )
                        for cart in carts:
                            cart.status = 'paid'
                            cart.save(update_fields=['status'])
                    else:
                        pharmacy_invoice.status = 'partially_paid'

                    pharmacy_invoice.save()
                    
                    # Audit log
                    log_audit_action(
                        request.user,
                        'create',
                        payment,
                        f'Recorded {payment_source} payment of ₦{amount:.2f} for prescription #{prescription.id}'
                    )
                    
                    # Notification
                    if prescription.doctor:
                        InternalNotification.objects.create(
                            user=prescription.doctor,
                            message=f'Payment of ₦{amount:.2f} recorded for prescription #{prescription.id} via {payment_source}'
                        )

                    messages.success(request, f'✅ Payment of ₦{amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')

                    # Redirect to cart if payment is complete and cart exists
                    if pharmacy_invoice.status == 'paid':
                        # Find the cart associated with this invoice
                        from pharmacy.cart_models import PrescriptionCart
                        cart = PrescriptionCart.objects.filter(
                            invoice=pharmacy_invoice,
                            status__in=['paid', 'invoiced']
                        ).first()

                        if cart:
                            messages.info(request, '💊 Payment complete! You can now dispense the medications.')
                            return redirect('pharmacy:view_cart', cart_id=cart.id)

                    # Fallback to prescription detail if no cart found
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                    
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
    else:
        # Pre-fill form with remaining amount and wallet payment as default
        form = PrescriptionPaymentForm(
            invoice=pharmacy_invoice,
            prescription=prescription,
            patient_wallet=patient_wallet,
            initial={
                'amount': remaining_amount,
                'payment_method': 'wallet',
                'payment_source': 'patient_wallet'
            }
        )
    
    # Get carts with status 'invoiced' or 'paid'
    invoiced_or_paid_carts = prescription.carts.filter(status__in=['invoiced', 'paid'])
    
    context = {
        'form': form,
        'prescription': prescription,
        'pharmacy_invoice': pharmacy_invoice,
        'invoice': pharmacy_invoice,  # Template expects 'invoice'
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'invoiced_or_paid_carts': invoiced_or_paid_carts,
        'title': f'Prescription Payment - #{prescription.id}'
    }
    
    return render(request, 'pharmacy/prescription_payment.html', context)


@login_required
def process_outstanding_wallet_payment(request, prescription_id):
    """View for processing outstanding payments from patient wallet"""
    from pharmacy_billing.models import Invoice as PharmacyInvoice
    from patients.models import PatientWallet
    from django.db import transaction
    from core.audit_utils import log_audit_action
    from core.models import InternalNotification
    
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get pharmacy invoice
    pharmacy_invoice = None
    try:
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        messages.error(request, 'No invoice found for this prescription.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # Get patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=prescription.patient)
    except PatientWallet.DoesNotExist:
        messages.error(request, 'Patient does not have a wallet.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    remaining_amount = pharmacy_invoice.get_balance()
    
    if remaining_amount <= 0:
        messages.info(request, 'This prescription has already been fully paid.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # Check if user has permission to process wallet payments
    # Only billing staff and pharmacists should be able to process wallet payments
    user_roles = request.user.roles.values_list('name', flat=True)
    if not any(role in ['billing_staff', 'pharmacist', 'admin'] for role in user_roles):
        messages.error(request, 'You do not have permission to process wallet payments.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Process payment from wallet
                patient_wallet.debit(
                    amount=remaining_amount,
                    description=f'Payment for outstanding prescription #{prescription.id}',
                    transaction_type='pharmacy_payment',
                    user=request.user
                )
                
                # Update invoice
                pharmacy_invoice.amount_paid += remaining_amount
                pharmacy_invoice.status = 'paid'
                pharmacy_invoice.save()
                
                # Update prescription payment status
                prescription.payment_status = 'paid'
                prescription.save(update_fields=['payment_status'])
                
                # Audit log
                log_audit_action(
                    request.user,
                    'create',
                    pharmacy_invoice,
                    f'Processed outstanding payment of ₦{remaining_amount:.2f} from wallet for prescription #{prescription.id}'
                )
                
                # Notification
                if prescription.doctor:
                    InternalNotification.objects.create(
                        user=prescription.doctor,
                        message=f'Outstanding payment of ₦{remaining_amount:.2f} processed from wallet for prescription #{prescription.id}'
                    )
                
                messages.success(request, f'Outstanding payment of ₦{remaining_amount:.2f} processed successfully from patient wallet.')
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    context = {
        'prescription': prescription,
        'pharmacy_invoice': pharmacy_invoice,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'title': f'Process Outstanding Payment - #{prescription.id}'
    }
    
    return render(request, 'pharmacy/process_outstanding_payment.html', context)


@login_required
def print_prescription(request, prescription_id):
    """View for printing prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get prescription items
    prescription_items = prescription.items.select_related('medication')
    
    # Get pharmacy invoice if exists
    pharmacy_invoice = None
    try:
        from pharmacy_billing.models import Invoice as PharmacyInvoice
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        pharmacy_invoice = None
    
    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'pharmacy_invoice': pharmacy_invoice,
        'title': f'Print Prescription - #{prescription.id}'
    }
    
    return render(request, 'pharmacy/print_prescription.html', context)


@login_required
def billing_office_medication_payment(request, prescription_id):
    """View for billing office medication payment - dual payment source support"""
    from pharmacy_billing.models import Invoice as PharmacyInvoice, Payment as PharmacyPayment
    from pharmacy_billing.utils import create_pharmacy_invoice
    from patients.models import PatientWallet
    from django.db import transaction
    from core.audit_utils import log_audit_action
    from core.models import InternalNotification
    
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get or create pharmacy invoice
    pharmacy_invoice = None
    try:
        pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    except PharmacyInvoice.DoesNotExist:
        # Create invoice using the utility function
        total_price = prescription.get_total_prescribed_price()
        pharmacy_invoice = create_pharmacy_invoice(request, prescription, total_price)
        if not pharmacy_invoice:
            messages.error(request, 'Failed to create invoice for this prescription.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # Get patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=prescription.patient)
    except PatientWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        patient_wallet = PatientWallet.objects.create(
            patient=prescription.patient,
            balance=0
        )
    
    remaining_amount = pharmacy_invoice.get_balance()
    
    if remaining_amount <= 0:
        messages.info(request, 'This prescription has already been fully paid.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    if request.method == 'POST':
        payment_source = request.POST.get('payment_source', 'billing_office')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'cash')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, 'Payment amount must be greater than zero.')
                return redirect('pharmacy:billing_office_medication_payment', prescription_id=prescription.id)
            
            if amount > pharmacy_invoice.get_balance():
                messages.error(request, f'Payment amount cannot exceed the remaining balance of ₦{pharmacy_invoice.get_balance():.2f}.')
                return redirect('pharmacy:billing_office_medication_payment', prescription_id=prescription.id)
            
            with transaction.atomic():
                # Force wallet payment method for wallet payments
                if payment_source == 'patient_wallet':
                    payment_method = 'wallet'
                
                # Create payment record using pharmacy billing system  
                payment = PharmacyPayment.objects.create(
                    invoice=pharmacy_invoice,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    notes=notes + f' (Billing office - {payment_source})',
                    received_by=request.user
                )
                
                # Handle wallet payment
                if payment_source == 'patient_wallet':
                    # Use wallet's debit method to ensure proper transaction creation
                    patient_wallet.debit(
                        amount=amount,
                        description=f'Payment for prescription #{prescription.id} (Billing office)',
                        transaction_type='pharmacy_payment',
                        user=request.user
                    )
                
                # Update invoice
                pharmacy_invoice.amount_paid += amount
                if pharmacy_invoice.amount_paid >= pharmacy_invoice.total_amount:
                    pharmacy_invoice.status = 'paid'
                    # Mark that this is a manual payment processed by billing staff
                    pharmacy_invoice._manual_payment_processed = True
                    prescription.payment_status = 'paid'
                    prescription.save(update_fields=['payment_status'])

                    # Update cart status to 'paid' if invoice is fully paid
                    from pharmacy.cart_models import PrescriptionCart
                    carts = PrescriptionCart.objects.filter(
                        invoice=pharmacy_invoice,
                        status='invoiced'
                    )
                    for cart in carts:
                        cart.status = 'paid'
                        cart.save(update_fields=['status'])
                else:
                    pharmacy_invoice.status = 'partially_paid'

                pharmacy_invoice.save()

                # Audit log
                log_audit_action(
                    request.user,
                    'create',
                    payment,
                    f'Billing office recorded {payment_source} payment of ₦{amount:.2f} for prescription #{prescription.id}'
                )

                # Notification
                if prescription.doctor:
                    InternalNotification.objects.create(
                        user=prescription.doctor,
                        message=f'Billing office recorded payment of ₦{amount:.2f} for prescription #{prescription.id} via {payment_source}'
                    )

                messages.success(request, f'✅ Payment of ₦{amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')

                # Redirect to cart if payment is complete and cart exists
                if pharmacy_invoice.status == 'paid':
                    # Find the cart associated with this invoice
                    from pharmacy.cart_models import PrescriptionCart
                    cart = PrescriptionCart.objects.filter(
                        invoice=pharmacy_invoice,
                        status__in=['paid', 'invoiced']
                    ).first()

                    if cart:
                        messages.info(request, '💊 Payment complete! Pharmacist can now dispense the medications from the cart.')
                        return redirect('pharmacy:view_cart', cart_id=cart.id)

                # Fallback to prescription detail if no cart found
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                
        except (ValueError, TypeError):
            messages.error(request, 'Invalid payment amount.')
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
    
    # Get payment history
    payments = pharmacy_invoice.payments.all().order_by('-payment_date')
    
    # Get pricing breakdown for enhanced NHIA display
    pricing_breakdown = prescription.get_pricing_breakdown()
    
    # Calculate item-level pricing for detailed display
    prescription_items = prescription.items.all().select_related('medication')
    items_with_pricing = []
    for item in prescription_items:
        item_total = item.medication.price * item.quantity
        if pricing_breakdown['is_nhia_patient']:
            patient_pays = item_total * Decimal('0.10')
            nhia_covers = item_total * Decimal('0.90')
        else:
            patient_pays = item_total
            nhia_covers = Decimal('0.00')

        items_with_pricing.append({
            'item': item,
            'total_cost': item_total,
            'patient_pays': patient_pays,
            'nhia_covers': nhia_covers
        })
    
    context = {
        'prescription': prescription,
        'pharmacy_invoice': pharmacy_invoice,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'payments': payments,
        'title': f'Billing Office - Medication Payment #{prescription.id}',
        # Enhanced NHIA context
        'pricing_breakdown': pricing_breakdown,
        'prescription_items': prescription_items,
        'items_with_pricing': items_with_pricing,
        'nhia_patient_pays_percentage': '10%' if pricing_breakdown['is_nhia_patient'] else '100%',
        'nhia_covers_percentage': '90%' if pricing_breakdown['is_nhia_patient'] else '0%',
        'patient_payment_amount': pricing_breakdown['patient_portion'],
        'total_medication_cost': pricing_breakdown['total_medication_cost'],
    }
    
    return render(request, 'pharmacy/billing_office_medication_payment.html', context)


@login_required
def create_prescription_invoice(request, prescription_id):
    """View for creating prescription invoice"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Use the centralized utility to create the invoice so behavior is consistent
    try:
        from core.prescription_utils import create_prescription_invoice as util_create_invoice

        invoice = util_create_invoice(prescription)
        if invoice:
            messages.success(request, f'Invoice #{invoice.invoice_number} created successfully.')
            # Redirect to the billing invoice detail view
            return redirect('billing:detail', invoice.id)
        else:
            messages.error(request, 'Failed to create invoice for this prescription.')
    except Exception as e:
        messages.error(request, f'Error creating invoice: {str(e)}')

    # On error, redirect back to the prescription detail page
    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)


@login_required
@require_http_methods(["POST"])
def check_medication_availability(request):
    """
    AJAX endpoint to check medication availability in a specific dispensary.
    Returns availability status for each medication.
    """
    import json
    from decimal import Decimal

    try:
        data = json.loads(request.body)
        dispensary_id = data.get('dispensary_id')
        medications = data.get('medications', [])

        if not dispensary_id:
            return JsonResponse({'error': 'Dispensary ID required'}, status=400)

        dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
        active_store = getattr(dispensary, 'active_store', None)

        results = []

        for med_data in medications:
            item_id = med_data.get('item_id')
            medication_id = med_data.get('medication_id')
            requested_quantity = Decimal(str(med_data.get('quantity', 0)))

            # Get medication
            medication = get_object_or_404(Medication, id=medication_id)

            # Check availability
            available_quantity = Decimal('0')

            # Check ActiveStoreInventory
            if active_store:
                inventory_items = ActiveStoreInventory.objects.filter(
                    medication=medication,
                    active_store=active_store,
                    stock_quantity__gt=0
                )
                available_quantity += sum(Decimal(str(inv.stock_quantity)) for inv in inventory_items)

            # Check legacy inventory
            try:
                legacy_inv = MedicationInventory.objects.filter(
                    medication=medication,
                    dispensary=dispensary,
                    stock_quantity__gt=0
                ).first()
                if legacy_inv:
                    available_quantity += Decimal(str(legacy_inv.stock_quantity))
            except:
                pass

            # Calculate price
            unit_price = medication.selling_price if hasattr(medication, 'selling_price') else medication.price
            total_price = unit_price * requested_quantity

            is_available = available_quantity >= requested_quantity

            results.append({
                'item_id': item_id,
                'medication_id': medication_id,
                'medication_name': medication.name,
                'quantity': float(requested_quantity),
                'stock_available': float(available_quantity),
                'available': is_available,
                'unit_price': float(unit_price),
                'total_price': float(total_price)
            })

        return JsonResponse({
            'success': True,
            'medications': results
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def pharmacist_generate_invoice(request, prescription_id):
    """
    View for pharmacist to generate invoice after checking medication availability.
    Only generates invoice for medications that are available in the selected dispensary.
    Accepts custom quantities from pharmacist input.
    """
    from pharmacy_billing.models import Invoice as PharmacyInvoice
    from pharmacy_billing.utils import create_pharmacy_invoice
    from django.db import transaction
    from core.audit_utils import log_audit_action
    import json

    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check if invoice already exists
    try:
        existing_invoice = PharmacyInvoice.objects.get(prescription=prescription)
        messages.warning(request, f'Invoice already exists for this prescription.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    except PharmacyInvoice.DoesNotExist:
        pass

    # Get all dispensaries
    dispensaries = Dispensary.objects.filter(is_active=True)

    if request.method == 'POST':
        dispensary_id = request.POST.get('dispensary_id')
        if not dispensary_id:
            messages.error(request, 'Please select a dispensary.')
            return redirect('pharmacy:pharmacist_generate_invoice', prescription_id=prescription.id)

        dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)

        # Get availability data from form
        availability_data_str = request.POST.get('availability_data')

        try:
            with transaction.atomic():
                # Parse availability data
                if availability_data_str:
                    availability_data = json.loads(availability_data_str)
                    medications_data = availability_data.get('medications', [])
                else:
                    messages.error(request, 'Please check availability before generating invoice.')
                    return redirect('pharmacy:pharmacist_generate_invoice', prescription_id=prescription.id)

                # Get prescription items
                prescription_items = prescription.items.all()
                available_items = []
                unavailable_items = []
                total_available_amount = Decimal('0.00')

                # Process each medication based on availability check
                for med_data in medications_data:
                    item_id = med_data.get('item_id')
                    is_available = med_data.get('available', False)
                    quantity = Decimal(str(med_data.get('quantity', 0)))

                    # Get the prescription item
                    try:
                        item = prescription_items.get(id=item_id)
                    except:
                        continue

                    # Get custom quantity from form if provided
                    custom_quantity_key = f'quantity_{item_id}'
                    if custom_quantity_key in request.POST:
                        quantity = Decimal(str(request.POST.get(custom_quantity_key, quantity)))

                    if quantity <= 0:
                        continue

                    medication = item.medication

                    if is_available:
                        available_items.append({
                            'item': item,
                            'quantity': quantity,
                            'status': 'available'
                        })

                        # Calculate amount based on NHIA status
                        unit_price = medication.selling_price if hasattr(medication, 'selling_price') else medication.price
                        item_cost = unit_price * quantity

                        if prescription.patient.is_nhia_patient():
                            # NHIA patients pay 10%
                            total_available_amount += item_cost * Decimal('0.10')
                        else:
                            total_available_amount += item_cost
                    else:
                        unavailable_items.append({
                            'item': item,
                            'quantity': quantity,
                            'status': 'insufficient'
                        })

                # If no items are available, show error
                if not available_items:
                    messages.error(request, 'No medications are available in the selected dispensary. Cannot generate invoice.')
                    return redirect('pharmacy:pharmacist_generate_invoice', prescription_id=prescription.id)

                # Create pharmacy invoice for available items only
                pharmacy_invoice = create_pharmacy_invoice(request, prescription, total_available_amount)

                if pharmacy_invoice:
                    # Log audit action
                    log_audit_action(
                        request.user,
                        'create',
                        pharmacy_invoice,
                        f'Generated invoice for prescription #{prescription.id} at {dispensary.name}. '
                        f'Available items: {len(available_items)}, Unavailable items: {len(unavailable_items)}'
                    )

                    success_msg = f'Invoice generated successfully for {len(available_items)} available medication(s).'
                    if unavailable_items:
                        success_msg += f' Note: {len(unavailable_items)} medication(s) are not available in {dispensary.name}.'

                    messages.success(request, success_msg)
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                else:
                    messages.error(request, 'Failed to create invoice.')
                    return redirect('pharmacy:pharmacist_generate_invoice', prescription_id=prescription.id)

        except Exception as e:
            messages.error(request, f'Error generating invoice: {str(e)}')
            return redirect('pharmacy:pharmacist_generate_invoice', prescription_id=prescription.id)

    # GET request - show availability check page
    # Check availability for all items across all dispensaries
    prescription_items = prescription.items.select_related('medication')
    items_availability = []

    for item in prescription_items:
        medication = item.medication
        quantity = item.quantity
        dispensary_stock = []

        for dispensary in dispensaries:
            active_store = getattr(dispensary, 'active_store', None)
            available_quantity = 0

            if active_store:
                inventory_items = ActiveStoreInventory.objects.filter(
                    medication=medication,
                    active_store=active_store,
                    stock_quantity__gt=0
                )
                available_quantity = sum(inv.stock_quantity for inv in inventory_items)

            # Also check legacy inventory
            try:
                legacy_inv = MedicationInventory.objects.filter(
                    medication=medication,
                    dispensary=dispensary,
                    stock_quantity__gt=0
                ).first()
                if legacy_inv:
                    available_quantity += legacy_inv.stock_quantity
            except:
                pass

            dispensary_stock.append({
                'dispensary': dispensary,
                'available': available_quantity,
                'sufficient': available_quantity >= quantity
            })

        items_availability.append({
            'item': item,
            'dispensary_stock': dispensary_stock
        })

    context = {
        'prescription': prescription,
        'items_availability': items_availability,
        'dispensaries': dispensaries,
        'page_title': f'Generate Invoice - Prescription #{prescription.id}',
        'active_nav': 'pharmacy',
    }

    return render(request, 'pharmacy/pharmacist_generate_invoice.html', context)


@login_required
def medication_api(request):
    """API endpoint for medications"""
    from django.http import JsonResponse

    # Get all active medications
    medications = Medication.objects.filter(is_active=True).select_related('category')

    # Build response data
    data = []
    for med in medications:
        data.append({
            'id': med.id,
            'name': med.name,
            'generic_name': med.generic_name,
            'category': med.category.name if med.category else None,
            'price': float(med.price),
            'dosage_form': med.dosage_form,
            'strength': med.strength,
        })

    return JsonResponse(data, safe=False)


@login_required
def expiring_medications_report(request):
    """View for expiring medications report"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Get medications expiring within 90 days (changed from 30 days)
    expiring_soon = ActiveStoreInventory.objects.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=90),
        expiry_date__gte=timezone.now().date()
    ).select_related('medication', 'active_store__dispensary').order_by('expiry_date')
    
    # Get already expired medications
    expired = ActiveStoreInventory.objects.filter(
        expiry_date__lt=timezone.now().date()
    ).select_related('medication', 'active_store__dispensary').order_by('expiry_date')
    
    context = {
        'expiring_soon': expiring_soon,
        'expired': expired,
        'title': 'Expiring Medications Report',
        'active_nav': 'pharmacy',
    }
    return render(request, 'pharmacy/reports/expiring_medications_report.html', context)


@login_required
def low_stock_medications_report(request):
    """View for low stock medications report"""
    # Get low stock items
    low_stock_items = ActiveStoreInventory.objects.filter(
        stock_quantity__lte=models.F('reorder_level')
    ).select_related('medication', 'active_store__dispensary').order_by('stock_quantity')
    
    context = {
        'low_stock_items': low_stock_items,
        'title': 'Low Stock Medications Report',
        'active_nav': 'pharmacy',
    }
    return render(request, 'pharmacy/reports/low_stock_medications_report.html', context)





@login_required
def dispensing_report(request):
    """View for dispensing report"""
    # Implementation for dispensing report
    pass


@login_required
def dispensed_items_tracker(request):
    """View for dispensed items tracker"""
    from .models import DispensingLog
    
    # Get all dispensing logs
    dispensing_logs = DispensingLog.objects.select_related(
        'prescription_item__medication',
        'prescription_item__prescription__patient',
        'dispensed_by',
        'dispensary'
    ).order_by('-dispensed_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        dispensing_logs = dispensing_logs.filter(
            Q(prescription_item__medication__name__icontains=search_query) |
            Q(prescription_item__prescription__patient__first_name__icontains=search_query) |
            Q(prescription_item__prescription__patient__last_name__icontains=search_query)
        )
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            dispensing_logs = dispensing_logs.filter(dispensed_date__date__gte=date_from)
        except ValueError:
            pass
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            dispensing_logs = dispensing_logs.filter(dispensed_date__date__lte=date_to)
        except ValueError:
            pass
    
    # Filter by dispensary
    dispensary_id = request.GET.get('dispensary', '')
    if dispensary_id:
        dispensing_logs = dispensing_logs.filter(dispensary_id=dispensary_id)
    
    # Pagination
    paginator = Paginator(dispensing_logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get dispensaries for filter dropdown
    dispensaries = Dispensary.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'dispensaries': dispensaries,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'dispensary_id': dispensary_id,
        'page_title': 'Dispensed Items Tracker',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/dispensed_items_tracker.html', context)


@login_required
def dispensed_item_detail(request, log_id):
    """View for dispensed item detail"""
    from .models import DispensingLog
    
    # Get the dispensing log
    dispensing_log = get_object_or_404(
        DispensingLog.objects.select_related(
            'prescription_item__medication',
            'prescription_item__prescription__patient',
            'prescription_item__prescription__doctor',
            'dispensed_by',
            'dispensary'
        ), 
        id=log_id
    )
    
    context = {
        'dispensing_log': dispensing_log,
        'page_title': f'Dispensed Item Detail - {dispensing_log.prescription_item.medication.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/dispensed_item_detail.html', context)


@login_required
def dispensed_items_export(request):
    """View for exporting dispensed items"""
    from .models import DispensingLog
    from django.http import HttpResponse
    import csv
    
    # Get all dispensing logs
    dispensing_logs = DispensingLog.objects.select_related(
        'prescription_item__medication',
        'prescription_item__prescription__patient',
        'dispensed_by',
        'dispensary'
    ).order_by('-dispensed_date')
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dispensed_items.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Medication', 'Strength', 'Patient', 'Quantity', 
        'Unit Price', 'Total Price', 'Dispensed By', 
        'Dispensary', 'Date'
    ])
    
    for log in dispensing_logs:
        writer.writerow([
            log.prescription_item.medication.name,
            log.prescription_item.medication.strength,
            log.prescription_item.prescription.patient.get_full_name(),
            log.dispensed_quantity,
            log.unit_price_at_dispense,
            log.total_price_for_this_log,
            log.dispensed_by.get_full_name() if log.dispensed_by else log.dispensed_by.username,
            log.dispensary.name if log.dispensary else 'N/A',
            log.dispensed_date.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response


@login_required
def dispensary_list(request):
    """View for listing dispensaries"""
    dispensaries = Dispensary.objects.filter(is_active=True).order_by('name')
    
    context = {
        'dispensaries': dispensaries,
        'page_title': 'Dispensary List',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/dispensary_list.html', context)


@login_required
def edit_dispensary(request, dispensary_id):
    """View for editing a dispensary and its associated active store"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)

    # Get or create the associated active store
    active_store = getattr(dispensary, 'active_store', None)

    if request.method == 'POST':
        form = DispensaryForm(request.POST, instance=dispensary)
        if form.is_valid():
            with transaction.atomic():
                # Save dispensary
                dispensary = form.save()

                # Create or update active store based on dispensary changes
                if not active_store:
                    # Create new active store if it doesn't exist
                    active_store = ActiveStore.objects.create(
                        dispensary=dispensary,
                        name=f"Active Store - {dispensary.name}",
                        location=dispensary.location or "Same as dispensary",
                        description=f"Active storage area for {dispensary.name}",
                        capacity=1000,  # Default capacity
                        is_active=dispensary.is_active
                    )
                    messages.success(request, f'Created active store for {dispensary.name}.')
                else:
                    # Update existing active store to match dispensary
                    active_store.name = f"Active Store - {dispensary.name}"
                    active_store.location = dispensary.location or active_store.location
                    active_store.is_active = dispensary.is_active
                    active_store.save()
                    messages.success(request, f'Updated active store for {dispensary.name}.')

                messages.success(request, f'Dispensary {dispensary.name} updated successfully.')
                return redirect('pharmacy:dispensary_list')
    else:
        form = DispensaryForm(instance=dispensary)

    context = {
        'form': form,
        'dispensary': dispensary,
        'active_store': active_store,
        'page_title': f'Edit Dispensary - {dispensary.name}',
        'active_nav': 'pharmacy',
    }

    return render(request, 'pharmacy/edit_dispensary.html', context)


@login_required
def add_dispensary(request):
    """View for adding a new dispensary with automatic active store creation"""
    if request.method == 'POST':
        form = DispensaryForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Save dispensary
                dispensary = form.save()

                # Automatically create associated active store
                active_store = ActiveStore.objects.create(
                    dispensary=dispensary,
                    name=f"Active Store - {dispensary.name}",
                    location=dispensary.location or "Same as dispensary",
                    description=f"Active storage area for {dispensary.name}",
                    capacity=1000,  # Default capacity
                    is_active=dispensary.is_active
                )

                messages.success(request, f'Dispensary {dispensary.name} created successfully with active store.')
                return redirect('pharmacy:dispensary_list')
    else:
        form = DispensaryForm()

    context = {
        'form': form,
        'page_title': 'Add Dispensary',
        'active_nav': 'pharmacy',
    }

    return render(request, 'pharmacy/add_dispensary.html', context)


@login_required
def delete_dispensary(request, dispensary_id):
    """View for deleting a dispensary"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    
    if request.method == 'POST':
        dispensary.is_active = False
        dispensary.save()
        messages.success(request, f'Dispensary {dispensary.name} deactivated successfully.')
        return redirect('pharmacy:dispensary_list')
    
    context = {
        'dispensary': dispensary,
        'page_title': f'Delete Dispensary - {dispensary.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/delete_dispensary.html', context)


@login_required
def dispensary_inventory(request, dispensary_id):
    """View for dispensary inventory"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    
    # Get inventory items from ActiveStoreInventory (new) and MedicationInventory (legacy)
    active_store_items = ActiveStoreInventory.objects.filter(
        active_store__dispensary=dispensary
    ).select_related('medication', 'active_store')

    legacy_items = MedicationInventory.objects.filter(
        dispensary=dispensary
    ).select_related('medication', 'dispensary')

    # Normalize legacy items into a common structure so template can iterate uniformly
    # We'll create a list of dicts with expected attributes used by template: medication, stock_quantity, reorder_level, last_restock_date, id
    inventory_items = []
    for item in active_store_items:
        inventory_items.append({
            'id': item.id,
            'medication': item.medication,
            'stock_quantity': item.stock_quantity,
            'reorder_level': getattr(item, 'reorder_level', None),
            'last_restock_date': getattr(item, 'last_restock_date', None),
            'source': 'active_store',
            'object': item,
        })

    for item in legacy_items:
        inventory_items.append({
            'id': item.id,
            'medication': item.medication,
            'stock_quantity': item.stock_quantity,
            'reorder_level': getattr(item, 'reorder_level', None),
            'last_restock_date': item.last_restock_date,
            'source': 'legacy',
            'object': item,
        })

    # Optional: sort by medication name for consistent display
    inventory_items.sort(key=lambda x: (x['medication'].name.lower() if x['medication'] and x['medication'].name else ''))
    
    context = {
        'dispensary': dispensary,
    'inventory_items': inventory_items,
        'page_title': f'{dispensary.name} Inventory',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/dispensary_inventory.html', context)


@login_required
def add_dispensary_inventory_item(request, dispensary_id):
    """View for adding a dispensary inventory item"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    # Prefer creating an ActiveStoreInventory tied to the dispensary's active store if present
    active_store = getattr(dispensary, 'active_store', None)
    if request.method == 'POST':
        if active_store:
            form = ActiveStoreInventoryForm(request.POST)
        else:
            form = MedicationInventoryForm(request.POST)

        if form.is_valid():
            new_item = form.save(commit=False)
            # If using legacy MedicationInventory form and dispensary provided, ensure association
            if isinstance(new_item, MedicationInventory) or not active_store:
                # Ensure dispensary set for legacy model
                if hasattr(new_item, 'dispensary'):
                    new_item.dispensary = dispensary
            else:
                # For ActiveStoreInventory, set active_store if not provided
                if hasattr(new_item, 'active_store') and not new_item.active_store:
                    new_item.active_store = active_store

            new_item.save()
            messages.success(request, 'Inventory item added successfully.')
            return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)
    else:
        # Prepopulate forms
        if active_store:
            form = ActiveStoreInventoryForm(initial={'active_store': active_store.id})
        else:
            form = MedicationInventoryForm(initial={'dispensary': dispensary.id})

    context = {
        'form': form,
        'dispensary': dispensary,
        'page_title': f'Add Inventory Item - {dispensary.name}',
        'active_nav': 'pharmacy',
    }
    return render(request, 'pharmacy/add_dispensary_inventory_item.html', context)


@login_required
def edit_dispensary_inventory_item(request, dispensary_id, inventory_item_id):
    """View for editing a dispensary inventory item"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    # Support both ActiveStoreInventory (new) and MedicationInventory (legacy)
    inventory_item = None
    source = None
    try:
        inventory_item = ActiveStoreInventory.objects.get(id=inventory_item_id)
        source = 'active_store'
    except ActiveStoreInventory.DoesNotExist:
        try:
            inventory_item = MedicationInventory.objects.get(id=inventory_item_id)
            source = 'legacy'
        except MedicationInventory.DoesNotExist:
            messages.error(request, 'Inventory item not found.')
            return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)

    if source == 'active_store':
        form_class = ActiveStoreInventoryForm
        instance = inventory_item
    else:
        form_class = MedicationInventoryForm
        instance = inventory_item

    if request.method == 'POST':
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Inventory item updated successfully.')
            return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)
    else:
        form = form_class(instance=instance)

    context = {
        'form': form,
        'dispensary': dispensary,
        'inventory_item': inventory_item,
        'page_title': f'Edit Inventory Item - {dispensary.name}',
        'active_nav': 'pharmacy',
    }
    return render(request, 'pharmacy/edit_dispensary_inventory_item.html', context)


@login_required
def delete_dispensary_inventory_item(request, dispensary_id, inventory_item_id):
    """View for deleting a dispensary inventory item"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    # Support both ActiveStoreInventory (new) and MedicationInventory (legacy)
    inventory_item = None
    source = None
    try:
        inventory_item = ActiveStoreInventory.objects.get(id=inventory_item_id)
        source = 'active_store'
    except ActiveStoreInventory.DoesNotExist:
        try:
            inventory_item = MedicationInventory.objects.get(id=inventory_item_id)
            source = 'legacy'
        except MedicationInventory.DoesNotExist:
            messages.error(request, 'Inventory item not found.')
            return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)

    if request.method == 'POST':
        inventory_item.delete()
        messages.success(request, 'Inventory item deleted successfully.')
        return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)

    context = {
        'dispensary': dispensary,
        'inventory_item': inventory_item,
        'source': source,
        'page_title': f'Delete Inventory Item - {dispensary.name}',
        'active_nav': 'pharmacy',
    }
    return render(request, 'pharmacy/delete_dispensary_inventory_item.html', context)





@login_required
def add_medication_stock(request):
    """View for adding medication stock"""
    # Implementation for adding medication stock
    pass
@login_required
def quick_add_stock(request):
    """View for quick adding stock"""
    # Implementation for quick adding stock
    pass


@login_required
def medication_autocomplete(request):
    """API endpoint for medication autocomplete"""
    # Implementation for medication autocomplete
    pass


@login_required
def get_stock_quantities(request, prescription_id):
    """AJAX endpoint to get stock quantities for prescription items at a given dispensary"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    dispensary_id = request.GET.get('dispensary_id') or request.POST.get('dispensary_id')
    response = {
        'success': False,
        'stock_quantities': [],
        'dispensary': None,
        'message': ''
    }

    if not dispensary_id:
        response['message'] = 'No dispensary specified.'
        return JsonResponse(response, status=400)

    try:
        dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
    except Dispensary.DoesNotExist:
        response['message'] = 'Dispensary not found.'
        return JsonResponse(response, status=404)

    # Build stock info for each prescription item
    stock_quantities = []
    for p_item in prescription.items.select_related('medication'):
        # Check both inventory models
        stock_qty = 0
        try:
            # First try MedicationInventory (legacy)
            med_inv = MedicationInventory.objects.get(medication=p_item.medication, dispensary=dispensary)
            stock_qty = med_inv.stock_quantity
        except MedicationInventory.DoesNotExist:
            # If not found, try ActiveStoreInventory (new)
            try:
                active_store = getattr(dispensary, 'active_store', None)
                if active_store:
                    # Handle multiple inventory records by summing all available stock
                    inventories = ActiveStoreInventory.objects.filter(
                        medication=p_item.medication, 
                        active_store=active_store
                    )
                    stock_qty = sum(inv.stock_quantity for inv in inventories)
            except Exception:
                stock_qty = 0

        stock_quantities.append({
            'prescription_item_id': p_item.id,
            'medication_id': p_item.medication.id,
            'medication_name': p_item.medication.name,
            'prescribed_quantity': p_item.quantity,
            'quantity_dispensed_so_far': p_item.quantity_dispensed_so_far,
            'remaining_to_dispense': p_item.remaining_quantity_to_dispense,
            'stock_quantity': stock_qty,
        })

    response['success'] = True
    response['stock_quantities'] = stock_quantities
    response['dispensary'] = {'id': dispensary.id, 'name': dispensary.name}
    return JsonResponse(response)


@login_required
def low_stock_alerts(request):
    """View to display low stock medications and send alerts"""
    # Get all active store inventories that are low on stock
    low_stock_items = ActiveStoreInventory.objects.filter(
        stock_quantity__lte=models.F('reorder_level')
    ).select_related('medication', 'active_store__dispensary')
    
    # Get expired medications
    from django.utils import timezone
    expired_items = ActiveStoreInventory.objects.filter(
        expiry_date__lte=timezone.now().date()
    ).select_related('medication', 'active_store__dispensary')
    
    # Get medications expiring within 90 days (changed from 30 days)
    from datetime import timedelta
    near_expiry_items = ActiveStoreInventory.objects.filter(
        expiry_date__gt=timezone.now().date(),
        expiry_date__lte=timezone.now().date() + timedelta(days=90)
    ).select_related('medication', 'active_store__dispensary')
    
    context = {
        'low_stock_items': low_stock_items,
        'expired_items': expired_items,
        'near_expiry_items': near_expiry_items,
        'page_title': 'Pharmacy Alerts',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/alerts.html', context)


# Medical Pack Management Views

@login_required
def medical_pack_list(request):
    """View for listing all medical packs"""
    from .forms import PackFilterForm
    
    form = PackFilterForm(request.GET)
    # Use proper prefetch for performance with the correct relationship
    try:
        packs = MedicalPack.objects.prefetch_related('items__medication')
    except Exception as e:
        messages.error(request, f'Error loading medical packs: {str(e)}')
        packs = MedicalPack.objects.none()
    
    # Apply filters
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            packs = packs.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(items__medication__name__icontains=search)
            ).distinct()
        
        if form.cleaned_data.get('pack_type'):
            packs = packs.filter(pack_type=form.cleaned_data['pack_type'])
        
        if form.cleaned_data.get('risk_level'):
            packs = packs.filter(risk_level=form.cleaned_data['risk_level'])
        
        if form.cleaned_data.get('is_active'):
            is_active = form.cleaned_data['is_active'] == 'true'
            packs = packs.filter(is_active=is_active)
    
    # Pagination
    paginator = Paginator(packs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'page_title': 'Medical Packs',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medical_packs/pack_list.html', context)


@login_required
def medical_pack_detail(request, pack_id):
    """View for displaying medical pack details"""
    pack = get_object_or_404(MedicalPack, id=pack_id)
    
    # Check if pack can be ordered
    can_order, order_message = pack.can_be_ordered()
    
    context = {
        'pack': pack,
        'can_order': can_order,
        'order_message': order_message,
        'page_title': f'Pack Details - {pack.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medical_packs/pack_detail.html', context)


@login_required
def create_medical_pack(request):
    """View for creating a new medical pack"""
    from .forms import MedicalPackForm
    
    if request.method == 'POST':
        form = MedicalPackForm(request.POST)
        if form.is_valid():
            pack = form.save(commit=False)
            pack.created_by = request.user
            pack.save()
            messages.success(request, f'Medical pack "{pack.name}" created successfully.')
            return redirect('pharmacy:medical_pack_detail', pack_id=pack.id)
    else:
        form = MedicalPackForm()
    
    context = {
        'form': form,
        'page_title': 'Create Medical Pack',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medical_packs/pack_form.html', context)


@login_required
def edit_medical_pack(request, pack_id):
    """View for editing a medical pack"""
    from .forms import MedicalPackForm
    
    pack = get_object_or_404(MedicalPack, id=pack_id)
    
    if request.method == 'POST':
        form = MedicalPackForm(request.POST, instance=pack)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medical pack "{pack.name}" updated successfully.')
            return redirect('pharmacy:medical_pack_detail', pack_id=pack.id)
    else:
        form = MedicalPackForm(instance=pack)
    
    context = {
        'form': form,
        'pack': pack,
        'page_title': f'Edit Pack - {pack.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medical_packs/pack_form.html', context)


@login_required
def manage_pack_items(request, pack_id):
    """View for managing items in a medical pack"""
    from .forms import PackItemForm
    
    pack = get_object_or_404(MedicalPack, id=pack_id)
    
    if request.method == 'POST':
        form = PackItemForm(request.POST)
        if form.is_valid():
            pack_item = form.save(commit=False)
            pack_item.pack = pack
            pack_item.save()
            pack.update_total_cost()
            messages.success(request, f'Added {pack_item.medication.name} to pack.')
            return redirect('pharmacy:manage_pack_items', pack_id=pack.id)
    else:
        form = PackItemForm()
    
    pack_items = pack.items.select_related('medication').order_by('order', 'medication__name')
    
    context = {
        'pack': pack,
        'pack_items': pack_items,
        'form': form,
        'page_title': f'Manage Items - {pack.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medical_packs/manage_pack_items.html', context)


@login_required
def delete_pack_item(request, pack_id, item_id):
    """View for deleting an item from a medical pack"""
    pack = get_object_or_404(MedicalPack, id=pack_id)
    pack_item = get_object_or_404(PackItem, id=item_id, pack=pack)
    
    if request.method == 'POST':
        medication_name = pack_item.medication.name
        pack_item.delete()
        pack.update_total_cost()
        messages.success(request, f'Removed {medication_name} from pack.')
        return redirect('pharmacy:manage_pack_items', pack_id=pack.id)
    
    context = {
        'pack': pack,
        'pack_item': pack_item,
        'page_title': f'Delete Item - {pack_item.medication.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/medical_packs/confirm_delete_item.html', context)


@login_required
def create_pack_order(request, pack_id=None):
    """View for creating a pack order"""
    from .forms import PackOrderForm
    from patients.models import Patient
    
    pack = None
    if pack_id:
        pack = get_object_or_404(MedicalPack, id=pack_id)
    
    # Check for surgery or labor record context
    surgery_id = request.GET.get('surgery_id')
    labor_id = request.GET.get('labor_id')
    patient_id = request.GET.get('patient_id')
    
    surgery = None
    labor_record = None
    patient = None
    
    if surgery_id:
        try:
            from theatre.models import Surgery
            surgery = Surgery.objects.get(id=surgery_id)
            patient = surgery.patient
        except Surgery.DoesNotExist:
            messages.error(request, 'Surgery not found.')
            return redirect('pharmacy:medical_pack_list')
        except ImportError:
            messages.error(request, 'Surgery module not available.')
            return redirect('pharmacy:medical_pack_list')
    
    if labor_id:
        try:
            from labor.models import LaborRecord
            labor_record = LaborRecord.objects.get(id=labor_id)
            patient = labor_record.patient
        except LaborRecord.DoesNotExist:
            messages.error(request, 'Labor record not found.')
            return redirect('pharmacy:medical_pack_list')
        except ImportError:
            messages.error(request, 'Labor module not available.')
            return redirect('pharmacy:medical_pack_list')
    
    if patient_id and not patient:
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient not found.')
            return redirect('pharmacy:medical_pack_list')
    
    if request.method == 'POST':
        form = PackOrderForm(
            request.POST,
            preselected_patient=patient,
            surgery=surgery,
            labor_record=labor_record
        )
        if form.is_valid():
            pack_order = form.save(commit=False)
            pack_order.ordered_by = request.user
            if pack:
                pack_order.pack = pack
            pack_order.save()
            
            # Automatically create prescription from pack items
            try:
                prescription = pack_order.create_prescription()
                
                # Add pack costs to patient billing
                _add_pack_to_patient_billing(pack_order.patient, pack_order, 'pharmacy')
                
                messages.success(
                    request,
                    f'Pack order for {pack_order.pack.name} created successfully. Order ID: {pack_order.id}. '
                    f'Prescription #{prescription.id} has been automatically created with {prescription.items.count()} medications. '
                    f'Pack cost (₦{pack_order.pack.get_total_cost():.2f}) has been added to patient billing.'
                )
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            except Exception as e:
                # Pack order was created but prescription failed
                messages.warning(
                    request,
                    f'Pack order for {pack_order.pack.name} created successfully (Order ID: {pack_order.id}), '
                    f'but prescription creation failed: {str(e)}. Please create the prescription manually if needed.'
                )
                return redirect('pharmacy:pack_order_detail', order_id=pack_order.id)
    else:
        initial_data = {}
        if pack:
            initial_data['pack'] = pack
        if patient:
            initial_data['patient'] = patient
            
        form = PackOrderForm(
            initial=initial_data,
            preselected_patient=patient,
            surgery=surgery,
            labor_record=labor_record
        )
    
    context = {
        'form': form,
        'pack': pack,
        'surgery': surgery,
        'labor_record': labor_record,
        'patient': patient,
        'page_title': 'Create Pack Order',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/pack_orders/pack_order_form.html', context)


@login_required
def pack_order_list(request):
    """View for listing pack orders"""
    from .forms import PackOrderFilterForm
    
    form = PackOrderFilterForm(request.GET)

    try:
        orders = PackOrder.objects.select_related('pack', 'patient', 'ordered_by', 'processed_by').order_by('-ordered_at')
    except Exception as e:
        messages.error(request, f'Error loading pack orders: {str(e)}')
        orders = PackOrder.objects.none()
    
    # Apply filters
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            orders = orders.filter(
                Q(pack__name__icontains=search) |
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__patient_id__icontains=search)
            )
        
        if form.cleaned_data.get('status'):
            orders = orders.filter(status=form.cleaned_data['status'])
        
        if form.cleaned_data.get('pack_type'):
            orders = orders.filter(pack__pack_type=form.cleaned_data['pack_type'])
        
        if form.cleaned_data.get('date_from'):
            orders = orders.filter(order_date__date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            orders = orders.filter(order_date__date__lte=form.cleaned_data['date_to'])
    
    # Pagination
    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'page_title': 'Pack Orders',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/pack_orders/pack_order_list.html', context)


@login_required
def pack_order_detail(request, order_id):
    """View for displaying pack order details"""
    pack_order = get_object_or_404(
        PackOrder.objects.select_related('pack', 'patient', 'ordered_by', 'processed_by'),
        id=order_id
    )
    
    context = {
        'pack_order': pack_order,
        'page_title': f'Pack Order #{pack_order.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/pack_orders/pack_order_detail.html', context)


@login_required
def approve_pack_order(request, order_id):
    """View for approving a pack order"""
    pack_order = get_object_or_404(PackOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            # Get approval notes from form
            approval_notes = request.POST.get('approval_notes', '').strip()
            
            # Store approval notes in processing_notes field
            if approval_notes:
                existing_notes = pack_order.processing_notes or ''
                approval_note_entry = f"[APPROVAL - {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name()}]: {approval_notes}"
                if existing_notes:
                    pack_order.processing_notes = f"{existing_notes}\n\n{approval_note_entry}"
                else:
                    pack_order.processing_notes = approval_note_entry
                pack_order.save()
            
            # Approve the order
            pack_order.approve_order(request.user)
            
            messages.success(request, f'Pack order #{pack_order.id} approved successfully.')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('pharmacy:pack_order_detail', order_id=pack_order.id)
    
    context = {
        'pack_order': pack_order,
        'page_title': f'Approve Pack Order #{pack_order.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/pack_orders/approve_pack_order.html', context)


@login_required
def process_pack_order(request, order_id):
    """View for processing a pack order (converting to prescription)"""
    pack_order = get_object_or_404(PackOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            prescription = pack_order.process_order(request.user)
            messages.success(
                request,
                f'Pack order #{pack_order.id} processed successfully. Prescription #{prescription.id} created.'
            )
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('pharmacy:pack_order_detail', order_id=pack_order.id)
    
    context = {
        'pack_order': pack_order,
        'page_title': f'Process Pack Order #{pack_order.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/pack_orders/process_pack_order.html', context)


@login_required
def pharmacy_payment_receipt(request, payment_id):
    """
    Generate and display printable payment receipt for pharmacy payments.
    Works with both pharmacy_billing.Payment and billing.Payment models.
    """
    from pharmacy_billing.models import Payment as PharmacyPayment, Invoice as PharmacyInvoice
    from billing.models import Payment as BillingPayment
    from django.utils import timezone

    # Try to get payment from pharmacy_billing first
    payment = None
    invoice = None
    is_pharmacy_billing = False

    try:
        payment = PharmacyPayment.objects.select_related(
            'invoice', 'invoice__prescription', 'invoice__patient', 'received_by'
        ).get(id=payment_id)
        invoice = payment.invoice
        is_pharmacy_billing = True
    except PharmacyPayment.DoesNotExist:
        # Try billing.Payment
        try:
            payment = BillingPayment.objects.select_related(
                'invoice', 'invoice__patient', 'received_by'
            ).get(id=payment_id)
            invoice = payment.invoice
        except BillingPayment.DoesNotExist:
            messages.error(request, 'Payment not found.')
            return redirect('pharmacy:dashboard')

    # Get prescription if available
    prescription = None
    if hasattr(invoice, 'prescription') and invoice.prescription:
        prescription = invoice.prescription
    elif hasattr(invoice, 'prescription_invoice'):
        prescription = invoice.prescription_invoice

    # Build items list for receipt
    items = []
    if prescription:
        for item in prescription.items.all():
            medication = item.medication
            quantity = item.quantity
            unit_price = medication.price

            # Calculate based on NHIA status
            if prescription.patient.is_nhia_patient():
                # NHIA patients pay 10%
                unit_price = unit_price * Decimal('0.10')

            items.append({
                'description': f'{medication.name} ({medication.strength})',
                'quantity': quantity,
                'unit_price': unit_price,
                'total': unit_price * quantity
            })

    # Prepare context
    context = {
        'payment': payment,
        'invoice': invoice,
        'patient': invoice.patient if invoice else None,
        'prescription': prescription,
        'items': items,
        'service_type': 'Pharmacy - Medication Dispensing',
        'service_description': f'Prescription #{prescription.id}' if prescription else 'Medication Payment',
        'receipt_number': f'PH-{payment.id}',
        'hospital_name': 'Hospital Management System',
        'hospital_address': '123 Medical Center Drive, City, State',
        'hospital_phone': '(123) 456-7890',
        'hospital_email': 'info@hospital.com',
        'now': timezone.now(),
    }

    return render(request, 'payments/payment_receipt.html', context)


@login_required
def laboratory_payment_receipt(request, payment_id):
    """Generate and display printable payment receipt for laboratory payments."""
    from billing.models import Payment
    from laboratory.models import TestRequest
    from django.utils import timezone

    payment = get_object_or_404(
        Payment.objects.select_related('invoice', 'invoice__patient', 'received_by'),
        id=payment_id
    )
    invoice = payment.invoice

    # Get test request
    test_request = None
    try:
        test_request = TestRequest.objects.get(invoice=invoice)
    except TestRequest.DoesNotExist:
        pass

    # Build items list
    items = []
    if test_request:
        for test in test_request.tests.all():
            items.append({
                'description': test.name,
                'quantity': 1,
                'unit_price': test.price,
                'total': test.price
            })

    context = {
        'payment': payment,
        'invoice': invoice,
        'patient': invoice.patient,
        'test_request': test_request,
        'items': items,
        'service_type': 'Laboratory Services',
        'service_description': f'Test Request #{test_request.id}' if test_request else 'Laboratory Tests',
        'receipt_number': f'LAB-{payment.id}',
        'hospital_name': 'Hospital Management System',
        'hospital_address': '123 Medical Center Drive, City, State',
        'hospital_phone': '(123) 456-7890',
        'hospital_email': 'info@hospital.com',
        'now': timezone.now(),
    }

    return render(request, 'payments/payment_receipt.html', context)


@login_required
def consultation_payment_receipt(request, payment_id):
    """Generate and display printable payment receipt for consultation payments."""
    from billing.models import Payment
    from consultations.models import Consultation
    from django.utils import timezone

    payment = get_object_or_404(
        Payment.objects.select_related('invoice', 'invoice__patient', 'received_by'),
        id=payment_id
    )
    invoice = payment.invoice

    # Get consultation
    consultation = None
    try:
        # Try to find consultation by invoice
        consultation = Consultation.objects.filter(patient=invoice.patient).first()
    except:
        pass

    # Build items list
    items = [{
        'description': f'Consultation with Dr. {consultation.doctor.get_full_name()}' if consultation else 'Medical Consultation',
        'quantity': 1,
        'unit_price': payment.amount,
        'total': payment.amount
    }]

    context = {
        'payment': payment,
        'invoice': invoice,
        'patient': invoice.patient,
        'consultation': consultation,
        'items': items,
        'service_type': 'Consultation Services',
        'service_description': f'Consultation with Dr. {consultation.doctor.get_full_name()}' if consultation else 'Medical Consultation',
        'receipt_number': f'CONS-{payment.id}',
        'hospital_name': 'Hospital Management System',
        'hospital_address': '123 Medical Center Drive, City, State',
        'hospital_phone': '(123) 456-7890',
        'hospital_email': 'info@hospital.com',
        'now': timezone.now(),
    }

    return render(request, 'payments/payment_receipt.html', context)


@login_required
def admission_payment_receipt(request, payment_id):
    """Generate and display printable payment receipt for admission payments."""
    from billing.models import Payment
    from inpatient.models import Admission
    from django.utils import timezone

    payment = get_object_or_404(
        Payment.objects.select_related('invoice', 'invoice__patient', 'received_by'),
        id=payment_id
    )
    invoice = payment.invoice

    # Get admission
    admission = None
    try:
        admission = Admission.objects.filter(patient=invoice.patient).first()
    except:
        pass

    # Build items list
    items = [{
        'description': f'Admission Fee - Ward: {admission.ward.name}' if admission and admission.ward else 'Admission Fee',
        'quantity': 1,
        'unit_price': payment.amount,
        'total': payment.amount
    }]

    context = {
        'payment': payment,
        'invoice': invoice,
        'patient': invoice.patient,
        'admission': admission,
        'items': items,
        'service_type': 'Admission Services',
        'service_description': f'Admission to {admission.ward.name}' if admission and admission.ward else 'Hospital Admission',
        'receipt_number': f'ADM-{payment.id}',
        'hospital_name': 'Hospital Management System',
        'hospital_address': '123 Medical Center Drive, City, State',
        'hospital_phone': '(123) 456-7890',
        'hospital_email': 'info@hospital.com',
        'now': timezone.now(),
    }

    return render(request, 'payments/payment_receipt.html', context)


@login_required
def dispense_pack_order(request, order_id):
    """View for marking a pack order as dispensed"""
    pack_order = get_object_or_404(PackOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            pack_order.dispense_order(request.user)
            messages.success(request, f'Pack order #{pack_order.id} marked as dispensed.')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('pharmacy:pack_order_detail', order_id=pack_order.id)
    
    context = {
        'pack_order': pack_order,
        'page_title': f'Dispense Pack Order #{pack_order.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/pack_orders/dispense_pack_order.html', context)


def _add_pack_to_patient_billing(patient, pack_order, source_context='pharmacy'):
    """Helper function to add pack costs to patient billing"""
    
    # Create or get invoice for patient
    invoice, created = Invoice.objects.get_or_create(
        patient=patient,
        status='pending',
        source_app='pharmacy',  # Using pharmacy as the source for pack orders
        defaults={
            'invoice_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=7),
            'subtotal': Decimal('0.00'),
            'tax_amount': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'created_by': pack_order.ordered_by,
        }
    )
    
    # Create or get medical pack service category
    pack_service_category, _ = ServiceCategory.objects.get_or_create(
        name="Medical Packs",
        defaults={'description': 'Pre-packaged medical supplies and medications'}
    )
    
    # Create or get service for this specific pack
    service, _ = Service.objects.get_or_create(
        name=f"Medical Pack: {pack_order.pack.name}",
        category=pack_service_category,
        defaults={
            'price': pack_order.pack.get_total_cost(),
            'description': f"Medical pack for {pack_order.pack.get_pack_type_display()}: {pack_order.pack.name}",
            'tax_percentage': Decimal('0.00')  # Assuming no tax on medical packs
        }
    )
    
    # Add invoice item for the pack
    pack_cost = pack_order.pack.get_total_cost()
    invoice_item = InvoiceItem.objects.create(
        invoice=invoice,
        service=service,
        description=f"Medical Pack: {pack_order.pack.name} (Order #{pack_order.id}) - {source_context.title()}",
        quantity=1,
        unit_price=pack_cost,
        tax_percentage=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        total_amount=pack_cost
    )
    
    # Update invoice totals
    invoice.subtotal = invoice.items.aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0.00')
    invoice.tax_amount = invoice.items.aggregate(
        total=models.Sum('tax_amount')
    )['total'] or Decimal('0.00')
    invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount_amount
    invoice.save()
    
    return invoice_item


@login_required
def create_dispensary_transfer(request):
    """Create a new dispensary transfer"""
    if request.method == 'POST':
        try:
            from pharmacy.models import DispensaryTransfer, Medication, ActiveStore, Dispensary

            medication_id = request.POST.get('medication_id')
            from_store_id = request.POST.get('from_store_id')
            to_dispensary_id = request.POST.get('to_dispensary_id')
            quantity = int(request.POST.get('quantity', 0))
            notes = request.POST.get('notes', '')

            # Validate inputs
            if not all([medication_id, from_store_id, to_dispensary_id, quantity > 0]):
                messages.error(request, 'All fields are required and quantity must be greater than 0')
                return redirect('pharmacy:active_store_list')

            # Get objects
            medication = Medication.objects.get(id=medication_id)
            from_store = ActiveStore.objects.get(id=from_store_id)
            to_dispensary = Dispensary.objects.get(id=to_dispensary_id)

            # Create transfer
            transfer = DispensaryTransfer.create_transfer(
                medication=medication,
                from_active_store=from_store,
                to_dispensary=to_dispensary,
                quantity=quantity,
                requested_by=request.user,
                notes=notes
            )

            messages.success(request, f'Transfer created successfully: {quantity} units of {medication.name}')

            # Execute the transfer immediately for now
            transfer.execute_transfer(request.user)
            messages.success(request, f'Transfer executed: {quantity} units moved from {from_store.name} to {to_dispensary.name}')

            return redirect('pharmacy:active_store_list')

        except Exception as e:
            messages.error(request, f'Error creating transfer: {str(e)}')
            return redirect('pharmacy:active_store_list')

    # This should not be reached as transfers are created via AJAX/POST
    return redirect('pharmacy:active_store_list')


@login_required
def transfer_medication_to_dispensary(request):
    """AJAX endpoint to transfer medication from active store to dispensary"""
    if request.method == 'POST':
        try:
            import json
            from pharmacy.models import DispensaryTransfer, Medication, ActiveStore, Dispensary

            data = json.loads(request.body)
            medication_id = data.get('medication_id')
            from_store_id = data.get('from_store_id')
            to_dispensary_id = data.get('to_dispensary_id')
            quantity = int(data.get('quantity', 0))

            # Validate inputs
            if not all([medication_id, from_store_id, to_dispensary_id, quantity > 0]):
                return JsonResponse({'success': False, 'error': 'Invalid input data'})

            # Get objects
            medication = Medication.objects.get(id=medication_id)
            from_store = ActiveStore.objects.get(id=from_store_id)
            to_dispensary = Dispensary.objects.get(id=to_dispensary_id)

            # Create and execute transfer
            transfer = DispensaryTransfer.create_transfer(
                medication=medication,
                from_active_store=from_store,
                to_dispensary=to_dispensary,
                quantity=quantity,
                requested_by=request.user
            )

            # Execute immediately
            transfer.execute_transfer(request.user)

            return JsonResponse({
                'success': True,
                'message': f'Successfully transferred {quantity} units of {medication.name} from {from_store.name} to {to_dispensary.name}'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})