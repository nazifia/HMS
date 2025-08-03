
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
    ).order_by('-dispensed_at')[:10]

    # Top dispensed medications (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    top_medications = DispensingLog.objects.filter(
        dispensed_at__gte=thirty_days_ago
    ).values(
        'prescription_item__medication__name'
    ).annotate(
        total_dispensed=Sum('quantity_dispensed')
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

            # Update purchase total
            total = PurchaseItem.objects.filter(purchase=pending_purchase).aggregate(
                total=Sum(F('quantity') * F('unit_price'))
            )['total'] or 0
            pending_purchase.total_amount = total
            pending_purchase.save()

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

            # Update purchase total
            total = PurchaseItem.objects.filter(purchase=pending_purchase).aggregate(
                total=Sum(F('quantity') * F('unit_price'))
            )['total'] or 0
            pending_purchase.total_amount = total

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
                        final_amount = pricing_breakdown['patient_pays']

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
