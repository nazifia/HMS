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
from datetime import timedelta
from django.views.decorators.http import require_http_methods
from django.db import models
from .models import Ward, Bed, Admission, DailyRound, NursingNote, ClinicalRecord, BedTransfer, WardTransfer
from .forms import WardForm, BedForm, AdmissionForm, DischargeForm, DailyRoundForm, NursingNoteForm, AdmissionSearchForm, ClinicalRecordForm, PatientTransferForm
from .services import (
    InpatientActionError,
    admit_patient,
    discharge_patient as discharge_service,
    transfer_patient as transfer_service,
)
from patients.models import Patient, PatientWallet, WalletTransaction, ClinicalNote
from accounts.permissions import permission_required

@login_required
@permission_required('inpatient.view')
def bed_dashboard(request):
    """Visual dashboard for bed management - Optimized to avoid N+1 queries"""
    beds_list = Bed.objects.select_related('ward').prefetch_related(
        models.Prefetch(
            'admissions',
            queryset=Admission.objects.filter(status='admitted').select_related('patient'),
            to_attr='current_admissions_list'
        )
    ).order_by('ward__name', 'bed_number')

    # Pre-calculate stats in a single query
    from django.db.models import Count, Case, When, IntegerField
    bed_stats = Bed.objects.aggregate(
        total=Count('id'),
        occupied=Count('id', filter=Q(is_occupied=True)),
        available=Count('id', filter=Q(is_occupied=False, is_active=True)),
        inactive=Count('id', filter=Q(is_active=False))
    )

    total_beds = bed_stats['total']
    occupied_beds = bed_stats['occupied']
    available_beds = bed_stats['available']
    inactive_beds = bed_stats['inactive']
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
@permission_required('inpatient.view')
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
@permission_required('inpatient.view')
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
@permission_required('inpatient.create')
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
@permission_required('inpatient.view')
def ward_detail(request, ward_id):
    """View for displaying ward details - Optimized to avoid N+1 queries"""
    ward = get_object_or_404(Ward.objects.prefetch_related(
        models.Prefetch(
            'beds',
            queryset=Bed.objects.prefetch_related(
                models.Prefetch(
                    'admissions',
                    queryset=Admission.objects.filter(status='admitted').select_related('patient', 'attending_doctor'),
                    to_attr='current_admissions_list'
                )
            ).order_by('bed_number')
        )
    ), id=ward_id)

    beds = ward.beds.all()

    # Pre-calculate bed stats in single queries
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
@permission_required('inpatient.edit')
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
@permission_required('inpatient.edit')
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
@permission_required('inpatient.view')
def bed_list(request):
    """View for listing all beds - Optimized to avoid N+1 queries"""
    beds = Bed.objects.select_related('ward').prefetch_related(
        models.Prefetch(
            'admissions',
            queryset=Admission.objects.filter(status='admitted').select_related('patient'),
            to_attr='current_admissions_list'
        )
    ).order_by('ward__name', 'bed_number')

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
@permission_required('inpatient.create')
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
@permission_required('inpatient.edit')
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
@permission_required('inpatient.edit')
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
@permission_required('inpatient.view')
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
@permission_required('inpatient.view')
def admission_detail(request, pk):
    """View for displaying admission details."""
    admission = get_object_or_404(Admission, pk=pk)
    
    # Handle POST requests for adding nursing notes and daily rounds
    if request.method == 'POST':
        if 'add_note' in request.POST:
            note_form = NursingNoteForm(request.POST)
            if note_form.is_valid():
                nursing_note = note_form.save(commit=False)
                nursing_note.admission = admission
                nursing_note.save()
                messages.success(request, 'Nursing note added successfully.')
                return redirect('inpatient:admission_detail', pk=admission.pk)
        elif 'add_round' in request.POST:
            round_form = DailyRoundForm(request.POST)
            if round_form.is_valid():
                daily_round = round_form.save(commit=False)
                daily_round.admission = admission
                daily_round.save()
                messages.success(request, 'Daily round added successfully.')
                return redirect('inpatient:admission_detail', pk=admission.pk)
    
    # Initialize forms for GET requests
    note_form = NursingNoteForm()
    round_form = DailyRoundForm()
    
    # Get related data
    daily_rounds = admission.daily_rounds.all().order_by('-date_time')
    nursing_notes = admission.nursing_notes.all().order_by('-date_time')
    clinical_records = admission.clinical_records.all().order_by('-date_time')
    clinical_notes = ClinicalNote.objects.filter(patient=admission.patient).order_by('-date')[:10]

    context = {
        'admission': admission,
        'daily_rounds': daily_rounds,
        'nursing_notes': nursing_notes,
        'clinical_records': clinical_records,
        'clinical_notes': clinical_notes,
        'note_form': note_form,
        'round_form': round_form,
        'title': f'Admission Details for {admission.patient.get_full_name()}'
    }
    return render(request, 'inpatient/admission_detail.html', context)

