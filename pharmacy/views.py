
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, F
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import csv
from decimal import Decimal
from django.db import transaction

from .models import (
    MedicationCategory, Medication, Supplier, Purchase,
    PurchaseItem, Prescription, PrescriptionItem, DispensingLog, Dispensary, MedicationInventory
)
from .forms import (
    MedicationCategoryForm, MedicationForm, SupplierForm, PurchaseForm,
    PurchaseItemForm, PrescriptionForm, PrescriptionItemForm, DispenseItemForm, BaseDispenseItemFormSet,
    MedicationSearchForm, PrescriptionSearchForm, DispensedItemsSearchForm, DispensaryForm, MedicationInventoryForm
)
from billing.models import Service
from pharmacy_billing.models import Invoice, InvoiceItem

from django.contrib.auth import get_user_model
User = get_user_model()

from django.forms import formset_factory

import logging

# Configure logging to a file
logging.basicConfig(filename='debug_output.txt', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')







from patients.models import Patient # Import Patient model

@login_required
def create_prescription(request, patient_id=None):
    logging.debug("create_prescription view called.")
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)

    initial_data = {}
    if patient:
        initial_data['patient'] = patient

    if request.method == 'POST':
        prescription_form = PrescriptionForm(request.POST, request=request, initial=initial_data)
        logging.debug(f"Form is valid: {prescription_form.is_valid()}")
        if not prescription_form.is_valid():
            logging.error(f"Form errors: {prescription_form.errors}")
            messages.error(request, 'Failed to create prescription. Please correct the form errors.')
            context = {
                'prescription_form': prescription_form,
                'medications': Medication.objects.filter(is_active=True),
                'title': 'Create New Prescription',
                'patient': patient,
            }
            return render(request, 'pharmacy/create_prescription.html', context, status=400) # Bad Request
        
        try:
            with transaction.atomic():
                prescription = prescription_form.save(commit=False)
                prescription.created_by = request.user
                prescription.save()
                logging.debug(f"Prescription saved: {prescription.id}")

                total_prescription_price = Decimal('0.00')
                medication_ids = request.POST.getlist('medication[]')
                quantities = request.POST.getlist('quantity[]')
                dosages = request.POST.getlist('dosage[]')
                frequencies = request.POST.getlist('frequency[]')
                durations = request.POST.getlist('duration[]')
                instructions = request.POST.getlist('instructions[]')

                for i in range(len(medication_ids)):
                    medication = get_object_or_404(Medication, id=medication_ids[i])
                    quantity = int(quantities[i])
                    PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication=medication,
                        dosage=dosages[i],
                        frequency=frequencies[i],
                        duration=durations[i],
                        instructions=instructions[i],
                        quantity=quantity
                    )
                    total_prescription_price += medication.price * quantity
                logging.debug(f"Prescription items created. Total price: {total_prescription_price}")

                medication_dispensing_service = Service.objects.get(name__iexact="Medication Dispensing")
                
                invoice = Invoice.objects.create(
                    patient=prescription.patient,
                    invoice_date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    created_by=request.user,
                    subtotal=total_prescription_price,
                    total_amount=total_prescription_price,
                    status='pending',
                )

                InvoiceItem.objects.create(
                    invoice=invoice,
                    service=medication_dispensing_service,
                    description=f'Invoice for Prescription {prescription.id}',
                    quantity=1,
                    unit_price=total_prescription_price,
                )

                prescription.invoice = invoice
                prescription.save()
                logging.debug(f"Invoice created: {invoice.id}")

            messages.success(request, 'Prescription created successfully!')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        
        except Service.DoesNotExist:
            messages.error(request, "Critical error: 'Medication Dispensing' service not found. Prescription not created.")
            logging.error("Service.DoesNotExist exception caught.")
            context = {
                'prescription_form': prescription_form,
                'medications': Medication.objects.filter(is_active=True),
                'title': 'Create New Prescription',
                'patient': patient,
            }
            return render(request, 'pharmacy/create_prescription.html', context, status=400)
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {e}')
            logging.error(f"General exception caught: {e}")
            context = {
                'prescription_form': prescription_form,
                'medications': Medication.objects.filter(is_active=True),
                'title': 'Create New Prescription',
                'patient': patient,
            }
            return render(request, 'pharmacy/create_prescription.html', context, status=400)
    else:
        prescription_form = PrescriptionForm(request=request, initial=initial_data)

    context = {
        'prescription_form': prescription_form,
        'medications': Medication.objects.filter(is_active=True),
        'title': 'Create New Prescription',
        'patient': patient,
    }
    return render(request, 'pharmacy/create_prescription.html', context, status=200) # Always return 200 on re-render for errors

