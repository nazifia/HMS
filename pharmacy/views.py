from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import (
    MedicationCategory, Medication, Supplier, Purchase,
    PurchaseItem, Prescription, PrescriptionItem, DispensingLog, PurchaseApproval
)
from .forms import (
    MedicationCategoryForm, MedicationForm, SupplierForm, PurchaseForm,
    PurchaseItemForm, PrescriptionForm, PrescriptionItemForm,
    DispenseItemForm, BaseDispenseItemFormSet, MedicationSearchForm, PrescriptionSearchForm,
    DispensedItemsSearchForm
)
from patients.models import Patient
from django.contrib.auth.models import User
from django.forms import formset_factory
from django.db import transaction
import json
from billing.models import Invoice, InvoiceItem, Service # Ensure Service is imported
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from core.models import send_notification_email, InternalNotification
from django.db.models import Q, Sum, Count
from django.http import HttpResponse

@login_required
def pharmacy_dashboard(request):
    total_medications = Medication.objects.filter(is_active=True).count()
    low_stock_count = Medication.objects.filter(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0, is_active=True).count()
    out_of_stock_count = Medication.objects.filter(stock_quantity=0, is_active=True).count()
    expired_count = Medication.objects.filter(expiry_date__lt=timezone.now().date(), is_active=True).count()

    pending_prescriptions = Prescription.objects.filter(status='pending').count()
    dispensed_today = DispensingLog.objects.filter(dispensed_date__date=timezone.now().date()).count()

    recent_prescriptions = Prescription.objects.order_by('-created_at')[:5]
    low_stock_medications = Medication.objects.filter(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0, is_active=True)[:5]

    context = {
        'total_medications': total_medications,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'expired_count': expired_count,
        'pending_prescriptions': pending_prescriptions,
        'dispensed_today': dispensed_today,
        'recent_prescriptions': recent_prescriptions,
        'low_stock_medications': low_stock_medications,
    }
    return render(request, 'pharmacy/dashboard.html', context)


# Helper function to create an invoice for a prescription (with logging)


def _create_pharmacy_invoice(request, prescription, subtotal_value):
    from pharmacy_billing.utils import create_pharmacy_invoice
    messages.info(request, f"[_create_pharmacy_invoice] Called for Prescription ID: {prescription.id}, Subtotal: {subtotal_value}")
    invoice = create_pharmacy_invoice(request, prescription, subtotal_value)
    if invoice is None:
        messages.error(request, "Invoice creation failed: 'Medication Dispensing' service not found or invoice item creation failed. No invoice was created.")
        raise Service.DoesNotExist("'Medication Dispensing' service not found or invoice item creation failed.")
    return invoice


@login_required
def inventory_list(request):
    # ...existing code...
    search_form = MedicationSearchForm(request.GET)
    medications = Medication.objects.all().order_by('name')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        category = search_form.cleaned_data.get('category')
        stock_status = search_form.cleaned_data.get('stock_status')
        is_active = search_form.cleaned_data.get('is_active')

        if search_query:
            medications = medications.filter(
                Q(name__icontains=search_query) |
                Q(generic_name__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        if category:
            medications = medications.filter(category=category)

        if stock_status:
            if stock_status == 'in_stock':
                medications = medications.filter(stock_quantity__gt=0)
            elif stock_status == 'low_stock':
                medications = medications.filter(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0)
            elif stock_status == 'out_of_stock':
                medications = medications.filter(stock_quantity=0)

        if is_active:
            if is_active == 'active':
                medications = medications.filter(is_active=True)
            elif is_active == 'inactive':
                medications = medications.filter(is_active=False) # Corrected syntax: is_active=False

    # Pagination
    paginator = Paginator(medications, 10)  # Show 10 medications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts for different statuses
    total_medications = Medication.objects.count()
    in_stock_count = Medication.objects.filter(stock_quantity__gt=0).count()
    low_stock_count = Medication.objects.filter(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0).count()
    out_of_stock_count = Medication.objects.filter(stock_quantity=0).count()
    expired_count = Medication.objects.filter(expiry_date__lt=timezone.now().date()).count()

    # Get categories for the filter
    categories = MedicationCategory.objects.all()

    # Real-time inventory alerts for low stock and expired medications
    low_stock_alerts = Medication.objects.filter(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0, is_active=True)
    expired_alerts = Medication.objects.filter(expiry_date__lt=timezone.now().date(), is_active=True)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_medications': total_medications,
        'in_stock_count': in_stock_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'expired_count': expired_count,
        'categories': categories,
        'low_stock_alerts': low_stock_alerts,
        'expired_alerts': expired_alerts,
        # ...existing context...
    }
    return render(request, 'pharmacy/inventory_list.html', context)

# Optionally, call check_and_notify_low_stock_and_expiry() on a schedule or after inventory update.

@login_required
def add_medication(request):
    # ...existing code...
    if request.method == 'POST':
        form = MedicationForm(request.POST)
        if form.is_valid():
            medication = form.save()
            messages.success(request, f'Medication {medication.name} has been added successfully.')
            return redirect('pharmacy:inventory')
    else:
        form = MedicationForm()

    context = {
        'form': form,
        'title': 'Add New Medication'
    }

    return render(request, 'pharmacy/medication_form.html', context)

@login_required
def edit_medication(request, medication_id):
    # ...existing code...
    medication = get_object_or_404(Medication, id=medication_id)

    if request.method == 'POST':
        form = MedicationForm(request.POST, instance=medication)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medication {medication.name} has been updated successfully.')
            return redirect('pharmacy:inventory')
    else:
        form = MedicationForm(instance=medication)

    context = {
        'form': form,
        'medication': medication,
        'title': f'Edit Medication: {medication.name}'
    }

    return render(request, 'pharmacy/medication_form.html', context)

@login_required
def delete_medication(request, medication_id):
    # ...existing code...
    medication = get_object_or_404(Medication, id=medication_id)

    if request.method == 'POST':
        medication.is_active = False
        medication.save()
        messages.success(request, f'Medication {medication.name} has been deactivated.')
        return redirect('pharmacy:inventory')

    context = {
        'medication': medication
    }

    return render(request, 'pharmacy/delete_medication.html', context)

@login_required
def medication_detail(request, medication_id):
    # ...existing code...
    medication = get_object_or_404(Medication, id=medication_id)

    # Get purchase history for this medication
    purchase_items = PurchaseItem.objects.filter(medication=medication).order_by('-purchase__purchase_date')

    # Get prescription history for this medication
    prescription_items = PrescriptionItem.objects.filter(medication=medication).order_by('-prescription__prescription_date')

    context = {
        'medication': medication,
        'purchase_items': purchase_items,
        'prescription_items': prescription_items,
    }

    return render(request, 'pharmacy/medication_detail.html', context)

@login_required
def manage_categories(request):
    # ...existing code...
    categories = MedicationCategory.objects.all().order_by('name')

    if request.method == 'POST':
        form = MedicationCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} has been added successfully.')
            return redirect('pharmacy:manage_categories')
    else:
        form = MedicationCategoryForm()

    context = {
        'form': form,
        'categories': categories,
        'title': 'Manage Medication Categories'
    }

    return render(request, 'pharmacy/manage_categories.html', context)

@login_required
def edit_category(request, category_id):
    # ...existing code...
    category = get_object_or_404(MedicationCategory, id=category_id)

    if request.method == 'POST':
        form = MedicationCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category {category.name} has been updated successfully.')
            return redirect('pharmacy:manage_categories')
    else:
        form = MedicationCategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}'
    }

    return render(request, 'pharmacy/category_form.html', context)

