from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponse
from django.db import models
from .models import Ward, Bed, Admission, DailyRound, NursingNote
from .forms import WardForm, BedForm, AdmissionForm, DischargeForm, DailyRoundForm, NursingNoteForm, AdmissionSearchForm
from patients.models import Patient

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

    # Get counts
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
    admissions = Admission.objects.all().select_related('patient', 'bed', 'bed__ward', 'attending_doctor').order_by('-admission_date')

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
    role_counts = Admission.objects.values('attending_doctor__roles__name').annotate(count=models.Count('id')).order_by('-count')
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
                        messages.success(request, f'Patient {admission.patient.get_full_name()} has been admitted successfully to {bed.ward.name}, Bed {bed.bed_number}.')
                        return redirect('inpatient:admission_detail', admission_id=admission.id)
                except Exception as e:
                    messages.error(request, f'Admission failed: {str(e)}')
        else:
            messages.error(request, 'Admission form is invalid. Please check the details and try again.')
    else:
        form = AdmissionForm(initial=initial_data)
        # Only show available and active beds
        form.fields['bed'].queryset = Bed.objects.filter(is_occupied=False, is_active=True)

    context = {
        'form': form,
        'title': 'Admit Patient',
        'form_errors': form.errors if form.errors else None
    }

    return render(request, 'inpatient/admission_form.html', context)

@login_required
def admission_detail(request, admission_id):
    """View for displaying admission details"""
    admission = get_object_or_404(Admission, id=admission_id)
    daily_rounds = DailyRound.objects.filter(admission=admission).order_by('-date_time')
    nursing_notes = NursingNote.objects.filter(admission=admission).order_by('-date_time')

    # Get prescriptions for this patient
    prescriptions = None
    if admission.patient:
        from pharmacy.models import Prescription
        prescriptions = Prescription.objects.filter(patient=admission.patient).order_by('-prescription_date')

    # Handle adding new daily round
    if request.method == 'POST' and 'add_round' in request.POST:
        round_form = DailyRoundForm(request.POST)
        if round_form.is_valid():
            daily_round = round_form.save(commit=False)
            daily_round.admission = admission
            daily_round.save()
            messages.success(request, 'Doctor round has been recorded successfully.')
            return redirect('inpatient:admission_detail', admission_id=admission.id)
    else:
        round_form = DailyRoundForm(initial={'doctor': request.user if request.user.profile.role == 'doctor' else None})

    # Handle adding new nursing note
    if request.method == 'POST' and 'add_note' in request.POST:
        note_form = NursingNoteForm(request.POST)
        if note_form.is_valid():
            nursing_note = note_form.save(commit=False)
            nursing_note.admission = admission
            nursing_note.save()
            messages.success(request, 'Nursing note has been recorded successfully.')
            return redirect('inpatient:admission_detail', admission_id=admission.id)
    else:
        note_form = NursingNoteForm(initial={'nurse': request.user if request.user.profile.role == 'nurse' else None})

    context = {
        'admission': admission,
        'daily_rounds': daily_rounds,
        'nursing_notes': nursing_notes,
        'round_form': round_form,
        'note_form': note_form,
        'prescriptions': prescriptions,
        'title': f'Admission: {admission.patient.get_full_name()}'
    }

    return render(request, 'inpatient/admission_detail.html', context)

@login_required
def edit_admission(request, admission_id):
    """View for editing an admission"""
    admission = get_object_or_404(Admission, id=admission_id)

    # Don't allow editing of discharged, transferred, or deceased admissions
    if admission.status in ['discharged', 'transferred', 'deceased']:
        messages.error(request, f'Cannot edit admission with status: {admission.get_status_display()}')
        return redirect('inpatient:admission_detail', admission_id=admission.id)

    # Get the current bed to check if it changed
    current_bed = admission.bed

    if request.method == 'POST':
        form = AdmissionForm(request.POST, instance=admission)
        if form.is_valid():
            # Check if bed has changed
            new_bed = form.cleaned_data.get('bed')
            if new_bed != current_bed:
                # Update old bed status
                current_bed.is_occupied = False
                current_bed.save()

                # Update new bed status
                new_bed.is_occupied = True
                new_bed.save()

            form.save()
            messages.success(request, f'Admission for {admission.patient.get_full_name()} has been updated successfully.')
            return redirect('inpatient:admission_detail', admission_id=admission.id)
    else:
        form = AdmissionForm(instance=admission)
        # Allow selecting the current bed even if it's occupied
        form.fields['bed'].queryset = Bed.objects.filter(Q(is_occupied=False, is_active=True) | Q(id=current_bed.id))

    context = {
        'form': form,
        'admission': admission,
        'title': f'Edit Admission: {admission.patient.get_full_name()}'
    }

    return render(request, 'inpatient/admission_form.html', context)

