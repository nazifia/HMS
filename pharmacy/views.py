
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, F, Avg, Count
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta, datetime
import csv
from decimal import Decimal
from django.db import transaction

from .models import (
    MedicationCategory, Medication, Supplier, Purchase,
    PurchaseItem, Prescription, PrescriptionItem, DispensingLog, Dispensary, MedicationInventory, ActiveStore
)
from .forms import (
    MedicationCategoryForm, MedicationForm, SupplierForm, PurchaseForm,
    PurchaseItemForm, PrescriptionForm, PrescriptionItemForm, DispenseItemForm, BaseDispenseItemFormSet,
    MedicationSearchForm, PrescriptionSearchForm, DispensedItemsSearchForm, DispensaryForm, MedicationInventoryForm,
    PrescriptionPaymentForm
)

# Active Store Detail View
@login_required
def active_store_detail(request, dispensary_id):
    dispensary = get_object_or_404(Dispensary, id=dispensary_id)
    active_store = getattr(dispensary, 'active_store', None)
    if not active_store:
        messages.error(request, 'Active Store not found for this dispensary.')
        return redirect('pharmacy:dispensary_list')
    context = {
        'active_store': active_store,
        'title': f"Active Store - {active_store.name}"
    }
    return render(request, 'pharmacy/active_store_detail.html', context)

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, F, Avg, Count
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta, datetime
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
    MedicationSearchForm, PrescriptionSearchForm, DispensedItemsSearchForm, DispensaryForm, MedicationInventoryForm,
    PrescriptionPaymentForm
)
from billing.models import Service, Invoice, Payment
from django.apps import apps
from django.db import transaction

from django.contrib.auth import get_user_model
User = get_user_model()

from django.forms import formset_factory









from patients.models import Patient # Import Patient model

@login_required
def create_prescription(request, patient_id=None):
    logging.debug("create_prescription view called.")
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)

    # Also check for patient in GET parameters (from patient detail page)
    if not patient and request.GET.get('patient'):
        try:
            patient = get_object_or_404(Patient, id=request.GET.get('patient'))
        except (ValueError, Patient.DoesNotExist):
            pass

    initial_data = {}
    if patient:
        initial_data['patient'] = patient

    if request.method == 'POST':
        prescription_form = PrescriptionForm(
            request.POST,
            request=request,
            initial=initial_data,
            preselected_patient=patient
        )
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
                
                from billing.models import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel

                invoice = InvoiceModel.objects.create(
                    patient=prescription.patient,
                    invoice_date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    created_by=request.user,
                    subtotal=total_prescription_price,
                    tax_amount=0,
                    total_amount=total_prescription_price,
                    status='pending',
                    prescription=prescription,
                )

                InvoiceItemModel.objects.create(
                    invoice=invoice,
                    service=medication_dispensing_service,
                    description=f'Invoice for Prescription {prescription.id}',
                    quantity=1,
                    unit_price=total_prescription_price,
                    tax_amount=0,
                    total_amount=total_prescription_price,
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
            logging.error(f"General exception caught: {type(e).__name__}: {e}")
            context = {
                'prescription_form': prescription_form,
                'medications': Medication.objects.filter(is_active=True),
                'title': 'Create New Prescription',
                'patient': patient,
            }
            return render(request, 'pharmacy/create_prescription.html', context, status=400)
    else:
        prescription_form = PrescriptionForm(
            request=request,
            initial=initial_data,
            preselected_patient=patient
        )

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

    # Calculate statistics
    today_stats = logs_query.filter(dispensed_date__date=today).aggregate(
        total_items=Sum('dispensed_quantity'),
        total_value=Sum('total_price_for_this_log')
    )
    week_stats = logs_query.filter(dispensed_date__date__gte=start_of_week).aggregate(
        total_items=Sum('dispensed_quantity'),
        total_value=Sum('total_price_for_this_log')
    )
    month_stats = logs_query.filter(dispensed_date__date__gte=start_of_month).aggregate(
        total_items=Sum('dispensed_quantity'),
        total_value=Sum('total_price_for_this_log')
    )

    stats = {
        'total_dispensed_today': today_stats['total_items'] or 0,
        'total_value_today': today_stats['total_value'] or 0,
        'total_dispensed_week': week_stats['total_items'] or 0,
        'total_value_week': week_stats['total_value'] or 0,
        'total_dispensed_month': month_stats['total_items'] or 0,
        'total_value_month': month_stats['total_value'] or 0,
        'avg_quantity_per_dispense': logs_query.aggregate(avg=Avg('dispensed_quantity'))['avg'] or 0
    }

    # Get top medications this month
    top_medications = logs_query.filter(dispensed_date__date__gte=start_of_month).values(
        'prescription_item__medication__name'
    ).annotate(
        total_quantity=Sum('dispensed_quantity'),
        total_value=Sum('total_price_for_this_log'),
        dispense_count=Count('id')
    ).order_by('-total_quantity')[:10]

    # Get top dispensing staff this month
    top_staff = logs_query.filter(dispensed_date__date__gte=start_of_month).values(
        'dispensed_by__first_name', 'dispensed_by__last_name'
    ).annotate(
        total_dispensed=Count('id'),
        total_value=Sum('total_price_for_this_log')
    ).order_by('-total_dispensed')[:10]

    context = {
        'search_form': form,  # Changed from 'form' to 'search_form'
        'page_obj': page_obj,
        'stats': stats,
        'total_results': logs_query.count(),
        'top_medications': top_medications,
        'top_staff': top_staff,
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
    from .forms import PharmacyDashboardSearchForm
    from django.db.models import Count, Sum, Q
    from datetime import datetime, timedelta

    # Initialize search form
    search_form = PharmacyDashboardSearchForm(request.GET or None)

    # Calculate dashboard statistics
    total_prescriptions = Prescription.objects.count()
    total_medications = Medication.objects.filter(is_active=True).count()

    # Calculate medications in stock (with inventory)
    medications_in_stock = MedicationInventory.objects.filter(
        stock_quantity__gt=0
    ).values('medication').distinct().count()

    # Calculate low stock alerts
    low_stock_count = MedicationInventory.objects.filter(
        stock_quantity__lte=F('reorder_level')
    ).count()

    # Calculate expiring medications (within 30 days)
    thirty_days_from_now = timezone.now().date() + timedelta(days=30)
    expiring_soon = Medication.objects.filter(
        expiry_date__lte=thirty_days_from_now,
        expiry_date__gte=timezone.now().date(),
        is_active=True
    ).count()

    # Recent dispensing activity (last 10)
    recent_dispensing = DispensingLog.objects.select_related(
        'prescription_item__prescription__patient',
        'prescription_item__medication',
        'dispensed_by__profile',
        'dispensary'
    ).order_by('-dispensed_date')[:10]

    # Top dispensed medications (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    top_medications = DispensingLog.objects.filter(
        dispensed_date__gte=thirty_days_ago
    ).values(
        'prescription_item__medication__name'
    ).annotate(
        total_dispensed=Sum('dispensed_quantity')
    ).order_by('-total_dispensed')[:5]

    # Search functionality
    search_results = {}
    if search_form.is_valid() and search_form.cleaned_data.get('search_query'):
        query = search_form.cleaned_data['search_query']
        search_type = search_form.cleaned_data.get('search_type', '')

        if not search_type or search_type == 'medications':
            medications = Medication.objects.filter(
                Q(name__icontains=query) |
                Q(generic_name__icontains=query) |
                Q(category__name__icontains=query)
            ).filter(is_active=True)

            # Apply additional filters
            category = search_form.cleaned_data.get('medication_category')
            if category:
                medications = medications.filter(category=category)

            stock_status = search_form.cleaned_data.get('stock_status')
            if stock_status:
                if stock_status == 'in_stock':
                    medications = medications.filter(inventories__stock_quantity__gt=0)
                elif stock_status == 'low_stock':
                    medications = medications.filter(inventories__stock_quantity__lte=F('inventories__reorder_level'))
                elif stock_status == 'out_of_stock':
                    medications = medications.filter(inventories__stock_quantity=0)

            search_results['medications'] = medications[:20]

        if not search_type or search_type == 'prescriptions':
            prescriptions = Prescription.objects.filter(
                Q(patient__first_name__icontains=query) |
                Q(patient__last_name__icontains=query) |
                Q(patient__patient_id__icontains=query) |
                Q(items__medication__name__icontains=query)
            ).distinct()

            # Apply date filters
            date_from = search_form.cleaned_data.get('date_from')
            date_to = search_form.cleaned_data.get('date_to')
            if date_from:
                prescriptions = prescriptions.filter(created_at__date__gte=date_from)
            if date_to:
                prescriptions = prescriptions.filter(created_at__date__lte=date_to)

            search_results['prescriptions'] = prescriptions[:20]

        if not search_type or search_type == 'patients':
            patients = Patient.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(patient_id__icontains=query) |
                Q(phone_number__icontains=query)
            ).filter(is_active=True)
            search_results['patients'] = patients[:20]

        if not search_type or search_type == 'suppliers':
            suppliers = Supplier.objects.filter(
                Q(name__icontains=query) |
                Q(contact_person__icontains=query) |
                Q(email__icontains=query)
            ).filter(is_active=True)
            search_results['suppliers'] = suppliers[:20]

    context = {
        'title': 'Pharmacy Dashboard',
        'search_form': search_form,
        'search_results': search_results,
        'total_prescriptions': total_prescriptions,
        'total_medications': total_medications,
        'medications_in_stock': medications_in_stock,
        'low_stock_count': low_stock_count,
        'expiring_soon': expiring_soon,
        'recent_dispensing': recent_dispensing,
        'top_medications': top_medications,
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
@permission_required('pharmacy.view_supplier', raise_exception=True)
def supplier_detail(request, supplier_id):
    """Detailed view of a supplier with purchase history and procurement options"""
    supplier = get_object_or_404(Supplier, id=supplier_id)

    # Get purchase history
    purchases = Purchase.objects.filter(supplier=supplier).order_by('-purchase_date')[:10]

    # Calculate statistics
    total_purchases = Purchase.objects.filter(supplier=supplier).count()
    total_amount = Purchase.objects.filter(supplier=supplier).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # Recent purchase items
    recent_items = PurchaseItem.objects.filter(
        purchase__supplier=supplier
    ).select_related('medication', 'purchase').order_by('-purchase__purchase_date')[:10]

    # Available medications for procurement
    medications = Medication.objects.filter(is_active=True).order_by('name')

    context = {
        'supplier': supplier,
        'purchases': purchases,
        'recent_items': recent_items,
        'medications': medications,
        'total_purchases': total_purchases,
        'total_amount': total_amount,
        'title': f'Supplier Details - {supplier.name}'
    }
    return render(request, 'pharmacy/supplier_detail.html', context)

@login_required
@permission_required('pharmacy.view_supplier', raise_exception=True)
def supplier_list(request):
    """List all suppliers with search and filter functionality"""
    suppliers = Supplier.objects.all().order_by('name')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    # Filter by active status
    is_active = request.GET.get('is_active', '')
    if is_active:
        suppliers = suppliers.filter(is_active=(is_active == 'true'))

    # Pagination
    paginator = Paginator(suppliers, 20)
    page_number = request.GET.get('page')
    suppliers = paginator.get_page(page_number)

    context = {
        'suppliers': suppliers,
        'search_query': search_query,
        'is_active': is_active,
        'title': 'Suppliers'
    }
    return render(request, 'pharmacy/supplier_list.html', context)

@login_required
@permission_required('pharmacy.add_purchase', raise_exception=True)
def quick_procurement(request, supplier_id):
    """Quick procurement functionality to add items to a purchase order"""
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        medication_id = request.POST.get('medication')
        quantity = request.POST.get('quantity')
        unit_price = request.POST.get('unit_price')

        try:
            medication = Medication.objects.get(id=medication_id)
            quantity = int(quantity)
            unit_price = float(unit_price)

            # Check if there's an existing pending purchase order for this supplier
            pending_purchase = Purchase.objects.filter(
                supplier=supplier,
                payment_status='pending'
            ).first()

            if not pending_purchase:
                # Create a new purchase order
                from datetime import date
                pending_purchase = Purchase.objects.create(
                    supplier=supplier,
                    purchase_date=date.today(),
                    invoice_number=f"PO-{supplier.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    total_amount=0,
                    payment_status='pending',
                    created_by=request.user,
                    notes=f"Quick procurement order created on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                )

            # Add or update the purchase item
            purchase_item, created = PurchaseItem.objects.get_or_create(
                purchase=pending_purchase,
                medication=medication,
                defaults={
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': quantity * unit_price
                }
            )

            if not created:
                # Update existing item
                purchase_item.quantity += quantity
                purchase_item.total_price = purchase_item.quantity * purchase_item.unit_price
                purchase_item.save()

            # Update purchase total using the new method
            pending_purchase.update_total_amount()

            messages.success(request, f"Added {quantity} units of {medication.name} to purchase order.")

        except (Medication.DoesNotExist, ValueError, TypeError) as e:
            messages.error(request, "Invalid data provided. Please check your inputs.")

    return redirect('pharmacy:supplier_detail', supplier_id=supplier.id)

@login_required
@permission_required('pharmacy.add_purchase', raise_exception=True)
def create_procurement_request(request, medication_id):
    """Create a procurement request for a specific medication"""
    medication = get_object_or_404(Medication, id=medication_id)

    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        quantity = request.POST.get('quantity')
        unit_price = request.POST.get('unit_price')
        notes = request.POST.get('notes', '')

        try:
            supplier = Supplier.objects.get(id=supplier_id)
            quantity = int(quantity)
            unit_price = float(unit_price)

            # Check if there's an existing pending purchase order for this supplier
            pending_purchase = Purchase.objects.filter(
                supplier=supplier,
                payment_status='pending'
            ).first()

            if not pending_purchase:
                # Create a new purchase order
                from datetime import date
                pending_purchase = Purchase.objects.create(
                    supplier=supplier,
                    purchase_date=date.today(),
                    invoice_number=f"PR-{supplier.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    total_amount=0,
                    payment_status='pending',
                    created_by=request.user,
                    notes=f"Procurement request created on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                )

            # Add or update the purchase item
            purchase_item, created = PurchaseItem.objects.get_or_create(
                purchase=pending_purchase,
                medication=medication,
                defaults={
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': quantity * unit_price
                }
            )

            if not created:
                # Update existing item
                purchase_item.quantity += quantity
                purchase_item.total_price = purchase_item.quantity * purchase_item.unit_price
                purchase_item.save()

            # Update purchase total using the new method
            pending_purchase.update_total_amount()

            # Add notes if provided
            if notes:
                if pending_purchase.notes:
                    pending_purchase.notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {medication.name}: {notes}"
                else:
                    pending_purchase.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {medication.name}: {notes}"

            pending_purchase.save()

            messages.success(request,
                f"Procurement request created successfully! Added {quantity} units of {medication.name} "
                f"to purchase order #{pending_purchase.invoice_number} from {supplier.name}."
            )

        except (Supplier.DoesNotExist, ValueError, TypeError) as e:
            messages.error(request, "Invalid data provided. Please check your inputs.")

    return redirect('pharmacy:inventory_list')

@login_required
def api_suppliers(request):
    """API endpoint to get suppliers for AJAX requests"""
    suppliers = Supplier.objects.filter(is_active=True).values('id', 'name')
    return JsonResponse(list(suppliers), safe=False)

@login_required
@permission_required('pharmacy.view_purchase', raise_exception=True)
def procurement_dashboard(request):
    """Comprehensive procurement dashboard for pharmacy staff"""

    # Get pending purchase orders
    pending_orders = Purchase.objects.filter(
        payment_status='pending'
    ).select_related('supplier').order_by('-created_at')

    # Get recent completed orders
    recent_orders = Purchase.objects.filter(
        payment_status__in=['paid', 'partial']
    ).select_related('supplier').order_by('-purchase_date')[:10]

    # Get low stock medications that need procurement
    low_stock_medications = MedicationInventory.objects.filter(
        stock_quantity__lte=F('reorder_level')
    ).select_related('medication', 'dispensary').order_by('stock_quantity')

    # Calculate statistics
    total_pending_value = pending_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    total_pending_orders = pending_orders.count()
    low_stock_count = low_stock_medications.count()

    # Get top suppliers by order value
    top_suppliers = Purchase.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=90)
    ).values(
        'supplier__name'
    ).annotate(
        total_value=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('-total_value')[:5]

    context = {
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
        'low_stock_medications': low_stock_medications,
        'total_pending_value': total_pending_value,
        'total_pending_orders': total_pending_orders,
        'low_stock_count': low_stock_count,
        'top_suppliers': top_suppliers,
        'title': 'Procurement Dashboard'
    }

    return render(request, 'pharmacy/procurement_dashboard.html', context)

@login_required
@permission_required('pharmacy.view_purchase', raise_exception=True)
def procurement_analytics(request):
    """Advanced procurement analytics and reporting"""
    from django.db.models import Avg, Max, Min, StdDev, Case, When, Value, F
    from django.db.models.functions import TruncMonth, TruncWeek
    from django.db import models

    # Date range for analysis (default to last 12 months)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)

    # Supplier Performance Analysis
    supplier_performance = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).values(
        'supplier__name', 'supplier__id'
    ).annotate(
        total_orders=Count('id'),
        total_value=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        on_time_deliveries=Count('id', filter=Q(payment_status='paid')),
        pending_orders=Count('id', filter=Q(payment_status='pending'))
    ).order_by('-total_value')

    # Cost Analysis and Trends
    monthly_procurement_costs = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('purchase_date')
    ).values('month').annotate(
        total_cost=Sum('total_amount'),
        order_count=Count('id'),
        avg_order_value=Avg('total_amount')
    ).order_by('month')

    # Medication Cost Analysis
    medication_cost_analysis = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).values(
        'medication__name', 'medication__id'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum('total_price'),
        avg_unit_price=Avg('unit_price'),
        min_price=Min('unit_price'),
        max_price=Max('unit_price'),
        price_variance=StdDev('unit_price'),
        order_frequency=Count('purchase', distinct=True)
    ).order_by('-total_cost')

    # Procurement Efficiency Metrics
    total_procurement_value = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Calculate average order processing time manually to avoid SQLite datetime aggregation issues
    paid_orders = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date],
        payment_status='paid'
    ).exclude(created_at__isnull=True)

    avg_order_processing_time = None
    if paid_orders.exists():
        total_processing_time = 0
        order_count = 0
        for order in paid_orders:
            if order.created_at:
                # Calculate processing time in days
                processing_time = (timezone.now() - order.created_at).days
                total_processing_time += processing_time
                order_count += 1

        if order_count > 0:
            avg_order_processing_time = total_processing_time / order_count

    # Inventory Turnover Analysis
    from django.db.models import Subquery, OuterRef
    inventory_turnover = MedicationInventory.objects.select_related(
        'medication'
    ).annotate(
        total_dispensed=Subquery(
            DispensingLog.objects.filter(
                prescription_item__medication=OuterRef('medication')
            ).values('prescription_item__medication').annotate(
                total=Sum('dispensed_quantity')
            ).values('total')[:1]
        ),
        avg_stock=Avg('stock_quantity'),
        turnover_ratio=F('total_dispensed') / F('avg_stock')
    ).order_by('-turnover_ratio')

    # Top Performing Categories
    category_performance = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).values(
        'medication__category__name'
    ).annotate(
        total_value=Sum('total_price'),
        total_quantity=Sum('quantity'),
        avg_price=Avg('unit_price')
    ).order_by('-total_value')

    context = {
        'supplier_performance': supplier_performance,
        'monthly_costs': monthly_procurement_costs,
        'medication_analysis': medication_cost_analysis,
        'total_procurement_value': total_procurement_value,
        'avg_processing_time': avg_order_processing_time,
        'inventory_turnover': inventory_turnover,
        'category_performance': category_performance,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Procurement Analytics'
    }

    return render(request, 'pharmacy/procurement_analytics.html', context)