@login_required
def delete_category(request, category_id):
    # ...existing code...
    category = get_object_or_404(MedicationCategory, id=category_id)

    if request.method == 'POST':
        # Check if there are medications in this category
        if category.medications.exists():
            messages.error(request, f'Cannot delete category {category.name} because it contains medications.')
            return redirect('pharmacy:manage_categories')

        category.delete()
        messages.success(request, f'Category {category.name} has been deleted.')
        return redirect('pharmacy:manage_categories')

    context = {
        'category': category
    }

    return render(request, 'pharmacy/delete_category.html', context)

@login_required
def manage_suppliers(request):
    # ...existing code...
    suppliers = Supplier.objects.all().order_by('name')

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier {supplier.name} has been added successfully.')
            return redirect('pharmacy:manage_suppliers')
    else:
        form = SupplierForm()

    context = {
        'form': form,
        'suppliers': suppliers,
        'title': 'Manage Suppliers'
    }

    return render(request, 'pharmacy/manage_suppliers.html', context)

@login_required
def edit_supplier(request, supplier_id):
    # ...existing code...
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Supplier {supplier.name} has been updated successfully.')
            return redirect('pharmacy:manage_suppliers')
    else:
        form = SupplierForm(instance=supplier)

    context = {
        'form': form,
        'supplier': supplier,
        'title': f'Edit Supplier: {supplier.name}'
    }

    return render(request, 'pharmacy/supplier_form.html', context)

@login_required
def delete_supplier(request, supplier_id):
    # ...existing code...
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        supplier.is_active = False
        supplier.save()
        messages.success(request, f'Supplier {supplier.name} has been deactivated.')
        return redirect('pharmacy:manage_suppliers')

    context = {
        'supplier': supplier
    }

    return render(request, 'pharmacy/delete_supplier.html', context)

@login_required
def manage_purchases(request):
    # ...existing code...
    purchases = Purchase.objects.all().order_by('-purchase_date')

    context = {
        'purchases': purchases,
        'title': 'Manage Purchases',
        'user': request.user,  # For approval UI logic
    }

    return render(request, 'pharmacy/manage_purchases.html', context)

@login_required
def add_purchase(request):
    # ...existing code...
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.created_by = request.user
            purchase.save()
            messages.success(request, f'Purchase #{purchase.invoice_number} has been added successfully.')
            return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    else:
        form = PurchaseForm(initial={'purchase_date': timezone.now().date()})

    context = {
        'form': form,
        'title': 'Add New Purchase'
    }

    return render(request, 'pharmacy/purchase_form.html', context)

@login_required
def purchase_detail(request, purchase_id):
    # ...existing code...
    purchase = get_object_or_404(Purchase, id=purchase_id)
    purchase_items = purchase.items.all()

    # Handle adding new purchase item
    if request.method == 'POST' and 'add_item' in request.POST:
        item_form = PurchaseItemForm(request.POST)
        if item_form.is_valid():
            item = item_form.save(commit=False)
            item.purchase = purchase
            item.total_price = item.quantity * item.unit_price
            item.save()

            # Update medication stock and expiry date
            medication = item.medication
            medication.stock_quantity += item.quantity

            # Update expiry date if the new batch has a later expiry date
            if not medication.expiry_date or item.expiry_date > medication.expiry_date:
                medication.expiry_date = item.expiry_date

            medication.save()

            # Update purchase total amount
            purchase.total_amount = purchase.items.aggregate(total=Sum('total_price'))['total'] or 0
            purchase.save()

            messages.success(request, f'{item.quantity} units of {item.medication.name} added to purchase.')
            return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    else:
        item_form = PurchaseItemForm()

    context = {
        'purchase': purchase,
        'purchase_items': purchase_items,
        'item_form': item_form,
    }

    return render(request, 'pharmacy/purchase_detail.html', context)

@login_required
def delete_purchase_item(request, item_id):
    # ...existing code...
    item = get_object_or_404(PurchaseItem, id=item_id)
    purchase = item.purchase

    if request.method == 'POST':
        # Update medication stock
        medication = item.medication
        medication.stock_quantity -= item.quantity
        medication.save()

        # Delete the item
        item.delete()

        # Update purchase total amount
        purchase.total_amount = purchase.items.aggregate(total=Sum('total_price'))['total'] or 0
        purchase.save()

        messages.success(request, f'Item {item.medication.name} has been removed from purchase.')
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

    context = {
        'item': item,
        'purchase': purchase
    }

    return render(request, 'pharmacy/delete_purchase_item.html', context)

@login_required
def prescription_list(request):
    # ...existing code...
    search_form = PrescriptionSearchForm(request.GET)
    # Use select_related for ForeignKey/OneToOne, prefetch_related for reverse/many-to-many
    prescriptions = Prescription.objects.all().select_related('patient', 'doctor').prefetch_related('items').order_by('-prescription_date')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        status = search_form.cleaned_data.get('status')
        doctor = search_form.cleaned_data.get('doctor')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            prescriptions = prescriptions.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query)
            )

        if status:
            prescriptions = prescriptions.filter(status=status)

        if doctor:
            prescriptions = prescriptions.filter(doctor=doctor)

        if date_from:
            prescriptions = prescriptions.filter(prescription_date__gte=date_from)

        if date_to:
            prescriptions = prescriptions.filter(prescription_date__lte=date_to)

    # Pagination
    paginator = Paginator(prescriptions, 10)  # Show 10 prescriptions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Use aggregate for counts
    from django.db.models import Count
    status_counts = Prescription.objects.values('status').annotate(count=Count('id'))
    status_count_dict = {item['status']: item['count'] for item in status_counts}
    pending_count = status_count_dict.get('pending', 0)
    processing_count = status_count_dict.get('processing', 0)
    completed_count = status_count_dict.get('completed', 0)
    cancelled_count = status_count_dict.get('cancelled', 0)

    # Advanced: Add role-based analytics for prescriptions
    role_counts = Prescription.objects.values('doctor__roles__name').annotate(count=Count('id')).order_by('-count')
    from core.models import AuditLog, InternalNotification
    # Advanced: Add audit log and notification fetch (if models exist)
    audit_logs = AuditLog.objects.all().order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]

    # Advanced: Analytics (e.g., item count, total value, status by role)
    from django.db.models import Count, Sum
    analytics = {
        'item_count': prescriptions.count(),
        'total_value': prescriptions.aggregate(
            total=Sum('items__medication__price')
        )['total'] or 0,
        'actions_by_role': AuditLog.objects.all().values('user__roles__name').annotate(count=Count('id')).order_by('-count')
    }

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_prescriptions': prescriptions.count(),
        'pending_count': pending_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'role_counts': role_counts,
        'audit_logs': audit_logs,
        'user_notifications': user_notifications,
    }

    return render(request, 'pharmacy/prescription_list.html', context)