@login_required
@permission_required('inpatient.create')
def create_admission(request):
    """View for creating a new admission"""
    # Pre-fill patient_id if provided in GET parameters
    patient_id = request.GET.get('patient_id')
    initial_data = {}

    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
            initial_data['patient'] = patient.id  # Pass patient ID, not patient object
            initial_data['patient_search'] = str(patient)  # Also set patient search field
        except Patient.DoesNotExist:
            pass

    if request.method == 'POST':
        # DEBUG: log every POST key so we can see what the browser actually sends
        logger.info("=== ADMISSION FORM POST DATA ===")
        for key, values in request.POST.lists():
            logger.info(f"  POST[{key!r}] = {values!r}")
        logger.info("================================")

        form = AdmissionForm(request.POST)
        patient_id = request.POST.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id)
                form.data = form.data.copy()
                form.data['patient'] = patient_id
                form.data['patient_search'] = str(patient)
            except Patient.DoesNotExist:
                messages.error(request, 'Selected patient not found.')
                return redirect('inpatient:create_admission')

        if not form.is_valid():
            logger.warning("=== ADMISSION FORM INVALID ===")
            for field, errors in form.errors.items():
                logger.warning(f"  FIELD ERROR [{field}]: {errors.as_text()!r}")
            logger.warning("==============================")
            messages.error(request, 'Please correct the errors below.')
        if form.is_valid():
            bed = form.cleaned_data['bed']
            authorization_code = form.cleaned_data.get('authorization_code')
            try:
                admission, invoice = admit_patient(
                    patient=form.cleaned_data['patient'],
                    bed=bed,
                    attending_doctor=form.cleaned_data['attending_doctor'],
                    diagnosis=form.cleaned_data['diagnosis'],
                    reason_for_admission=form.cleaned_data['reason_for_admission'],
                    user=request.user,
                    admission_notes=form.cleaned_data.get('admission_notes') or '',
                    admission_date=form.cleaned_data.get('admission_date'),
                    admission_service=form.cleaned_data.get('admission_service'),
                    authorization_code=authorization_code,
                )
            except InpatientActionError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'An error occurred during admission creation: {e}')
                logger.exception('Error during admission creation.')
            else:
                if invoice is None:
                    messages.success(request, 'Admission created successfully. No Admission Fee service configured — no charge applied.')
                elif authorization_code:
                    messages.success(
                        request,
                        f'Admission created successfully! Invoice #{invoice.invoice_number} '
                        f'generated and paid via NHIA authorization code. No daily charges will apply.'
                    )
                else:
                    messages.success(
                        request,
                        f'Admission created successfully! Invoice #{invoice.invoice_number} '
                        f'generated and admission fee deducted from wallet. Daily charges of '
                        f'₦{bed.ward.charge_per_day} will be automatically deducted at 12:00 AM.'
                    )
                return redirect('inpatient:admission_detail', pk=admission.pk)
    else:
        # Pre-select the 'Admission Fee' service if it exists
        try:
            admission_fee_service = Service.objects.get(name='Admission Fee')
            initial_data['admission_service'] = admission_fee_service
        except Service.DoesNotExist:
            pass
        form = AdmissionForm(initial=initial_data)

    # Restore selected patient for UI (survives re-render after validation failure)
    selected_patient = None
    patient_id_val = request.POST.get('patient') if request.method == 'POST' else request.GET.get('patient_id')
    if patient_id_val:
        try:
            selected_patient = Patient.objects.get(id=patient_id_val)
        except Patient.DoesNotExist:
            pass

    context = {
        'form': form,
        'title': 'Create New Admission',
        'all_patients': Patient.objects.filter(is_active=True).select_related().order_by('first_name', 'last_name'),
        'selected_patient': selected_patient,
    }
    return render(request, 'inpatient/admission_form.html', context)