@login_required
@permission_required('pharmacy.view_dispensinglog', raise_exception=True)
def comprehensive_revenue_analysis(request):
    """Comprehensive revenue analysis across all hospital modules"""
    from django.db.models import Sum, Count, Avg, F, Q
    from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
    from datetime import datetime, timedelta
    from decimal import Decimal

    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # 1. PHARMACY REVENUE
    pharmacy_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).aggregate(
        total_revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')),
        total_prescriptions=Count('prescription_item__prescription', distinct=True),
        total_medications_dispensed=Sum('dispensed_quantity')
    )

    # 2. LABORATORY REVENUE
    try:
        from laboratory.models import TestRequest, LaboratoryPayment
        lab_revenue = LaboratoryPayment.objects.filter(
            payment_date__range=[start_date, end_date]
        ).aggregate(
            total_revenue=Sum('amount'),
            total_tests=Count('invoice__test_request', distinct=True)
        )
    except ImportError:
        lab_revenue = {'total_revenue': 0, 'total_tests': 0}

    # 3. CONSULTATION REVENUE
    try:
        from consultations.models import Consultation
        from billing.models import Invoice
        consultation_revenue = Invoice.objects.filter(
            created_at__date__range=[start_date, end_date],
            source_app='consultations',
            status='paid'
        ).aggregate(
            total_revenue=Sum('total_amount'),
            total_consultations=Count('id')
        )
    except ImportError:
        consultation_revenue = {'total_revenue': 0, 'total_consultations': 0}

    # 4. THEATRE/SURGERY REVENUE
    try:
        from theatre.models import TheatrePayment
        theatre_revenue = TheatrePayment.objects.filter(
            payment_date__range=[start_date, end_date]
        ).aggregate(
            total_revenue=Sum('amount'),
            total_surgeries=Count('invoice__surgery', distinct=True)
        )
    except ImportError:
        theatre_revenue = {'total_revenue': 0, 'total_surgeries': 0}

    # 5. BILLING REVENUE (General)
    try:
        from billing.models import Payment
        general_revenue = Payment.objects.filter(
            payment_date__range=[start_date, end_date]
        ).aggregate(
            total_revenue=Sum('amount'),
            total_payments=Count('id')
        )
    except ImportError:
        general_revenue = {'total_revenue': 0, 'total_payments': 0}

    # Calculate totals
    total_revenue = (
        (pharmacy_revenue['total_revenue'] or 0) +
        (lab_revenue['total_revenue'] or 0) +
        (consultation_revenue['total_revenue'] or 0) +
        (theatre_revenue['total_revenue'] or 0) +
        (general_revenue['total_revenue'] or 0)
    )

    # Monthly trends for all modules
    monthly_trends = []
    for i in range(6):  # Last 6 months
        month_start = (timezone.now().date().replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Pharmacy revenue for this month
        month_pharmacy = DispensingLog.objects.filter(
            dispensed_date__date__range=[month_start, month_end]
        ).aggregate(revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')))['revenue'] or 0

        # Lab revenue for this month
        try:
            month_lab = LaboratoryPayment.objects.filter(
                payment_date__range=[month_start, month_end]
            ).aggregate(revenue=Sum('amount'))['revenue'] or 0
        except:
            month_lab = 0

        # Consultation revenue for this month
        try:
            month_consultation = Invoice.objects.filter(
                created_at__date__range=[month_start, month_end],
                source_app='consultations',
                status='paid'
            ).aggregate(revenue=Sum('total_amount'))['revenue'] or 0
        except:
            month_consultation = 0

        monthly_trends.append({
            'month': month_start.strftime('%B %Y'),
            'pharmacy': month_pharmacy,
            'laboratory': month_lab,
            'consultations': month_consultation,
            'total': month_pharmacy + month_lab + month_consultation
        })

    monthly_trends.reverse()  # Show oldest to newest

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'pharmacy_revenue': pharmacy_revenue,
        'lab_revenue': lab_revenue,
        'consultation_revenue': consultation_revenue,
        'theatre_revenue': theatre_revenue,
        'general_revenue': general_revenue,
        'total_revenue': total_revenue,
        'monthly_trends': monthly_trends,
        'title': 'Comprehensive Revenue Analysis'
    }

    return render(request, 'pharmacy/comprehensive_revenue_analysis.html', context)

@login_required
@permission_required('pharmacy.view_prescription', raise_exception=True)
def revenue_analysis(request):
    """Comprehensive revenue analysis for pharmacy operations"""
    from django.db.models import Case, When, Value, CharField, F, Sum, Count, Avg
    from django.db.models.functions import Coalesce, TruncMonth, TruncWeek
    from django.db import models

    # Date range for analysis (default to last 12 months)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)

    # Revenue from Prescription Sales
    prescription_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).aggregate(
        total_revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')),
        total_prescriptions=Count('prescription_item__prescription', distinct=True),
        total_medications_dispensed=Sum('dispensed_quantity')
    )

    # Monthly Revenue Trends
    monthly_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('dispensed_date')
    ).values('month').annotate(
        revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')),
        prescriptions=Count('prescription_item__prescription', distinct=True),
        medications_sold=Sum('dispensed_quantity')
    ).order_by('month')

    # Medication Revenue Analysis
    medication_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).values(
        'prescription_item__medication__name', 'prescription_item__medication__id'
    ).annotate(
        total_revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')),
        total_quantity=Sum('dispensed_quantity'),
        avg_price=Avg('prescription_item__medication__price'),
        profit_margin=Case(
            When(prescription_item__medication__price__gt=0, then=(F('prescription_item__medication__price') - Avg('prescription_item__medication__purchaseitem__unit_price')) / F('prescription_item__medication__price') * 100),
            default=Value(0),
            output_field=models.DecimalField()
        )
    ).order_by('-total_revenue')

    # Profit Margin Analysis
    profit_analysis = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).values(
        'medication__name', 'medication__id'
    ).annotate(
        avg_cost_price=Avg('unit_price'),
        current_selling_price=F('medication__price'),
        profit_per_unit=F('medication__price') - Avg('unit_price'),
        profit_margin_percent=Case(
            When(medication__price__gt=0, then=(F('medication__price') - Avg('unit_price')) / F('medication__price') * 100),
            default=Value(0),
            output_field=models.DecimalField()
        )
    ).order_by('-profit_margin_percent')

    # Category Revenue Performance
    category_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).values(
        'prescription_item__medication__category__name'
    ).annotate(
        total_revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')),
        total_quantity=Sum('dispensed_quantity'),
        avg_price=Avg('prescription_item__medication__price')
    ).order_by('-total_revenue')

    # Patient Revenue Analysis
    patient_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).values(
        'prescription_item__prescription__patient__first_name',
        'prescription_item__prescription__patient__last_name',
        'prescription_item__prescription__patient__id'
    ).annotate(
        total_spent=Sum(F('dispensed_quantity') * F('prescription_item__medication__price')),
        total_prescriptions=Count('prescription_item__prescription', distinct=True),
        total_medications=Sum('dispensed_quantity')
    ).order_by('-total_spent')[:20]  # Top 20 patients

    # Revenue Performance Metrics
    total_revenue = prescription_revenue['total_revenue'] or 0
    total_cost = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).aggregate(total=Sum('total_price'))['total'] or 0

    gross_profit = total_revenue - total_cost
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Weekly Revenue Trends
    weekly_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).annotate(
        week=TruncWeek('dispensed_date')
    ).values('week').annotate(
        revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price'))
    ).order_by('week')

    context = {
        'prescription_revenue': prescription_revenue,
        'monthly_revenue': monthly_revenue,
        'medication_revenue': medication_revenue,
        'profit_analysis': profit_analysis,
        'category_revenue': category_revenue,
        'patient_revenue': patient_revenue,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'gross_profit': gross_profit,
        'profit_margin': profit_margin,
        'weekly_revenue': weekly_revenue,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Revenue Analysis'
    }

    return render(request, 'pharmacy/revenue_analysis.html', context)

