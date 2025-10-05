"""
Prescription Cart Views for HMS Pharmacy Module

Handles cart operations: create, view, update, checkout, and complete dispensing.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from django.utils import timezone

from .cart_models import PrescriptionCart, PrescriptionCartItem
from .models import Prescription, PrescriptionItem, Dispensary, DispensingLog
from .models import ActiveStoreInventory, MedicationInventory
from pharmacy_billing.models import Invoice as PharmacyInvoice
from pharmacy_billing.utils import create_pharmacy_invoice
from core.audit_utils import log_audit_action


@login_required
def create_cart_from_prescription(request, prescription_id):
    """
    Create a new cart from prescription.
    Adds all prescription items to cart with prescribed quantities.
    """
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check if prescription can be dispensed
    can_dispense, message = prescription.can_be_dispensed()
    if not can_dispense:
        messages.error(request, message)
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
def view_cart(request, cart_id):
    """
    View cart details with all items.
    Allows selecting dispensary and reviewing items before checkout.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)
    
    # Get all dispensaries
    dispensaries = Dispensary.objects.filter(is_active=True)
    
    # Calculate totals
    subtotal = cart.get_subtotal()
    patient_payable = cart.get_patient_payable()
    nhia_coverage = cart.get_nhia_coverage()
    
    # Check if cart can generate invoice
    can_checkout, checkout_message = cart.can_generate_invoice()
    
    # Get pricing breakdown
    is_nhia_patient = cart.prescription.patient.is_nhia_patient()
    
    context = {
        'cart': cart,
        'dispensaries': dispensaries,
        'subtotal': subtotal,
        'patient_payable': patient_payable,
        'nhia_coverage': nhia_coverage,
        'can_checkout': can_checkout,
        'checkout_message': checkout_message,
        'is_nhia_patient': is_nhia_patient,
        'page_title': f'Prescription Cart #{cart.id}',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/cart/view_cart.html', context)


@login_required
def update_cart_dispensary(request, cart_id):
    """
    Update the dispensary for the cart.
    This triggers stock availability update for all items.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)
    
    if request.method == 'POST':
        dispensary_id = request.POST.get('dispensary_id')
        
        if dispensary_id:
            try:
                dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
                cart.dispensary = dispensary
                cart.save()
                
                # Update stock availability for all items
                for item in cart.items.all():
                    item.update_available_stock()
                    item.save()
                
                messages.success(request, f'Dispensary updated to {dispensary.name}')
            except Dispensary.DoesNotExist:
                messages.error(request, 'Invalid dispensary selected')
        else:
            cart.dispensary = None
            cart.save()
            messages.info(request, 'Dispensary cleared')
    
    return redirect('pharmacy:view_cart', cart_id=cart.id)


@login_required
def update_cart_item_quantity(request, item_id):
    """
    Update quantity for a cart item.
    AJAX endpoint.
    """
    if request.method == 'POST':
        import json
        
        try:
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 0))
            
            item = get_object_or_404(PrescriptionCartItem, id=item_id)
            
            # Validate quantity
            if quantity <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Quantity must be greater than zero'
                }, status=400)
            
            remaining = item.prescription_item.remaining_quantity_to_dispense
            if quantity > remaining:
                return JsonResponse({
                    'success': False,
                    'error': f'Quantity exceeds remaining quantity ({remaining})'
                }, status=400)
            
            # Update quantity
            item.quantity = quantity
            item.save()
            
            # Recalculate totals
            cart = item.cart
            
            return JsonResponse({
                'success': True,
                'item_subtotal': float(item.get_subtotal()),
                'item_patient_pays': float(item.get_patient_pays()),
                'item_nhia_covers': float(item.get_nhia_covers()),
                'cart_subtotal': float(cart.get_subtotal()),
                'cart_patient_payable': float(cart.get_patient_payable()),
                'cart_nhia_coverage': float(cart.get_nhia_coverage()),
                'stock_status': item.get_stock_status()
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
def remove_cart_item(request, item_id):
    """
    Remove an item from cart.
    """
    item = get_object_or_404(PrescriptionCartItem, id=item_id)
    cart_id = item.cart.id
    
    item.delete()
    messages.success(request, 'Item removed from cart')
    
    return redirect('pharmacy:view_cart', cart_id=cart_id)


@login_required
def generate_invoice_from_cart(request, cart_id):
    """
    Generate invoice from cart.
    Creates pharmacy_billing.Invoice and updates cart status.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)
    
    # Check if invoice can be generated
    can_checkout, message = cart.can_generate_invoice()
    if not can_checkout:
        messages.error(request, f'Cannot generate invoice: {message}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)
    
    try:
        with transaction.atomic():
            # Calculate patient payable amount
            patient_payable = cart.get_patient_payable()
            
            # Create invoice
            invoice = create_pharmacy_invoice(request, cart.prescription, patient_payable)
            
            if not invoice:
                messages.error(request, 'Failed to create invoice')
                return redirect('pharmacy:view_cart', cart_id=cart.id)
            
            # Update cart
            cart.invoice = invoice
            cart.status = 'invoiced'
            cart.save()
            
            # Log audit action
            log_audit_action(
                request.user,
                'update',
                cart,
                f'Generated invoice #{invoice.id} from cart'
            )
            
            messages.success(request, f'Invoice created successfully. Total: ₦{patient_payable:.2f}')
            
            # Redirect to payment page
            return redirect('pharmacy:prescription_payment', prescription_id=cart.prescription.id)
    
    except Exception as e:
        messages.error(request, f'Error generating invoice: {str(e)}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)


@login_required
def complete_dispensing_from_cart(request, cart_id):
    """
    Complete dispensing after payment.
    Actually dispenses medications and updates inventory.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)
    
    # Check if dispensing can be completed
    can_complete, message = cart.can_complete_dispensing()
    if not can_complete:
        messages.error(request, f'Cannot complete dispensing: {message}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)
    
    try:
        with transaction.atomic():
            dispensed_count = 0
            
            for cart_item in cart.items.all():
                p_item = cart_item.prescription_item
                medication = p_item.medication
                quantity = cart_item.quantity
                dispensary = cart.dispensary
                
                # Check stock availability one more time
                if not cart_item.has_sufficient_stock():
                    messages.error(request, f'Insufficient stock for {medication.name}')
                    continue
                
                # Create dispensing log
                unit_price = cart_item.unit_price
                total_price = cart_item.get_subtotal()
                
                DispensingLog.objects.create(
                    prescription_item=p_item,
                    dispensed_by=request.user,
                    dispensed_quantity=quantity,
                    unit_price_at_dispense=unit_price,
                    total_price_for_this_log=total_price,
                    dispensary=dispensary
                )
                
                # Update inventory
                # Try ActiveStoreInventory first
                active_store = getattr(dispensary, 'active_store', None)
                inventory_updated = False
                
                if active_store:
                    inventory_items = ActiveStoreInventory.objects.filter(
                        medication=medication,
                        active_store=active_store,
                        stock_quantity__gte=quantity
                    ).first()
                    
                    if inventory_items:
                        inventory_items.stock_quantity -= quantity
                        inventory_items.save()
                        inventory_updated = True
                
                # Try legacy inventory if not updated
                if not inventory_updated:
                    legacy_inv = MedicationInventory.objects.filter(
                        medication=medication,
                        dispensary=dispensary,
                        stock_quantity__gte=quantity
                    ).first()
                    
                    if legacy_inv:
                        legacy_inv.stock_quantity -= quantity
                        legacy_inv.save()
                
                # Update prescription item
                p_item.quantity_dispensed_so_far += quantity
                if p_item.quantity_dispensed_so_far >= p_item.quantity:
                    p_item.is_dispensed = True
                    p_item.dispensed_at = timezone.now()
                p_item.save()
                
                dispensed_count += 1
            
            # Update prescription status
            prescription = cart.prescription
            total_items = prescription.items.count()
            fully_dispensed = prescription.items.filter(is_dispensed=True).count()
            
            if fully_dispensed == total_items:
                prescription.status = 'dispensed'
            elif fully_dispensed > 0:
                prescription.status = 'partially_dispensed'
            
            prescription.save()
            
            # Update cart status
            cart.status = 'completed'
            cart.save()
            
            # Log audit action
            log_audit_action(
                request.user,
                'update',
                cart,
                f'Completed dispensing of {dispensed_count} items from cart'
            )
            
            messages.success(request, f'Successfully dispensed {dispensed_count} items')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    except Exception as e:
        messages.error(request, f'Error completing dispensing: {str(e)}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)


@login_required
def cancel_cart(request, cart_id):
    """Cancel a cart"""
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    if cart.status in ['completed', 'paid']:
        messages.error(request, 'Cannot cancel cart that is paid or completed')
        return redirect('pharmacy:view_cart', cart_id=cart.id)

    cart.cancel_cart()
    messages.success(request, 'Cart cancelled')

    return redirect('pharmacy:prescription_detail', prescription_id=cart.prescription.id)


@login_required
def cart_list(request):
    """
    List all prescription carts with filtering options.
    """
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    status_filter = request.GET.get('status', '')
    dispensary_filter = request.GET.get('dispensary', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    carts = PrescriptionCart.objects.select_related(
        'prescription__patient',
        'created_by',
        'dispensary',
        'invoice'
    ).order_by('-created_at')

    # Apply filters
    if status_filter:
        carts = carts.filter(status=status_filter)

    if dispensary_filter:
        carts = carts.filter(dispensary_id=dispensary_filter)

    if search_query:
        carts = carts.filter(
            Q(prescription__patient__first_name__icontains=search_query) |
            Q(prescription__patient__last_name__icontains=search_query) |
            Q(prescription__id__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(carts, 20)  # 20 carts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all dispensaries for filter dropdown
    dispensaries = Dispensary.objects.filter(is_active=True)

    context = {
        'carts': page_obj,
        'dispensaries': dispensaries,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_title': 'Prescription Carts',
        'active_nav': 'pharmacy',
    }

    return render(request, 'pharmacy/cart/cart_list.html', context)


@login_required
def cart_receipt(request, cart_id):
    """
    Display printable cart receipt.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)

    # Get hospital information (you may need to adjust this based on your settings)
    from django.conf import settings

    context = {
        'cart': cart,
        'hospital_name': getattr(settings, 'HOSPITAL_NAME', 'Hospital Management System'),
        'hospital_address': getattr(settings, 'HOSPITAL_ADDRESS', ''),
        'hospital_phone': getattr(settings, 'HOSPITAL_PHONE', ''),
        'now': timezone.now(),
        'page_title': f'Cart Receipt #{cart.id}',
    }

    return render(request, 'pharmacy/cart/cart_receipt.html', context)