@login_required
@permission_required('inpatient.edit')
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
@permission_required('inpatient.edit')
def transfer_patient(request, admission_id):
    """Handles both bed and ward transfers for a patient."""
    admission = get_object_or_404(Admission, id=admission_id, status='admitted')

    if request.method == 'POST':
        form = PatientTransferForm(request.POST, current_bed=admission.bed)
        if form.is_valid():
            to_bed = form.cleaned_data['to_bed']
            from_bed = admission.bed
            try:
                transfer_service(
                    admission, to_bed,
                    user=request.user,
                    notes=form.cleaned_data.get('notes') or '',
                )
            except InpatientActionError as e:
                messages.error(request, str(e))
            else:
                if from_bed and from_bed.ward_id != to_bed.ward_id:
                    messages.success(request, f"Patient transferred from ward {from_bed.ward.name} to {to_bed.ward.name}.")
                else:
                    messages.success(request, f"Patient transferred to bed {to_bed.bed_number}.")
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
@permission_required('inpatient.discharge')
def discharge_patient(request, admission_id):
    """View for discharging a patient"""
    admission = get_object_or_404(Admission, id=admission_id)

    if request.method == 'POST':
        # Bind to a separate copy: validation writes the POSTed status onto the
        # instance, and the service needs to see the admission as it stands.
        form = DischargeForm(request.POST, instance=Admission.objects.get(pk=admission.pk))
        if form.is_valid():
            try:
                discharge_service(
                    admission,
                    user=request.user,
                    status=form.cleaned_data['status'],
                    discharge_date=form.cleaned_data.get('discharge_date'),
                    discharge_notes=form.cleaned_data.get('discharge_notes') or '',
                )
            except InpatientActionError as e:
                messages.error(request, str(e))
            else:
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
@permission_required('inpatient.create')
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
@permission_required('inpatient.view')
def bed_occupancy_report(request):
    """Enhanced view for generating comprehensive bed occupancy report with statistics"""
    from django.db.models import Count, Q, Avg
    from datetime import datetime, timedelta

    # Bed counts per ward in one annotated query instead of 2 per ward
    wards = Ward.objects.annotate(
        total_beds_count=Count('beds', filter=Q(beds__is_active=True)),
        occupied_beds_count=Count('beds', filter=Q(beds__is_occupied=True, beds__is_active=True)),
    )
    report_data = []

    # Overall statistics
    total_beds_hospital = Bed.objects.filter(is_active=True).count()
    total_occupied_hospital = Bed.objects.filter(is_occupied=True, is_active=True).count()
    total_available_hospital = total_beds_hospital - total_occupied_hospital
    overall_occupancy_rate = (total_occupied_hospital / total_beds_hospital * 100) if total_beds_hospital > 0 else 0

    # Fetch all current admissions once; reuse for hospital avg and per-ward lists
    current_admissions = list(
        Admission.objects.filter(status='admitted')
        .select_related('patient', 'attending_doctor', 'bed')
    )
    avg_length_of_stay = 0
    if current_admissions:
        total_days = sum(admission.get_duration() for admission in current_admissions)
        avg_length_of_stay = total_days / len(current_admissions)

    admissions_by_ward = {}
    for admission in current_admissions:
        if admission.bed_id:
            admissions_by_ward.setdefault(admission.bed.ward_id, []).append(admission)

    # Ward-specific statistics (no per-ward queries)
    for ward in wards:
        total_beds = ward.total_beds_count
        occupied_beds = ward.occupied_beds_count
        available_beds = total_beds - occupied_beds
        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

        current_ward_admissions = admissions_by_ward.get(ward.pk, [])

        ward_avg_los = 0
        if current_ward_admissions:
            ward_total_days = sum(admission.get_duration() for admission in current_ward_admissions)
            ward_avg_los = ward_total_days / len(current_ward_admissions)

        report_data.append({
            'ward': ward,
            'total_beds': total_beds,
            'occupied_beds': occupied_beds,
            'available_beds': available_beds,
            'occupancy_rate': occupancy_rate,
            'current_admissions': current_ward_admissions,
            'avg_length_of_stay': ward_avg_los
        })

    context = {
        'report_data': report_data,
        'total_beds_hospital': total_beds_hospital,
        'total_occupied_hospital': total_occupied_hospital,
        'total_available_hospital': total_available_hospital,
        'overall_occupancy_rate': overall_occupancy_rate,
        'avg_length_of_stay': avg_length_of_stay,
        'page_title': 'Bed Occupancy Report'
    }

    return render(request, 'inpatient/bed_occupancy_report.html', context)


@login_required
@permission_required('inpatient.view')
def admission_net_impact(request, pk):
    """View for analyzing admission net impact on patient wallet"""
    admission = get_object_or_404(Admission, pk=pk)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=admission.patient)
    
    # Calculate admission net impact without updating the balance
    admission_net_impact = admission.get_total_wallet_impact(update_balance=False)
    
    # Calculate projected balance after applying net impact
    projected_balance = max(admission_net_impact, 0)
    
    context = {
        'admission': admission,
        'patient': admission.patient,
        'wallet': wallet,
        'admission_net_impact': admission_net_impact,
        'projected_balance': projected_balance,
        'page_title': f'Admission Net Impact - {admission.patient.get_full_name()}',
    }
    
    return render(request, 'inpatient/admission_net_impact.html', context)


@login_required
@permission_required('inpatient.discharge')
def apply_admission_net_impact(request, pk):
    """View for applying admission net impact calculation to patient wallet"""
    admission = get_object_or_404(Admission, pk=pk)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=admission.patient)
    
    if request.method == 'POST':
        try:
            # Apply net impact calculation and update wallet balance
            net_impact = admission.get_total_wallet_impact(update_balance=True)
            
            # Determine if the balance is positive or negative
            if net_impact >= 0:
                message = f'Successfully applied admission net impact calculation. New wallet balance: ₦{net_impact:.2f}'
                messages.success(request, message)
            else:
                message = f'Applied admission net impact calculation. Wallet balance is now ₦0.00 with outstanding debt of ₦{abs(net_impact):.2f}'
                messages.warning(request, message)
            
            return redirect('inpatient:admission_net_impact', pk=admission.id)
            
        except Exception as e:
            messages.error(request, f'Error applying admission net impact calculation: {str(e)}')
            return redirect('inpatient:admission_net_impact', pk=admission.id)
    
    # If not POST, redirect to the net impact page
    return redirect('inpatient:admission_net_impact', pk=admission.id)


@login_required
@permission_required('inpatient.view')
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