@login_required
@permission_required('pharmacy.view_purchase', raise_exception=True)
def expense_analysis(request):
    """Comprehensive expense analysis for pharmacy operations"""
    from django.db.models import Case, When, Value, F, Sum, Count, Avg, Min, Max, StdDev
    from django.db.models.functions import TruncMonth
    from django.db import models

    # Date range for analysis (default to last 12 months)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)

    # Total Procurement Expenses
    procurement_expenses = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).aggregate(
        total_expenses=Sum('total_amount'),
        total_orders=Count('id'),
        avg_order_value=Avg('total_amount'),
        pending_payments=Sum('total_amount', filter=Q(payment_status='pending'))
    )

    # Monthly Expense Trends
    monthly_expenses = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('purchase_date')
    ).values('month').annotate(
        total_expenses=Sum('total_amount'),
        order_count=Count('id'),
        avg_order_value=Avg('total_amount')
    ).order_by('month')

    # Supplier Expense Analysis
    supplier_expenses = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).values(
        'supplier__name', 'supplier__id'
    ).annotate(
        total_spent=Sum('total_amount'),
        order_count=Count('id'),
        avg_order_value=Avg('total_amount'),
        payment_efficiency=Case(
            When(total_amount__gt=0, then=Sum('total_amount', filter=Q(payment_status='paid')) / Sum('total_amount') * 100),
            default=Value(0),
            output_field=models.DecimalField()
        )
    ).order_by('-total_spent')

    # Category Expense Analysis
    category_expenses = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).values(
        'medication__category__name'
    ).annotate(
        total_cost=Sum('total_price'),
        total_quantity=Sum('quantity'),
        avg_unit_cost=Avg('unit_price'),
        order_frequency=Count('purchase', distinct=True)
    ).order_by('-total_cost')

    # Medication Cost Efficiency Analysis
    medication_cost_efficiency = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).values(
        'medication__name', 'medication__id'
    ).annotate(
        total_cost=Sum('total_price'),
        total_quantity=Sum('quantity'),
        avg_unit_cost=Avg('unit_price'),
        min_unit_cost=Min('unit_price'),
        max_unit_cost=Max('unit_price'),
        cost_variance=StdDev('unit_price'),
        potential_savings=Case(
            When(unit_price__gt=Min('unit_price'),
                 then=(Avg('unit_price') - Min('unit_price')) * Sum('quantity')),
            default=Value(0),
            output_field=models.DecimalField()
        )
    ).order_by('-potential_savings')

    # Payment Status Analysis
    payment_analysis = Purchase.objects.filter(
        purchase_date__range=[start_date, end_date]
    ).values('payment_status').annotate(
        count=Count('id'),
        total_amount=Sum('total_amount')
    )

    # Cost Optimization Opportunities
    # Find medications with high price variance between suppliers
    price_variance_opportunities = PurchaseItem.objects.filter(
        purchase__purchase_date__range=[start_date, end_date]
    ).values(
        'medication__name'
    ).annotate(
        avg_price=Avg('unit_price'),
        min_price=Min('unit_price'),
        max_price=Max('unit_price'),
        price_range=Max('unit_price') - Min('unit_price'),
        supplier_count=Count('purchase__supplier', distinct=True)
    ).filter(
        supplier_count__gt=1,
        price_range__gt=0
    ).order_by('-price_range')

    # Expense Ratios and KPIs
    total_expenses = procurement_expenses['total_expenses'] or 0

    # Calculate expense ratios
    expense_ratios = {
        'procurement_to_revenue': 0,
        'avg_monthly_expense': total_expenses / 12 if total_expenses > 0 else 0,
        'expense_per_order': procurement_expenses['avg_order_value'] or 0
    }

    # Get revenue for ratio calculation
    total_revenue = DispensingLog.objects.filter(
        dispensed_date__date__range=[start_date, end_date]
    ).aggregate(
        revenue=Sum(F('dispensed_quantity') * F('prescription_item__medication__price'))
    )['revenue'] or 0

    if total_revenue > 0:
        expense_ratios['procurement_to_revenue'] = (total_expenses / total_revenue) * 100

    context = {
        'procurement_expenses': procurement_expenses,
        'monthly_expenses': monthly_expenses,
        'supplier_expenses': supplier_expenses,
        'category_expenses': category_expenses,
        'medication_efficiency': medication_cost_efficiency,
        'payment_analysis': payment_analysis,
        'optimization_opportunities': price_variance_opportunities,
        'expense_ratios': expense_ratios,
        'total_expenses': total_expenses,
        'total_revenue': total_revenue,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Expense Analysis'
    }

    return render(request, 'pharmacy/expense_analysis.html', context)

@login_required
@permission_required('pharmacy.view_purchase', raise_exception=True)
def automated_reorder_suggestions(request):
    """Generate automated reorder suggestions based on consumption patterns"""

    # Get medications that need reordering based on various criteria
    suggestions = []

    # Criteria 1: Stock below reorder level
    low_stock_items = MedicationInventory.objects.filter(
        stock_quantity__lte=F('reorder_level')
    ).select_related('medication')

    for item in low_stock_items:
        # Calculate suggested order quantity based on consumption rate
        last_30_days_consumption = DispensingLog.objects.filter(
            prescription_item__medication=item.medication,
            dispensed_date__gte=timezone.now() - timedelta(days=30)
        ).aggregate(total=Sum('dispensed_quantity'))['total'] or 0

        # Calculate monthly consumption rate
        monthly_consumption = last_30_days_consumption

        # Suggest 2-3 months worth of stock
        suggested_quantity = max(monthly_consumption * 2, item.reorder_level * 2)

        # Find best supplier based on price and reliability
        best_supplier = get_best_supplier_for_medication(item.medication)

        suggestions.append({
            'medication': item.medication,
            'current_stock': item.stock_quantity,
            'reorder_level': item.reorder_level,
            'monthly_consumption': monthly_consumption,
            'suggested_quantity': suggested_quantity,
            'best_supplier': best_supplier,
            'urgency': 'high' if item.stock_quantity <= item.reorder_level * 0.5 else 'medium'
        })

    # Criteria 2: Fast-moving items that might run out soon
    from django.db.models import Subquery, OuterRef
    last_30_days = timezone.now() - timedelta(days=30)
    fast_moving_items = MedicationInventory.objects.annotate(
        consumption_rate=Subquery(
            DispensingLog.objects.filter(
                prescription_item__medication=OuterRef('medication'),
                dispensed_date__gte=last_30_days
            ).values('prescription_item__medication').annotate(
                total=Sum('dispensed_quantity')
            ).values('total')[:1]
        )
    ).filter(
        consumption_rate__gt=0,
        stock_quantity__gt=F('reorder_level')
    ).select_related('medication')

    for item in fast_moving_items:
        consumption_rate = item.consumption_rate or 0
        days_until_reorder = (item.stock_quantity - item.reorder_level) / (consumption_rate / 30) if consumption_rate > 0 else 999

        if days_until_reorder <= 14:  # Will hit reorder level in 2 weeks
            best_supplier = get_best_supplier_for_medication(item.medication)
            suggested_quantity = consumption_rate * 2  # 2 months worth

            suggestions.append({
                'medication': item.medication,
                'current_stock': item.stock_quantity,
                'reorder_level': item.reorder_level,
                'monthly_consumption': consumption_rate,
                'suggested_quantity': suggested_quantity,
                'best_supplier': best_supplier,
                'urgency': 'medium',
                'days_until_reorder': int(days_until_reorder)
            })

    context = {
        'suggestions': suggestions,
        'title': 'Automated Reorder Suggestions'
    }

    return render(request, 'pharmacy/reorder_suggestions.html', context)

