from django.shortcuts import render, get_object_or_404, redirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.db import models
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import (
    Medication, MedicationCategory, Supplier, Purchase, PurchaseItem,
    Prescription, PrescriptionItem, Dispensary, ActiveStore, ActiveStoreInventory, MedicationInventory,
    BulkStore, BulkStoreInventory, MedicationTransfer, DispensingLog,
    MedicalPack, PackItem, PackOrder
)
from .forms import (
    MedicationForm, MedicationCategoryForm, SupplierForm, PurchaseForm, PurchaseItemForm,
    PrescriptionForm, PrescriptionItemForm, DispensaryForm,
    MedicationInventoryForm, ActiveStoreInventoryForm
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
    
    # Pagination
    paginator = Paginator(medications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = MedicationCategory.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
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
    }
    
    return render(request, 'pharmacy/add_medication.html', context)


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
    }
    
    return render(request, 'pharmacy/edit_medication.html', context)


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
        'page_title': 'Manage Categories',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/manage_categories.html', context)


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
    }
    
    return render(request, 'pharmacy/edit_category.html', context)


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
    }
    
    return render(request, 'pharmacy/delete_category.html', context)


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
    """View for quick procurement from a supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
    # Implementation for quick procurement
    pass


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
    pass


@login_required
def automated_reorder_suggestions(request):
    """View for automated reorder suggestions"""
    # Implementation for automated reorder suggestions
    pass


@login_required
def revenue_analysis(request):
    """View for revenue analysis"""
    # Implementation for revenue analysis
    pass


@login_required
def comprehensive_revenue_analysis(request):
    """Enhanced view for comprehensive revenue analysis across all hospital departments"""
    from .revenue_service import RevenueAggregationService, MonthFilterHelper
    from .forms import ComprehensiveRevenueFilterForm
    import csv
    import json
    from django.http import HttpResponse
    
    # Initialize form with request data
    filter_form = ComprehensiveRevenueFilterForm(request.GET or None)
    
    # Get date range based on form input or default to current month
    if filter_form.is_valid():
        start_date, end_date = filter_form.get_date_range()
        selected_departments = filter_form.cleaned_data.get('departments', [])
        include_daily_breakdown = filter_form.cleaned_data.get('include_daily_breakdown', False)
    else:
        # Default to current month
        start_date, end_date = MonthFilterHelper.get_current_month()
        selected_departments = []
        include_daily_breakdown = False
    
    # Initialize revenue aggregation service
    revenue_service = RevenueAggregationService(start_date, end_date)
    
    # Get comprehensive revenue data
    comprehensive_data = revenue_service.get_comprehensive_revenue()
    
    # Handle CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="revenue_analysis_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        
        # Write header information
        writer.writerow(['Hospital Revenue Analysis Report'])
        writer.writerow(['Period:', f'{start_date} to {end_date}'])
        writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])  # Empty row
        
        # Write summary data
        writer.writerow(['Department', 'Revenue (₦)', 'Transactions', 'Percentage of Total'])
        total_revenue = comprehensive_data['total_revenue']
        
        for dept_key, dept_name in [
            ('pharmacy_revenue', 'Pharmacy'),
            ('laboratory_revenue', 'Laboratory'),
            ('consultation_revenue', 'Consultations'),
            ('theatre_revenue', 'Theatre'),
            ('admission_revenue', 'Admissions'),
            ('general_revenue', 'General & Others'),
            ('wallet_revenue', 'Wallet Transactions')
        ]:
            dept_data = comprehensive_data[dept_key]
            revenue = dept_data['total_revenue']
            transactions = dept_data.get('total_payments', dept_data.get('total_transactions', 0))
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            writer.writerow([
                dept_name,
                f'{revenue:.2f}',
                transactions,
                f'{percentage:.1f}%'
            ])
        
        writer.writerow(['Total', f'{total_revenue:.2f}', '', '100%'])
        
        # Add monthly trends if available
        monthly_trends = revenue_service.get_monthly_trends(12)
        if monthly_trends:
            writer.writerow([])  # Empty row
            writer.writerow(['Monthly Trends (Last 12 Months)'])
            writer.writerow(['Month', 'Pharmacy', 'Laboratory', 'Consultations', 'Theatre', 'Admissions', 'General', 'Wallet', 'Total'])
            
            for trend in monthly_trends:
                writer.writerow([
                    trend['month'],
                    f"{trend['pharmacy']:.2f}",
                    f"{trend['laboratory']:.2f}",
                    f"{trend['consultations']:.2f}",
                    f"{trend['theatre']:.2f}",
                    f"{trend['admissions']:.2f}",
                    f"{trend['general']:.2f}",
                    f"{trend['wallet']:.2f}",
                    f"{trend['total_revenue']:.2f}"
                ])
        
        # Add daily breakdown if requested
        if include_daily_breakdown:
            daily_breakdown = revenue_service.get_daily_breakdown()
            if daily_breakdown:
                writer.writerow([])  # Empty row
                writer.writerow(['Daily Breakdown'])
                writer.writerow(['Date', 'Pharmacy', 'Laboratory', 'Consultations', 'Theatre', 'Admissions', 'General', 'Wallet', 'Total'])
                
                for day in daily_breakdown:
                    writer.writerow([
                        day['date_str'],
                        f"{day['pharmacy']:.2f}",
                        f"{day['laboratory']:.2f}",
                        f"{day['consultations']:.2f}",
                        f"{day['theatre']:.2f}",
                        f"{day['admissions']:.2f}",
                        f"{day['general']:.2f}",
                        f"{day['wallet']:.2f}",
                        f"{day['total_revenue']:.2f}"
                    ])
        
        return response
    
    # Get monthly trends (last 12 months)
    monthly_trends = revenue_service.get_monthly_trends(12)
    
    # Get daily breakdown if requested and date range is reasonable (max 90 days)
    daily_breakdown = []
    if include_daily_breakdown:
        date_diff = (end_date - start_date).days
        if date_diff <= 90:  # Only include daily breakdown for up to 90 days
            daily_breakdown = revenue_service.get_daily_breakdown()
    
    # Filter departments if specific ones are selected
    if selected_departments:
        # Filter out unselected departments from display
        filtered_data = {}
        for dept in selected_departments:
            if dept == 'pharmacy':
                filtered_data['pharmacy_revenue'] = comprehensive_data['pharmacy_revenue']
            elif dept == 'laboratory':
                filtered_data['laboratory_revenue'] = comprehensive_data['laboratory_revenue']
            elif dept == 'consultations':
                filtered_data['consultation_revenue'] = comprehensive_data['consultation_revenue']
            elif dept == 'theatre':
                filtered_data['theatre_revenue'] = comprehensive_data['theatre_revenue']
            elif dept == 'admissions':
                filtered_data['admission_revenue'] = comprehensive_data['admission_revenue']
            elif dept == 'general':
                filtered_data['general_revenue'] = comprehensive_data['general_revenue']
            elif dept == 'wallet':
                filtered_data['wallet_revenue'] = comprehensive_data['wallet_revenue']
        
        # Recalculate total revenue for filtered departments
        filtered_total = sum(data['total_revenue'] for data in filtered_data.values())
        comprehensive_data.update(filtered_data)
        comprehensive_data['total_revenue'] = filtered_total
    
    # Calculate revenue distribution percentages
    total_revenue = comprehensive_data['total_revenue']
    if total_revenue > 0:
        for dept_key in ['pharmacy_revenue', 'laboratory_revenue', 'consultation_revenue', 
                        'theatre_revenue', 'admission_revenue', 'general_revenue', 'wallet_revenue']:
            if dept_key in comprehensive_data:
                dept_revenue = comprehensive_data[dept_key]['total_revenue']
                comprehensive_data[dept_key]['percentage'] = (dept_revenue / total_revenue) * 100
    
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
        'filter_form': filter_form,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'comprehensive_data': comprehensive_data,
        'monthly_trends': monthly_trends,
        'daily_breakdown': daily_breakdown,
        'chart_data': chart_data,
        'revenue_sources': revenue_sources,
        'performance_metrics': performance_metrics,
        'include_daily_breakdown': include_daily_breakdown,
        'selected_departments': selected_departments,
        'page_title': 'Comprehensive Revenue Analysis',
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
    
    return render(request, 'pharmacy/comprehensive_revenue_analysis.html', context)


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
    
    return render(request, 'pharmacy/comprehensive_revenue_analysis.html', context)


@login_required
def comprehensive_revenue_analysis_debug(request):
    """Debug view for comprehensive revenue analysis to check data flow"""
    from .revenue_service import RevenueAggregationService, MonthFilterHelper
    from .forms import ComprehensiveRevenueFilterForm
    
    # Initialize form with request data
    filter_form = ComprehensiveRevenueFilterForm(request.GET or None)
    
    # Get date range based on form input or default to current month
    if filter_form.is_valid():
        start_date, end_date = filter_form.get_date_range()
        selected_departments = filter_form.cleaned_data.get('departments', [])
        include_daily_breakdown = filter_form.cleaned_data.get('include_daily_breakdown', False)
    else:
        # Default to current month
        start_date, end_date = MonthFilterHelper.get_current_month()
        selected_departments = []
        include_daily_breakdown = False
    
    # Initialize revenue aggregation service
    revenue_service = RevenueAggregationService(start_date, end_date)
    
    # Get comprehensive revenue data
    comprehensive_data = revenue_service.get_comprehensive_revenue()
    
    # Get monthly trends (last 12 months)
    monthly_trends = revenue_service.get_monthly_trends(12)
    
    # Prepare chart data for monthly trends
    chart_months = [trend['month'] for trend in monthly_trends]
    chart_data = {
        'months': chart_months,
        'pharmacy': [float(trend['pharmacy']) for trend in monthly_trends],
        'laboratory': [float(trend['laboratory']) for trend in monthly_trends],
        'consultations': [float(trend['consultations']) for trend in monthly_trends],
        'theatre': [float(trend['theatre']) for trend in monthly_trends],
        'admissions': [float(trend['admissions']) for trend in monthly_trends],
        'general': [float(trend['general']) for trend in monthly_trends],
        'wallet': [float(trend['wallet']) for trend in monthly_trends],
        'total': [float(trend['total_revenue']) for trend in monthly_trends]
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
        'filter_form': filter_form,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'comprehensive_data': comprehensive_data,
        'monthly_trends': monthly_trends,
        'chart_data': chart_data,
        'revenue_sources': revenue_sources,
        'performance_metrics': performance_metrics,
        'include_daily_breakdown': include_daily_breakdown,
        'selected_departments': selected_departments,
        'page_title': 'Revenue Analysis Debug',
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
    
    return render(request, 'pharmacy/revenue_debug.html', context)


@login_required
def expense_analysis(request):
    """View for expense analysis"""
    # Implementation for expense analysis
    pass


@login_required
def create_procurement_request(request, medication_id):
    """View for creating a procurement request"""
    medication = get_object_or_404(Medication, id=medication_id)
    # Implementation for creating procurement request
    pass


@login_required
def api_suppliers(request):
    """API endpoint for suppliers"""
    # Implementation for API suppliers
    pass


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
def request_medication_transfer(request):
    """View for requesting medication transfer"""
    # Implementation for requesting medication transfer
    pass


@login_required
def approve_medication_transfer(request, transfer_id):
    """View for approving medication transfer"""
    transfer = get_object_or_404(MedicationTransfer, id=transfer_id)
    # Implementation for approving medication transfer
    pass


@login_required
def execute_medication_transfer(request, transfer_id):
    """View for executing medication transfer"""
    transfer = get_object_or_404(MedicationTransfer, id=transfer_id)
    # Implementation for executing medication transfer
    pass


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
    """View for listing prescriptions"""
    # Get all prescriptions
    prescriptions = Prescription.objects.select_related('patient', 'doctor').order_by('-prescription_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        prescriptions = prescriptions.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(doctor__first_name__icontains=search_query) |
            Q(doctor__last_name__icontains=search_query) |
            Q(diagnosis__icontains=search_query)
        )
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        prescriptions = prescriptions.filter(status=status)
    
    # Pagination
    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status': status,
        'page_title': 'Prescription List',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/prescription_list.html', context)


@login_required
def patient_prescriptions(request, patient_id):
    """View for listing prescriptions for a patient"""
    # Implementation for patient prescriptions
    pass


@login_required
def create_prescription(request, patient_id=None):
    """View for creating a prescription"""
    # Implementation for creating prescription
    pass


@login_required
def pharmacy_create_prescription(request, patient_id=None):
    """View for pharmacy creating a prescription"""
    # Implementation for pharmacy creating prescription
    pass


@login_required
def prescription_detail(request, prescription_id):
    """View for displaying prescription details"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get prescription items
    prescription_items = prescription.items.select_related('medication')
    # Provide an empty form for the "Add Medication" modal
    item_form = PrescriptionItemForm()

    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'item_form': item_form,
        'page_title': f'Prescription Details - #{prescription.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/prescription_detail.html', context)


