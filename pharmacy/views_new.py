"""
Views for HMS Pharmacy Module

Handles all pharmacy operations including inventory, dispensing, prescriptions, cart, procurement, and reporting.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal

from .models import (
    Medication, Supplier, Purchase, PurchaseItem, 
    Dispensary, BulkStore, ActiveStoreInventory, MedicationInventory,
    Prescription, PrescriptionItem, DispensingLog,
    Pack, PackItem, MedicalPack
)

from .cart_models import PrescriptionCart, PrescriptionCartItem
from .pharmacy_billing.models import Invoice as PharmacyInvoice
from .pharmacy_billing.utils import create_pharmacy_invoice
from core.audit_utils import log_audit_action

# Basic views that don't require authentication
def features_showcase(request):
    """Showcase of pharmacy features"""
    return render(request, 'pharmacy/features_showcase.html')

@login_required
def pharmacy_dashboard(request):
    """Main pharmacy dashboard"""
    context = {'active_nav': 'pharmacy'}
    return render(request, 'pharmacy/pharmacy_dashboard.html', context)

@login_required
def inventory_list(request):
    """List all medications in inventory"""
    medications = Medication.objects.all().order_by('name')
    return render(request, 'pharmacy/inventory_list.html', {'medications': medications, 'active_nav': 'pharmacy'})

@login_required
def medication_detail(request, medication_id):
    """Show details of a specific medication"""
    medication = get_object_or_404(Medication, id=medication_id)
    return render(request, 'pharmacy/medication_detail.html', {'medication': medication, 'active_nav': 'pharmacy'})

@login_required
def add_medication(request):
    """Add a new medication to inventory"""
    if request.method == 'POST':
        form = MedicationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medication {form.cleaned_data["name"]} added successfully.')
            return redirect('pharmacy:medication_detail', medication_id=form.instance.id)
    else:
        form = MedicationForm()
        return render(request, 'pharmacy/medication_form.html', {'form': form, 'active_nav': 'pharmacy'})

@login_required
def edit_medication(request, medication_id):
    """Edit an existing medication"""
    medication = get_object_or_404(Medication, id=medication_id)
    if request.method == 'POST':
        form = MedicationForm(request.POST, instance=medication)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medication {form.cleaned_data["name"]} updated successfully.')
            return redirect('pharmacy:medication_detail', medication_id=medication.id)
    else:
        form = MedicationForm(instance=medication)
        return render(request, 'pharmacy/medication_form.html', {'form': form, 'active_nav': 'pharmacy'})

@login_required
def delete_medication(request, medication_id):
    """Delete a medication from inventory"""
    medication = get_object_or_404(Medication, id=medication_id)
    if request.method == 'POST':
        medication.delete()
        messages.success(request, f'Medication {medication.name} deleted successfully.')
        return redirect('pharmacy:inventory_list')
    return render(request, 'pharmacy/medication_detail.html', {'medication': medication, 'active_nav': 'pharmacy'})

# Supplier management
@login_required
def manage_suppliers(request):
    """Manage all suppliers"""
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    return render(request, 'pharmacy/manage_suppliers.html', {'suppliers': suppliers, 'active_nav': 'pharmacy'})

@login_required
def supplier_detail(request, supplier_id):
    """Show details of a specific supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    return render(request, 'pharmacy/supplier_detail.html', {'supplier': supplier, 'active_nav': 'pharmacy'})

@login_required
def api_suppliers(request):
    """API endpoint for suppliers"""
    suppliers = Supplier.objects.filter(is_active=True).values('id', 'name')
    return JsonResponse(list(suppliers), safe=False)

@login_required
def create_cart_from_prescription(request, prescription_id):
    """Create a new cart from prescription.
    Adds all prescription items to cart with prescribed quantities.
    """
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check if prescription can be dispensed
    can_dispense, message = prescription.can_be_dispensed()
    if not can_dispense:
        # Enhanced message styling for dispensed prescriptions
        if prescription.status == 'dispensed':
            messages.success(request, f'✅ {message} - This prescription has already been fully dispensed.', extra_tags='dispensed-status')
        elif prescription.status == 'cancelled':
            messages.warning(request, f'⚠️ {message}', extra_tags='cancelled-status')
        else:
            messages.error(request, f'❌ {message}', extra_tags='error-status')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # Check if there's already an active cart for this prescription
    existing_cart = PrescriptionCart.objects.filter(
        prescription=prescription,
        status='active'
    ).first()
    
    if existing_cart:
        messages.info(request, 'Active cart already exists for this prescription.')
        return redirect('pharmacy:view_cart', cart_id=existing_cart.id)
    
    try:
        with transaction.atomic():
            # Create new cart
            cart = PrescriptionCart.objects.create(
                prescription=prescription,
                created_by=request.user
            )
            
            # Add all prescription items to cart
            items_added = 0
            for p_item in prescription.items.filter(is_dispensed=False):
                remaining_qty = p_item.remaining_quantity_to_dispense
                if remaining_qty > 0:
                    PrescriptionCartItem.objects.create(
                        cart=cart,
                        prescription_item=p_item,
                        quantity=remaining_qty,
                        unit_price=p_item.medication.price or Decimal('0.00')
                    )
                    items_added += 1
            
            if items_added == 0:
                cart.delete()
                messages.warning(request, 'No items to add to cart. All items may be already dispensed.')
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            
            # Log audit action
            log_audit_action(
                request.user,
                'create',
                cart,
                f'Created prescription cart with {items_added} items'
            )
            
            messages.success(request, f'Cart created with {items_added} items.')
            return redirect('pharmacy:view_cart', cart_id=cart.id)
    
    except Exception as e:
        messages.error(request, f'Error creating cart: {str(e)}')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

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
def api_suppliers(request):
    """API endpoint for suppliers"""
    suppliers = Supplier.objects.filter(is_active=True).values('id', 'name')
    return JsonResponse(list(suppliers), safe=False)

# Category management
@login_required
def manage_categories(request):
    """Manage all medication categories"""
    categories = MedicationCategory.objects.all().order_by('name')
    return render(request, 'pharmacy/manage_categories.html', {'categories': categories, 'active_nav': 'pharmacy'})

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
        return render(request, 'pharmacy/add_edit_category.html', {'form': form, 'category': category, 'active_nav': 'pharmacy'})

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
        'title': f'Delete Category - {category.name}'
    }
    
    return render(request, 'pharmacy/confirm_delete_category.html', context)

# Remaining views from original file...