def get_best_supplier_for_medication(medication):
    """Get the best supplier for a medication based on price and reliability"""

    # Get recent purchase data for this medication
    recent_purchases = PurchaseItem.objects.filter(
        medication=medication,
        purchase__purchase_date__gte=timezone.now().date() - timedelta(days=180)
    ).select_related('purchase__supplier')

    if not recent_purchases.exists():
        return None

    # Calculate supplier scores
    supplier_scores = {}

    for purchase_item in recent_purchases:
        supplier = purchase_item.purchase.supplier

        if supplier.id not in supplier_scores:
            supplier_scores[supplier.id] = {
                'supplier': supplier,
                'total_orders': 0,
                'avg_price': 0,
                'prices': [],
                'on_time_deliveries': 0,
                'total_deliveries': 0
            }

        supplier_scores[supplier.id]['total_orders'] += 1
        supplier_scores[supplier.id]['prices'].append(purchase_item.unit_price)
        supplier_scores[supplier.id]['total_deliveries'] += 1

        # Count on-time deliveries (paid orders are considered delivered)
        if purchase_item.purchase.payment_status == 'paid':
            supplier_scores[supplier.id]['on_time_deliveries'] += 1

    # Calculate final scores
    best_supplier = None
    best_score = 0

    for supplier_id, data in supplier_scores.items():
        avg_price = float(sum(data['prices']) / len(data['prices']))
        reliability_score = float(data['on_time_deliveries'] / data['total_deliveries']) if data['total_deliveries'] > 0 else 0.0

        # Score based on price (lower is better) and reliability (higher is better)
        # Normalize price score (assuming lower prices are better)
        price_score = 1.0 / avg_price if avg_price > 0 else 0.0

        # Combined score (weighted: 60% reliability, 40% price)
        combined_score = (reliability_score * 0.6) + (price_score * 0.4)

        if combined_score > best_score:
            best_score = combined_score
            best_supplier = data['supplier']
            best_supplier.avg_price = avg_price
            best_supplier.reliability_score = reliability_score

    return best_supplier

@login_required
@permission_required('pharmacy.view_bulkstoreinventory', raise_exception=True)
def bulk_store_dashboard(request):
    """Dashboard for bulk store management"""
    from .models import BulkStore, BulkStoreInventory, MedicationTransfer

    # Get or create main bulk store
    bulk_store, created = BulkStore.objects.get_or_create(
        name='Main Bulk Store',
        defaults={
            'location': 'Central Storage Area',
            'description': 'Main bulk storage for all procured medications',
            'capacity': 50000,
            'temperature_controlled': True,
            'humidity_controlled': True,
            'security_level': 'high',
            'is_active': True
        }
    )

    # Get bulk store inventory
    bulk_inventory = BulkStoreInventory.objects.filter(
        bulk_store=bulk_store,
        stock_quantity__gt=0
    ).select_related('medication', 'supplier').order_by('medication__name')

    # Get recent transfers
    recent_transfers = MedicationTransfer.objects.filter(
        from_bulk_store=bulk_store
    ).select_related(
        'medication', 'to_active_store__dispensary', 'requested_by'
    ).order_by('-requested_at')[:10]

    # Get pending transfer requests
    pending_transfers = MedicationTransfer.objects.filter(
        from_bulk_store=bulk_store,
        status='pending'
    ).select_related(
        'medication', 'to_active_store__dispensary', 'requested_by'
    ).order_by('requested_at')

    # Get available dispensaries
    from .models import Dispensary, ActiveStore
    dispensaries = Dispensary.objects.filter(is_active=True).order_by('name')

    # Create default dispensaries if none exist
    if not dispensaries.exists():
        default_dispensaries = [
            {
                'name': 'Main Pharmacy',
                'location': 'Ground Floor, Main Building',
                'description': 'Primary pharmacy dispensary for outpatient services'
            },
            {
                'name': 'Emergency Pharmacy',
                'location': 'Emergency Department',
                'description': 'Emergency pharmacy for urgent medication needs'
            },
            {
                'name': 'Inpatient Pharmacy',
                'location': 'Second Floor, Ward Block',
                'description': 'Pharmacy serving inpatient wards and units'
            },
            {
                'name': 'Pediatric Pharmacy',
                'location': 'Pediatric Wing',
                'description': 'Specialized pharmacy for pediatric medications'
            }
        ]

        for dispensary_data in default_dispensaries:
            Dispensary.objects.create(**dispensary_data)

        # Refresh the queryset
        dispensaries = Dispensary.objects.filter(is_active=True).order_by('name')

    # Ensure each dispensary has an active store
    for dispensary in dispensaries:
        ActiveStore.objects.get_or_create(
            dispensary=dispensary,
            defaults={
                'name': f"{dispensary.name} Active Store",
                'location': dispensary.location or f"{dispensary.name} Location",
                'description': f"Active storage area for {dispensary.name}",
                'capacity': 1000,
                'temperature_controlled': False,
                'humidity_controlled': False,
                'security_level': 'medium',
                'is_active': True
            }
        )

    # Calculate statistics
    total_medications = bulk_inventory.count()
    total_stock_value = bulk_inventory.aggregate(
        total=Sum(F('stock_quantity') * F('unit_cost'))
    )['total'] or 0

    low_stock_items = bulk_inventory.filter(stock_quantity__lte=50)
    expiring_soon = bulk_inventory.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
    ).exclude(expiry_date__isnull=True)

    context = {
        'bulk_store': bulk_store,
        'bulk_inventory': bulk_inventory,
        'recent_transfers': recent_transfers,
        'pending_transfers': pending_transfers,
        'dispensaries': dispensaries,
        'total_medications': total_medications,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_items.count(),
        'expiring_soon_count': expiring_soon.count(),
        'title': 'Bulk Store Dashboard'
    }

    return render(request, 'pharmacy/bulk_store_dashboard.html', context)

@login_required
@permission_required('pharmacy.add_medicationtransfer', raise_exception=True)
def request_medication_transfer(request):
    """Request transfer of medication from bulk store to active store"""
    from .models import BulkStore, ActiveStore, BulkStoreInventory, MedicationTransfer

    if request.method == 'POST':
        medication_id = request.POST.get('medication')
        active_store_id = request.POST.get('active_store')
        quantity = int(request.POST.get('quantity', 0))
        notes = request.POST.get('notes', '')

        try:
            medication = get_object_or_404(Medication, id=medication_id)
            active_store = get_object_or_404(ActiveStore, id=active_store_id)

            # Get main bulk store
            bulk_store = BulkStore.objects.get(name='Main Bulk Store')

            # Check if sufficient stock exists in bulk store
            bulk_inventory = BulkStoreInventory.objects.filter(
                medication=medication,
                bulk_store=bulk_store,
                stock_quantity__gte=quantity
            ).first()

            if not bulk_inventory:
                messages.error(request, f'Insufficient stock in bulk store for {medication.name}')
                return redirect('pharmacy:bulk_store_dashboard')

            # Create transfer request
            transfer = MedicationTransfer.objects.create(
                medication=medication,
                from_bulk_store=bulk_store,
                to_active_store=active_store,
                quantity=quantity,
                batch_number=bulk_inventory.batch_number,
                expiry_date=bulk_inventory.expiry_date,
                unit_cost=bulk_inventory.unit_cost,
                requested_by=request.user,
                notes=notes
            )

            messages.success(
                request,
                f'Transfer request created for {quantity} units of {medication.name} '
                f'to {active_store.dispensary.name}'
            )

        except Exception as e:
            messages.error(request, f'Error creating transfer request: {str(e)}')

    return redirect('pharmacy:bulk_store_dashboard')

@login_required
@permission_required('pharmacy.change_medicationtransfer', raise_exception=True)
def approve_medication_transfer(request, transfer_id):
    """Approve a medication transfer request"""
    from .models import MedicationTransfer

    transfer = get_object_or_404(MedicationTransfer, id=transfer_id)

    if transfer.can_approve():
        transfer.approved_by = request.user
        transfer.approved_at = timezone.now()
        transfer.status = 'in_transit'
        transfer.save()

        messages.success(
            request,
            f'Transfer approved: {transfer.quantity} units of {transfer.medication.name} '
            f'to {transfer.to_active_store.dispensary.name}'
        )
    else:
        messages.error(request, 'Transfer cannot be approved in current status')

    return redirect('pharmacy:bulk_store_dashboard')

@login_required
@permission_required('pharmacy.change_medicationtransfer', raise_exception=True)
def execute_medication_transfer(request, transfer_id):
    """Execute an approved medication transfer"""
    from .models import MedicationTransfer

    transfer = get_object_or_404(MedicationTransfer, id=transfer_id)

    try:
        if transfer.can_execute():
            transfer.execute_transfer(request.user)

            messages.success(
                request,
                f'Transfer completed: {transfer.quantity} units of {transfer.medication.name} '
                f'moved to {transfer.to_active_store.dispensary.name}'
            )
        else:
            messages.error(request, 'Transfer cannot be executed in current status')

    except Exception as e:
        messages.error(request, f'Error executing transfer: {str(e)}')

    return redirect('pharmacy:bulk_store_dashboard')

@login_required
def features_showcase(request):
    """Features showcase page demonstrating all new functionality"""
    context = {
        'title': 'HMS Pharmacy Features Showcase'
    }
    return render(request, 'pharmacy/features_showcase.html', context)

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

            # Auto-generate invoice number
            import uuid
            purchase.invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

            # Set initial total amount to 0 (will be calculated when items are added)
            purchase.total_amount = 0

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

    # Get approval history
    approvals = purchase.approvals.all().select_related('approver').order_by('-created_at')

    # Get payment history if exists
    payments = []
    try:
        from billing.models import Payment
        payments = Payment.objects.filter(
            invoice__purchase=purchase
        ).select_related('received_by').order_by('-payment_date')
    except:
        pass

    # Handle different POST actions
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_item':
            # Check if purchase is in draft status
            if purchase.approval_status != 'draft':
                messages.error(request, "Items can only be added to draft purchases.")
                return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

            item_form = PurchaseItemForm(request.POST)
            if item_form.is_valid():
                try:
                    purchase_item = item_form.save(commit=False)
                    purchase_item.purchase = purchase
                    purchase_item.save()

                    # Update purchase total amount using the new method
                    purchase.update_total_amount()

                    messages.success(request, f"Added {purchase_item.quantity} units of {purchase_item.medication.name} to purchase.")
                    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
                except Exception as e:
                    messages.error(request, f"Error saving item: {str(e)}")
            else:
                # Show specific form errors
                error_messages = []
                for field, errors in item_form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                messages.error(request, f"Form validation errors: {'; '.join(error_messages)}")

        elif action == 'submit_for_approval':
            if purchase.approval_status == 'draft' and purchase.items.exists():
                try:
                    purchase.approval_status = 'pending'
                    purchase.approval_updated_at = timezone.now()
                    # Store submission comments in approval_notes for now
                    submission_comments = request.POST.get('approval_comments', '')
                    if submission_comments:
                        purchase.approval_notes = f"Submission comments: {submission_comments}"
                    purchase.save()

                    messages.success(request, "Purchase submitted for approval successfully!")
                    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
                except Exception as e:
                    messages.error(request, f"Error submitting for approval: {str(e)}")
            else:
                if purchase.approval_status != 'draft':
                    messages.error(request, f"Only draft purchases can be submitted for approval. Current status: {purchase.approval_status}")
                elif not purchase.items.exists():
                    messages.error(request, "Cannot submit empty purchase for approval. Please add items first.")
                else:
                    messages.error(request, "Purchase cannot be submitted for approval.")

        elif action == 'approve_purchase':
            if purchase.can_be_approved() and request.user.has_perm('pharmacy.approve_purchase'):
                purchase.approval_status = 'approved'
                purchase.current_approver = request.user
                purchase.approval_notes = request.POST.get('approval_notes', '')
                purchase.approval_updated_at = timezone.now()
                purchase.save()

                # Update approval record
                approval = purchase.approvals.filter(status='pending').first()
                if approval:
                    approval.status = 'approved'
                    approval.comments = request.POST.get('approval_notes', '')
                    approval.save()

                messages.success(request, "Purchase approved successfully!")
                return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
            else:
                messages.error(request, "You don't have permission to approve this purchase.")

        elif action == 'reject_purchase':
            if purchase.approval_status == 'pending' and request.user.has_perm('pharmacy.approve_purchase'):
                purchase.approval_status = 'rejected'
                purchase.current_approver = request.user
                purchase.approval_notes = request.POST.get('rejection_notes', '')
                purchase.approval_updated_at = timezone.now()
                purchase.save()

                # Update approval record
                approval = purchase.approvals.filter(status='pending').first()
                if approval:
                    approval.status = 'rejected'
                    approval.comments = request.POST.get('rejection_notes', '')
                    approval.save()

                messages.warning(request, "Purchase rejected.")
                return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)
            else:
                messages.error(request, "You don't have permission to reject this purchase.")

        elif action == 'process_payment':
            if purchase.can_be_paid() and request.user.has_perm('pharmacy.pay_purchase'):
                try:
                    payment_amount = request.POST.get('payment_amount')
                    payment_method = request.POST.get('payment_method', 'cash')

                    if not payment_amount:
                        payment_amount = purchase.total_amount
                    else:
                        payment_amount = float(payment_amount)

                    # Update purchase payment status
                    if payment_amount >= purchase.total_amount:
                        purchase.payment_status = 'paid'

                        # Automatically move all purchased medications to bulk store when fully paid
                        for item in purchase.items.all():
                            try:
                                item._add_to_bulk_store()
                            except Exception as e:
                                messages.warning(request, f"Warning: Could not add {item.medication.name} to bulk store: {str(e)}")

                        messages.info(request, "All purchased medications have been automatically moved to bulk store.")
                    else:
                        purchase.payment_status = 'partial'

                    purchase.save()

                    # Create payment record (assuming Payment model exists)
                    from django.apps import apps
                    try:
                        Payment = apps.get_model('billing', 'Payment')
                        Payment.objects.create(
                            purchase=purchase,
                            amount=payment_amount,
                            payment_method=payment_method,
                            processed_by=request.user,
                            reference=request.POST.get('payment_reference', ''),
                            notes=request.POST.get('payment_notes', '')
                        )
                    except LookupError:
                        # Payment model doesn't exist, just update purchase status
                        pass

                    messages.success(request, f"Payment of ${payment_amount} processed successfully!")
                    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

                except (ValueError, TypeError) as e:
                    messages.error(request, f"Invalid payment amount: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Error processing payment: {str(e)}")
            else:
                messages.error(request, "You don't have permission to process payments for this purchase.")

    # Initialize forms
    if request.method == 'POST' and request.POST.get('action') == 'add_item':
        item_form = PurchaseItemForm(request.POST)
    else:
        item_form = PurchaseItemForm()

    context = {
        'purchase': purchase,
        'purchase_items': purchase_items,
        'item_form': item_form,
        'approvals': approvals,
        'payments': payments,
        'can_approve': request.user.has_perm('pharmacy.approve_purchase'),
        'can_pay': request.user.has_perm('pharmacy.pay_purchase'),
        'title': f'Purchase Detail - #{purchase.invoice_number}'
    }
    return render(request, 'pharmacy/purchase_detail.html', context)