@login_required
def print_prescription(request, prescription_id):
    """View for printing a prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Implementation for printing prescription
    pass


@login_required
def update_prescription_status(request, prescription_id):
    """View for updating prescription status"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Implementation for updating prescription status
    pass


@login_required
def dispense_prescription(request, prescription_id):
    """View for dispensing a prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Prepare prescription items for dispensing
    prescription_items = list(prescription.items.select_related('medication'))

    # Build a formset class that uses our BaseDispenseItemFormSet
    DispenseFormSet = formset_factory(DispenseItemForm, formset=BaseDispenseItemFormSet, extra=0)

    # Selected dispensary handling (optional pre-selection)
    selected_dispensary = None
    if request.method == 'POST':
        dispensary_id = request.POST.get('dispensary_select') or request.POST.get('selected_dispensary')
        if dispensary_id:
            try:
                selected_dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
            except Dispensary.DoesNotExist:
                selected_dispensary = None

        # Prepare POST data copy so we can inject the selected dispensary into each form
        post_data = request.POST.copy()
        if selected_dispensary:
            # Inject a hidden dispensary value for each form so bound forms receive it
            for i in range(len(prescription_items)):
                post_data[f'form-{i}-dispensary'] = str(selected_dispensary.id)

        # Instantiate formset with modified POST data and bind prescription items
        formset = DispenseFormSet(post_data, prefix='form', prescription_items_qs=prescription_items, form_kwargs={'selected_dispensary': selected_dispensary})

        # If user attempted to dispense items but didn't pick a dispensary, show a clear message
        any_checked = any(request.POST.get(f'form-{i}-dispense_this_item') in ['on', 'True', 'true', '1'] for i in range(len(prescription_items)))
        if not selected_dispensary and any_checked:
            messages.error(request, 'Please select a dispensary before dispensing items.')
            context = {
                'prescription': prescription,
                'page_title': f'Dispense Prescription - #{prescription.id}',
                'dispensaries': Dispensary.objects.filter(is_active=True),
                'formset': formset,
                'selected_dispensary': selected_dispensary,
            }
            return render(request, 'pharmacy/dispense_prescription.html', context)

        if formset.is_valid():
            # Process each selected form
            any_dispensed = False
            skipped_items = []
            for form in formset:
                if not form.cleaned_data:
                    continue
                dispense = form.cleaned_data.get('dispense_this_item')
                qty = form.cleaned_data.get('quantity_to_dispense') or 0
                dispensary = form.cleaned_data.get('dispensary') or selected_dispensary
                if dispense and qty > 0 and dispensary:
                    prescription_item = form.prescription_item
                    medication = prescription_item.medication

                    # Prevent redispensing items that are already fully dispensed
                    if prescription_item.is_dispensed or prescription_item.remaining_quantity_to_dispense <= 0:
                        # Collect for a single warning later
                        skipped_items.append(prescription_item)
                        continue

                    # Get or create inventory record at dispensary
                    try:
                        med_inventory = MedicationInventory.objects.get(medication=medication, dispensary=dispensary)
                    except MedicationInventory.DoesNotExist:
                        messages.error(request, f'No inventory record for {medication.name} at {dispensary.name}.')
                        return redirect('pharmacy:dispense_prescription', prescription_id=prescription.id)

                    # Ensure enough stock
                    if med_inventory.stock_quantity < qty:
                        messages.error(request, f'Not enough stock for {medication.name} at {dispensary.name}.')
                        return redirect('pharmacy:dispense_prescription', prescription_id=prescription.id)

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

                    # Update inventory
                    med_inventory.stock_quantity -= qty
                    med_inventory.save()

                    # Update prescription item quantities
                    prescription_item.quantity_dispensed_so_far += qty
                    if prescription_item.quantity_dispensed_so_far >= prescription_item.quantity:
                        prescription_item.is_dispensed = True
                        prescription_item.dispensed_date = timezone.now()
                        prescription_item.dispensed_by = request.user
                    prescription_item.save()

                    any_dispensed = True

            if any_dispensed:
                # Optionally mark prescription as dispensed if all items are dispensed
                remaining = prescription.items.filter(is_dispensed=False).count()
                if remaining == 0:
                    prescription.status = 'dispensed'
                    prescription.save(update_fields=['status'])
                messages.success(request, 'Selected medications dispensed successfully.')
                if skipped_items:
                    names = ', '.join([s.medication.name for s in skipped_items])
                    messages.warning(request, f'Some items were skipped because they are already fully dispensed: {names}')
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
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

    else:
        # GET request - build empty formset with initial data bound to prescription items
        initial_data = []
        for p_item in prescription_items:
            initial_data.append({
                'item_id': p_item.id,
                'dispense_this_item': False,
                'quantity_to_dispense': 0,
                'dispensary': None,
                'stock_quantity_display': ''
            })

        formset = DispenseFormSet(initial=initial_data, prefix='form', prescription_items_qs=prescription_items)

    context = {
        'prescription': prescription,
        'page_title': f'Dispense Prescription - #{prescription.id}',
        'dispensaries': Dispensary.objects.filter(is_active=True),
        'formset': formset,
        'selected_dispensary': selected_dispensary,
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
    # Implementation for debugging prescription dispensing
    pass


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
    # Implementation for deleting prescription item
    pass


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
                    amount = form.cleaned_data['amount']
                    payment_method = form.cleaned_data['payment_method']
                    payment_source = form.cleaned_data['payment_source']
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
                        # Create wallet transaction for negative balance support
                        from patients.models import WalletTransaction
                        WalletTransaction.objects.create(
                            wallet=patient_wallet,
                            transaction_type='pharmacy_payment',
                            amount=-amount,  # Negative for deduction
                            description=f'Payment for prescription #{prescription.id}',
                            created_by=request.user
                        )
                        # Update wallet balance
                        patient_wallet.balance -= amount
                        patient_wallet.save()
                    
                    # Update invoice
                    pharmacy_invoice.amount_paid += amount
                    if pharmacy_invoice.amount_paid >= pharmacy_invoice.total_amount:
                        pharmacy_invoice.status = 'paid'
                        prescription.payment_status = 'paid'
                        prescription.save(update_fields=['payment_status'])
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
                    
                    messages.success(request, f'Payment of ₦{amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')
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
    
    context = {
        'form': form,
        'prescription': prescription,
        'pharmacy_invoice': pharmacy_invoice,
        'invoice': pharmacy_invoice,  # Template expects 'invoice'
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'title': f'Prescription Payment - #{prescription.id}'
    }
    
    return render(request, 'pharmacy/prescription_payment.html', context)


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
                    # Create wallet transaction for negative balance support
                    from patients.models import WalletTransaction
                    WalletTransaction.objects.create(
                        wallet=patient_wallet,
                        transaction_type='pharmacy_payment',
                        amount=-amount,  # Negative for deduction
                        description=f'Payment for prescription #{prescription.id} (Billing office)',
                        created_by=request.user
                    )
                    # Update wallet balance
                    patient_wallet.balance -= amount
                    patient_wallet.save()
                
                # Update invoice
                pharmacy_invoice.amount_paid += amount
                if pharmacy_invoice.amount_paid >= pharmacy_invoice.total_amount:
                    pharmacy_invoice.status = 'paid'
                    # Mark that this is a manual payment processed by billing staff
                    pharmacy_invoice._manual_payment_processed = True
                    prescription.payment_status = 'paid'
                    prescription.save(update_fields=['payment_status'])
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
                
                messages.success(request, f'Payment of ₦{amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                
        except (ValueError, TypeError):
            messages.error(request, 'Invalid payment amount.')
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
    
    # Get payment history
    payments = pharmacy_invoice.payments.all().order_by('-payment_date')
    
    context = {
        'prescription': prescription,
        'pharmacy_invoice': pharmacy_invoice,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'payments': payments,
        'title': f'Billing Office - Medication Payment #{prescription.id}'
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
def medication_api(request):
    """API endpoint for medications"""
    # Implementation for medication API
    pass


@login_required
def expiring_medications_report(request):
    """View for expiring medications report"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Get medications expiring within 30 days
    expiring_soon = ActiveStoreInventory.objects.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30),
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
    """View for editing a dispensary"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    
    if request.method == 'POST':
        form = DispensaryForm(request.POST, instance=dispensary)
        if form.is_valid():
            dispensary = form.save()
            messages.success(request, f'Dispensary {dispensary.name} updated successfully.')
            return redirect('pharmacy:dispensary_list')
    else:
        form = DispensaryForm(instance=dispensary)
    
    context = {
        'form': form,
        'dispensary': dispensary,
        'page_title': f'Edit Dispensary - {dispensary.name}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/edit_dispensary.html', context)


@login_required
def add_dispensary(request):
    """View for adding a new dispensary"""
    if request.method == 'POST':
        form = DispensaryForm(request.POST)
        if form.is_valid():
            dispensary = form.save()
            messages.success(request, f'Dispensary {dispensary.name} created successfully.')
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
            'last_restock_date': item.last_restock_date,
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
def active_store_detail(request, dispensary_id):
    """View for active store detail"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    active_store = getattr(dispensary, 'active_store', None)
    if not active_store:
        messages.error(request, "No active store found for this dispensary.")
        return redirect('pharmacy:dispensary_list')

    context = {
        'active_store': active_store,
        'dispensary': dispensary,
        'title': f"Active Store - {active_store.name}",
        'active_nav': 'pharmacy',
    }
    return render(request, 'pharmacy/active_store_detail.html', context)


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
    """API endpoint for getting stock quantities"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    dispensary_id = request.GET.get('dispensary_id') or request.POST.get('dispensary_id')
    response = {
        'success': False,
        'items': [],
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
    items = []
    for p_item in prescription.items.select_related('medication'):
        try:
            med_inv = MedicationInventory.objects.get(medication=p_item.medication, dispensary=dispensary)
            stock_qty = med_inv.stock_quantity
        except MedicationInventory.DoesNotExist:
            stock_qty = 0

        items.append({
            'prescription_item_id': p_item.id,
            'medication_id': p_item.medication.id,
            'medication_name': p_item.medication.name,
            'prescribed_quantity': p_item.quantity,
            'quantity_dispensed_so_far': p_item.quantity_dispensed_so_far,
            'remaining_to_dispense': p_item.remaining_quantity_to_dispense,
            'stock_quantity': stock_qty,
        })

    response['success'] = True
    response['items'] = items
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
    
    # Get medications expiring within 30 days
    from datetime import timedelta
    near_expiry_items = ActiveStoreInventory.objects.filter(
        expiry_date__gt=timezone.now().date(),
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
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
    packs = MedicalPack.objects.select_related().prefetch_related('items__medication')
    
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
    orders = PackOrder.objects.select_related('pack', 'patient', 'ordered_by', 'processed_by').order_by('-order_date')
    
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
        PackOrder.objects.select_related('pack', 'patient', 'ordered_by', 'processed_by', 'prescription'),
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