@login_required
def create_prescription(request):
    # ...existing code...
    messages.info(request, f"[create_prescription] View called. Method: {request.method}")
    is_direct_post = request.method == 'POST' and 'patient' in request.POST and 'doctor' in request.POST and 'medication[]' in request.POST
    messages.info(request, f"[create_prescription] Is Direct POST: {is_direct_post}")
    
    form = None # Initialize form variable

    if is_direct_post:
        messages.info(request, "[create_prescription] Handling as Direct POST.")
        prescription = None # Initialize prescription variable
        try:
            with transaction.atomic():
                patient_id = request.POST.get('patient')
                doctor_id = request.POST.get('doctor')
                diagnosis = request.POST.get('diagnosis')
                notes = request.POST.get('notes')

                patient = Patient.objects.get(id=patient_id)
                doctor = User.objects.get(id=doctor_id)

                prescription = Prescription.objects.create(
                    patient=patient,
                    doctor=doctor,
                    prescription_date=timezone.now().date(),
                    diagnosis=diagnosis,
                    notes=notes,
                    status='pending',
                    payment_status='unpaid' 
                )
                messages.info(request, f"[create_prescription:DirectPOST] Prescription object created. ID: {prescription.id}")

                medications = request.POST.getlist('medication[]')
                dosages = request.POST.getlist('dosage[]')
                frequencies = request.POST.getlist('frequency[]')
                durations = request.POST.getlist('duration[]')
                quantities = request.POST.getlist('quantity[]')
                instructions_list = request.POST.getlist('instructions[]')
                
                messages.info(request, f"[create_prescription:DirectPOST] Found {len(medications)} medication entries, {len(quantities)} quantity entries.")
                total_prescription_value = Decimal('0.00')
                items_created_count = 0

                for i in range(len(medications)):
                    if medications[i] and i < len(quantities) and quantities[i]:
                        med_id = medications[i]
                        qty_str = quantities[i]
                        try:
                            medication_obj = Medication.objects.get(id=med_id)
                            quantity = int(qty_str)
                            if quantity <= 0:
                                messages.warning(request, f"[create_prescription:DirectPOST] Skipped medication {medication_obj.name} due to zero or negative quantity: {quantity}")
                                continue

                            PrescriptionItem.objects.create(
                                prescription=prescription,
                                medication=medication_obj,
                                dosage=dosages[i] if i < len(dosages) else '',
                                frequency=frequencies[i] if i < len(frequencies) else '',
                                duration=durations[i] if i < len(durations) else '',
                                quantity=quantity,
                                instructions=instructions_list[i] if i < len(instructions_list) else ''
                            )
                            total_prescription_value += medication_obj.price * Decimal(quantity)
                            items_created_count += 1
                        except Medication.DoesNotExist:
                            messages.error(request, f"[create_prescription:DirectPOST] Medication with ID {med_id} not found. Skipping item.")
                        except ValueError:
                            messages.error(request, f"[create_prescription:DirectPOST] Invalid quantity '{qty_str}' for medication ID {med_id}. Skipping item.")
                
                messages.info(request, f"[create_prescription:DirectPOST] Items processed. Count: {items_created_count}, Total Value: {total_prescription_value}")
                # --- REMOVE invoice generation from here ---
                if items_created_count > 0 and total_prescription_value > Decimal('0.00'):
                    messages.success(request, f'Prescription for {prescription.patient.get_full_name()} created.')
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                elif items_created_count > 0:
                    messages.success(request, f'Prescription for {prescription.patient.get_full_name()} created (no billable items/zero value).')
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                else:
                    messages.warning(request, f'Prescription for {prescription.patient.get_full_name()} created, but no valid items were processed.')
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

        except (Patient.DoesNotExist, User.DoesNotExist) as e:
            messages.error(request, f'[create_prescription:DirectPOST] Error creating prescription (data lookup failed): {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'pharmacy:prescription_list'))
        except Service.DoesNotExist: 
            messages.error(request, "[create_prescription:DirectPOST] Invoice creation failed: 'Medication Dispensing' service not found. Prescription may have been saved.")
            if prescription and prescription.pk:
                 return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            return redirect(request.META.get('HTTP_REFERER', 'pharmacy:prescription_list'))
        except Exception as e:
            messages.error(request, f'[create_prescription:DirectPOST] An unexpected error occurred: {str(e)}')
            if prescription and prescription.pk: # If prescription was created before error
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            return redirect(request.META.get('HTTP_REFERER', 'pharmacy:prescription_list'))

    elif request.method == 'POST':
        messages.info(request, "[create_prescription] Handling as Form-based POST.")
        form = PrescriptionForm(request.POST, request=request)
        prescription = None # Initialize
        if form.is_valid():
            messages.info(request, "[create_prescription:FormPOST] PrescriptionForm is valid.")
            try:
                with transaction.atomic():
                    prescription = form.save(commit=False)
                    if not prescription.doctor_id: 
                        prescription.doctor = request.user
                    prescription.payment_status = 'unpaid'
                    prescription.save()
                    messages.info(request, f"[create_prescription:FormPOST] Prescription object saved. ID: {prescription.id}")

                    medications = request.POST.getlist('medication[]')
                    dosages = request.POST.getlist('dosage[]')
                    frequencies = request.POST.getlist('frequency[]')
                    durations = request.POST.getlist('duration[]')
                    quantities = request.POST.getlist('quantity[]')
                    instructions_list = request.POST.getlist('instructions[]')
                    messages.info(request, f"[create_prescription:FormPOST] Found {len(medications)} medication entries, {len(quantities)} quantity entries from form POST.")
                    
                    total_prescription_value = Decimal('0.00')
                    items_created_count = 0

                    if medications: 
                        for i in range(len(medications)):
                            if medications[i] and i < len(quantities) and quantities[i]:
                                med_id = medications[i]
                                qty_str = quantities[i]
                                try:
                                    medication_obj = Medication.objects.get(id=med_id)
                                    quantity_val = int(qty_str)
                                    if quantity_val <= 0: 
                                        messages.warning(request, f"[create_prescription:FormPOST] Skipped medication {medication_obj.name} due to zero or negative quantity: {quantity_val}")
                                        continue
                                    PrescriptionItem.objects.create(
                                        prescription=prescription,
                                        medication=medication_obj,
                                        dosage=dosages[i] if i < len(dosages) else '',
                                        frequency=frequencies[i] if i < len(frequencies) else '',
                                        duration=durations[i] if i < len(durations) else '',
                                        quantity=quantity_val,
                                        instructions=instructions_list[i] if i < len(instructions_list) else ''
                                    )
                                    total_prescription_value += medication_obj.price * Decimal(quantity_val)
                                    items_created_count += 1
                                except Medication.DoesNotExist:
                                    messages.error(request, f"[create_prescription:FormPOST] Medication with ID {med_id} not found. Skipping item.")
                                except ValueError:
                                    messages.error(request, f"[create_prescription:FormPOST] Invalid quantity '{qty_str}' for medication ID {med_id}. Skipping item.")
                    
                    messages.info(request, f"[create_prescription:FormPOST] Items processed. Count: {items_created_count}, Total Value: {total_prescription_value}")

                    # --- REMOVE invoice generation from here ---
                    if items_created_count > 0 and total_prescription_value > Decimal('0.00'):
                        messages.success(request, f'Prescription for {prescription.patient.get_full_name()} created.')
                        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                    elif items_created_count > 0:
                        messages.success(request, f'Prescription for {prescription.patient.get_full_name()} created (no billable items/zero value).')
                        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                    else:
                        messages.success(request, f'Prescription for {prescription.patient.get_full_name()} created. Please add items to it if intended, as none were processed from the form submission.')
                        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

            except Service.DoesNotExist: 
                messages.error(request, "[create_prescription:FormPOST] Invoice creation failed: 'Medication Dispensing' service not found. Prescription may have been saved.")
                if prescription and prescription.pk:
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            except Exception as e:
                messages.error(request, f'[create_prescription:FormPOST] An unexpected error occurred: {str(e)}')
                if prescription and prescription.pk:
                     return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        else: 
            messages.error(request, f"[create_prescription:FormPOST] PrescriptionForm is invalid. Errors: {form.errors.as_json()}")
            
    if not form: 
        patient_id = request.GET.get('patient_id') or request.GET.get('patient')
        initial_data = {
            'doctor': request.user,
            'prescription_date': timezone.now().date()
        }
        if patient_id:
            initial_data['patient'] = patient_id
        form = PrescriptionForm(initial=initial_data, request=request)
        # Ensure all patients are available in the patient field
        form.fields['patient'].queryset = Patient.objects.all()
        messages.info(request, "[create_prescription:GET] Prepared new PrescriptionForm for GET request.")

    # Also ensure this for POST (form-based)
    if form:
        form.fields['patient'].queryset = Patient.objects.all()

    context = {
        'form': form,
        'title': 'Create New Prescription',
    }
    # Add selected_patient to context if available
    patient_obj = None
    if form.initial.get('patient'):
        try:
            patient_obj = Patient.objects.get(pk=form.initial['patient'])
        except Exception:
            pass
    elif request.GET.get('patient'):
        try:
            patient_obj = Patient.objects.get(pk=request.GET['patient'])
        except Exception:
            pass
    if patient_obj:
        context['selected_patient'] = patient_obj
    return render(request, 'pharmacy/prescription_form.html', context)

@login_required
def prescription_detail(request, prescription_id):
    """View for displaying prescription details and handling item additions/invoice logic."""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    item_form = PrescriptionItemForm() 

    if request.method == 'POST' and 'add_item' in request.POST:
        item_form = PrescriptionItemForm(request.POST) 
        if item_form.is_valid():
            item = item_form.save(commit=False)
            item.prescription = prescription
            item.save()
            messages.success(request, f'{item.medication.name} added to prescription.')
            # Invoice logic removed: Invoice is now only generated after dispensing
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        else:
            messages.error(request, "Failed to add medication. Please check the form details.")

    prescription_items = prescription.items.all()
    # Fetch latest invoice for this prescription (if any)
    latest_invoice = (
        Invoice.objects.filter(prescription=prescription)
        .order_by('-created_at')
        .first()
    )

    # Advanced: Fetch audit logs related to this prescription
    from core.models import AuditLog, InternalNotification
    audit_logs = AuditLog.objects.filter(
        details__icontains=str(prescription.id)
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains=str(prescription.id),
        is_read=False
    ).order_by('-created_at')[:10]

    # Advanced: Analytics (e.g., item count, total value, status by role)
    from django.db.models import Count, Sum
    analytics = {
        'item_count': prescription_items.count(),
        'total_value': prescription_items.aggregate(
            total=Sum('medication__price')
        )['total'] or 0,
        'actions_by_role': AuditLog.objects.filter(
            details__icontains=str(prescription.id)
        ).values('user__profile__role').annotate(count=Count('id')).order_by('-count')
    }

    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'item_form': item_form, 
        'latest_invoice': latest_invoice,  # Pass to template
        # Advanced features:
        'audit_logs': audit_logs,
        'user_notifications': user_notifications,
        'analytics': analytics,
    }
    return render(request, 'pharmacy/prescription_detail.html', context)