@login_required
def dispensed_items_tracker(request):
    form = DispensedItemsSearchForm(request.GET or None)
    logs_query = DispensingLog.objects.select_related(
        'prescription_item__prescription__patient',
        'prescription_item__medication__category',
        'dispensed_by__profile',
        'dispensary'
    ).all()

    if form.is_valid():
        data = form.cleaned_data
        if data.get('medication_name'):
            logs_query = logs_query.filter(prescription_item__medication__name__icontains=data['medication_name'])
        if data.get('date_from'):
            logs_query = logs_query.filter(dispensed_date__date__gte=data['date_from'])
        if data.get('date_to'):
            logs_query = logs_query.filter(dispensed_date__date__lte=data['date_to'])
        if data.get('patient_name'):
            logs_query = logs_query.filter(
                Q(prescription_item__prescription__patient__first_name__icontains=data['patient_name']) |
                Q(prescription_item__prescription__patient__last_name__icontains=data['patient_name'])
            )
        if data.get('dispensed_by'):
            logs_query = logs_query.filter(dispensed_by=data['dispensed_by'])
        if data.get('category'):
            logs_query = logs_query.filter(prescription_item__medication__category=data['category'])
        if data.get('min_quantity'):
            logs_query = logs_query.filter(dispensed_quantity__gte=data['min_quantity'])
        if data.get('max_quantity'):
            logs_query = logs_query.filter(dispensed_quantity__lte=data['max_quantity'])
        if data.get('prescription_type'):
            logs_query = logs_query.filter(prescription_item__prescription__prescription_type=data['prescription_type'])

    paginator = Paginator(logs_query, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    stats = {
        'today': logs_query.filter(dispensed_date__date=today).aggregate(
            total_items=Sum('dispensed_quantity'),
            total_value=Sum('total_price_for_this_log')
        ),
        'this_week': logs_query.filter(dispensed_date__date__gte=start_of_week).aggregate(
            total_items=Sum('dispensed_quantity'),
            total_value=Sum('total_price_for_this_log')
        ),
        'this_month': logs_query.filter(dispensed_date__date__gte=start_of_month).aggregate(
            total_items=Sum('dispensed_quantity'),
            total_value=Sum('total_price_for_this_log')
        )
    }

    context = {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
        'title': 'Dispensed Items Tracker'
    }
    return render(request, 'pharmacy/dispensed_items_tracker.html', context)

@login_required
def dispensed_item_detail(request, log_id):
    log_entry = get_object_or_404(
        DispensingLog.objects.select_related(
            'prescription_item__prescription__patient',
            'prescription_item__medication',
            'dispensed_by__profile',
            'dispensary'
        ),
        id=log_id
    )
    context = {
        'log_entry': log_entry,
        'title': 'Dispensed Item Detail'
    }
    return render(request, 'pharmacy/dispensed_item_detail.html', context)

@login_required
def dispensed_items_export(request):
    form = DispensedItemsSearchForm(request.GET or None)
    logs_query = DispensingLog.objects.select_related(
        'prescription_item__prescription__patient',
        'prescription_item__medication__category',
        'dispensed_by__profile',
        'dispensary'
    ).all()

    if form.is_valid():
        data = form.cleaned_data
        if data.get('medication_name'):
            logs_query = logs_query.filter(prescription_item__medication__name__icontains=data['medication_name'])
        if data.get('date_from'):
            logs_query = logs_query.filter(dispensed_date__date__gte=data['date_from'])
        if data.get('date_to'):
            logs_query = logs_query.filter(dispensed_date__date__lte=data['date_to'])
        if data.get('patient_name'):
            logs_query = logs_query.filter(
                Q(prescription_item__prescription__patient__first_name__icontains=data['patient_name']) |
                Q(prescription_item__prescription__patient__last_name__icontains=data['patient_name'])
            )
        if data.get('dispensed_by'):
            logs_query = logs_query.filter(dispensed_by=data['dispensed_by'])
        if data.get('category'):
            logs_query = logs_query.filter(prescription_item__medication__category=data['category'])
        if data.get('min_quantity'):
            logs_query = logs_query.filter(dispensed_quantity__gte=data['min_quantity'])
        if data.get('max_quantity'):
            logs_query = logs_query.filter(dispensed_quantity__lte=data['max_quantity'])
        if data.get('prescription_type'):
            logs_query = logs_query.filter(prescription_item__prescription__prescription_type=data['prescription_type'])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dispensed_items_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Log ID', 'Dispensed Date', 'Medication', 'Category', 'Dispensed Quantity',
        'Unit Price', 'Total Price', 'Patient', 'Prescription ID', 'Dispensed By', 'Dispensary'
    ])

    for log in logs_query:
        writer.writerow([
            log.id,
            log.dispensed_date.strftime('%Y-%m-%d %H:%M'),
            log.prescription_item.medication.name,
            log.prescription_item.medication.category.name if log.prescription_item.medication.category else 'N/A',
            log.dispensed_quantity,
            log.unit_price_at_dispense,
            log.total_price_for_this_log,
            log.prescription_item.prescription.patient.get_full_name(),
            log.prescription_item.prescription.id,
            log.dispensed_by.get_full_name() if log.dispensed_by else 'N/A',
            log.dispensary.name if log.dispensary else 'N/A'
        ])

    return response