@login_required
def discharge_patient(request, admission_id):
    """View for discharging a patient"""
    admission = get_object_or_404(Admission, id=admission_id)

    # Don't allow discharging already discharged, transferred, or deceased patients
    if admission.status in ['discharged', 'transferred', 'deceased']:
        messages.error(request, f'Patient has already been {admission.get_status_display().lower()}.')
        return redirect('inpatient:admission_detail', admission_id=admission.id)

    if request.method == 'POST':
        form = DischargeForm(request.POST, instance=admission)
        if form.is_valid():
            # Update the admission
            admission = form.save()

            # Free up the bed
            bed = admission.bed
            bed.is_occupied = False
            bed.save()

            messages.success(request, f'Patient {admission.patient.get_full_name()} has been {admission.get_status_display().lower()} successfully.')
            return redirect('inpatient:admission_detail', admission_id=admission.id)
    else:
        form = DischargeForm(instance=admission)

    context = {
        'form': form,
        'admission': admission,
        'title': f'Discharge Patient: {admission.patient.get_full_name()}'
    }

    return render(request, 'inpatient/discharge_form.html', context)

@login_required
def patient_admissions(request, patient_id):
    """View for displaying admissions for a specific patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    admissions = Admission.objects.filter(patient=patient).order_by('-admission_date')

    context = {
        'patient': patient,
        'admissions': admissions,
        'title': f'Admissions for {patient.get_full_name()}'
    }

    return render(request, 'inpatient/patient_admissions.html', context)

@login_required
def bed_dashboard(request):
    """Enhanced bed management dashboard: filter, bulk actions, notifications, analytics, CSV export."""
    from .models import Bed, Ward, Admission
    wards = Ward.objects.filter(is_active=True).order_by('name')
    beds = Bed.objects.select_related('ward').all()

    # Filters
    ward_id = request.GET.get('ward')
    bed_status = request.GET.get('status')
    search = request.GET.get('search', '')
    if ward_id:
        beds = beds.filter(ward_id=ward_id)
    if bed_status == 'available':
        beds = beds.filter(is_occupied=False, is_active=True)
    elif bed_status == 'occupied':
        beds = beds.filter(is_occupied=True)
    elif bed_status == 'inactive':
        beds = beds.filter(is_active=False)
    if search:
        beds = beds.filter(Q(bed_number__icontains=search) | Q(ward__name__icontains=search))

    # Bulk actions: Mark beds as available/inactive
    if request.method == 'POST' and 'bulk_action' in request.POST:
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_beds')
        if selected_ids:
            qs = Bed.objects.filter(id__in=selected_ids)
            if action == 'mark_available':
                qs.update(is_active=True, is_occupied=False)
                messages.success(request, f"{qs.count()} bed(s) marked as available.")
            elif action == 'mark_inactive':
                qs.update(is_active=False)
                messages.success(request, f"{qs.count()} bed(s) marked as inactive.")
            return redirect('inpatient:bed_dashboard')

    # Analytics
    total_beds = beds.count()
    available_beds = beds.filter(is_occupied=False, is_active=True).count()
    occupied_beds = beds.filter(is_occupied=True).count()
    inactive_beds = beds.filter(is_active=False).count()
    occupancy_rate = (occupied_beds / total_beds * 100) if total_beds else 0

    # CSV export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bed_dashboard.csv"'
        import csv
        writer = csv.writer(response)
        writer.writerow(['Ward', 'Bed Number', 'Status', 'Description', 'Current Patient'])
        for bed in beds:
            status = 'Inactive' if not bed.is_active else ('Occupied' if bed.is_occupied else 'Available')
            current_patient = ''
            if bed.is_occupied:
                admission = bed.admissions.filter(status='admitted').first()
                if admission:
                    current_patient = admission.patient.get_full_name()
            writer.writerow([
                bed.ward.name,
                bed.bed_number,
                status,
                bed.description or '-',
                current_patient
            ])
        return response

    # Pagination
    paginator = Paginator(beds.order_by('ward__name', 'bed_number'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wards': wards,
        'page_obj': page_obj,
        'ward_id': ward_id,
        'bed_status': bed_status,
        'search': search,
        'total_beds': total_beds,
        'available_beds': available_beds,
        'occupied_beds': occupied_beds,
        'inactive_beds': inactive_beds,
        'occupancy_rate': occupancy_rate,
        'page_title': 'Bed Management Dashboard',
        'active_nav': 'bed_dashboard',
    }
    return render(request, 'inpatient/bed_dashboard.html', context)
