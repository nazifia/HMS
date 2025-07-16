import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

from django.shortcuts import render, get_object_or_404, redirect
from billing.models import Service, Invoice, InvoiceItem, Payment
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import models
from .models import Ward, Bed, Admission, DailyRound, NursingNote, ClinicalRecord, BedTransfer, WardTransfer
from .forms import WardForm, BedForm, AdmissionForm, DischargeForm, DailyRoundForm, NursingNoteForm, AdmissionSearchForm, ClinicalRecordForm, PatientTransferForm
from patients.models import Patient, PatientWallet, WalletTransaction

@login_required
def bed_dashboard(request):
    """Visual dashboard for bed management"""
    beds_list = Bed.objects.select_related('ward').prefetch_related('admissions__patient').order_by('ward__name', 'bed_number')

    # Annotate each bed with its current admission (status='admitted')
    for bed in beds_list:
        bed.current_admission = bed.admissions.filter(status='admitted').first()

    total_beds = beds_list.count()
    occupied_beds = beds_list.filter(is_occupied=True).count()
    available_beds = beds_list.filter(is_occupied=False, is_active=True).count()
    inactive_beds = beds_list.filter(is_active=False).count()
    occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

    paginator = Paginator(beds_list, 20)  # Show 20 beds per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_beds')
        action = request.POST.get('bulk_action')
        if selected_ids and action:
            selected_beds = Bed.objects.filter(id__in=selected_ids)
            if action == 'mark_available':
                selected_beds.update(is_occupied=False, is_active=True)
                messages.success(request, f'{selected_beds.count()} beds marked as available.')
            elif action == 'mark_inactive':
                selected_beds.update(is_active=False)
                messages.success(request, f'{selected_beds.count()} beds marked as inactive.')
            return redirect('inpatient:bed_dashboard')

    context = {
        'page_obj': page_obj,
        'total_beds': total_beds,
        'available_beds': available_beds,
        'occupied_beds': occupied_beds,
        'inactive_beds': inactive_beds,
        'occupancy_rate': occupancy_rate,
        'title': 'Bed Dashboard'
    }

    return render(request, 'inpatient/bed_dashboard.html', context)

@login_required
def patient_admissions(request, patient_id):
    """List of admissions for a specific patient."""
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('patients:patient_list')

    admissions_list = Admission.objects.filter(patient=patient).select_related('ward', 'bed', 'attending_doctor').order_by('-admission_date')
    # Get the current admission (status == 'admitted')
    current_admission = admissions_list.filter(status='admitted').first()
    
    paginator = Paginator(admissions_list, 10)  # Show 10 admissions per page
    page_number = request.GET.get('page')
    admissions = paginator.get_page(page_number)

    context = {
        'patient': patient,
        'admissions': admissions,
        'current_admission': current_admission,
        'title': f'Admissions for {patient.get_full_name()}'
    }

    return render(request, 'inpatient/patient_admissions.html', context)

@login_required
def ward_list(request):
    """View for listing all wards"""
    wards = Ward.objects.all().order_by('name')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        wards = wards.filter(
            Q(name__icontains=search_query) |
            Q(ward_type__icontains=search_query) |
            Q(floor__icontains=search_query)
        )

    # Filter by ward type
    ward_type = request.GET.get('ward_type', '')
    if ward_type:
        wards = wards.filter(ward_type=ward_type)

    # Filter by active status
    is_active = request.GET.get('is_active', '')
    if is_active:
        is_active = is_active == 'true'
        wards = wards.filter(is_active=is_active)

    # Pagination
    paginator = Paginator(wards, 10)  # Show 10 wards per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get ward types for filter dropdown
    ward_types = dict(Ward.WARD_TYPE_CHOICES)

    context = {
        'page_obj': page_obj,
        'ward_types': ward_types,
        'search_query': search_query,
        'ward_type': ward_type,
        'is_active': is_active,
        'title': 'Wards'
    }

    return render(request, 'inpatient/ward_list.html', context)