@login_required
def medication_autocomplete(request):
    if 'term' in request.GET:
        query = request.GET.get('term')
        medications = Medication.objects.filter(name__icontains=query)[:10]
        results = [med.name for med in medications]
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

@login_required
def pharmacy_dashboard(request):
    context = {
        'title': 'Pharmacy Dashboard'
    }
    return render(request, 'pharmacy/pharmacy_dashboard.html', context)

@login_required
def add_dispensary(request):
    if request.method == 'POST':
        form = DispensaryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Dispensary added successfully!")
            return redirect('pharmacy:dispensary_list')
        else:
            messages.error(request, "Error adding dispensary. Please correct the form errors.")
    else:
        form = DispensaryForm()
    context = {
        'form': form,
        'title': 'Add New Dispensary'
    }
    return render(request, 'pharmacy/add_edit_dispensary.html', context)

@login_required
def dispensary_list(request):
    dispensaries = Dispensary.objects.all().order_by('name')
    context = {
        'dispensaries': dispensaries,
        'title': 'Dispensary List'
    }
    return render(request, 'pharmacy/dispensary_list.html', context)

@login_required
def edit_dispensary(request, dispensary_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    if request.method == 'POST':
        form = DispensaryForm(request.POST, instance=dispensary)
        if form.is_valid():
            form.save()
            messages.success(request, "Dispensary updated successfully!")
            return redirect('pharmacy:dispensary_list')
        else:
            messages.error(request, "Error updating dispensary. Please correct the form errors.")
    else:
        form = DispensaryForm(instance=dispensary)
    context = {
        'form': form,
        'title': 'Edit Dispensary'
    }
    return render(request, 'pharmacy/add_edit_dispensary.html', context)

@login_required
def delete_dispensary(request, dispensary_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    if request.method == 'POST':
        dispensary.delete()
        messages.success(request, "Dispensary deleted successfully!")
        return redirect('pharmacy:dispensary_list')
    context = {
        'dispensary': dispensary,
        'title': 'Confirm Delete Dispensary'
    }
    return render(request, 'pharmacy/confirm_delete_dispensary.html', context)

@login_required
def add_dispensary_inventory_item(request, dispensary_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    if request.method == 'POST':
        form = MedicationInventoryForm(request.POST)
        if form.is_valid():
            inventory_item = form.save(commit=False)
            inventory_item.dispensary = dispensary
            inventory_item.save()
            messages.success(request, "Medication added to dispensary inventory successfully!")
            return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)
        else:
            messages.error(request, "Error adding medication to inventory. Please correct the form errors.")
    else:
        form = MedicationInventoryForm(initial={'dispensary': dispensary})
    context = {
        'form': form,
        'dispensary': dispensary,
        'title': f'Add Medication to {dispensary.name} Inventory'
    }
    return render(request, 'pharmacy/add_edit_inventory_item.html', context)

@login_required
def edit_dispensary_inventory_item(request, dispensary_id, inventory_item_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    inventory_item = get_object_or_404(MedicationInventory, id=inventory_item_id, dispensary=dispensary)

    if request.method == 'POST':
        form = MedicationInventoryForm(request.POST, instance=inventory_item)
        if form.is_valid():
            form.save()
            messages.success(request, "Inventory item updated successfully!")
            return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)
        else:
            messages.error(request, "Error updating inventory item. Please correct the form errors.")
    else:
        form = MedicationInventoryForm(instance=inventory_item)
    context = {
        'form': form,
        'dispensary': dispensary,
        'inventory_item': inventory_item,
        'title': 'Edit Inventory Item'
    }
    return render(request, 'pharmacy/add_edit_inventory_item.html', context)

@login_required
def delete_dispensary_inventory_item(request, dispensary_id, inventory_item_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    inventory_item = get_object_or_404(MedicationInventory, id=inventory_item_id, dispensary=dispensary)

    if request.method == 'POST':
        inventory_item.delete()
        messages.success(request, "Inventory item deleted successfully!")
        return redirect('pharmacy:dispensary_inventory', dispensary_id=dispensary.id)
    context = {
        'inventory_item': inventory_item,
        'dispensary': dispensary,
        'title': 'Confirm Delete Inventory Item'
    }
    return render(request, 'pharmacy/confirm_delete_inventory_item.html', context)

@login_required
@permission_required('pharmacy.view_medicationinventory', raise_exception=True)
def dispensary_inventory(request, dispensary_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    inventory_items = MedicationInventory.objects.filter(dispensary=dispensary).select_related('medication').order_by('medication__name')

    context = {
        'dispensary': dispensary,
        'inventory_items': inventory_items,
        'title': f'{dispensary.name} Inventory'
    }
    return render(request, 'pharmacy/dispensary_inventory.html', context)

@login_required
@permission_required('pharmacy.view_medication', raise_exception=True)
def inventory_list(request):
    medications = Medication.objects.all().order_by('name')
    form = MedicationSearchForm(request.GET or None)

    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        category = form.cleaned_data.get('category')
        is_active = form.cleaned_data.get('is_active')

        if search_query:
            medications = medications.filter(
                Q(name__icontains=search_query) |
                Q(generic_name__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        if category:
            medications = medications.filter(category=category)
        if is_active:
            medications = medications.filter(is_active=(is_active == 'active'))

    paginator = Paginator(medications, 10) # Show 10 medications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
        'title': 'Medication Inventory'
    }
    return render(request, 'pharmacy/inventory_list.html', context)

@login_required
@permission_required('pharmacy.add_medication', raise_exception=True)
def add_medication(request):
    if request.method == 'POST':
        form = MedicationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Medication added successfully!")
            return redirect('pharmacy:inventory')
        else:
            messages.error(request, "Error adding medication. Please correct the form errors.")
    else:
        form = MedicationForm()
    context = {
        'form': form,
        'title': 'Add New Medication'
    }
    return render(request, 'pharmacy/add_edit_medication.html', context)

@login_required
@permission_required('pharmacy.view_medication', raise_exception=True)
def medication_detail(request, medication_id):
    medication = get_object_or_404(Medication, id=medication_id)
    context = {
        'medication': medication,
        'title': 'Medication Detail'
    }
    return render(request, 'pharmacy/medication_detail.html', context)

@login_required
@permission_required('pharmacy.change_medication', raise_exception=True)
def edit_medication(request, medication_id):
    medication = get_object_or_404(Medication, id=medication_id)
    if request.method == 'POST':
        form = MedicationForm(request.POST, instance=medication)
        if form.is_valid():
            form.save()
            messages.success(request, "Medication updated successfully!")
            return redirect('pharmacy:medication_detail', medication_id=medication.id)
        else:
            messages.error(request, "Error updating medication. Please correct the form errors.")
    else:
        form = MedicationForm(instance=medication)
    context = {
        'form': form,
        'title': 'Edit Medication'
    }
    return render(request, 'pharmacy/add_edit_medication.html', context)

@login_required
@permission_required('pharmacy.delete_medication', raise_exception=True)
def delete_medication(request, medication_id):
    medication = get_object_or_404(Medication, id=medication_id)
    if request.method == 'POST':
        medication.delete()
        messages.success(request, "Medication deleted successfully!")
        return redirect('pharmacy:inventory')
    context = {
        'medication': medication,
        'title': 'Confirm Delete Medication'
    }
    return render(request, 'pharmacy/confirm_delete_medication.html', context)

@login_required
@permission_required('pharmacy.view_medicationcategory', raise_exception=True)
def manage_categories(request):
    categories = MedicationCategory.objects.all().order_by('name')
    if request.method == 'POST':
        form = MedicationCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully!")
            return redirect('pharmacy:manage_categories')
        else:
            messages.error(request, "Error adding category. Please correct the form errors.")
    else:
        form = MedicationCategoryForm()
    context = {
        'categories': categories,
        'form': form,
        'title': 'Manage Medication Categories'
    }
    return render(request, 'pharmacy/manage_categories.html', context)

@login_required
@permission_required('pharmacy.change_medicationcategory', raise_exception=True)
def edit_category(request, category_id):
    category = get_object_or_404(MedicationCategory, id=category_id)
    if request.method == 'POST':
        form = MedicationCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully!")
            return redirect('pharmacy:manage_categories')
        else:
            messages.error(request, "Error updating category. Please correct the form errors.")
    else:
        form = MedicationCategoryForm(instance=category)
    context = {
        'form': form,
        'title': 'Edit Medication Category'
    }
    return render(request, 'pharmacy/add_edit_category.html', context)

@login_required
@permission_required('pharmacy.delete_medicationcategory', raise_exception=True)
def delete_category(request, category_id):
    category = get_object_or_404(MedicationCategory, id=category_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted successfully!")
        return redirect('pharmacy:manage_categories')
    context = {
        'category': category,
        'title': 'Confirm Delete Category'
    }
    return render(request, 'pharmacy/confirm_delete_category.html', context)

@login_required
@permission_required('pharmacy.view_supplier', raise_exception=True)
def manage_suppliers(request):
    suppliers = Supplier.objects.all().order_by('name')
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier added successfully!")
            return redirect('pharmacy:manage_suppliers')
        else:
            messages.error(request, "Error adding supplier. Please correct the form errors.")
    else:
        form = SupplierForm()
    context = {
        'suppliers': suppliers,
        'form': form,
        'title': 'Manage Suppliers'
    }
    return render(request, 'pharmacy/manage_suppliers.html', context)

@login_required
@permission_required('pharmacy.change_supplier', raise_exception=True)
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier updated successfully!")
            return redirect('pharmacy:manage_suppliers')
        else:
            messages.error(request, "Error updating supplier. Please correct the form errors.")
    else:
        form = SupplierForm(instance=supplier)
    context = {
        'form': form,
        'title': 'Edit Supplier'
    }
    return render(request, 'pharmacy/add_edit_supplier.html', context)

@login_required
@permission_required('pharmacy.delete_supplier', raise_exception=True)
def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, "Supplier deleted successfully!")
        return redirect('pharmacy:manage_suppliers')
    context = {
        'supplier': supplier,
        'title': 'Confirm Delete Supplier'
    }
    return render(request, 'pharmacy/confirm_delete_supplier.html', context)

@login_required
@permission_required('pharmacy.view_purchase', raise_exception=True)
def manage_purchases(request):
    purchases = Purchase.objects.all().select_related('supplier', 'created_by').order_by('-purchase_date')
    context = {
        'purchases': purchases,
        'title': 'Manage Purchases'
    }
    return render(request, 'pharmacy/manage_purchases.html', context)

@login_required
@permission_required('pharmacy.add_purchase', raise_exception=True)
def add_purchase(request):
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.created_by = request.user
            purchase.save()
            messages.success(request, "Purchase added successfully!")
            return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
        else:
            messages.error(request, "Error adding purchase. Please correct the form errors.")
    else:
        form = PurchaseForm()
    context = {
        'form': form,
        'title': 'Add New Purchase'
    }
    return render(request, 'pharmacy/add_purchase.html', context)

@login_required
@permission_required('pharmacy.view_purchase', raise_exception=True)
def purchase_detail(request, purchase_id):
    purchase = get_object_or_404(Purchase.objects.select_related('supplier', 'created_by', 'dispensary'), id=purchase_id)
    purchase_items = purchase.items.all().select_related('medication')
    context = {
        'purchase': purchase,
        'purchase_items': purchase_items,
        'title': f'Purchase Detail - #{purchase.invoice_number}'
    }
    return render(request, 'pharmacy/purchase_detail.html', context)

@login_required
@permission_required('pharmacy.delete_purchaseitem', raise_exception=True)
def delete_purchase_item(request, item_id):
    purchase_item = get_object_or_404(PurchaseItem, id=item_id)
    purchase = purchase_item.purchase
    if request.method == 'POST':
        purchase_item.delete()
        messages.success(request, "Purchase item deleted successfully!")
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    context = {
        'purchase_item': purchase_item,
        'purchase': purchase,
        'title': 'Confirm Delete Purchase Item'
    }
    return render(request, 'pharmacy/confirm_delete_purchase_item.html', context)

@login_required
@permission_required('pharmacy.change_purchase', raise_exception=True)
def submit_purchase_for_approval(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if request.method == 'POST':
        if purchase.approval_status == 'draft':
            purchase.approval_status = 'pending'
            purchase.current_approver = request.user # Assign current user as initial approver
            purchase.approval_updated_at = timezone.now()
            purchase.save()
            messages.success(request, "Purchase submitted for approval successfully!")
        else:
            messages.warning(request, "Purchase is not in 'draft' status and cannot be submitted for approval.")
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    context = {
        'purchase': purchase,
        'title': 'Submit Purchase for Approval'
    }
    return render(request, 'pharmacy/confirm_submit_purchase_for_approval.html', context)

@login_required
@permission_required('pharmacy.change_purchase', raise_exception=True)
def approve_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if request.method == 'POST':
        if purchase.approval_status == 'pending':
            purchase.approval_status = 'approved'
            purchase.approval_notes = request.POST.get('approval_notes', '')
            purchase.approval_updated_at = timezone.now()
            purchase.save()
            messages.success(request, "Purchase approved successfully!")
        else:
            messages.warning(request, "Purchase is not in 'pending' status and cannot be approved.")
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    context = {
        'purchase': purchase,
        'title': 'Approve Purchase'
    }
    return render(request, 'pharmacy/confirm_approve_purchase.html', context)

@login_required
@permission_required('pharmacy.change_purchase', raise_exception=True)
def reject_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    if request.method == 'POST':
        if purchase.approval_status == 'pending':
            purchase.approval_status = 'rejected'
            purchase.approval_notes = request.POST.get('approval_notes', '')
            purchase.approval_updated_at = timezone.now()
            purchase.save()
            messages.success(request, "Purchase rejected successfully!")
        else:
            messages.warning(request, "Purchase is not in 'pending' status and cannot be rejected.")
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
    context = {
        'purchase': purchase,
        'title': 'Reject Purchase'
    }
    return render(request, 'pharmacy/confirm_reject_purchase.html', context)

@login_required
@permission_required('pharmacy.view_prescription', raise_exception=True)
def prescription_list(request):
    prescriptions = Prescription.objects.all().select_related('patient', 'doctor').order_by('-prescription_date')
    form = PrescriptionSearchForm(request.GET or None)

    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        status = form.cleaned_data.get('status')
        doctor = form.cleaned_data.get('doctor')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')

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

    paginator = Paginator(prescriptions, 10) # Show 10 prescriptions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
        'title': 'Prescription List'
    }
    return render(request, 'pharmacy/prescription_list.html', context)

@login_required
@permission_required('pharmacy.view_prescription', raise_exception=True)
def prescription_detail(request, prescription_id):
    prescription = get_object_or_404(Prescription.objects.select_related('patient', 'doctor'), id=prescription_id)
    prescription_items = prescription.items.all().select_related('medication')
    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'title': f'Prescription Detail - #{prescription.id}'
    }
    return render(request, 'pharmacy/prescription_detail.html', context)

@login_required
@permission_required('pharmacy.view_prescription', raise_exception=True)
def print_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription.objects.select_related('patient', 'doctor'), id=prescription_id)
    prescription_items = prescription.items.all().select_related('medication')
    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'title': f'Print Prescription - #{prescription.id}'
    }
    return render(request, 'pharmacy/print_prescription.html', context)

@login_required
@permission_required('pharmacy.change_prescription', raise_exception=True)
def update_prescription_status(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status in [choice[0] for choice in Prescription.STATUS_CHOICES]:
            prescription.status = new_status
            prescription.save()
            messages.success(request, f"Prescription status updated to {prescription.get_status_display}!")
        else:
            messages.error(request, "Invalid status provided.")
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    context = {
        'prescription': prescription,
        'status_choices': Prescription.STATUS_CHOICES,
        'title': 'Update Prescription Status'
    }
    return render(request, 'pharmacy/update_prescription_status.html', context)

@login_required
@permission_required('pharmacy.change_prescription', raise_exception=True)
def dispense_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    prescription_items = prescription.items.all().select_related('medication')

    # Filter out items that are already fully dispensed
    initial_data = []
    for item in prescription_items:
        if not item.is_dispensed:
            initial_data.append({'item_id': item.id})

    DispenseItemFormSet = formset_factory(DispenseItemForm, formset=BaseDispenseItemFormSet, extra=len(initial_data), can_delete=False)
    DispenseItemFormSet.formset_kwargs = {'prescription_items_qs': prescription_items}

    if request.method == 'POST':
        selected_dispensary_id = request.POST.get('dispensary_select')
        if not selected_dispensary_id:
            messages.error(request, "Please select a dispensary to proceed with dispensing.")
            formset = DispenseItemFormSet(request.POST)
            context = {
                'prescription': prescription,
                'formset': formset,
                'dispensaries': Dispensary.objects.filter(is_active=True),
                'title': f'Dispense Prescription {prescription.id}'
            }
            return render(request, 'pharmacy/dispense_prescription.html', context)

        selected_dispensary = get_object_or_404(Dispensary, id=selected_dispensary_id)
        
        formset = DispenseItemFormSet(request.POST, form_kwargs={'selected_dispensary': selected_dispensary})

        if formset.is_valid():
            dispensed_count = 0
            total_dispensed_value = Decimal('0.00')
            
            with transaction.atomic():
                for form in formset:
                    if form.cleaned_data.get('dispense_this_item') and form.cleaned_data.get('quantity_to_dispense', 0) > 0:
                        prescription_item = get_object_or_404(PrescriptionItem, id=form.cleaned_data['item_id'])
                        quantity_to_dispense = form.cleaned_data['quantity_to_dispense']

                        # Get or create MedicationInventory for the selected dispensary
                        med_inventory, created = MedicationInventory.objects.get_or_create(
                            medication=prescription_item.medication,
                            dispensary=selected_dispensary,
                            defaults={'stock_quantity': 0}
                        )

                        if med_inventory.stock_quantity >= quantity_to_dispense:
                            # Decrement stock from inventory
                            med_inventory.stock_quantity -= quantity_to_dispense
                            med_inventory.save()

                            # Update PrescriptionItem
                            prescription_item.quantity_dispensed_so_far += quantity_to_dispense
                            prescription_item.dispensed_by = request.user
                            prescription_item.dispensed_date = timezone.now()
                            if prescription_item.quantity_dispensed_so_far >= prescription_item.quantity:
                                prescription_item.is_dispensed = True
                            prescription_item.save()

                            # Create DispensingLog entry
                            DispensingLog.objects.create(
                                prescription_item=prescription_item,
                                dispensed_by=request.user,
                                dispensed_quantity=quantity_to_dispense,
                                unit_price_at_dispense=prescription_item.medication.price,
                                dispensary=selected_dispensary
                            )
                            dispensed_count += 1
                            total_dispensed_value += prescription_item.medication.price * quantity_to_dispense
                        else:
                            messages.error(request, f"Not enough stock for {prescription_item.medication.name} at {selected_dispensary.name}. Available: {med_inventory.stock_quantity}.")
                            # Rollback transaction and re-render form with errors
                            transaction.set_rollback(True)
                            context = {
                                'prescription': prescription,
                                'formset': formset,
                                'dispensaries': Dispensary.objects.filter(is_active=True),
                                'selected_dispensary_id': selected_dispensary_id,
                                'title': f'Dispense Prescription {prescription.id}'
                            }
                            return render(request, 'pharmacy/dispense_prescription.html', context)

                if dispensed_count > 0:
                    # Update prescription status
                    if prescription.items.filter(is_dispensed=False).exists():
                        prescription.status = 'partially_dispensed'
                    else:
                        prescription.status = 'dispensed'
                    prescription.save()

                    messages.success(request, f"Successfully dispensed {dispensed_count} item(s) for Prescription {prescription.id}.")
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
                else:
                    messages.warning(request, "No items were selected for dispensing or no quantity specified.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        formset = DispenseItemFormSet(initial=initial_data)

    context = {
        'prescription': prescription,
        'formset': formset,
        'dispensaries': Dispensary.objects.filter(is_active=True),
        'title': f'Dispense Prescription {prescription.id}'
    }
    return render(request, 'pharmacy/dispense_prescription.html', context)

@login_required
@permission_required('pharmacy.view_dispensinglog', raise_exception=True)
def prescription_dispensing_history(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    dispensing_logs = DispensingLog.objects.filter(prescription_item__prescription=prescription).select_related(
        'prescription_item__medication', 'dispensed_by', 'dispensary'
    ).order_by('-dispensed_date')

    context = {
        'prescription': prescription,
        'dispensing_logs': dispensing_logs,
        'title': f'Dispensing History for Prescription {prescription.id}'
    }
    return render(request, 'pharmacy/prescription_dispensing_history.html', context)

@login_required
@permission_required('pharmacy.delete_prescriptionitem', raise_exception=True)
def delete_prescription_item(request, item_id):
    prescription_item = get_object_or_404(PrescriptionItem, id=item_id)
    prescription = prescription_item.prescription
    if request.method == 'POST':
        prescription_item.delete()
        messages.success(request, "Prescription item deleted successfully!")
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    context = {
        'prescription_item': prescription_item,
        'prescription': prescription,
        'title': 'Confirm Delete Prescription Item'
    }
    return render(request, 'pharmacy/confirm_delete_prescription_item.html', context)

@login_required
def medication_api(request):
    if 'term' in request.GET:
        query = request.GET.get('term')
        medications = Medication.objects.filter(name__icontains=query)[:10]
        results = [med.name for med in medications]
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

@login_required
@permission_required('pharmacy.view_medication', raise_exception=True)
def expiring_medications_report(request):
    today = timezone.now().date()
    # Medications expiring within the next 90 days or already expired
    expiring_items = MedicationInventory.objects.filter(
        Q(medication__expiry_date__lte=today + timezone.timedelta(days=90)) |
        Q(medication__expiry_date__isnull=False, medication__expiry_date__lt=today)
    ).select_related('medication', 'dispensary').order_by('medication__expiry_date', 'medication__name')

    context = {
        'expiring_items': expiring_items,
        'title': 'Expiring Medications Report'
    }
    return render(request, 'pharmacy/reports/expiring_medications_report.html', context)

@login_required
@permission_required('pharmacy.view_medication', raise_exception=True)
def low_stock_medications_report(request):
    low_stock_items = MedicationInventory.objects.filter(stock_quantity__lte=F('reorder_level')).select_related('medication', 'dispensary').order_by('medication__name', 'dispensary__name')

    context = {
        'low_stock_items': low_stock_items,
        'title': 'Low Stock Medications Report'
    }
    return render(request, 'pharmacy/reports/low_stock_medications_report.html', context)

@login_required
def dispensing_report(request):
    return render(request, 'pharmacy/placeholder.html', {'title': 'Dispensing Report'})

@login_required
def pharmacy_sales_report(request):
    return render(request, 'pharmacy/placeholder.html', {'title': 'Pharmacy Sales Report'})

@login_required
@permission_required('pharmacy.view_medicationinventory', raise_exception=True)
def dispensary_inventory(request, dispensary_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    inventory_items = MedicationInventory.objects.filter(dispensary=dispensary).select_related('medication').order_by('medication__name')

    context = {
        'dispensary': dispensary,
        'inventory_items': inventory_items,
        'title': f'{dispensary.name} Inventory'
    }
    return render(request, 'pharmacy/dispensary_inventory.html', context)