@login_required
@permission_required('pharmacy.change_purchase', raise_exception=True)
def process_purchase_payment(request, purchase_id):
    """Process payment for an approved purchase"""
    purchase = get_object_or_404(Purchase, id=purchase_id)

    if not purchase.can_be_paid():
        messages.error(request, "This purchase cannot be paid at this time.")
        return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment_amount = Decimal(request.POST.get('payment_amount', '0'))
                payment_method = request.POST.get('payment_method', 'bank_transfer')
                payment_reference = request.POST.get('payment_reference', '')
                payment_notes = request.POST.get('payment_notes', '')

                if payment_amount <= 0:
                    messages.error(request, "Payment amount must be greater than zero.")
                    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

                # Create or get invoice for the purchase
                try:
                    from billing.models import Invoice, InvoiceItem, Payment
                    from core.models import Service

                    # Get or create procurement service
                    service, created = Service.objects.get_or_create(
                        name="Procurement Payment",
                        defaults={
                            'description': 'Payment for procurement/purchase orders',
                            'price': 0,
                            'tax_percentage': 0
                        }
                    )

                    # Create invoice if it doesn't exist
                    invoice, created = Invoice.objects.get_or_create(
                        purchase=purchase,
                        defaults={
                            'patient': None,  # Procurement invoices don't have patients
                            'status': 'pending',
                            'total_amount': purchase.total_amount,
                            'subtotal': purchase.total_amount,
                            'tax_amount': 0,
                            'created_by': request.user,
                            'source_app': 'pharmacy_procurement'
                        }
                    )

                    if created:
                        # Create invoice item
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            service=service,
                            description=f"Procurement Payment - Purchase #{purchase.invoice_number}",
                            quantity=1,
                            unit_price=purchase.total_amount,
                            tax_amount=0,
                            total_amount=purchase.total_amount,
                        )

                    # Create payment record
                    payment = Payment.objects.create(
                        invoice=invoice,
                        amount=payment_amount,
                        payment_method=payment_method,
                        transaction_id=payment_reference,
                        notes=payment_notes,
                        received_by=request.user,
                        payment_date=timezone.now().date()
                    )

                    # Update invoice payment status
                    invoice.amount_paid += payment_amount
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = 'paid'
                        purchase.payment_status = 'paid'
                    else:
                        invoice.status = 'partially_paid'
                        purchase.payment_status = 'partial'

                    invoice.save()
                    purchase.save()

                    messages.success(request, f"Payment of ₦{payment_amount:,.2f} recorded successfully!")
                    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

                except Exception as e:
                    messages.error(request, f"Error processing payment: {str(e)}")
                    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
            return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

    # If GET request, redirect back to purchase detail
    return redirect('pharmacy:purchase_detail', purchase_id=purchase.id)

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
        if purchase.can_be_approved():
            purchase.approval_status = 'approved'
            purchase.approval_notes = request.POST.get('approval_notes', '')
            purchase.approval_updated_at = timezone.now()
            purchase.save()
            messages.success(request, f"Purchase #{purchase.invoice_number} approved successfully! Total amount: ₦{purchase.total_amount}")
        else:
            if purchase.approval_status != 'pending':
                messages.warning(request, "Purchase is not in 'pending' status and cannot be approved.")
            elif not purchase.items.exists():
                messages.error(request, "Cannot approve purchase with no items.")
            elif purchase.total_amount <= 0:
                messages.error(request, "Cannot approve purchase with zero or negative total amount.")
            else:
                messages.error(request, "Purchase cannot be approved at this time.")
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
    """Enhanced prescription list with comprehensive search functionality"""
    prescriptions = Prescription.objects.all().select_related('patient', 'doctor').order_by('-prescription_date')
    form = PrescriptionSearchForm(request.GET or None)

    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        patient_number = form.cleaned_data.get('patient_number')
        medication_name = form.cleaned_data.get('medication_name')
        status = form.cleaned_data.get('status')
        payment_status = form.cleaned_data.get('payment_status')
        doctor = form.cleaned_data.get('doctor')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')

        # Enhanced patient search by name, number, or phone
        if search_query:
            prescriptions = prescriptions.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query)
            )

        if patient_number:
            prescriptions = prescriptions.filter(
                Q(patient__patient_id__icontains=patient_number)
            )

        if medication_name:
            prescriptions = prescriptions.filter(
                items__medication__name__icontains=medication_name
            ).distinct()

        if status:
            prescriptions = prescriptions.filter(status=status)

        if payment_status:
            prescriptions = prescriptions.filter(payment_status=payment_status)

        if doctor:
            prescriptions = prescriptions.filter(doctor=doctor)

        if date_from:
            prescriptions = prescriptions.filter(prescription_date__gte=date_from)

        if date_to:
            prescriptions = prescriptions.filter(prescription_date__lte=date_to)

    paginator = Paginator(prescriptions, 15) # Show 15 prescriptions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
        'title': 'Prescription List',
        'total_prescriptions': prescriptions.count()
    }
    return render(request, 'pharmacy/prescription_list.html', context)


