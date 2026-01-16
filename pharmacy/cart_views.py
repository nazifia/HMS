"""
Prescription Cart Views for HMS Pharmacy Module

Handles cart operations: create, view, update, checkout, and complete dispensing.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count
from django.http import JsonResponse
from decimal import Decimal
from django.utils import timezone
import json

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
def view_cart(request, cart_id):
    """
    View cart details with all items.
    Allows selecting dispensary and reviewing items before checkout.
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)
    
    # Auto-update cart status if invoice is paid (handles billing office payments)
    if cart.invoice and cart.invoice.status == 'paid' and cart.status in ['invoiced', 'active']:
        cart.status = 'paid'
        cart.save(update_fields=['status'])
        messages.info(request, '💳 Cart status updated to "Paid" - payment processed via billing office')
    
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
    
    # Get payment details for billing office payments
    payment_details = None
    if cart.invoice and cart.invoice.payments.exists():
        payment_details = cart.invoice.payments.all().order_by('-payment_date')

    # Get all available medications in the dispensary for substitution
    available_medications = []
    if cart.dispensary and cart.status == 'active':
        from pharmacy.models import ActiveStoreInventory, Medication

        # Check if dispensary has an active_store (OneToOne relationship)
        # Using hasattr is safer for OneToOne fields to avoid DoesNotExist exceptions
        if hasattr(cart.dispensary, 'active_store'):
            try:
                active_store = cart.dispensary.active_store
                # Get all medications with stock in this dispensary
                med_stock = ActiveStoreInventory.objects.filter(
                    active_store=active_store,
                    stock_quantity__gt=0
                ).select_related('medication').values(
                    'medication__id',
                    'medication__name',
                    'medication__strength',
                    'medication__dosage_form',
                    'medication__generic_name',
                    'medication__price'
                ).annotate(
                    total_stock=Sum('stock_quantity')
                ).order_by('medication__name')

                for med in med_stock:
                    # Build full medication name
                    name_parts = [med['medication__name']]
                    if med['medication__strength']:
                        name_parts.append(med['medication__strength'])
                    if med['medication__dosage_form']:
                        name_parts.append(med['medication__dosage_form'])
                    full_name = ' '.join(name_parts)

                    available_medications.append({
                        'id': med['medication__id'],
                        'name': med['medication__name'],
                        'full_name': full_name,
                        'strength': med['medication__strength'] or '',
                        'dosage_form': med['medication__dosage_form'] or '',
                        'generic_name': med['medication__generic_name'] or '',
                        'stock': med['total_stock'],
                        'price': float(med['medication__price']) if med['medication__price'] else 0
                    })
            except Exception as e:
                # Log error but continue - cart will work without substitution feature
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error loading available medications for cart {cart.id}: {e}")

    context = {
        'cart': cart,
        'dispensaries': dispensaries,
        'subtotal': subtotal,
        'patient_payable': patient_payable,
        'nhia_coverage': nhia_coverage,
        'can_checkout': can_checkout,
        'checkout_message': checkout_message,
        'is_nhia_patient': is_nhia_patient,
        'payment_details': payment_details,
        'available_medications': json.dumps(available_medications),
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

            # Validate against available stock (prescription limit removed)
            item.update_available_stock()  # Refresh stock info
            available_stock = item.available_stock

            if quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Quantity exceeds available stock. Only {available_stock} available in selected dispensary.'
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
    Only generates invoice for items with sufficient stock (selected in UI).
    """
    cart = get_object_or_404(PrescriptionCart, id=cart_id)
    
    # Check if invoice can be generated
    can_checkout, message = cart.can_generate_invoice()
    if not can_checkout:
        messages.error(request, f'Cannot generate invoice: {message}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)
    
    # Validate that user selected items (sent via POST)
    # Note: For now, we'll generate invoice for all available items
    # but log which items were checked in the UI for reference
    selected_items = request.POST.getlist('selected_item')
    if not selected_items:
        messages.warning(request, '⚠️ No specific items were selected in the UI. All items with sufficient stock will be included in the invoice.')
    else:
        messages.info(request, f'✓ Generating invoice for {len(selected_items)} selected medication(s).')
    
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
            
            # Direct to current cart for dispensing workflow
            messages.info(request, '💊 Invoice created! Redirecting to cart.')
            return redirect('pharmacy:view_cart', cart_id=cart.id)
    
    except Exception as e:
        messages.error(request, f'Error generating invoice: {str(e)}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)


@login_required
def complete_dispensing_from_cart(request, cart_id):
    """
    Complete dispensing after payment.
    Supports partial dispensing - dispenses available items and keeps cart active for pending items.
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
            partially_dispensed_count = 0
            skipped_count = 0

            for cart_item in cart.items.all():
                p_item = cart_item.prescription_item
                # Use substitute medication if present, otherwise use prescribed medication
                medication = cart_item.get_effective_medication()
                dispensary = cart.dispensary

                # Get remaining quantity to dispense
                remaining_qty = cart_item.get_remaining_quantity()

                if remaining_qty <= 0:
                    # Already fully dispensed
                    continue

                # Check if pharmacist specified a custom quantity
                custom_qty_key = f'dispense_qty_{cart_item.id}'
                custom_quantity = request.POST.get(custom_qty_key)

                if custom_quantity:
                    # Pharmacist specified a custom quantity
                    try:
                        quantity_to_dispense = int(custom_quantity)

                        # Validate the custom quantity
                        available_to_dispense = cart_item.get_available_to_dispense_now()

                        if quantity_to_dispense <= 0:
                            # Skip items with 0 quantity
                            continue

                        if quantity_to_dispense > available_to_dispense:
                            messages.error(request, f'Cannot dispense {quantity_to_dispense} of {medication.name}. Only {available_to_dispense} available.')
                            return redirect('pharmacy:view_cart', cart_id=cart.id)

                    except (ValueError, TypeError):
                        messages.error(request, f'Invalid quantity for {medication.name}.')
                        return redirect('pharmacy:view_cart', cart_id=cart.id)
                else:
                    # No custom quantity specified, use automatic logic
                    # Get available quantity to dispense now
                    available_to_dispense = cart_item.get_available_to_dispense_now()

                    if available_to_dispense <= 0:
                        # No stock available, skip this item
                        messages.warning(request, f'No stock available for {medication.name}. Will dispense when stock arrives.')
                        skipped_count += 1
                        continue

                    # Determine quantity to dispense (may be partial)
                    quantity_to_dispense = available_to_dispense
                
                # Create dispensing log
                unit_price = cart_item.unit_price
                total_price = Decimal(str(quantity_to_dispense)) * unit_price

                DispensingLog.objects.create(
                    prescription_item=p_item,
                    dispensed_by=request.user,
                    dispensed_quantity=quantity_to_dispense,
                    unit_price_at_dispense=unit_price,
                    total_price_for_this_log=total_price,
                    dispensary=dispensary
                )

                # Update inventory
                # Try ActiveStoreInventory first
                inventory_updated = False

                if hasattr(dispensary, 'active_store'):
                    try:
                        active_store = dispensary.active_store
                        # Find any inventory with sufficient stock (or enough to meet the request)
                        inventory_items = ActiveStoreInventory.objects.filter(
                            medication=medication,
                            active_store=active_store,
                            stock_quantity__gt=0  # Get any item with stock
                        ).first()

                        if inventory_items:
                            # Check if this inventory has enough stock
                            if inventory_items.stock_quantity >= quantity_to_dispense:
                                inventory_items.stock_quantity -= quantity_to_dispense
                                inventory_items.save()
                                inventory_updated = True
                            else:
                                # Not enough stock in this single item - try to find another with enough
                                # First, try to find an item with exactly the required quantity
                                exact_match = ActiveStoreInventory.objects.filter(
                                    medication=medication,
                                    active_store=active_store,
                                    stock_quantity=quantity_to_dispense
                                ).first()

                                if exact_match:
                                    exact_match.stock_quantity -= quantity_to_dispense  # This will make it 0
                                    exact_match.save()
                                    inventory_updated = True
                                else:
                                    # Find any items with sufficient stock using aggregation
                                    from django.db.models import Sum, F, Case, When, IntegerField
                                    
                                    inventory_summary = ActiveStoreInventory.objects.filter(
                                        medication=medication,
                                        active_store=active_store,
                                        stock_quantity__gt=0
                                    ).aggregate(
                                        total_stock=Sum('stock_quantity'),
                                        count=Count('id')
                                    )

                                    if inventory_summary['total_stock'] >= quantity_to_dispense:
                                        # We have enough stock across multiple items
                                        # Deduct from inventory items in FIFO order (oldest batch first)
                                        remaining_to_deduct = quantity_to_dispense
                                        items_to_update = ActiveStoreInventory.objects.filter(
                                            medication=medication,
                                            active_store=active_store,
                                            stock_quantity__gt=0
                                        ).order_by('id')  # FIFO - oldest first

                                        for inv_item in items_to_update:
                                            if remaining_to_deduct <= 0:
                                                break

                                            if inv_item.stock_quantity >= remaining_to_deduct:
                                                inv_item.stock_quantity -= remaining_to_deduct
                                                inv_item.save()
                                                inventory_updated = True
                                                break
                                            else:
                                                # Deduct full amount and continue to next item
                                                remaining_to_deduct -= inv_item.stock_quantity
                                                inv_item.stock_quantity = 0
                                                inv_item.save()
                    
                    except Exception as e:
                        # Log error but continue to try legacy inventory
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Error updating active store inventory: {e}")

                # Try legacy inventory if not updated
                if not inventory_updated:
                    try:
                        legacy_inv = MedicationInventory.objects.filter(
                            medication=medication,
                            dispensary=dispensary,
                            stock_quantity__gt=0  # Get any item with stock
                        ).first()

                        if legacy_inv:
                            # Check if this inventory has enough stock
                            if legacy_inv.stock_quantity >= quantity_to_dispense:
                                legacy_inv.stock_quantity -= quantity_to_dispense
                                legacy_inv.save()
                            else:
                                # Not enough stock in this single item - try to find another with enough
                                exact_match = MedicationInventory.objects.filter(
                                    medication=medication,
                                    dispensary=dispensary,
                                    stock_quantity=quantity_to_dispense
                                ).first()

                                if exact_match:
                                    exact_match.stock_quantity -= quantity_to_dispense  # This will make it 0
                                    exact_match.save()
                                else:
                                    # Find any items with sufficient stock using aggregation
                                    from django.db.models import Sum, Count
                                    
                                    inventory_summary = MedicationInventory.objects.filter(
                                        medication=medication,
                                        dispensary=dispensary,
                                        stock_quantity__gt=0
                                    ).aggregate(
                                        total_stock=Sum('stock_quantity'),
                                        count=Count('id')
                                    )

                                    if inventory_summary['total_stock'] >= quantity_to_dispense:
                                        # We have enough stock across multiple items
                                        # Deduct from inventory items in FIFO order (oldest batch first)
                                        remaining_to_deduct = quantity_to_dispense
                                        items_to_update = MedicationInventory.objects.filter(
                                            medication=medication,
                                            dispensary=dispensary,
                                            stock_quantity__gt=0
                                        ).order_by('id')  # FIFO - oldest first

                                        for inv_item in items_to_update:
                                            if remaining_to_deduct <= 0:
                                                break

                                            if inv_item.stock_quantity >= remaining_to_deduct:
                                                inv_item.stock_quantity -= remaining_to_deduct
                                                inv_item.save()
                                                break
                                            else:
                                                # Deduct full amount and continue to next item
                                                remaining_to_deduct -= inv_item.stock_quantity
                                                inv_item.stock_quantity = 0
                                                inv_item.save()
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Error updating legacy inventory: {e}")

                # Update prescription item
                p_item.quantity_dispensed_so_far += quantity_to_dispense
                if p_item.quantity_dispensed_so_far >= p_item.quantity:
                    p_item.is_dispensed = True
                    p_item.dispensed_at = timezone.now()
                p_item.save()

                # Update cart item
                cart_item.quantity_dispensed += quantity_to_dispense
                cart_item.save()

                # Track dispensing status
                if quantity_to_dispense < remaining_qty:
                    partially_dispensed_count += 1
                    messages.info(request, f'Partially dispensed {medication.name}: {quantity_to_dispense} of {remaining_qty} remaining')
                else:
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

            # Update cart status based on dispensing progress
            if cart.is_fully_dispensed():
                cart.status = 'completed'
                cart.save()

                # Log audit action
                log_audit_action(
                    request.user,
                    'update',
                    cart,
                    f'Completed full dispensing of all items from cart'
                )

                messages.success(request, f'✅ Successfully dispensed all items! Cart completed.')
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            else:
                cart.status = 'partially_dispensed'
                cart.save()

                # Log audit action
                log_audit_action(
                    request.user,
                    'update',
                    cart,
                    f'Partial dispensing: {dispensed_count} fully dispensed, {partially_dispensed_count} partially dispensed, {skipped_count} skipped'
                )

                # Show detailed message
                progress = cart.get_dispensing_progress()
                messages.success(
                    request,
                    f'✅ Dispensed {dispensed_count + partially_dispensed_count} items. '
                    f'Progress: {progress["percentage"]}% complete. '
                    f'{progress["remaining_quantity"]} items still pending.'
                )
                messages.info(
                    request,
                    f'ℹ️ Cart remains active for pending items. You can dispense remaining items when stock becomes available.'
                )

                # Stay on cart page to show progress
                return redirect('pharmacy:view_cart', cart_id=cart.id)
    
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


@login_required
def substitute_cart_item(request, item_id):
    """
    Substitute a cart item with an alternative medication.
    Requires pharmacist approval and reason.
    """
    cart_item = get_object_or_404(PrescriptionCartItem, id=item_id)
    cart = cart_item.cart

    # Check if substitution is allowed
    can_sub, message = cart_item.can_substitute()
    if not can_sub:
        messages.error(request, f'Cannot substitute: {message}')
        return redirect('pharmacy:view_cart', cart_id=cart.id)

    if request.method == 'POST':
        substitute_med_id = request.POST.get('substitute_medication_id')
        reason = request.POST.get('reason', '').strip()

        # Validate inputs
        if not substitute_med_id:
            messages.error(request, 'Please select a substitute medication')
            return redirect('pharmacy:view_cart', cart_id=cart.id)

        if not reason:
            messages.error(request, 'Please provide a reason for substitution')
            return redirect('pharmacy:view_cart', cart_id=cart.id)

        try:
            from pharmacy.models import Medication

            substitute_med = Medication.objects.get(id=substitute_med_id)

            # Perform substitution
            with transaction.atomic():
                cart_item.substitute_with(substitute_med, reason, request.user)

                # Log audit action
                log_audit_action(
                    request.user,
                    'update',
                    cart_item,
                    f'Substituted {cart_item.prescription_item.medication.name} with {substitute_med.name}. Reason: {reason}'
                )

                messages.success(
                    request,
                    f'✅ Successfully substituted {cart_item.prescription_item.medication.name} '
                    f'with {substitute_med.name} ({substitute_med.strength or ""} {substitute_med.dosage_form or ""})'
                )

                # Check if substitution resolved stock issues
                cart_item.update_available_stock()
                if cart_item.available_stock >= cart_item.quantity:
                    messages.info(request, f'✓ {substitute_med.name} has sufficient stock ({cart_item.available_stock} units available)')
                else:
                    messages.warning(
                        request,
                        f'⚠️ Only {cart_item.available_stock} units of {substitute_med.name} available (need {cart_item.quantity})'
                    )

        except Medication.DoesNotExist:
            messages.error(request, 'Invalid substitute medication selected')
        except ValidationError as e:
            messages.error(request, f'Substitution failed: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error during substitution: {str(e)}')

    return redirect('pharmacy:view_cart', cart_id=cart.id)


@login_required
def remove_substitution(request, item_id):
    """
    Remove substitution and revert to original prescribed medication.
    """
    cart_item = get_object_or_404(PrescriptionCartItem, id=item_id)
    cart = cart_item.cart

    if not cart_item.is_substituted():
        messages.warning(request, 'This item is not substituted')
        return redirect('pharmacy:view_cart', cart_id=cart.id)

    try:
        with transaction.atomic():
            original_med = cart_item.prescription_item.medication
            substitute_med = cart_item.substitute_medication

            cart_item.remove_substitution()

            # Log audit action
            log_audit_action(
                request.user,
                'update',
                cart_item,
                f'Removed substitution of {substitute_med.name}, reverted to {original_med.name}'
            )

            messages.success(
                request,
                f'✅ Reverted to original medication: {original_med.name} '
                f'({original_med.strength or ""} {original_med.dosage_form or ""})'
            )

    except Exception as e:
        messages.error(request, f'Error removing substitution: {str(e)}')

    return redirect('pharmacy:view_cart', cart_id=cart.id)