@login_required
def add_ward(request):
    """View for adding a new ward"""
    if request.method == 'POST':
        form = WardForm(request.POST)
        if form.is_valid():
            ward = form.save()
            messages.success(request, f'Ward {ward.name} has been created successfully.')
            return redirect('inpatient:ward_detail', ward_id=ward.id)
    else:
        form = WardForm()

    context = {
        'form': form,
        'title': 'Add New Ward'
    }

    return render(request, 'inpatient/ward_form.html', context)

@login_required
def ward_detail(request, ward_id):
    """View for displaying ward details"""
    ward = get_object_or_404(Ward, id=ward_id)
    beds = ward.beds.all().order_by('bed_number')

    # Annotate each bed with its current admission (status='admitted')
    for bed in beds:
        bed.current_admission = bed.admissions.filter(status='admitted').first()

    # Add missing bed counts
    total_beds = beds.count()
    available_beds = beds.filter(is_occupied=False, is_active=True).count()
    occupied_beds = beds.filter(is_occupied=True).count()
    inactive_beds = beds.filter(is_active=False).count()

    context = {
        'ward': ward,
        'beds': beds,
        'total_beds': total_beds,
        'available_beds': available_beds,
        'occupied_beds': occupied_beds,
        'inactive_beds': inactive_beds,
        'title': f'Ward: {ward.name}'
    }

    return render(request, 'inpatient/ward_detail.html', context)

@login_required
def edit_ward(request, ward_id):
    """View for editing a ward"""
    ward = get_object_or_404(Ward, id=ward_id)

    if request.method == 'POST':
        form = WardForm(request.POST, instance=ward)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ward {ward.name} has been updated successfully.')
            return redirect('inpatient:ward_detail', ward_id=ward.id)
    else:
        form = WardForm(instance=ward)

    context = {
        'form': form,
        'ward': ward,
        'title': f'Edit Ward: {ward.name}'
    }

    return render(request, 'inpatient/ward_form.html', context)

@login_required
def delete_ward(request, ward_id):
    """View for deleting a ward"""
    ward = get_object_or_404(Ward, id=ward_id)

    # Check if there are any beds in this ward
    if ward.beds.exists():
        messages.error(request, f'Cannot delete ward {ward.name} because it contains beds. Please delete or move the beds first.')
        return redirect('inpatient:ward_detail', ward_id=ward.id)

    if request.method == 'POST':
        ward_name = ward.name
        ward.delete()
        messages.success(request, f'Ward {ward_name} has been deleted successfully.')
        return redirect('inpatient:wards')

    context = {
        'ward': ward,
        'title': f'Delete Ward: {ward.name}'
    }

    return render(request, 'inpatient/delete_ward.html', context)

