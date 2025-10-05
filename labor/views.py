from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from decimal import Decimal
from .models import LaborRecord
from .forms import LaborRecordForm, LaborRecordSearchForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from pharmacy.models import Prescription, PrescriptionItem, MedicalPack, PackOrder
from pharmacy.forms import PackOrderForm
from billing.models import Invoice, InvoiceItem, Service, ServiceCategory

@login_required
def labor_records_list(request):
    """View to list all labor records with search and pagination"""
    records = LaborRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = LaborRecordSearchForm(request.GET)
    search_query = None
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if search_query:
            records = records.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(diagnosis__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(visit_date__gte=date_from)
            
        if date_to:
            records = records.filter(visit_date__lte=date_to)
    
    # Get counts for stats
    total_records = records.count()
    follow_up_count = records.filter(follow_up_required=True).count()
    
    # Pagination
    paginator = Paginator(records, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': total_records,
        'follow_up_count': follow_up_count,
    }
    return render(request, 'labor/labor_records_list.html', context)

@login_required
def create_labor_record(request):
    """View to create a new labor record"""
    if request.method == 'POST':
        form = LaborRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Labor record created successfully.')
            return redirect('labor:labor_record_detail', record_id=record.id)
    else:
        form = LaborRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Labor Record'
    }
    return render(request, 'labor/labor_record_form.html', context)

@login_required
def labor_record_detail(request, record_id):
    """View to display details of a specific labor record"""
    record = get_object_or_404(
        LaborRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'labor/labor_record_detail.html', context)

@login_required
def edit_labor_record(request, record_id):
    """View to edit an existing labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        form = LaborRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Labor record updated successfully.')
            return redirect('labor:labor_record_detail', record_id=record.id)
    else:
        form = LaborRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Labor Record'
    }
    return render(request, 'labor/labor_record_form.html', context)

@login_required
def delete_labor_record(request, record_id):
    """View to delete a labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Labor record deleted successfully.')
        return redirect('labor:labor_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'labor/labor_record_confirm_delete.html', context)

@login_required
def search_labor_patients(request):
    """AJAX view for searching patients in Labor module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_labor(request, record_id):
    """Create a prescription for a labor patient"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        prescription_form = MedicalModulePrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        
        if prescription_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Create the prescription
                    diagnosis = prescription_form.cleaned_data['diagnosis']
                    notes = prescription_form.cleaned_data['notes']
                    prescription_type = prescription_form.cleaned_data['prescription_type']
                    
                    prescription = Prescription.objects.create(
                        patient=record.patient,
                        doctor=request.user,
                        diagnosis=diagnosis,
                        notes=notes,
                        prescription_type=prescription_type
                    )
                    
                    # Add prescription items
                    for form in formset.cleaned_data:
                        if form and not form.get('DELETE', False):
                            medication = form['medication']
                            dosage = form['dosage']
                            frequency = form['frequency']
                            duration = form['duration']
                            quantity = form['quantity']
                            instructions = form.get('instructions', '')
                            
                            PrescriptionItem.objects.create(
                                prescription=prescription,
                                medication=medication,
                                dosage=dosage,
                                frequency=frequency,
                                duration=duration,
                                quantity=quantity,
                                instructions=instructions
                            )
                    
                    messages.success(request, 'Prescription created successfully!')
                    return redirect('labor:labor_record_detail', record_id=record.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating prescription: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        prescription_form = MedicalModulePrescriptionForm()
        formset = PrescriptionItemFormSet()
    
    context = {
        'record': record,
        'prescription_form': prescription_form,
        'formset': formset,
        'title': 'Create Prescription'
    }
    return render(request, 'labor/create_prescription.html', context)


@login_required
def order_medical_pack_for_labor(request, record_id):
    """Order a medical pack for a specific labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    # Get labor-specific packs
    available_packs = MedicalPack.objects.filter(
        is_active=True,
        pack_type='labor'
    )
    
    # Filter by labor type if available
    if record.mode_of_delivery:
        delivery_type_packs = available_packs.filter(
            labor_type__icontains=record.mode_of_delivery.lower()
        )
        if delivery_type_packs.exists():
            available_packs = delivery_type_packs
    
    if request.method == 'POST':
        form = PackOrderForm(request.POST, labor_record=record, preselected_patient=record.patient)

        if form.is_valid():
            try:
                with transaction.atomic():
                    pack_order = form.save(commit=False)
                    pack_order.patient = record.patient
                    pack_order.labor_record = record
                    pack_order.ordered_by = request.user
                    
                    # Set scheduled date to labor visit date if not provided
                    if not pack_order.scheduled_date:
                        pack_order.scheduled_date = record.visit_date
                    
                    pack_order.save()
                    
                    # Automatically create prescription from pack items
                    try:
                        prescription = pack_order.create_prescription()
                        
                        # Add pack costs to patient billing
                        _add_pack_to_patient_billing(record.patient, pack_order, 'labor')
                        
                        messages.success(
                            request, 
                            f'Medical pack "{pack_order.pack.name}" ordered successfully for labor record. '
                            f'Prescription #{prescription.id} has been automatically created with {prescription.items.count()} medications. '
                            f'Pack cost (₦{pack_order.pack.get_total_cost():.2f}) has been added to patient billing.'
                        )
                    except Exception as e:
                        # Pack order was created but prescription failed
                        messages.warning(
                            request,
                            f'Medical pack "{pack_order.pack.name}" ordered successfully, but prescription creation failed: {str(e)}. '
                            f'Please create the prescription manually if needed.'
                        )
                    return redirect('labor:labor_record_detail', record_id=record.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating pack order: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        # Pre-populate form with labor context
        initial_data = {
            'scheduled_date': record.visit_date,
            'order_notes': f'Pack order for labor record: {record.diagnosis or "Labor/Delivery"}'
        }
        form = PackOrderForm(initial=initial_data, labor_record=record, preselected_patient=record.patient)
        
        # Filter pack choices to labor-specific packs
        form.fields['pack'].queryset = available_packs
        form.fields['patient'].initial = record.patient
        form.fields['patient'].widget.attrs['readonly'] = True
    
    context = {
        'record': record,
        'form': form,
        'available_packs': available_packs,
        'page_title': 'Order Medical Pack for Labor',
        'pack': None  # Will be set if pack_id is in GET params
    }
    
    # Handle pack preview
    pack_id = request.GET.get('pack_id')
    if pack_id:
        try:
            pack = get_object_or_404(MedicalPack, id=pack_id, is_active=True)
            context['pack'] = pack
            context['form'].fields['pack'].initial = pack
        except:
            pass
    
    return render(request, 'labor/order_medical_pack.html', context)


def _add_pack_to_patient_billing(patient, pack_order, source_context='general'):
    """Helper function to add pack costs to patient billing"""
    from django.utils import timezone
    
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
    from django.db import models
    invoice.subtotal = invoice.items.aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0.00')
    invoice.tax_amount = invoice.items.aggregate(
        total=models.Sum('tax_amount')
    )['total'] or Decimal('0.00')
    invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount_amount
    invoice.save()
    
    return invoice_item