@login_required
def print_prescription(request, prescription_id):
    """View for printing a prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    prescription_items = prescription.items.all()

    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'hospital_name': 'Hospital Management System',
        'hospital_address': '123 Medical Center Drive, City, Country',
        'hospital_contact': 'Phone: (123) 456-7890 | Email: info@hospital.com',
    }

    return render(request, 'pharmacy/print_prescription.html', context)

@login_required
def delete_prescription_item(request, item_id):
    """View for deleting a prescription item and updating/deleting its invoice."""
    item = get_object_or_404(PrescriptionItem, id=item_id)
    prescription = item.prescription

    if request.method == 'POST':
        if item.is_dispensed:
            messages.error(request, f'Cannot delete {item.medication.name} because it has already been dispensed.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

        item_name = item.medication.name
        item.delete()
        messages.success(request, f'{item_name} has been removed from prescription.')
        
        current_total_value = Decimal('0.00')
        for pres_item in prescription.items.all():
            if pres_item.medication and hasattr(pres_item.medication, 'price') and pres_item.quantity:
                try:
                    item_price = pres_item.medication.price if pres_item.medication.price is not None else Decimal('0.00')
                    item_quantity = Decimal(str(pres_item.quantity)) if pres_item.quantity is not None else Decimal('0')
                    current_total_value += item_price * item_quantity
                except (TypeError, InvalidOperation) as e:
                    messages.warning(request, f"[delete_prescription_item] Could not calculate price for {pres_item.medication.name}. Error: {e}.")
        
        messages.info(request, f"[delete_prescription_item] Calculated current_total_value after delete: {current_total_value} for PID: {prescription.id}")
        pending_invoice = Invoice.objects.filter(prescription=prescription, status='pending').first()

        if pending_invoice:
            if current_total_value > Decimal('0.00'):
                messages.info(request, f"[delete_prescription_item] Updating existing pending Invoice ID: {pending_invoice.id}.")
                pending_invoice.subtotal = current_total_value
                pharmacy_service = None
                tax_percentage_for_item = Decimal('0.00')
                try:
                    pharmacy_service = Service.objects.get(name__iexact="Medication Dispensing")
                    if pharmacy_service.tax_percentage is not None:
                        tax_percentage_for_item = pharmacy_service.tax_percentage
                except Service.DoesNotExist:
                    messages.error(request, "Cannot update invoice tax: 'Medication Dispensing' service not found.")
                
                pending_invoice.tax_amount = (current_total_value * tax_percentage_for_item) / Decimal('100.00')
                pending_invoice.tax_amount = pending_invoice.tax_amount.quantize(Decimal('0.01'))
                try:
                    pending_invoice.save()
                    summary_invoice_item = pending_invoice.items.filter(service=pharmacy_service).first() if pharmacy_service else pending_invoice.items.first()
                    if summary_invoice_item:
                        summary_invoice_item.unit_price = current_total_value
                        summary_invoice_item.tax_percentage = tax_percentage_for_item
                        summary_invoice_item.save()
                        messages.info(request, f"Updated summary InvoiceItem ID: {summary_invoice_item.id} after item deletion.")
                    else: # Should ideally not happen if invoice was created by _create_pharmacy_invoice
                        messages.warning(request, f"Summary invoice item not found for Invoice ID: {pending_invoice.id} after deletion. Creating new one.")
                        if pharmacy_service:
                            InvoiceItem.objects.create(
                                invoice=pending_invoice,
                                service=pharmacy_service,
                                description=f"Medications for Prescription #{prescription.id} (Total Prescribed Value)",
                                quantity=1,
                                unit_price=current_total_value,
                                tax_percentage=tax_percentage_for_item,
                            )
                            pending_invoice.save() # Recalculate totals
                            messages.info(request, "Created new summary invoice item as it was missing.")
                        else:
                            messages.error(request, "Cannot create summary invoice item: 'Medication Dispensing' service not found.")

                    messages.success(request, f"Invoice #{pending_invoice.invoice_number} updated after item deletion.")
                except Exception as e:
                    messages.error(request, f"Error updating invoice after item deletion: {str(e)}")
            else:
                messages.info(request, f"[delete_prescription_item] Prescription total is zero after delete. Deleting Invoice ID: {pending_invoice.id}.")
                try:
                    pending_invoice.delete()
                    messages.success(request, "Invoice deleted as prescription total became zero.")
                except Exception as e:
                    messages.error(request, f"Error deleting invoice after item deletion: {str(e)}")
        elif current_total_value > Decimal('0.00'):
             messages.warning(request, "[delete_prescription_item] No pending invoice found to update, but prescription has value. This might be an inconsistent state.")

        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # For GET request to confirm deletion
    context = {
        'item': item,
        'prescription': prescription
    }
    return render(request, 'pharmacy/delete_prescription_item.html', context)

@login_required
def update_prescription_status(request, prescription_id):
    # ...existing code...
    prescription = get_object_or_404(Prescription, id=prescription_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Prescription.STATUS_CHOICES):
            prescription.status = status
            prescription.save()
            messages.success(request, f'Prescription status updated to {prescription.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status.')

        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

@login_required
def dispense_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    messages.info(request, f"[dispense_prescription] Called for Prescription ID: {prescription.id}, Payment Status: {prescription.payment_status}")

    # Show warning if unpaid, but do not block dispensing
    related_invoice = Invoice.objects.filter(prescription=prescription).order_by('-created_at').first()
    if related_invoice and related_invoice.status != 'paid':
        messages.warning(request, f"[dispense_prescription] Payment for Invoice #{related_invoice.invoice_number} is not complete. Dispensing is allowed, but payment is still pending.")
    elif not related_invoice:
        messages.info(request, "[dispense_prescription] No invoice found for this prescription. Dispensing is allowed.")
    else:
        messages.info(request, "[dispense_prescription] Payment confirmed as 'paid' or status is not blocking. Proceeding with dispensing logic.")

    undispensed_items_qs = prescription.items.filter(is_dispensed=False).order_by('id')
    eligible_items_for_formset = [
        item for item in undispensed_items_qs
        if item.remaining_quantity_to_dispense > 0 and item.medication.stock_quantity > 0
    ]
    messages.info(request, f"[dispense_prescription] Found {len(eligible_items_for_formset)} eligible items for dispensing formset.")

    if not eligible_items_for_formset and prescription.items.filter(is_dispensed=True).exists() and not prescription.items.filter(is_dispensed=False).exists():
        messages.info(request, '[dispense_prescription] All medications already fully dispensed.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    elif not eligible_items_for_formset:
        messages.info(request, '[dispense_prescription] No items currently eligible for dispensing.')

    DispenseItemFormSet = formset_factory(DispenseItemForm, formset=BaseDispenseItemFormSet, extra=0)
    formset_instance = None 

    if request.method == 'POST' and 'form-TOTAL_FORMS' in request.POST:
        messages.info(request, "[dispense_prescription] Handling POST request for dispensing items.")
        formset_instance = DispenseItemFormSet(request.POST, prescription_items_qs=eligible_items_for_formset)

        if formset_instance.is_valid():
            messages.info(request, "[dispense_prescription] Dispense formset is valid.")
            try:
                with transaction.atomic():
                    total_dispensed_value_this_transaction = Decimal('0.00')
                    items_dispensed_count_this_transaction = 0

                    for i, form_item in enumerate(formset_instance):
                        if form_item.cleaned_data.get('dispense_this_item'):
                            quantity_to_dispense = form_item.cleaned_data.get('quantity_to_dispense')
                            if i < len(eligible_items_for_formset):
                                prescription_item = eligible_items_for_formset[i]
                            else:
                                messages.error(request, "[dispense_prescription] Error matching form to prescription item during POST. Aborting dispense.")
                                raise IndexError("Formset item out of bounds with eligible items")

                            if quantity_to_dispense > 0:
                                if prescription_item.medication.stock_quantity < quantity_to_dispense:
                                    messages.error(request, f"[dispense_prescription] Insufficient stock for {prescription_item.medication.name}. Available: {prescription_item.medication.stock_quantity}, Requested: {quantity_to_dispense}. Skipping item.")
                                    continue 
                                messages.info(request, f"[dispense_prescription] Dispensing {quantity_to_dispense} of {prescription_item.medication.name}")
                                DispensingLog.objects.create(
                                    prescription_item=prescription_item,
                                    dispensed_by=request.user,
                                    dispensed_quantity=quantity_to_dispense,
                                    unit_price_at_dispense=prescription_item.medication.price,
                                )
                                medication = prescription_item.medication
                                medication.stock_quantity -= quantity_to_dispense
                                medication.save()

                                prescription_item.quantity_dispensed_so_far += quantity_to_dispense
                                prescription_item.dispensed_by = request.user
                                prescription_item.dispensed_date = timezone.now()
                                if prescription_item.quantity_dispensed_so_far >= prescription_item.quantity:
                                    prescription_item.is_dispensed = True
                                prescription_item.save()
                                
                                total_dispensed_value_this_transaction += prescription_item.medication.price * Decimal(str(quantity_to_dispense))
                                items_dispensed_count_this_transaction += 1
                                messages.success(request, f"Dispensed {quantity_to_dispense} of {medication.name}.")
                    # Invoice generation and MCP integration
                    if items_dispensed_count_this_transaction > 0:
                        if not Invoice.objects.filter(prescription=prescription).exists():
                            invoice = _create_pharmacy_invoice(request, prescription, prescription.get_total_prescribed_price())
                            send_billing_task_to_office_mcp(request, prescription, invoice)
                        messages.info(request, f"[dispense_prescription] Total value dispensed in this transaction: {total_dispensed_value_this_transaction:.2f}.")
                    all_items_dispensed = not prescription.items.filter(is_dispensed=False).exists()
                    if all_items_dispensed:
                        prescription.status = 'dispensed'
                        messages.success(request, '[dispense_prescription] All medications for this prescription are now fully dispensed.')
                    elif items_dispensed_count_this_transaction > 0 :
                        prescription.status = 'partially_dispensed'
                        messages.info(request, '[dispense_prescription] Prescription is now partially dispensed.')
                    if items_dispensed_count_this_transaction > 0 or all_items_dispensed:
                        prescription.save()
                        messages.info(request, f"[dispense_prescription] Prescription ID {prescription.id} status updated to {prescription.status}.")
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
            except IndexError as e:
                messages.error(request, f"[dispense_prescription] Error processing dispense items (IndexError): {str(e)}.")
            except Exception as e:
                messages.error(request, f"[dispense_prescription] Unexpected error during dispensing transaction: {e}")
        else: 
            messages.error(request, f"[dispense_prescription] Dispense formset is invalid. Errors: {str(formset_instance.errors)}")

    if not formset_instance: 
        initial_data_for_formset = [{} for _ in eligible_items_for_formset]
        formset_instance = DispenseItemFormSet(
            initial=initial_data_for_formset,
            prescription_items_qs=eligible_items_for_formset
        )
        messages.info(request, "[dispense_prescription] Prepared new dispense formset for GET request or invalid POST.")

    context = {
        'prescription': prescription,
        'formset': formset_instance,
        'undispensed_items_list': eligible_items_for_formset, 
        'title': f'Dispense Prescription #{prescription.id} (Payment: {prescription.get_payment_status_display()})'
    }
    return render(request, 'pharmacy/dispense_prescription.html', context)

def send_billing_task_to_office_mcp(request, prescription, invoice):
    """
    Send a billing task to the billing office using context7 MCP and Taskmaster.
    Replace this with actual MCP/Taskmaster API integration as needed.
    """
    # Simulate MCP/Taskmaster API call
    # Example payload
    payload = {
        "task_type": "pharmacy_billing",
        "prescription_id": prescription.id,
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "patient_id": prescription.patient.id,
        "patient_name": prescription.patient.get_full_name(),
        "total_amount": str(invoice.total_amount),
        "created_by": invoice.created_by.username if invoice.created_by else None,
        "created_at": str(invoice.created_at),
        "status": invoice.status,
        "source": "pharmacy",
    }
    # Here you would call the real MCP/Taskmaster API, e.g.:
    # response = context7_mcp.send_task('billing', payload)
    # Or: response = taskmaster.create_task(payload)
    # For now, just log the payload for demonstration
    import logging
    logger = logging.getLogger("pharmacy.mcp")
    logger.info(f"[MCP/Taskmaster] Billing task payload: {payload}")
    from django.contrib import messages
    messages.info(request, f"[Taskmaster/MCP] Billing task sent for Prescription #{prescription.id}, Invoice #{invoice.invoice_number} via MCP/Taskmaster.")

@login_required
def medication_api(request):
    # ...existing code...
    search_term = request.GET.get('term', '')

    if len(search_term) < 2:
        return JsonResponse([], safe=False)

    medications = Medication.objects.filter(
        Q(name__icontains=search_term) |
        Q(generic_name__icontains=search_term)
    ).filter(is_active=True, stock_quantity__gt=0)[:10]

    results = [{
        'id': med.id,
        'text': f"{med.name} ({med.strength}) - {med.dosage_form}",
        'name': med.name,
        'generic_name': med.generic_name,
        'dosage_form': med.dosage_form,
        'strength': med.strength,
        'stock_quantity': med.stock_quantity,
        'price': float(med.price)
    } for med in medications]

    return JsonResponse(results, safe=False)

@login_required
def expiring_medications_report(request):
    # ...existing code...
    warning_days = int(request.GET.get('warning_days', 90))

    # Calculate the warning date
    today = timezone.now().date()
    warning_date = today + timezone.timedelta(days=warning_days)

    # Get medications that expire within the warning period
    expiring_medications = Medication.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=warning_date,
        is_active=True
    ).order_by('expiry_date')

    # Get already expired medications
    expired_medications = Medication.objects.filter(
        expiry_date__lt=today,
        is_active=True
    ).order_by('expiry_date')

    context = {
        'expiring_medications': expiring_medications,
        'expired_medications': expired_medications,
        'warning_days': warning_days,
        'today': today,
        'warning_date': warning_date,
        'title': 'Expiring Medications Report'
    }

    return render(request, 'pharmacy/expiring_medications_report.html', context)

@login_required
def low_stock_medications_report(request):
    # ...existing code...
    low_stock_medications = Medication.objects.filter(
        stock_quantity__lte=F('reorder_level'),
        stock_quantity__gt=0,
        is_active=True
    ).order_by('stock_quantity')

    # Get out of stock medications
    out_of_stock_medications = Medication.objects.filter(
        stock_quantity=0,
        is_active=True
    ).order_by('name')

    context = {
        'low_stock_medications': low_stock_medications,
        'out_of_stock_medications': out_of_stock_medications,
        'title': 'Low Stock Medications Report'
    }

    return render(request, 'pharmacy/low_stock_medications_report.html', context)

@login_required
def prescription_dispensing_history(request, prescription_id):
    """View for displaying the dispensing history of a specific prescription."""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Get all dispensing logs related to this prescription, ordered by date
    dispensing_logs = DispensingLog.objects.filter(prescription_item__prescription=prescription).order_by('-dispensed_date')

    context = {
        'prescription': prescription,
        'dispensing_logs': dispensing_logs,
        'title': f'Dispensing History for Prescription #{prescription.id}'
    }
    return render(request, 'pharmacy/dispensing_history.html', context)

def check_and_notify_low_stock_and_expiry():
    from .models import Medication
    today = timezone.now().date()
    low_stock_meds = Medication.objects.filter(stock_quantity__lte=F('reorder_level'), is_active=True)
    expired_meds = Medication.objects.filter(expiry_date__lt=today, is_active=True)
    notified_users = User.objects.filter(is_active=True, is_staff=True)
    for med in low_stock_meds:
        for user in notified_users:
            InternalNotification.objects.get_or_create(
                user=user,
                message=f"Low stock alert: {med.name} (Current: {med.stock_quantity}, Reorder Level: {med.reorder_level})"
            )
            send_notification_email(
                subject="Low Stock Alert",
                message=f"Medication {med.name} is low in stock (Current: {med.stock_quantity}, Reorder Level: {med.reorder_level}).",
                recipient_list=[user.email]
            )
    for med in expired_meds:
        for user in notified_users:
            InternalNotification.objects.get_or_create(
                user=user,
                message=f"Expiry alert: {med.name} expired on {med.expiry_date}"
            )
            send_notification_email(
                subject="Medication Expiry Alert",
                message=f"Medication {med.name} expired on {med.expiry_date}.",
                recipient_list=[user.email]
            )

@login_required
def approve_purchase(request, purchase_id):
    from .models import Purchase
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if request.method == 'POST':
        purchase.payment_status = 'paid'
        purchase.save()
        # Notify supplier (if email exists)
        if purchase.supplier.email:
            send_notification_email(
                subject="Purchase Approved",
                message=f"Your purchase order {purchase.invoice_number} has been approved and paid.",
                recipient_list=[purchase.supplier.email]
            )
        messages.success(request, f"Purchase {purchase.invoice_number} approved and supplier notified.")
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    context = {'purchase': purchase}
    return render(request, 'pharmacy/approve_purchase.html', context)

@login_required
def notify_prescription_dispensed(request, prescription_id):
    from .models import Prescription
    prescription = get_object_or_404(Prescription, id=prescription_id)
    # Notify doctor and patient
    if prescription.doctor:
        InternalNotification.objects.create(
            user=prescription.doctor,
            message=f"Prescription for {prescription.patient.get_full_name()} has been dispensed."
        )
        send_notification_email(
            subject="Prescription Dispensed",
            message=f"Prescription for {prescription.patient.get_full_name()} has been dispensed.",
            recipient_list=[prescription.doctor.email]
        )
    if hasattr(prescription.patient, 'user') and getattr(prescription.patient.user, 'email', None):
        InternalNotification.objects.create(
            user=prescription.patient.user,
            message=f"Your prescription has been dispensed."
        )
        send_notification_email(
            subject="Your Prescription is Ready",
            message=f"Your prescription has been dispensed.",
            recipient_list=[prescription.patient.user.email]
        )
    messages.success(request, "Dispensing notifications sent.")
    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

@login_required
def submit_purchase_for_approval(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if purchase.approval_status != 'draft':
        messages.warning(request, 'Purchase is already submitted or processed.')
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    # Example: Define approval chain (could be dynamic)
    approval_chain = [user for user in User.objects.filter(groups__name='PharmacyManager').order_by('id')]
    if not approval_chain:
        messages.error(request, 'No approvers defined for this workflow.')
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    # Create approval steps
    for idx, approver in enumerate(approval_chain, start=1):
        PurchaseApproval.objects.get_or_create(
            purchase=purchase,
            approver=approver,
            step_order=idx
        )
    purchase.approval_status = 'pending'
    purchase.current_approver = approval_chain[0]
    purchase.approval_updated_at = timezone.now()
    purchase.save()
    messages.success(request, 'Purchase submitted for approval.')
    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

@login_required
def approve_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if purchase.approval_status != 'pending' or request.user != purchase.current_approver:
        messages.error(request, 'You are not authorized to approve this purchase.')
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    approval = PurchaseApproval.objects.filter(purchase=purchase, approver=request.user, status='pending').first()
    if approval:
        approval.status = 'approved'
        approval.comments = request.POST.get('comments', '')
        approval.decided_at = timezone.now()
        approval.save()
    # Advance to next approver or mark as approved
    next_approval = PurchaseApproval.objects.filter(purchase=purchase, status='pending').order_by('step_order').first()
    if next_approval:
        purchase.current_approver = next_approval.approver
    else:
        purchase.approval_status = 'approved'
        purchase.current_approver = None
    purchase.approval_updated_at = timezone.now()
    purchase.save()
    messages.success(request, 'Purchase approved.')
    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

@login_required
def reject_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if purchase.approval_status != 'pending' or request.user != purchase.current_approver:
        messages.error(request, 'You are not authorized to reject this purchase.')
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    approval = PurchaseApproval.objects.filter(purchase=purchase, approver=request.user, status='pending').first()
    if approval:
        approval.status = 'rejected'
        approval.comments = request.POST.get('comments', '')
        approval.decided_at = timezone.now()
        approval.save()
    purchase.approval_status = 'rejected'
    purchase.current_approver = None
    purchase.approval_updated_at = timezone.now()
    purchase.save()
    messages.success(request, 'Purchase rejected.')
    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

@login_required
# Add @receptionist_required or @pharmacist_required if available

def dispensing_report(request):
    """Pharmacy dispensing report with filters and CSV export."""
    from .models import DispensingLog, PrescriptionItem
    dispensing_logs = DispensingLog.objects.select_related(
        'prescription_item__prescription', 'prescription_item__medication', 'dispensed_by'
    )

    # Filters
    patient = request.GET.get('patient')
    doctor = request.GET.get('doctor')
    medication = request.GET.get('medication')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if patient:
        dispensing_logs = dispensing_logs.filter(prescription_item__prescription__patient__id=patient)
    if doctor:
        dispensing_logs = dispensing_logs.filter(prescription_item__prescription__doctor__id=doctor)
    if medication:
        dispensing_logs = dispensing_logs.filter(prescription_item__medication__id=medication)
    if status:
        if status == 'dispensed':
            dispensing_logs = dispensing_logs.filter(prescription_item__is_dispensed=True)
        elif status == 'pending':
            dispensing_logs = dispensing_logs.filter(prescription_item__is_dispensed=False)
    if date_from:
        dispensing_logs = dispensing_logs.filter(dispensed_date__date__gte=date_from)
    if date_to:
        dispensing_logs = dispensing_logs.filter(dispensed_date__date__lte=date_to)

    # CSV export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dispensing_report.csv"'
        import csv
        writer = csv.writer(response)
        writer.writerow(['Date', 'Patient', 'Doctor', 'Medication', 'Quantity', 'Dispensed By', 'Status'])
        for log in dispensing_logs:
            writer.writerow([
                log.dispensed_date.strftime('%Y-%m-%d %H:%M'),
                log.prescription_item.prescription.patient.get_full_name(),
                log.prescription_item.prescription.doctor.get_full_name(),
                log.prescription_item.medication.name,
                log.dispensed_quantity,
                log.dispensed_by.get_full_name() if log.dispensed_by else '',
                'Dispensed' if log.prescription_item.is_dispensed else 'Pending',
            ])
        return response

    # Pagination
    paginator = Paginator(dispensing_logs.order_by('-dispensed_date'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filters': {
            'patient': patient,
            'doctor': doctor,
            'medication': medication,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        },
        'page_title': 'Pharmacy Dispensing Report',
        'active_nav': 'pharmacy_report',
    }
    return render(request, 'pharmacy/dispensing_report.html', context)

@login_required
def create_procurement_order(request):
    """Stub for creating a procurement order for medications/supplies"""
    # TODO: Add form for selecting items, quantities, and supplier
    context = {
        'title': 'Create Procurement Order',
        'message': 'Procurement order creation form goes here.'
    }
    return render(request, 'pharmacy/procurement_order_stub.html', context)

@login_required
def confirm_procurement_delivery(request, order_id):
    """Stub for confirming delivery of a procurement order"""
    # TODO: Integrate with inventory update logic
    context = {
        'order_id': order_id,
        'title': 'Confirm Procurement Delivery',
        'message': 'Procurement delivery confirmation logic goes here.'
    }
    return render(request, 'pharmacy/procurement_delivery_stub.html', context)

@login_required
def procurement_status_list(request):
    """Stub for listing procurement orders and their statuses"""
    # TODO: Integrate with procurement order model and supplier info
    context = {
        'title': 'Procurement Orders',
        'orders': [],  # Placeholder for procurement order list
        'message': 'Procurement order status list goes here.'
    }
    return render(request, 'pharmacy/procurement_status_stub.html', context)

@login_required
def pharmacy_sales_report(request):
    """View for daily sales by user and total monthly sales from pharmacy."""
    from pharmacy.models import DispensingLog
    from django.db.models import Sum, F
    from django.utils import timezone
    from django.contrib.auth.models import User

    today = timezone.now().date()
    month_start = today.replace(day=1)
    # Find the last day of the month
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month - timezone.timedelta(days=1)

    # Use dispensed_date instead of date
    daily_sales = (
        DispensingLog.objects.filter(dispensed_date=today)
        .values('dispensed_by__id', 'dispensed_by__first_name', 'dispensed_by__last_name')
        .annotate(total_sales=Sum('total_price_for_this_log'))
        .order_by('-total_sales')
    )

    monthly_sales = (
        DispensingLog.objects.filter(dispensed_date__gte=month_start, dispensed_date__lte=month_end)
        .aggregate(total=Sum('total_price_for_this_log'))['total'] or 0
    )

    context = {
        'daily_sales': daily_sales,
        'monthly_sales': monthly_sales,
        'today': today,
        'month_start': month_start,
        'month_end': month_end,
        'title': 'Pharmacy Sales Report',
    }
    return render(request, 'pharmacy/sales_report.html', context)


# ============================================================================
# DISPENSED ITEMS TRACKING VIEWS
# ============================================================================

@login_required
def dispensed_items_tracker(request):
    """
    Main view for tracking dispensed items with advanced search capabilities.
    Allows searching by medication name (first few letters), date range, and other filters.
    """
    search_form = DispensedItemsSearchForm(request.GET or None)

    # Base queryset with optimized joins
    dispensing_logs = DispensingLog.objects.select_related(
        'prescription_item__medication__category',
        'prescription_item__prescription__patient',
        'prescription_item__prescription__doctor',
        'dispensed_by'
    ).order_by('-dispensed_date')

    # Apply search filters
    if search_form.is_valid():
        medication_name = search_form.cleaned_data.get('medication_name')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        patient_name = search_form.cleaned_data.get('patient_name')
        dispensed_by = search_form.cleaned_data.get('dispensed_by')
        category = search_form.cleaned_data.get('category')
        min_quantity = search_form.cleaned_data.get('min_quantity')
        max_quantity = search_form.cleaned_data.get('max_quantity')
        prescription_type = search_form.cleaned_data.get('prescription_type')

        # Search by medication name (supports partial matching from first letters)
        if medication_name:
            dispensing_logs = dispensing_logs.filter(
                Q(prescription_item__medication__name__istartswith=medication_name) |
                Q(prescription_item__medication__generic_name__istartswith=medication_name)
            )

        # Date range filter
        if date_from:
            dispensing_logs = dispensing_logs.filter(dispensed_date__date__gte=date_from)
        if date_to:
            dispensing_logs = dispensing_logs.filter(dispensed_date__date__lte=date_to)

        # Patient name filter
        if patient_name:
            dispensing_logs = dispensing_logs.filter(
                Q(prescription_item__prescription__patient__first_name__icontains=patient_name) |
                Q(prescription_item__prescription__patient__last_name__icontains=patient_name)
            )

        # Staff filter
        if dispensed_by:
            dispensing_logs = dispensing_logs.filter(dispensed_by=dispensed_by)

        # Category filter
        if category:
            dispensing_logs = dispensing_logs.filter(
                prescription_item__medication__category=category
            )

        # Quantity range filters
        if min_quantity:
            dispensing_logs = dispensing_logs.filter(dispensed_quantity__gte=min_quantity)
        if max_quantity:
            dispensing_logs = dispensing_logs.filter(dispensed_quantity__lte=max_quantity)

        # Prescription type filter
        if prescription_type:
            dispensing_logs = dispensing_logs.filter(
                prescription_item__prescription__prescription_type=prescription_type
            )

    # Calculate summary statistics
    total_logs = dispensing_logs.count()
    total_quantity_dispensed = dispensing_logs.aggregate(
        total=Sum('dispensed_quantity')
    )['total'] or 0
    total_value_dispensed = dispensing_logs.aggregate(
        total=Sum('total_price_for_this_log')
    )['total'] or 0

    # Get unique medications dispensed count
    unique_medications = dispensing_logs.values(
        'prescription_item__medication'
    ).distinct().count()

    # Get top dispensed medications
    top_medications = dispensing_logs.values(
        'prescription_item__medication__name'
    ).annotate(
        total_quantity=Sum('dispensed_quantity'),
        total_value=Sum('total_price_for_this_log'),
        dispense_count=Count('id')
    ).order_by('-total_quantity')[:10]

    # Pagination
    paginator = Paginator(dispensing_logs, 25)  # Show 25 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'search_form': search_form,
        'page_obj': page_obj,
        'total_logs': total_logs,
        'total_quantity_dispensed': total_quantity_dispensed,
        'total_value_dispensed': total_value_dispensed,
        'unique_medications': unique_medications,
        'top_medications': top_medications,
        'title': 'Dispensed Items Tracker'
    }

    return render(request, 'pharmacy/dispensed_items_tracker.html', context)


@login_required
def dispensed_item_detail(request, log_id):
    """
    Detailed view for a specific dispensing log entry.
    Shows complete information about the dispensed item.
    """
    dispensing_log = get_object_or_404(
        DispensingLog.objects.select_related(
            'prescription_item__medication__category',
            'prescription_item__prescription__patient',
            'prescription_item__prescription__doctor',
            'dispensed_by'
        ),
        id=log_id
    )

    # Get related dispensing logs for the same prescription item
    related_logs = DispensingLog.objects.filter(
        prescription_item=dispensing_log.prescription_item
    ).exclude(id=log_id).order_by('-dispensed_date')

    # Get prescription details
    prescription = dispensing_log.prescription_item.prescription

    context = {
        'dispensing_log': dispensing_log,
        'related_logs': related_logs,
        'prescription': prescription,
        'title': f'Dispensing Log #{dispensing_log.id}'
    }

    return render(request, 'pharmacy/dispensed_item_detail.html', context)


@login_required
def medication_autocomplete(request):
    """
    AJAX endpoint for medication name autocomplete.
    Returns JSON list of medications matching the search term.
    """
    term = request.GET.get('term', '').strip()

    if len(term) < 2:  # Require at least 2 characters
        return JsonResponse([], safe=False)

    # Search medications by name or generic name (case-insensitive, starts with)
    medications = Medication.objects.filter(
        Q(name__istartswith=term) | Q(generic_name__istartswith=term),
        is_active=True
    ).values('name', 'generic_name').distinct()[:10]

    # Format results for autocomplete
    results = []
    for med in medications:
        # Add both name and generic name if different
        if med['name']:
            results.append({
                'label': med['name'],
                'value': med['name']
            })
        if med['generic_name'] and med['generic_name'] != med['name']:
            results.append({
                'label': f"{med['generic_name']} (Generic)",
                'value': med['generic_name']
            })

    # Remove duplicates while preserving order
    seen = set()
    unique_results = []
    for item in results:
        if item['value'] not in seen:
            seen.add(item['value'])
            unique_results.append(item)

    return JsonResponse(unique_results[:10], safe=False)


@login_required
def dispensed_items_export(request):
    """
    Export dispensed items data to CSV format.
    Applies the same filters as the main tracker view.
    """
    search_form = DispensedItemsSearchForm(request.GET or None)

    # Base queryset with optimized joins
    dispensing_logs = DispensingLog.objects.select_related(
        'prescription_item__medication__category',
        'prescription_item__prescription__patient',
        'prescription_item__prescription__doctor',
        'dispensed_by'
    ).order_by('-dispensed_date')

    # Apply the same filters as the main view
    if search_form.is_valid():
        medication_name = search_form.cleaned_data.get('medication_name')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        patient_name = search_form.cleaned_data.get('patient_name')
        dispensed_by = search_form.cleaned_data.get('dispensed_by')
        category = search_form.cleaned_data.get('category')
        min_quantity = search_form.cleaned_data.get('min_quantity')
        max_quantity = search_form.cleaned_data.get('max_quantity')
        prescription_type = search_form.cleaned_data.get('prescription_type')

        if medication_name:
            dispensing_logs = dispensing_logs.filter(
                Q(prescription_item__medication__name__istartswith=medication_name) |
                Q(prescription_item__medication__generic_name__istartswith=medication_name)
            )
        if date_from:
            dispensing_logs = dispensing_logs.filter(dispensed_date__date__gte=date_from)
        if date_to:
            dispensing_logs = dispensing_logs.filter(dispensed_date__date__lte=date_to)
        if patient_name:
            dispensing_logs = dispensing_logs.filter(
                Q(prescription_item__prescription__patient__first_name__icontains=patient_name) |
                Q(prescription_item__prescription__patient__last_name__icontains=patient_name)
            )
        if dispensed_by:
            dispensing_logs = dispensing_logs.filter(dispensed_by=dispensed_by)
        if category:
            dispensing_logs = dispensing_logs.filter(
                prescription_item__medication__category=category
            )
        if min_quantity:
            dispensing_logs = dispensing_logs.filter(dispensed_quantity__gte=min_quantity)
        if max_quantity:
            dispensing_logs = dispensing_logs.filter(dispensed_quantity__lte=max_quantity)
        if prescription_type:
            dispensing_logs = dispensing_logs.filter(
                prescription_item__prescription__prescription_type=prescription_type
            )

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dispensed_items_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    import csv
    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Date & Time',
        'Medication Name',
        'Generic Name',
        'Category',
        'Quantity Dispensed',
        'Unit Price',
        'Total Price',
        'Patient Name',
        'Patient ID',
        'Doctor',
        'Dispensed By',
        'Prescription Type',
        'Prescription ID'
    ])

    # Write data rows
    for log in dispensing_logs:
        writer.writerow([
            log.dispensed_date.strftime('%Y-%m-%d %H:%M:%S'),
            log.prescription_item.medication.name,
            log.prescription_item.medication.generic_name or '',
            log.prescription_item.medication.category.name if log.prescription_item.medication.category else '',
            log.dispensed_quantity,
            f"{log.unit_price_at_dispense:.2f}",
            f"{log.total_price_for_this_log:.2f}",
            log.prescription_item.prescription.patient.get_full_name(),
            log.prescription_item.prescription.patient.patient_id,
            log.prescription_item.prescription.doctor.get_full_name(),
            log.dispensed_by.get_full_name() if log.dispensed_by else '',
            log.prescription_item.prescription.get_prescription_type_display(),
            log.prescription_item.prescription.id
        ])

    return response