@login_required
@permission_required('pharmacy.view_prescription', raise_exception=True)
def patient_prescriptions(request, patient_id):
    """View all prescriptions for a specific patient - enhanced for pharmacy staff"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Get all prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=patient).select_related(
        'doctor', 'invoice'
    ).prefetch_related(
        'items__medication'
    ).order_by('-prescription_date')

    # Apply additional filters if provided
    status_filter = request.GET.get('status')
    payment_status_filter = request.GET.get('payment_status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if status_filter:
        prescriptions = prescriptions.filter(status=status_filter)

    if payment_status_filter:
        prescriptions = prescriptions.filter(payment_status=payment_status_filter)

    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            prescriptions = prescriptions.filter(prescription_date__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            prescriptions = prescriptions.filter(prescription_date__lte=date_to)
        except ValueError:
            pass

    # Calculate summary statistics
    total_prescriptions = prescriptions.count()
    pending_prescriptions = prescriptions.filter(status='pending').count()
    dispensed_prescriptions = prescriptions.filter(status='dispensed').count()
    unpaid_prescriptions = prescriptions.filter(payment_status='unpaid').count()

    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'patient': patient,
        'page_obj': page_obj,
        'total_prescriptions': total_prescriptions,
        'pending_prescriptions': pending_prescriptions,
        'dispensed_prescriptions': dispensed_prescriptions,
        'unpaid_prescriptions': unpaid_prescriptions,
        'status_filter': status_filter,
        'payment_status_filter': payment_status_filter,
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
        'title': f'Prescriptions for {patient.get_full_name()}'
    }
    return render(request, 'pharmacy/patient_prescriptions.html', context)

@login_required
@permission_required('pharmacy.view_prescription', raise_exception=True)
def prescription_detail(request, prescription_id):
    prescription = get_object_or_404(Prescription.objects.select_related('patient', 'doctor'), id=prescription_id)
    prescription_items = prescription.items.all().select_related('medication')
    medications = Medication.objects.filter(is_active=True).order_by('name')
    # Add form for the modal
    item_form = PrescriptionItemForm()
    
    context = {
        'prescription': prescription,
        'prescription_items': prescription_items,
        'medications': medications,
        'item_form': item_form,
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
# @permission_required('pharmacy.change_prescription', raise_exception=True)  # Temporarily disabled for testing
def dispense_prescription(request, prescription_id):
    """Modern dispensing view with formset support and enhanced payment verification"""
    print(f"=== DISPENSE VIEW CALLED FOR PRESCRIPTION {prescription_id} ===")

    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Enhanced payment verification
    if not prescription.is_payment_verified():
        messages.error(request,
            'Payment must be completed before dispensing medications. '
            'Please process payment through the billing office or patient wallet first.'
        )
        # Redirect to payment page if invoice exists, otherwise to prescription detail
        if hasattr(prescription, 'invoice') and prescription.invoice:
            return redirect('pharmacy:prescription_payment', prescription_id=prescription.id)
        else:
            return redirect('pharmacy:create_prescription_invoice', prescription_id=prescription.id)

    # Check if prescription can be dispensed (includes other conditions)
    can_dispense, reason = prescription.can_be_dispensed()
    if not can_dispense:
        messages.warning(request, reason)
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    if request.method == 'POST':
        return _handle_formset_dispensing_submission(request, prescription)

    # GET request - display the dispensing interface
    pending_items = prescription.items.filter(is_dispensed=False).select_related('medication')

    print(f"Prescription {prescription.id} has {pending_items.count()} pending items")
    for item in pending_items:
        print(f"Item {item.id}: {item.medication.name}, is_dispensed={item.is_dispensed}")

    if not pending_items.exists():
        messages.info(request, 'All items in this prescription have been dispensed.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Add debug message
    messages.info(request, f'Found {pending_items.count()} items ready for dispensing.')

    # Create formset for the template
    from django.forms import formset_factory

    # Create initial data for the formset
    initial_data = []
    for item in pending_items:
        initial_data.append({
            'item_id': item.id,
            'quantity_to_dispense': item.remaining_quantity_to_dispense,
            'dispense_this_item': False,
        })

    # Create the formset
    DispenseItemFormSet = formset_factory(
        DispenseItemForm,
        formset=BaseDispenseItemFormSet,
        extra=0,
        can_delete=False
    )

    # Initialize the formset
    formset = DispenseItemFormSet(initial=initial_data)

    # Attach prescription items to each form for template access
    for form, item in zip(formset.forms, pending_items):
        form.prescription_item = item

    context = {
        'prescription': prescription,
        'formset': formset,
        'dispensaries': Dispensary.objects.filter(is_active=True).order_by('name'),
        'title': f'Dispense Prescription #{prescription.id}'
    }

    print(f"Context formset forms count: {len(formset.forms)}")

    return render(request, 'pharmacy/dispense_prescription.html', context)

@login_required
def dispense_prescription_original(request, prescription_id):
    """Original dispensing view using template"""
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check if prescription can be dispensed (includes payment verification)
    can_dispense, reason = prescription.can_be_dispensed()
    if not can_dispense:
        messages.warning(request, reason)
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    if request.method == 'POST':
        return _handle_dispensing_submission(request, prescription)

    # GET request - display the dispensing interface
    pending_items = prescription.items.filter(is_dispensed=False).select_related('medication')

    print(f"Original view: Found {pending_items.count()} pending items")

    # Add debug message
    messages.info(request, f'Found {pending_items.count()} items ready for dispensing.')

    context = {
        'prescription': prescription,
        'prescription_items': list(pending_items),
        'dispensaries': Dispensary.objects.filter(is_active=True).order_by('name'),
        'title': f'Dispense Prescription #{prescription.id}'
    }
    return render(request, 'pharmacy/dispense_prescription.html', context)

def _handle_dispensing_submission(request, prescription):
    """Handle the actual dispensing process with enhanced error handling and workflow logic"""
    try:
        # Verify payment before processing dispensing
        can_dispense, reason = prescription.can_be_dispensed()
        if not can_dispense:
            messages.error(request, f'Cannot dispense: {reason}')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

        dispensary_id = request.POST.get('dispensary_id')
        if not dispensary_id:
            messages.error(request, 'Please select a dispensary.')
            return redirect('pharmacy:dispense_prescription', prescription_id=prescription.id)

        dispensary = get_object_or_404(Dispensary, id=dispensary_id)
        dispensed_items = []
        errors = []

        with transaction.atomic():
            for key, value in request.POST.items():
                if key.startswith('dispense_item_') and value == 'on':
                    item_id = key.replace('dispense_item_', '')
                    quantity_key = f'quantity_{item_id}'

                    try:
                        quantity = int(request.POST.get(quantity_key, 0))
                    except (ValueError, TypeError):
                        errors.append(f'Invalid quantity for item {item_id}')
                        continue

                    if quantity <= 0:
                        errors.append(f'Quantity must be greater than 0 for item {item_id}')
                        continue

                    try:
                        prescription_item = get_object_or_404(
                            PrescriptionItem,
                            id=item_id,
                            prescription=prescription,
                            is_dispensed=False
                        )

                        # Validate quantity doesn't exceed remaining
                        remaining = prescription_item.remaining_quantity_to_dispense
                        if quantity > remaining:
                            errors.append(f'Cannot dispense {quantity} of {prescription_item.medication.name}. Only {remaining} remaining.')
                            continue

                        # Get or create inventory record
                        inventory, _ = MedicationInventory.objects.get_or_create(
                            medication=prescription_item.medication,
                            dispensary=dispensary,
                            defaults={
                                'stock_quantity': 0,
                                'reorder_level': 10,
                                'last_restock_date': timezone.now()
                            }
                        )

                        if inventory.stock_quantity < quantity:
                            errors.append(f'Insufficient stock for {prescription_item.medication.name}. Available: {inventory.stock_quantity}, Requested: {quantity}')
                            continue

                        # Update inventory
                        inventory.stock_quantity -= quantity
                        inventory.save()

                        # Create dispensing log
                        DispensingLog.objects.create(
                            prescription_item=prescription_item,
                            dispensed_quantity=quantity,
                            dispensed_by=request.user,
                            dispensary=dispensary,
                            unit_price_at_dispense=prescription_item.medication.price,
                            total_price_for_this_log=prescription_item.medication.price * quantity
                        )

                        # Update prescription item
                        prescription_item.quantity_dispensed_so_far += quantity
                        prescription_item.dispensed_by = request.user
                        prescription_item.dispensed_date = timezone.now()

                        # Mark as dispensed if fully dispensed
                        if prescription_item.quantity_dispensed_so_far >= prescription_item.quantity:
                            prescription_item.is_dispensed = True

                        prescription_item.save()
                        dispensed_items.append(f'{prescription_item.medication.name} ({quantity} units)')

                    except PrescriptionItem.DoesNotExist:
                        errors.append(f'Prescription item {item_id} not found or already dispensed')
                        continue

        # Handle results
        if errors:
            for error in errors:
                messages.error(request, error)

        if dispensed_items:
            messages.success(request, f'Successfully dispensed: {", ".join(dispensed_items)}')

            # Update prescription status based on dispensing progress
            _update_prescription_status_after_dispensing(prescription)
        else:
            if not errors:
                messages.warning(request, 'No items were selected for dispensing.')

    except Exception as e:
        messages.error(request, f'Unexpected error during dispensing: {str(e)}')
        logging.error(f"Dispensing error for prescription {prescription.id}: {str(e)}")

    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

def _update_prescription_status_after_dispensing(prescription):
    """Update prescription status based on dispensing progress and handle invoice updates"""
    total_items = prescription.items.count()
    dispensed_items = prescription.items.filter(is_dispensed=True).count()

    if dispensed_items == 0:
        # No items dispensed yet, keep current status
        return
    elif dispensed_items == total_items:
        # All items fully dispensed
        prescription.status = 'dispensed'
        prescription.save()

        # Note: Invoice status should only be updated through payment processing, not dispensing
        # Dispensing indicates service delivery, but payment status should remain separate
        if prescription.invoice:
            try:
                logging.info(f"Prescription {prescription.id} fully dispensed. Invoice {prescription.invoice.id} payment status: {prescription.invoice.status}")
            except Exception as e:
                logging.error(f"Error logging invoice status for prescription {prescription.id}: {str(e)}")
    else:
        # Some items dispensed but not all
        prescription.status = 'partially_dispensed'
        prescription.save()

        # Update invoice to partial if exists
        if prescription.invoice and prescription.invoice.status == 'pending':
            try:
                prescription.invoice.status = 'partial'
                prescription.invoice.save()
                logging.info(f"Invoice {prescription.invoice.id} marked as partial after partial dispensing of prescription {prescription.id}")
            except Exception as e:
                logging.error(f"Error updating invoice status for prescription {prescription.id}: {str(e)}")

def _handle_formset_dispensing_submission(request, prescription):
    """Handle dispensing submission from formset-based template"""
    try:
        # Verify payment before processing dispensing
        can_dispense, reason = prescription.can_be_dispensed()
        if not can_dispense:
            messages.error(request, f'Cannot dispense: {reason}')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

        # Get the selected dispensary from the dropdown
        dispensary_id = request.POST.get('dispensary_select')
        if not dispensary_id:
            messages.error(request, 'Please select a dispensary.')
            return redirect('pharmacy:dispense_prescription', prescription_id=prescription.id)

        dispensary = get_object_or_404(Dispensary, id=dispensary_id)
        dispensed_items = []
        errors = []

        # Get form count from formset management form
        form_count = int(request.POST.get('form-TOTAL_FORMS', 0))

        with transaction.atomic():
            for i in range(form_count):
                # Check if this item should be dispensed
                dispense_checkbox = request.POST.get(f'form-{i}-dispense_this_item')
                if dispense_checkbox == 'on':
                    # Get the item details
                    item_id = request.POST.get(f'form-{i}-item_id')
                    quantity_str = request.POST.get(f'form-{i}-quantity_to_dispense', '0')

                    try:
                        quantity = int(quantity_str)
                    except (ValueError, TypeError):
                        errors.append(f'Invalid quantity for item {item_id}')
                        continue

                    if quantity <= 0:
                        errors.append(f'Quantity must be greater than 0 for item {item_id}')
                        continue

                    try:
                        prescription_item = get_object_or_404(
                            PrescriptionItem,
                            id=item_id,
                            prescription=prescription,
                            is_dispensed=False
                        )

                        # Validate quantity doesn't exceed remaining
                        remaining = prescription_item.remaining_quantity_to_dispense
                        if quantity > remaining:
                            errors.append(f'Cannot dispense {quantity} of {prescription_item.medication.name}. Only {remaining} remaining.')
                            continue

                        # Get or create inventory record
                        inventory, _ = MedicationInventory.objects.get_or_create(
                            medication=prescription_item.medication,
                            dispensary=dispensary,
                            defaults={
                                'stock_quantity': 0,
                                'reorder_level': 10,
                                'last_restock_date': timezone.now()
                            }
                        )

                        if inventory.stock_quantity < quantity:
                            errors.append(f'Insufficient stock for {prescription_item.medication.name}. Available: {inventory.stock_quantity}, Requested: {quantity}')
                            continue

                        # Update inventory
                        inventory.stock_quantity -= quantity
                        inventory.save()

                        # Create dispensing log
                        DispensingLog.objects.create(
                            prescription_item=prescription_item,
                            dispensed_quantity=quantity,
                            dispensed_by=request.user,
                            dispensary=dispensary,
                            unit_price_at_dispense=prescription_item.medication.price,
                            total_price_for_this_log=prescription_item.medication.price * quantity
                        )

                        # Update prescription item
                        prescription_item.quantity_dispensed_so_far += quantity
                        prescription_item.dispensed_by = request.user
                        prescription_item.dispensed_date = timezone.now()

                        # Mark as dispensed if fully dispensed
                        if prescription_item.quantity_dispensed_so_far >= prescription_item.quantity:
                            prescription_item.is_dispensed = True

                        prescription_item.save()
                        dispensed_items.append(f'{prescription_item.medication.name} ({quantity} units)')

                    except PrescriptionItem.DoesNotExist:
                        errors.append(f'Prescription item {item_id} not found or already dispensed')
                        continue

        # Handle results
        if errors:
            for error in errors:
                messages.error(request, error)

        if dispensed_items:
            messages.success(request, f'Successfully dispensed: {", ".join(dispensed_items)}')
            # Update prescription status based on dispensing progress
            _update_prescription_status_after_dispensing(prescription)
        else:
            if not errors:
                messages.warning(request, 'No items were selected for dispensing.')

    except Exception as e:
        messages.error(request, f'Unexpected error during dispensing: {str(e)}')
        logging.error(f"Formset dispensing error for prescription {prescription.id}: {str(e)}")

    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

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
def add_prescription_item(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    if request.method == 'POST':
        form = PrescriptionItemForm(request.POST)
        if form.is_valid():
            prescription_item = form.save(commit=False)
            prescription_item.prescription = prescription
            prescription_item.save()
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Medication added to prescription successfully!'
                })
            
            messages.success(request, "Medication added to prescription successfully!")
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        else:
            # Handle AJAX requests with form errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'Error adding medication. Please correct the form errors.'
                })
            
            messages.error(request, "Error adding medication. Please correct the form errors.")
    else:
        form = PrescriptionItemForm()
    
    context = {
        'form': form,
        'prescription': prescription,
        'title': f'Add Medication to Prescription #{prescription.id}'
    }
    return render(request, 'pharmacy/add_prescription_item.html', context)

@login_required
@permission_required('pharmacy.add_medicationinventory', raise_exception=True)
def add_medication_stock(request):
    """View for adding medication stock to dispensary inventory via UI"""
    if request.method == 'POST':
        form = MedicationInventoryForm(request.POST)
        if form.is_valid():
            medication = form.cleaned_data['medication']
            dispensary = form.cleaned_data['dispensary']
            stock_quantity = form.cleaned_data['stock_quantity']
            reorder_level = form.cleaned_data['reorder_level']
            
            # Check if inventory record already exists
            inventory, created = MedicationInventory.objects.get_or_create(
                medication=medication,
                dispensary=dispensary,
                defaults={
                    'stock_quantity': stock_quantity,
                    'reorder_level': reorder_level,
                    'last_restock_date': timezone.now()
                }
            )
            
            if not created:
                # Update existing inventory
                inventory.stock_quantity += stock_quantity
                inventory.last_restock_date = timezone.now()
                inventory.save()
                messages.success(request, f"Added {stock_quantity} units to existing stock. New total: {inventory.stock_quantity} units.")
            else:
                messages.success(request, f"Created new inventory record with {stock_quantity} units.")
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f"Stock updated successfully. Current stock: {inventory.stock_quantity} units.",
                    'new_stock': inventory.stock_quantity
                })
            
            return redirect('pharmacy:medication_inventory_list')
        else:
            # Handle AJAX requests with form errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'Error adding stock. Please correct the form errors.'
                })
            
            messages.error(request, "Error adding stock. Please correct the form errors.")
    else:
        form = MedicationInventoryForm()
    
    context = {
        'form': form,
        'title': 'Add Medication Stock',
        'medications': Medication.objects.filter(is_active=True),
        'dispensaries': Dispensary.objects.filter(is_active=True)
    }
    return render(request, 'pharmacy/add_medication_stock.html', context)

@login_required
@permission_required('pharmacy.add_medicationinventory', raise_exception=True)
def quick_add_stock(request):
    """AJAX view for quickly adding stock from dispense prescription page"""
    if request.method == 'POST':
        medication_id = request.POST.get('medication_id')
        dispensary_id = request.POST.get('dispensary_id')
        stock_quantity = request.POST.get('stock_quantity')
        
        try:
            medication = get_object_or_404(Medication, id=medication_id)
            dispensary = get_object_or_404(Dispensary, id=dispensary_id)
            stock_quantity = int(stock_quantity)
            
            if stock_quantity <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Stock quantity must be greater than 0.'
                })
            
            # Check if inventory record already exists
            inventory, created = MedicationInventory.objects.get_or_create(
                medication=medication,
                dispensary=dispensary,
                defaults={
                    'stock_quantity': stock_quantity,
                    'reorder_level': 10,  # Default reorder level
                    'last_restock_date': timezone.now()
                }
            )
            
            if not created:
                # Update existing inventory
                inventory.stock_quantity += stock_quantity
                inventory.last_restock_date = timezone.now()
                inventory.save()
            
            return JsonResponse({
                'success': True,
                'message': f"Added {stock_quantity} units. Current stock: {inventory.stock_quantity} units.",
                'new_stock': inventory.stock_quantity
            })
            
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Invalid stock quantity. Please enter a valid number.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error adding stock: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

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
def get_stock_quantities(request, prescription_id):
    """AJAX view to get stock quantities for prescription items at a specific dispensary"""
    logging.info(f"get_stock_quantities called for prescription {prescription_id}")
    logging.info(f"Request method: {request.method}")
    logging.info(f"Request content type: {request.content_type}")

    try:
        # Accept both JSON and form-encoded POST
        dispensary_id = None
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            dispensary_id = data.get('dispensary_id')
            logging.info(f"JSON data: {data}")
        else:
            dispensary_id = request.POST.get('dispensary_id')
            logging.info(f"POST data: {dict(request.POST)}")

        logging.info(f"Dispensary ID: {dispensary_id}")

        if not dispensary_id:
            logging.error("No dispensary ID provided")
            return JsonResponse({
                'success': False,
                'error': 'Dispensary ID is required'
            })

        prescription = get_object_or_404(Prescription, id=prescription_id)
        logging.info(f"Found prescription: {prescription}")

        stock_quantities = {}
        for item in prescription.items.all():
            try:
                inventory = MedicationInventory.objects.get(medication=item.medication, dispensary_id=dispensary_id)
                stock_quantities[item.id] = inventory.stock_quantity
                logging.info(f"Item {item.id}: {inventory.stock_quantity} units")
            except MedicationInventory.DoesNotExist:
                stock_quantities[item.id] = 0
                logging.info(f"Item {item.id}: No inventory found")

        logging.info(f"Returning stock quantities: {stock_quantities}")
        return JsonResponse({
            'success': True,
            'stock_quantities': stock_quantities
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

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
    """Comprehensive pharmacy sales statistics by dispensaries"""
    from django.db.models import Q, Sum, Count, Avg
    from datetime import datetime, timedelta
    from decimal import Decimal

    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    dispensary_id = request.GET.get('dispensary')
    medication_id = request.GET.get('medication')
    patient_type = request.GET.get('patient_type')  # nhia or non_nhia

    # Default date range (last 30 days)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Base queryset for dispensing logs
    dispensing_logs = DispensingLog.objects.filter(
        dispensed_date__date__gte=start_date,
        dispensed_date__date__lte=end_date
    ).select_related(
        'prescription_item__prescription__patient',
        'prescription_item__medication',
        'dispensary',
        'dispensed_by'
    )

    # Apply filters
    if dispensary_id:
        dispensing_logs = dispensing_logs.filter(dispensary_id=dispensary_id)

    if medication_id:
        dispensing_logs = dispensing_logs.filter(prescription_item__medication_id=medication_id)

    if patient_type:
        if patient_type == 'nhia':
            dispensing_logs = dispensing_logs.filter(prescription_item__prescription__patient__patient_type='nhia')
        elif patient_type == 'non_nhia':
            dispensing_logs = dispensing_logs.exclude(prescription_item__prescription__patient__patient_type='nhia')

    # Sales by Dispensary
    dispensary_stats = dispensing_logs.values(
        'dispensary__name',
        'dispensary__id'
    ).annotate(
        total_sales=Sum('total_price_for_this_log'),
        total_items=Sum('dispensed_quantity'),
        total_transactions=Count('id'),
        avg_transaction_value=Avg('total_price_for_this_log'),
        unique_patients=Count('prescription_item__prescription__patient', distinct=True),
        unique_medications=Count('prescription_item__medication', distinct=True)
    ).order_by('-total_sales')

    # Top Medications by Sales Value
    top_medications = dispensing_logs.values(
        'prescription_item__medication__name',
        'prescription_item__medication__id'
    ).annotate(
        total_sales=Sum('total_price_for_this_log'),
        total_quantity=Sum('dispensed_quantity'),
        total_transactions=Count('id')
    ).order_by('-total_sales')[:10]

    # Sales by Patient Type (NHIA vs Non-NHIA)
    nhia_stats = dispensing_logs.filter(
        prescription_item__prescription__patient__patient_type='nhia'
    ).aggregate(
        total_sales=Sum('total_price_for_this_log'),
        total_items=Sum('dispensed_quantity'),
        total_transactions=Count('id')
    )

    non_nhia_stats = dispensing_logs.exclude(
        prescription_item__prescription__patient__patient_type='nhia'
    ).aggregate(
        total_sales=Sum('total_price_for_this_log'),
        total_items=Sum('dispensed_quantity'),
        total_transactions=Count('id')
    )

    # Daily Sales Trend
    daily_sales = dispensing_logs.extra(
        select={'day': 'DATE(dispensed_date)'}
    ).values('day').annotate(
        daily_total=Sum('total_price_for_this_log'),
        daily_items=Sum('dispensed_quantity'),
        daily_transactions=Count('id')
    ).order_by('day')

    # Top Performing Staff
    top_staff = dispensing_logs.values(
        'dispensed_by__first_name',
        'dispensed_by__last_name',
        'dispensed_by__id'
    ).annotate(
        total_sales=Sum('total_price_for_this_log'),
        total_items=Sum('dispensed_quantity'),
        total_transactions=Count('id')
    ).order_by('-total_sales')[:10]

    # Overall Statistics
    overall_stats = dispensing_logs.aggregate(
        total_sales=Sum('total_price_for_this_log'),
        total_items=Sum('dispensed_quantity'),
        total_transactions=Count('id'),
        avg_transaction_value=Avg('total_price_for_this_log'),
        unique_patients=Count('prescription_item__prescription__patient', distinct=True),
        unique_medications=Count('prescription_item__medication', distinct=True),
        unique_dispensaries=Count('dispensary', distinct=True)
    )

    # Calculate NHIA vs Non-NHIA percentages
    total_sales = overall_stats['total_sales'] or Decimal('0')
    nhia_percentage = 0
    non_nhia_percentage = 0

    if total_sales > 0:
        nhia_sales = nhia_stats['total_sales'] or Decimal('0')
        non_nhia_sales = non_nhia_stats['total_sales'] or Decimal('0')
        nhia_percentage = (nhia_sales / total_sales) * 100
        non_nhia_percentage = (non_nhia_sales / total_sales) * 100

    # Get filter options
    dispensaries = Dispensary.objects.filter(is_active=True).order_by('name')
    medications = Medication.objects.filter(is_active=True).order_by('name')

    context = {
        'title': 'Pharmacy Sales Statistics by Dispensaries',
        'start_date': start_date,
        'end_date': end_date,
        'dispensary_stats': dispensary_stats,
        'top_medications': top_medications,
        'top_staff': top_staff,
        'daily_sales': daily_sales,
        'overall_stats': overall_stats,
        'nhia_stats': nhia_stats,
        'non_nhia_stats': non_nhia_stats,
        'nhia_percentage': nhia_percentage,
        'non_nhia_percentage': non_nhia_percentage,
        'dispensaries': dispensaries,
        'medications': medications,
        'selected_dispensary': dispensary_id,
        'selected_medication': medication_id,
        'selected_patient_type': patient_type,
    }

    return render(request, 'pharmacy/reports/sales_statistics.html', context)

@login_required
def debug_dispense_prescription(request, prescription_id):
    """Debug version of the dispensing view"""
    from django.http import HttpResponse

    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Get pending items
    pending_items = prescription.items.filter(is_dispensed=False).select_related('medication')

    # Create simple HTML response
    html = f"""
    <html>
    <head><title>Debug Dispensing</title></head>
    <body>
        <h1>Debug Dispensing for Prescription {prescription.id}</h1>
        <p><strong>Patient:</strong> {prescription.patient.get_full_name()}</p>
        <p><strong>Status:</strong> {prescription.status}</p>
        <p><strong>Total Items:</strong> {prescription.items.count()}</p>
        <p><strong>Pending Items:</strong> {pending_items.count()}</p>

        <h2>Items Details:</h2>
        <ul>
    """

    for item in pending_items:
        html += f"""
            <li>Item {item.id}: {item.medication.name}
                - Prescribed: {item.quantity}
                - Dispensed: {item.quantity_dispensed_so_far}
                - Remaining: {item.remaining_quantity_to_dispense}
                - Is Dispensed: {item.is_dispensed}
            </li>
        """

    html += """
        </ul>
        <p><a href="/pharmacy/prescriptions/3/dispense/">Go to actual dispensing page</a></p>
    </body>
    </html>
    """

    return HttpResponse(html)

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
@permission_required('pharmacy.view_prescription', raise_exception=True)
def prescription_payment(request, prescription_id):
    """Handle payment processing for prescription invoices"""
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check if prescription already has payment verified
    if prescription.is_payment_verified():
        messages.info(request, 'This prescription has already been paid for.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Get or create invoice for the prescription
    invoice = None
    if hasattr(prescription, 'invoices') and prescription.invoices.exists():
        invoice = prescription.invoices.first()
    elif hasattr(prescription, 'invoice') and prescription.invoice:
        invoice = prescription.invoice

    if not invoice:
        messages.warning(request, 'No invoice found for this prescription. Please create an invoice first.')
        return redirect('pharmacy:create_prescription_invoice', prescription_id=prescription.id)

    # Calculate remaining amount
    remaining_amount = invoice.get_balance()

    if remaining_amount <= 0:
        messages.info(request, 'This invoice has already been fully paid.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Get patient wallet for enhanced payment options
    from patients.models import PatientWallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=prescription.patient)
    except PatientWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        patient_wallet = PatientWallet.objects.create(
            patient=prescription.patient,
            balance=0
        )

    # Get pricing breakdown for NHIA display
    pricing_breakdown = prescription.get_pricing_breakdown()

    if request.method == 'POST':
        form = PrescriptionPaymentForm(
            request.POST,
            invoice=invoice,
            prescription=prescription,
            patient_wallet=patient_wallet
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.received_by = request.user

                    payment_source = form.cleaned_data['payment_source']

                    if payment_source == 'patient_wallet':
                        # Force wallet payment method
                        payment.payment_method = 'wallet'

                    payment.save()

                    # Update invoice amounts and status
                    invoice.amount_paid += payment.amount
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = 'paid'
                        invoice.payment_date = payment.payment_date
                        invoice.payment_method = payment.payment_method
                        # Mark that this is a manual payment processed by billing staff
                        invoice._manual_payment_processed = True
                    else:
                        invoice.status = 'partially_paid'
                    invoice.save()

                    # Update prescription payment status
                    if invoice.status == 'paid':
                        prescription.payment_status = 'paid'
                        prescription.save(update_fields=['payment_status'])

                    # Enhanced success message with NHIA information
                    payment_type = "NHIA Patient (10%)" if pricing_breakdown['is_nhia_patient'] else "Non-NHIA Patient (100%)"
                    messages.success(request, f'Payment of ₦{payment.amount:.2f} recorded successfully for {payment_type} via {payment_source.replace("_", " ").title()}.')
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
    else:
        form = PrescriptionPaymentForm(
            invoice=invoice,
            prescription=prescription,
            patient_wallet=patient_wallet,
            initial={
                'payment_date': timezone.now().date(),
                'payment_method': 'cash'
            }
        )

    context = {
        'form': form,
        'prescription': prescription,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'pricing_breakdown': pricing_breakdown,
        'remaining_amount': remaining_amount,
        'title': f'Payment for Prescription #{prescription.id}'
    }

    return render(request, 'pharmacy/prescription_payment.html', context)

@login_required
@permission_required('billing.add_payment', raise_exception=True)
def billing_office_medication_payment(request, prescription_id):
    """Billing office interface for processing medication payments"""
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check if prescription already has payment verified
    if prescription.is_payment_verified():
        messages.info(request, 'This prescription has already been paid for.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Get or create invoice for the prescription
    invoice = None
    if hasattr(prescription, 'invoices') and prescription.invoices.exists():
        invoice = prescription.invoices.first()
    elif hasattr(prescription, 'invoice') and prescription.invoice:
        invoice = prescription.invoice

    if not invoice:
        messages.warning(request, 'No invoice found for this prescription. Creating invoice...')
        return redirect('pharmacy:create_prescription_invoice', prescription_id=prescription.id)

    # Calculate remaining amount
    remaining_amount = invoice.get_balance()

    if remaining_amount <= 0:
        messages.info(request, 'This invoice has already been fully paid.')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

    # Get patient wallet
    from patients.models import PatientWallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=prescription.patient)
    except PatientWallet.DoesNotExist:
        patient_wallet = PatientWallet.objects.create(
            patient=prescription.patient,
            balance=0
        )

    # Get pricing breakdown for NHIA display
    pricing_breakdown = prescription.get_pricing_breakdown()

    if request.method == 'POST':
        form = PrescriptionPaymentForm(
            request.POST,
            invoice=invoice,
            prescription=prescription,
            patient_wallet=patient_wallet
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.received_by = request.user

                    payment_source = form.cleaned_data['payment_source']

                    if payment_source == 'patient_wallet':
                        payment.payment_method = 'wallet'
                        # Deduct from wallet
                        patient_wallet.debit(
                            amount=payment.amount,
                            description=f"Medication payment for prescription #{prescription.id}",
                            transaction_type="medication_payment",
                            user=request.user,
                            invoice=invoice,
                            payment_instance=payment
                        )

                    payment.save()

                    # Update invoice amounts and status
                    invoice.amount_paid += payment.amount
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = 'paid'
                        invoice.payment_date = payment.payment_date
                        invoice.payment_method = payment.payment_method
                        # Mark that this is a manual payment processed by billing staff
                        invoice._manual_payment_processed = True
                        prescription.payment_status = 'paid'
                        prescription.save(update_fields=['payment_status'])
                    else:
                        invoice.status = 'partially_paid'
                    invoice.save()

                    # Enhanced success message
                    payment_type = "NHIA Patient (10%)" if pricing_breakdown['is_nhia_patient'] else "Non-NHIA Patient (100%)"
                    messages.success(request,
                        f'Payment of ₦{payment.amount:.2f} recorded successfully for {payment_type} '
                        f'via {payment_source.replace("_", " ").title()}. '
                        f'Prescription is now ready for dispensing.'
                    )
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
    else:
        form = PrescriptionPaymentForm(
            invoice=invoice,
            prescription=prescription,
            patient_wallet=patient_wallet,
            initial={
                'amount': remaining_amount,
                'payment_date': timezone.now().date(),
                'payment_method': 'cash',
                'payment_source': 'billing_office'
            }
        )

    context = {
        'form': form,
        'prescription': prescription,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'pricing_breakdown': pricing_breakdown,
        'remaining_amount': remaining_amount,
        'title': f'Billing Office - Medication Payment for Prescription #{prescription.id}',
        'is_billing_office': True
    }

    return render(request, 'pharmacy/billing_office_medication_payment.html', context)

@login_required
@permission_required('pharmacy.add_prescription', raise_exception=True)
def pharmacy_create_prescription(request, patient_id=None):
    """Pharmacy staff prescription creation with enhanced workflow"""
    from core.decorators import pharmacist_required

    # Check if user is pharmacy staff
    user_roles = list(request.user.roles.values_list('name', flat=True))
    if not any(role in ['pharmacist', 'admin'] for role in user_roles):
        messages.error(request, 'Only pharmacy staff can create prescriptions through this interface.')
        return redirect('pharmacy:pharmacy_dashboard')

    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)

    # Also check for patient in GET parameters
    if not patient and request.GET.get('patient'):
        try:
            patient = get_object_or_404(Patient, id=request.GET.get('patient'))
        except (ValueError, Patient.DoesNotExist):
            pass

    initial_data = {}
    if patient:
        initial_data['patient'] = patient

    # Set the doctor to the current user if they are a pharmacist creating the prescription
    initial_data['doctor'] = request.user

    if request.method == 'POST':
        prescription_form = PrescriptionForm(
            request.POST,
            request=request,
            initial=initial_data,
            preselected_patient=patient
        )

        if prescription_form.is_valid():
            try:
                with transaction.atomic():
                    prescription = prescription_form.save(commit=False)
                    prescription.created_by = request.user
                    # For pharmacy staff prescriptions, set doctor to the pharmacist
                    prescription.doctor = request.user
                    prescription.save()

                    total_prescription_price = Decimal('0.00')
                    medication_ids = request.POST.getlist('medication[]')
                    quantities = request.POST.getlist('quantity[]')
                    dosages = request.POST.getlist('dosage[]')
                    frequencies = request.POST.getlist('frequency[]')
                    durations = request.POST.getlist('duration[]')
                    instructions_list = request.POST.getlist('instructions[]')

                    for i, medication_id in enumerate(medication_ids):
                        if medication_id:
                            medication = Medication.objects.get(id=medication_id)
                            quantity = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                            dosage = dosages[i] if i < len(dosages) else ''
                            frequency = frequencies[i] if i < len(frequencies) else ''
                            duration = durations[i] if i < len(durations) else ''
                            instructions = instructions_list[i] if i < len(instructions_list) else ''

                            PrescriptionItem.objects.create(
                                prescription=prescription,
                                medication=medication,
                                dosage=dosage,
                                frequency=frequency,
                                duration=duration,
                                instructions=instructions,
                                quantity=quantity
                            )
                            total_prescription_price += medication.price * quantity

                    # Create invoice for pharmacy prescription
                    try:
                        service = Service.objects.get(name__iexact="Medication Dispensing")

                        # Calculate pricing based on NHIA status
                        pricing_breakdown = prescription.get_pricing_breakdown()
                        final_amount = pricing_breakdown['patient_portion']

                        invoice = Invoice.objects.create(
                            patient=prescription.patient,
                            status='pending',
                            total_amount=final_amount,
                            subtotal=final_amount,
                            tax_amount=0,
                            discount_amount=0,
                            created_by=request.user,
                            source_app='pharmacy'
                        )

                        InvoiceItem.objects.create(
                            invoice=invoice,
                            service=service,
                            description=f"Pharmacy Prescription #{prescription.id} - {prescription.items.count()} medications",
                            quantity=1,
                            unit_price=final_amount,
                            tax_amount=0,
                            total_amount=final_amount,
                        )

                        prescription.invoice = invoice
                        prescription.save()

                    except Service.DoesNotExist:
                        messages.warning(request,
                            "Prescription created successfully, but invoice creation failed. "
                            "Please create an invoice manually before dispensing."
                        )

                    messages.success(request,
                        f'Prescription created successfully by pharmacy staff! '
                        f'Total cost: ₦{total_prescription_price:.2f}'
                    )
                    return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

            except Exception as e:
                messages.error(request, f'Error creating prescription: {str(e)}')

        else:
            messages.error(request, 'Please correct the form errors below.')
    else:
        prescription_form = PrescriptionForm(
            request=request,
            initial=initial_data,
            preselected_patient=patient
        )

    context = {
        'prescription_form': prescription_form,
        'medications': Medication.objects.filter(is_active=True),
        'title': 'Pharmacy Staff - Create Prescription',
        'patient': patient,
        'is_pharmacy_staff': True,
        'current_user': request.user,
    }
    return render(request, 'pharmacy/pharmacy_create_prescription.html', context)


@login_required
@permission_required('pharmacy.change_prescription', raise_exception=True)
def create_prescription_invoice(request, prescription_id):
    """Create an invoice for a prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check if prescription already has an invoice
    if (hasattr(prescription, 'invoices') and prescription.invoices.exists()) or \
       (hasattr(prescription, 'invoice') and prescription.invoice):
        messages.info(request, 'This prescription already has an invoice.')
        return redirect('pharmacy:prescription_payment', prescription_id=prescription.id)

    try:
        with transaction.atomic():
            # Calculate total prescription price
            total_prescription_price = prescription.get_total_prescribed_price()

            if total_prescription_price <= 0:
                messages.error(request, 'Cannot create invoice: prescription has no items or all items have zero price.')
                return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)

            # Get medication dispensing service
            try:
                medication_dispensing_service = Service.objects.get(name__iexact="Medication Dispensing")
            except Service.DoesNotExist:
                # Create the service if it doesn't exist
                medication_dispensing_service = Service.objects.create(
                    name="Medication Dispensing",
                    description="Dispensing of prescribed medications",
                    price=0.00,  # Price will be calculated based on medications
                    category=None
                )

            # Create invoice
            invoice = Invoice.objects.create(
                patient=prescription.patient,
                prescription=prescription,
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                status='pending',
                subtotal=total_prescription_price,
                tax_amount=0,  # No tax for now
                discount_amount=0,
                total_amount=total_prescription_price,
                created_by=request.user,
                source_app='pharmacy'
            )

            # Create invoice items for each prescription item
            from billing.models import InvoiceItem
            for prescription_item in prescription.items.all():
                item_total = prescription_item.medication.price * prescription_item.quantity
                InvoiceItem.objects.create(
                    invoice=invoice,
                    service=medication_dispensing_service,
                    description=f'{prescription_item.medication.name} - {prescription_item.dosage} ({prescription_item.quantity} units)',
                    quantity=prescription_item.quantity,
                    unit_price=prescription_item.medication.price,
                    tax_percentage=Decimal('0.00'),
                    tax_amount=Decimal('0.00'),
                    discount_amount=Decimal('0.00'),
                    total_amount=item_total
                )

            # Link invoice to prescription
            prescription.invoice = invoice
            prescription.save(update_fields=['invoice'])

            messages.success(request, f'Invoice #{invoice.invoice_number} created successfully.')
            return redirect('pharmacy:prescription_payment', prescription_id=prescription.id)

    except Exception as e:
        messages.error(request, f'Error creating invoice: {str(e)}')
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
