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
    Prescription, PrescriptionItem, Dispensary, ActiveStore, ActiveStoreInventory,
    BulkStore, BulkStoreInventory, MedicationTransfer, DispensingLog
)
from .forms import (
    MedicationForm, MedicationCategoryForm, SupplierForm, PurchaseForm, PurchaseItemForm,
    PrescriptionForm, PrescriptionItemForm, DispensaryForm
)
from reporting.forms import PharmacySalesReportForm


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
    """View for comprehensive revenue analysis"""
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=30)
    
    # Override with form data if provided
    if request.GET.get('start_date'):
        try:
            start_date = timezone.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if request.GET.get('end_date'):
        try:
            end_date = timezone.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Ensure start_date is not after end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Get all prescriptions within the date range that have been dispensed
    prescriptions = Prescription.objects.filter(
        prescription_date__range=[start_date, end_date],
        status__in=['dispensed', 'partially_dispensed']
    ).select_related('patient', 'doctor')
    
    # Calculate revenue from dispensed items
    total_revenue = 0
    medication_revenue = {}
    doctor_revenue = {}
    daily_revenue = {}
    
    # Initialize daily revenue for each day in the range
    current_date = start_date
    while current_date <= end_date:
        daily_revenue[current_date] = 0
        current_date += timezone.timedelta(days=1)
    
    for prescription in prescriptions:
        # Get all dispensing logs for this prescription
        dispensing_logs = DispensingLog.objects.filter(
            prescription_item__prescription=prescription,
            dispensed_date__date__range=[start_date, end_date]
        ).select_related('prescription_item__medication', 'dispensed_by')
        
        for log in dispensing_logs:
            # Add to total revenue
            total_revenue += float(log.total_price_for_this_log)
            
            # Add to medication revenue
            medication_name = log.prescription_item.medication.name
            if medication_name in medication_revenue:
                medication_revenue[medication_name] += float(log.total_price_for_this_log)
            else:
                medication_revenue[medication_name] = float(log.total_price_for_this_log)
            
            # Add to doctor revenue
            doctor_name = prescription.doctor.get_full_name() if prescription.doctor else "Unknown"
            if doctor_name in doctor_revenue:
                doctor_revenue[doctor_name] += float(log.total_price_for_this_log)
            else:
                doctor_revenue[doctor_name] = float(log.total_price_for_this_log)
            
            # Add to daily revenue
            log_date = log.dispensed_date.date()
            if log_date in daily_revenue:
                daily_revenue[log_date] += float(log.total_price_for_this_log)
    
    # Sort medication revenue by value (descending)
    medication_revenue_sorted = sorted(medication_revenue.items(), key=lambda x: x[1], reverse=True)
    
    # Sort doctor revenue by value (descending)
    doctor_revenue_sorted = sorted(doctor_revenue.items(), key=lambda x: x[1], reverse=True)
    
    # Convert daily revenue to sorted list for charting
    daily_revenue_sorted = sorted(daily_revenue.items())
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'medication_revenue': medication_revenue_sorted,
        'doctor_revenue': doctor_revenue_sorted,
        'daily_revenue': daily_revenue_sorted,
        'page_title': 'Comprehensive Revenue Analysis',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/comprehensive_revenue_analysis.html', context)


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
            purchase = form.save()
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
    
    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
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
    # You can add more context as needed
    context = {
        'prescription': prescription,
        'page_title': f'Dispense Prescription - #{prescription.id}'
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
    # Implementation for adding prescription item
    pass


@login_required
def delete_prescription_item(request, item_id):
    """View for deleting a prescription item"""
    item = get_object_or_404(PrescriptionItem, id=item_id)
    # Implementation for deleting prescription item
    pass


@login_required
def prescription_payment(request, prescription_id):
    """View for prescription payment"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Implementation for prescription payment
    pass


@login_required
def billing_office_medication_payment(request, prescription_id):
    """View for billing office medication payment"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Implementation for billing office medication payment
    pass


@login_required
def create_prescription_invoice(request, prescription_id):
    """View for creating prescription invoice"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Implementation for creating prescription invoice
    pass


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
    
    # Get inventory items
    inventory_items = ActiveStoreInventory.objects.filter(
        active_store__dispensary=dispensary
    ).select_related('medication', 'active_store')
    
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
    # Implementation for adding dispensary inventory item
    pass


@login_required
def edit_dispensary_inventory_item(request, dispensary_id, inventory_item_id):
    """View for editing a dispensary inventory item"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    inventory_item = get_object_or_404(ActiveStoreInventory, id=inventory_item_id)
    # Implementation for editing dispensary inventory item
    pass


@login_required
def delete_dispensary_inventory_item(request, dispensary_id, inventory_item_id):
    """View for deleting a dispensary inventory item"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    inventory_item = get_object_or_404(ActiveStoreInventory, id=inventory_item_id)
    # Implementation for deleting dispensary inventory item
    pass


@login_required
def active_store_detail(request, dispensary_id):
    """View for active store detail"""
    dispensary = get_object_or_404(Dispensary, id=dispensary_id, is_active=True)
    # Implementation for active store detail
    pass


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
    # Implementation for getting stock quantities
    pass


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