@login_required
def bed_list(request):
    """View for listing all beds"""
    beds = Bed.objects.all().select_related('ward')

    # Annotate each bed with its current admission (status='admitted')
    for bed in beds:
        bed.current_admission = bed.admissions.filter(status='admitted').first()

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        beds = beds.filter(
            Q(bed_number__icontains=search_query) |
            Q(ward__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by ward
    ward_id = request.GET.get('ward', '')
    if ward_id:
        beds = beds.filter(ward_id=ward_id)

    # Filter by occupancy status
    occupancy = request.GET.get('occupancy', '')
    if occupancy:
        is_occupied = occupancy == 'occupied'
        beds = beds.filter(is_occupied=is_occupied)

    # Filter by active status
    is_active = request.GET.get('is_active', '')
    if is_active:
        is_active = is_active == 'true'
        beds = beds.filter(is_active=is_active)

    # Pagination
    paginator = Paginator(beds, 20)  # Show 20 beds per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get wards for filter dropdown
    wards = Ward.objects.filter(is_active=True).order_by('name')

    context = {
        'page_obj': page_obj,
        'wards': wards,
        'search_query': search_query,
        'ward_id': ward_id,
        'occupancy': occupancy,
        'is_active': is_active,
        'title': 'Beds'
    }

    return render(request, 'inpatient/bed_list.html', context)

@login_required
def add_bed(request):
    """View for adding a new bed"""
    # Pre-fill ward_id if provided in GET parameters
    ward_id = request.GET.get('ward_id')
    initial_data = {}

    if ward_id:
        try:
            ward = Ward.objects.get(id=ward_id)
            initial_data['ward'] = ward
        except Ward.DoesNotExist:
            pass

    if request.method == 'POST':
        form = BedForm(request.POST)
        if form.is_valid():
            bed = form.save()
            messages.success(request, f'Bed {bed.bed_number} has been added to {bed.ward.name} successfully.')

            # Redirect back to the ward detail page if this bed was added from there
            if 'ward_id' in request.GET:
                return redirect('inpatient:ward_detail', ward_id=bed.ward.id)
            return redirect('inpatient:beds')
    else:
        form = BedForm(initial=initial_data)

    context = {
        'form': form,
        'title': 'Add New Bed'
    }

    return render(request, 'inpatient/bed_form.html', context)

@login_required
def edit_bed(request, bed_id):
    """View for editing a bed"""
    bed = get_object_or_404(Bed, id=bed_id)

    if request.method == 'POST':
        form = BedForm(request.POST, instance=bed)
        if form.is_valid():
            bed = form.save()
            messages.success(request, f'Bed {bed.bed_number} has been updated successfully.')
            return redirect('inpatient:ward_detail', ward_id=bed.ward.id)
    else:
        form = BedForm(instance=bed)

    context = {
        'form': form,
        'bed': bed,
        'title': f'Edit Bed: {bed.bed_number} in {bed.ward.name}'
    }

    return render(request, 'inpatient/bed_form.html', context)

@login_required
def delete_bed(request, bed_id):
    """View for deleting a bed"""
    bed = get_object_or_404(Bed, id=bed_id)
    ward_id = bed.ward.id

    # Check if the bed is occupied
    if bed.is_occupied:
        messages.error(request, f'Cannot delete bed {bed.bed_number} because it is currently occupied.')
        return redirect('inpatient:ward_detail', ward_id=ward_id)

    if request.method == 'POST':
        bed_number = bed.bed_number
        ward_name = bed.ward.name
        bed.delete()
        messages.success(request, f'Bed {bed_number} in {ward_name} has been deleted successfully.')
        return redirect('inpatient:ward_detail', ward_id=ward_id)

    context = {
        'bed': bed,
        'title': f'Delete Bed: {bed.bed_number}'
    }

    return render(request, 'inpatient/delete_bed.html', context)

@login_required
def admission_list(request):
    """View for listing all admissions"""
    search_form = AdmissionSearchForm(request.GET)
    # Use select_related for ForeignKey/OneToOne, prefetch_related for reverse/many-to-many
    admissions = Admission.objects.filter(status='admitted').select_related('patient', 'bed', 'bed__ward', 'attending_doctor').order_by('-admission_date')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        doctor = search_form.cleaned_data.get('doctor')
        ward = search_form.cleaned_data.get('ward')

        if search_query:
            admissions = admissions.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(diagnosis__icontains=search_query)
            )

        if status:
            admissions = Admission.objects.all().select_related('patient', 'bed', 'bed__ward', 'attending_doctor').order_by('-admission_date')
            admissions = admissions.filter(status=status)

        if date_from:
            admissions = admissions.filter(admission_date__date__gte=date_from)

        if date_to:
            admissions = admissions.filter(admission_date__date__lte=date_to)

        if doctor:
            admissions = admissions.filter(attending_doctor=doctor)

        if ward:
            # Only show admissions with a bed in the selected ward
            admissions = admissions.filter(bed__ward=ward)

    # Pagination
    paginator = Paginator(admissions, 10)  # Show 10 admissions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Use aggregate for counts
    status_counts = Admission.objects.values('status').annotate(count=Count('id'))
    status_count_dict = {item['status']: item['count'] for item in status_counts}
    admitted_count = status_count_dict.get('admitted', 0)
    discharged_count = status_count_dict.get('discharged', 0)
    transferred_count = status_count_dict.get('transferred', 0)
    deceased_count = status_count_dict.get('deceased', 0)

    # Advanced: Add role-based analytics for admissions
    role_counts = Admission.objects.values('attending_doctor__profile__role').annotate(count=models.Count('id')).order_by('-count')
    # Advanced: Add audit log and notification fetch (if models exist)
    from core.models import AuditLog, InternalNotification
    audit_logs = AuditLog.objects.filter(
        details__icontains='Admission'
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='Admission',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_admissions': admissions.count(),
        'admitted_count': admitted_count,
        'discharged_count': discharged_count,
        'transferred_count': transferred_count,
        'deceased_count': deceased_count,
        'title': 'Admissions',
        'role_counts': role_counts,
        'audit_logs': audit_logs,
        'user_notifications': user_notifications,
    }

    return render(request, 'inpatient/admission_list.html', context)

@login_required
def admission_detail(request, pk):
    """View for displaying admission details."""
    admission = get_object_or_404(Admission, pk=pk)
    context = {
        'admission': admission,
        'title': f'Admission Details for {admission.patient.get_full_name()}'
    }
    return render(request, 'inpatient/admission_detail.html', context)

@login_required
def create_admission(request):
    """View for creating a new admission"""
    from django.db import transaction
    # Pre-fill patient_id if provided in GET parameters
    patient_id = request.GET.get('patient_id')
    initial_data = {}

    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
            initial_data['patient'] = patient
        except Patient.DoesNotExist:
            pass

    if request.method == 'POST':
        form = AdmissionForm(request.POST)
        if form.is_valid():
            bed = form.cleaned_data['bed']
            # Ensure bed is available and active at the time of admission
            if not bed.is_active or bed.is_occupied:
                messages.error(request, f'Selected bed {bed.bed_number} in {bed.ward.name} is not available. Please choose another bed.')
            else:
                admission = form.save(commit=False)  # <-- Move this up
                # Assign attending doctor based on primary determinant (e.g., ward's primary doctor or patient's primary doctor)
                primary_doctor = None
                if hasattr(admission.patient, 'primary_doctor') and admission.patient.primary_doctor:
                    primary_doctor = admission.patient.primary_doctor
                elif admission.bed and admission.bed.ward and hasattr(admission.bed.ward, 'primary_doctor') and admission.bed.ward.primary_doctor:
                    primary_doctor = admission.bed.ward.primary_doctor
                else:
                    primary_doctor = admission.attending_doctor  # fallback
                admission.attending_doctor = primary_doctor
                try:
                    with transaction.atomic():
                        # admission = form.save(commit=False)  # already done above
                        # Set default status if not present in form
                        if not hasattr(admission, 'status') or not admission.status:
                            admission.status = 'admitted'
                        admission.save()
                        # Update bed status
                        bed.is_occupied = True
                        bed.save()

                        # Create and process admission charge
                        logger.info(f"Attempting to process admission charge for patient: {admission.patient.get_full_name()}")

                        try:
                            admission_service = form.cleaned_data['admission_service']
                            logger.info(f'Found admission service: {admission_service.name} with price {admission_service.price}')
                            wallet = PatientWallet.objects.get(patient=admission.patient)
                            logger.info(f'Found wallet for patient {wallet.patient.get_full_name()} with balance {wallet.balance}')

                            if wallet.balance >= admission_service.price:
                                logger.info('Wallet balance is sufficient. Proceeding with transaction.')
                                # Create Invoice
                                invoice = Invoice.objects.create(
                                    patient=admission.patient,
                                    invoice_date=timezone.now(),
                                    due_date=timezone.now() + timedelta(days=7), # Example: due in 7 days
                                    notes=form.cleaned_data['admission_notes'],
                                    subtotal=admission_service.price,
                                    tax_amount=0,
                                    discount_amount=0,
                                    total_amount=admission_service.price,
                                    admission=admission, # Link invoice to admission
                                    source_app='inpatient',
                                ) 
                                # Create InvoiceItem
                                InvoiceItem.objects.create(
                                    invoice=invoice,
                                    service=admission_service,
                                    quantity=1,
                                    unit_price=admission_service.price,
                                    total_amount=admission_service.price
                                )
                                # Deduct from wallet
                                wallet.balance -= admission_service.price
                                wallet.save()
                                logger.info(f'Deducted {admission_service.price} from wallet. New balance: {wallet.balance}')

                                # Create WalletTransaction
                                WalletTransaction.objects.create(
                                    wallet=wallet,
                                    transaction_type='admission_fee',
                                    amount=admission_service.price,
                                    description=f'Admission fee for {admission.patient.get_full_name()}',
                                    invoice=invoice
                                )

                                messages.success(request, 'Admission created successfully and wallet deducted.')
                                return redirect('inpatient:admission_detail', pk=admission.pk)
                            else:
                                messages.error(request, 'Insufficient wallet balance to cover admission fee.')
                                logger.warning(
                                f'Insufficient wallet balance for patient {admission.patient.get_full_name()}. '
                                f'Balance: {wallet.balance}, Required: {admission_service.price}'
                                )
                                messages.warning(request, f'Patient {admission.patient.get_full_name()} admitted, but insufficient wallet balance for admission fee.')

                        except Service.DoesNotExist:
                            messages.error(request, 'Admission Fee service not found. Please configure it in the billing settings.')
                            logger.error('Admission Fee service not found.')
                        except PatientWallet.DoesNotExist:
                            messages.error(request, 'Patient wallet not found. Please create a wallet for the patient.')
                            logger.error(f'Patient wallet not found for patient: {admission.patient.get_full_name()}')
                        except Exception as e:
                            messages.error(request, f'An error occurred during admission charge processing: {e}')
                            logger.exception('Error during admission charge processing.')

                except Exception as e:
                    messages.error(request, f'An error occurred during admission creation: {e}')
                    logger.exception('Error during admission creation.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-select the 'Admission Fee' service if it exists
        try:
            admission_fee_service = Service.objects.get(name='Admission Fee')
            initial_data['admission_service'] = admission_fee_service
        except Service.DoesNotExist:
            pass
        form = AdmissionForm(initial=initial_data)

    context = {
        'form': form,
        'title': 'Create New Admission',
    }
    return render(request, 'inpatient/admission_form.html', context)


@login_required
def edit_admission(request, admission_id):
    """View for editing an admission"""
    admission = get_object_or_404(Admission, id=admission_id)
    if request.method == 'POST':
        form = AdmissionForm(request.POST, instance=admission)
        if form.is_valid():
            form.save()
            messages.success(request, 'Admission details updated successfully.')
            return redirect('inpatient:admission_detail', pk=admission.id)
    else:
        form = AdmissionForm(instance=admission)

    context = {
        'form': form,
        'admission': admission,
        'title': f'Edit Admission for {admission.patient.get_full_name()}'
    }
    return render(request, 'inpatient/admission_form.html', context)


@login_required
@require_http_methods(["GET"])
def transfer_patient(request, admission_id):
    """Handles both bed and ward transfers for a patient."""
    admission = get_object_or_404(Admission, id=admission_id, status='admitted')
    
    if request.method == 'POST':
        form = PatientTransferForm(request.POST, current_bed=admission.bed)
        if form.is_valid():
            new_bed = form.cleaned_data['new_bed']
            transfer_type = form.cleaned_data['transfer_type']
            notes = form.cleaned_data['notes']
            
            # Check if the new bed is available
            if new_bed.is_occupied:
                messages.error(request, f"Bed {new_bed.bed_number} is already occupied.")
                return redirect('inpatient:transfer_patient', admission_id=admission.id)

            # Create a transfer record
            if transfer_type == 'bed':
                BedTransfer.objects.create(
                    admission=admission,
                    old_bed=admission.bed,
                    new_bed=new_bed,
                    notes=notes
                )
                messages.success(request, f"Patient transferred from bed {admission.bed.bed_number} to {new_bed.bed_number}.")
            elif transfer_type == 'ward':
                WardTransfer.objects.create(
                    admission=admission,
                    old_ward=admission.bed.ward,
                    new_ward=new_bed.ward,
                    notes=notes
                )
                messages.success(request, f"Patient transferred from ward {admission.bed.ward.name} to {new_bed.ward.name}.")

            # Update admission and bed statuses
            old_bed = admission.bed
            old_bed.is_occupied = False
            old_bed.save()
            
            new_bed.is_occupied = True
            new_bed.save()
            
            admission.bed = new_bed
            admission.save()
            
            return redirect('inpatient:admission_detail', pk=admission.id)
    else:
        form = PatientTransferForm(current_bed=admission.bed)

    context = {
        'form': form,
        'admission': admission,
        'patient': admission.patient,
        'title': 'Transfer Patient'
    }
    return render(request, 'inpatient/transfer_patient.html', context)


@login_required
def discharge_patient(request, admission_id):
    """View for discharging a patient"""
    admission = get_object_or_404(Admission, id=admission_id)

    if request.method == 'POST':
        form = DischargeForm(request.POST, instance=admission)
        if form.is_valid():
            admission = form.save(commit=False)
            admission.status = 'discharged'
            admission.discharge_date = timezone.now()
            admission.save()
            logger.info(f"Admission {admission.id} status after save: {admission.status}")

            # Update bed status
            if admission.bed:
                admission.bed.is_occupied = False
                admission.bed.save()
                logger.info(f"Bed {admission.bed.id} occupied status after save: {admission.bed.is_occupied}")

            messages.success(request, f'Patient {admission.patient.get_full_name()} has been discharged successfully.')
            return redirect('inpatient:admission_detail', pk=admission.id)
    else:
        form = DischargeForm(instance=admission)

    context = {
        'form': form,
        'admission': admission,
        'title': f'Discharge Patient: {admission.patient.get_full_name()}'
    }

    return render(request, 'inpatient/discharge_form.html', context)

@login_required
def add_clinical_record(request, admission_id):
    """View for adding a clinical record to an admission"""
    admission = get_object_or_404(Admission, id=admission_id)

    if request.method == 'POST':
        form = ClinicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.admission = admission
            record.recorded_by = request.user.profile
            record.save()
            messages.success(request, 'Clinical record added successfully.')
            return redirect('inpatient:admission_detail', pk=admission.id)
    else:
        form = ClinicalRecordForm()

    context = {
        'form': form,
        'admission': admission,
        'title': 'Add Clinical Record'
    }

    return render(request, 'inpatient/clinical_record_form.html', context)

@login_required
def bed_occupancy_report(request):
    """View for generating a bed occupancy report"""
    wards = Ward.objects.all()
    report_data = []

    for ward in wards:
        total_beds = ward.beds.count()
        occupied_beds = ward.beds.filter(is_occupied=True).count()
        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
        report_data.append({
            'ward_name': ward.name,
            'total_beds': total_beds,
            'occupied_beds': occupied_beds,
            'occupancy_rate': occupancy_rate
        })

    context = {
        'report_data': report_data,
        'title': 'Bed Occupancy Report'
    }

    return render(request, 'inpatient/bed_occupancy_report.html', context)

@login_required
def load_beds(request):
    """AJAX view to load beds based on selected ward."""
    ward_id = request.GET.get('ward_id')
    try:
        ward = Ward.objects.get(id=ward_id)
        # Filter for beds that are active and not occupied
        beds = Bed.objects.filter(ward=ward, is_active=True, is_occupied=False).order_by('bed_number')
        # Format the data for the dropdown
        bed_list = [{'id': bed.id, 'text': bed.bed_number} for bed in beds]
        return JsonResponse({'beds': bed_list})
    except Ward.DoesNotExist:
        return JsonResponse({'error': 'Ward not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)