from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from accounts.models import CustomUser
from django.contrib.auth.models import User
from django.db import models

from .models import ConsultingRoom, WaitingList, Consultation, ConsultationNote, Referral, SOAPNote
from .forms import (
    ConsultationForm, ConsultationNoteForm, ReferralForm, VitalsSelectionForm,
    ConsultingRoomForm, WaitingListForm
)
from patients.models import Patient, Vitals
from appointments.models import Appointment
from core.decorators import doctor_required, receptionist_required
from pharmacy.models import Prescription, PrescriptionItem
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from core.audit_utils import log_audit_action
from core.models import send_notification_email, send_notification_sms, InternalNotification
from billing.models import Invoice

@login_required
@doctor_required
def doctor_dashboard(request):
    """Dashboard view for doctors showing assigned patients with vitals"""
    doctor = request.user

    # Get today's date
    today = timezone.now().date()

    # Get today's appointments for this doctor
    appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today,
        status__in=['scheduled', 'confirmed']
    ).order_by('appointment_time')

    # Get patients with vitals taken today
    patients_with_vitals = Patient.objects.filter(
        vitals__date_time__date=today,
        appointments__doctor=doctor,
        appointments__appointment_date=today
    ).distinct()

    # Get pending consultations
    pending_consultations = Consultation.objects.filter(
        doctor=doctor,
        status__in=['pending', 'in_progress']
    ).order_by('-consultation_date')[:5]

    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor=doctor,
        status='completed'
    ).order_by('-consultation_date')[:5]

    # Get pending referrals
    pending_referrals = Referral.objects.filter(
        referred_to=doctor,
        status='pending'
    ).order_by('-referral_date')

    context = {
        'appointments': appointments,
        'patients_with_vitals': patients_with_vitals,
        'pending_consultations': pending_consultations,
        'recent_consultations': recent_consultations,
        'pending_referrals': pending_referrals,
        'today': today,
        'page_title': 'Doctor Dashboard',
        'active_nav': 'dashboard',
    }

    return render(request, 'consultations/doctor_dashboard.html', context)

@login_required
@doctor_required
def patient_list(request):
    """View for doctors to see their patients"""
    doctor = request.user

    # Get patients with appointments for this doctor
    patients = Patient.objects.filter(
        appointments__doctor=doctor
    ).distinct().order_by('-appointments__appointment_date')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(patient_id__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(patients, 10)  # Show 10 patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'page_title': 'My Patients',
        'active_nav': 'patients',
    }

    return render(request, 'consultations/patient_list.html', context)

@login_required
@doctor_required
def patient_detail(request, patient_id):
    """View for doctors to see patient details and vitals"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Get patient's vitals
    vitals = Vitals.objects.filter(patient=patient).order_by('-date_time')

    # Get patient's consultations with this doctor
    consultations = Consultation.objects.filter(
        patient=patient,
        doctor=request.user
    ).order_by('-consultation_date')

    # Get patient's appointments with this doctor
    appointments = Appointment.objects.filter(
        patient=patient,
        doctor=request.user
    ).order_by('-appointment_date')

    context = {
        'patient': patient,
        'vitals': vitals,
        'consultations': consultations,
        'appointments': appointments,
        'page_title': f'Patient Details: {patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/patient_detail.html', context)

@login_required
def create_consultation(request, patient_id):
    """View for creating a new consultation"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Check if there's an appointment for today
    today = timezone.now().date()
    appointment = Appointment.objects.filter(
        patient=patient,
        doctor=request.user,
        appointment_date=today
    ).first()

    # Get the latest vitals
    latest_vitals = Vitals.objects.filter(patient=patient).order_by('-date_time').first()

    if request.method == 'POST':
        # Handle direct form submission from modal
        chief_complaint = request.POST.get('chief_complaint')
        symptoms = request.POST.get('symptoms')
        diagnosis = request.POST.get('diagnosis')
        consultation_notes = request.POST.get('consultation_notes')

        if chief_complaint and symptoms:
            consultation = Consultation(
                patient=patient,
                doctor=request.user,
                chief_complaint=chief_complaint,
                symptoms=symptoms,
                diagnosis=diagnosis,
                consultation_notes=consultation_notes,
                status='completed'
            )

            # Set the appointment if it exists
            if appointment:
                consultation.appointment = appointment

            # Set the latest vitals if they exist
            if latest_vitals:
                consultation.vitals = latest_vitals

            consultation.save()

            messages.success(request, f"Consultation for {patient.get_full_name()} created successfully.")
            return redirect('patients:detail', patient_id=patient.id)
        else:
            messages.error(request, "Chief complaint and symptoms are required.")
            return redirect('patients:detail', patient_id=patient.id)
    else:
        # Pre-fill the form
        initial_data = {
            'patient': patient,
            'doctor': request.user,
        }

        form = ConsultationForm(initial=initial_data)
        vitals_form = VitalsSelectionForm(patient)

    context = {
        'form': form,
        'vitals_form': vitals_form,
        'patient': patient,
        'latest_vitals': latest_vitals,
        'appointment': appointment,
        'page_title': 'New Consultation',
        'active_nav': 'consultations',
    }

    return render(request, 'consultations/consultation_form.html', context)

@login_required
@doctor_required
def consultation_detail(request, consultation_id):
    """View for displaying consultation details"""
    consultation = get_object_or_404(Consultation, id=consultation_id)

    # Check if the logged-in doctor is the one who created the consultation
    if consultation.doctor != request.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this consultation.")
        return redirect('consultations:doctor_dashboard')

    # Get consultation notes
    notes = consultation.notes.all().order_by('-created_at')

    # Get referrals
    referrals = consultation.referrals.all().order_by('-referral_date')

    # In consultation_detail context, add billing info if available
    invoice = Invoice.objects.filter(patient=consultation.patient).order_by('-created_at').first()

    # Handle adding new note
    if request.method == 'POST' and 'add_note' in request.POST:
        note_form = ConsultationNoteForm(request.POST)
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.consultation = consultation
            note.created_by = request.user
            note.save()
            messages.success(request, "Note added successfully.")
            return redirect('consultations:consultation_detail', consultation_id=consultation.id)
    else:
        note_form = ConsultationNoteForm()

    # Handle adding new referral
    if request.method == 'POST' and 'add_referral' in request.POST:
        referral_form = ReferralForm(request.POST)
        if referral_form.is_valid():
            referral = referral_form.save(commit=False)
            referral.consultation = consultation
            referral.patient = consultation.patient
            referral.referring_doctor = request.user
            referral.save()
            messages.success(request, "Referral created successfully.")
            return redirect('consultations:consultation_detail', consultation_id=consultation.id)
    else:
        referral_form = ReferralForm()

    # Advanced: Fetch audit logs related to this consultation
    from core.models import AuditLog
    # Note: Current AuditLog model doesn't have object_id/content_type fields
    # Filtering by details that might contain consultation information
    audit_logs = AuditLog.objects.filter(
        details__icontains=f'consultation {consultation.id}'
    ).order_by('-timestamp')

    # Advanced: Fetch internal notifications for the current user related to this consultation
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains=str(consultation.id),
        is_read=False
    ).order_by('-created_at')[:10]

    # Advanced: Role-based analytics (counts)
    analytics = {
        'note_count': notes.count(),
        'referral_count': referrals.count(),
        'soap_count': consultation.soapnote_set.count(),
        'actions_by_role': AuditLog.objects.filter(
            details__icontains=f'consultation {consultation.id}'
        ).values('user__first_name', 'user__last_name').annotate(count=models.Count('id')).order_by('-count')
    }

    context = {
        'consultation': consultation,
        'notes': notes,
        'referrals': referrals,
        'note_form': note_form,
        'referral_form': referral_form,
        'page_title': 'Consultation Details',
        'active_nav': 'consultations',
        'invoice': invoice,
        # Advanced features:
        'audit_logs': audit_logs,
        'user_notifications': user_notifications,
        'analytics': analytics,
    }

    return render(request, 'consultations/consultation_detail.html', context)

@login_required
@doctor_required
def edit_consultation(request, consultation_id):
    """View for editing a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id)

    # Check if the logged-in doctor is the one who created the consultation
    if consultation.doctor != request.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit this consultation.")
        return redirect('consultations:doctor_dashboard')

    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        vitals_form = VitalsSelectionForm(consultation.patient, request.POST)

        if form.is_valid() and vitals_form.is_valid():
            consultation = form.save()

            # Update vitals if selected
            selected_vitals = vitals_form.cleaned_data.get('vitals')
            if selected_vitals:
                consultation.vitals = selected_vitals
                consultation.save()

            messages.success(request, "Consultation updated successfully.")
            return redirect('consultations:consultation_detail', consultation_id=consultation.id)
    else:
        form = ConsultationForm(instance=consultation)
        vitals_form = VitalsSelectionForm(consultation.patient, initial={'vitals': consultation.vitals})

    context = {
        'form': form,
        'vitals_form': vitals_form,
        'consultation': consultation,
    }

    return render(request, 'consultations/consultation_form.html', context)

@login_required
@doctor_required
def consultation_list(request):
    """View for listing all consultations for a doctor"""
    doctor = request.user

    # Get consultations for this doctor
    consultations = Consultation.objects.filter(doctor=doctor).order_by('-consultation_date')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        consultations = consultations.filter(status=status)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            consultations = consultations.filter(consultation_date__date__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            consultations = consultations.filter(consultation_date__date__lte=date_to)
        except ValueError:
            pass

    # Search by patient name or ID
    search_query = request.GET.get('search', '')
    if search_query:
        consultations = consultations.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(consultations, 10)  # Show 10 consultations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status': status,
        'date_from': date_from if isinstance(date_from, str) else date_from.strftime('%Y-%m-%d') if date_from else '',
        'date_to': date_to if isinstance(date_to, str) else date_to.strftime('%Y-%m-%d') if date_to else '',
        'search_query': search_query,
    }

    return render(request, 'consultations/consultation_list.html', context)

@login_required
@doctor_required
def referral_list(request):
    """View for listing all referrals for a doctor"""
    doctor = request.user

    # Get referrals made by this doctor
    referrals_made = Referral.objects.filter(referring_doctor=doctor).order_by('-referral_date')

    # Get referrals received by this doctor
    referrals_received = Referral.objects.filter(referred_to=doctor).order_by('-referral_date')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        referrals_made = referrals_made.filter(status=status)
        referrals_received = referrals_received.filter(status=status)

    # Pagination for referrals made
    made_paginator = Paginator(referrals_made, 5)
    made_page = request.GET.get('made_page')
    made_page_obj = made_paginator.get_page(made_page)

    # Pagination for referrals received
    received_paginator = Paginator(referrals_received, 5)
    received_page = request.GET.get('received_page')
    received_page_obj = received_paginator.get_page(received_page)

    context = {
        'made_page_obj': made_page_obj,
        'received_page_obj': received_page_obj,
        'status': status,
    }

    return render(request, 'consultations/referral_list.html', context)

@login_required
def create_referral(request):
    """View for creating a new referral directly from the patient detail page"""
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        referring_doctor_id = request.POST.get('referring_doctor')
        referred_to_id = request.POST.get('referred_to')
        reason = request.POST.get('reason')
        notes = request.POST.get('notes')
        urgency = request.POST.get('urgency', 'normal')
        referral_date = request.POST.get('referral_date')

        if patient_id and referring_doctor_id and referred_to_id and reason:
            try:
                patient = Patient.objects.get(id=patient_id)
                referring_doctor = User.objects.get(id=referring_doctor_id)
                referred_to = User.objects.get(id=referred_to_id)

                # Create a new referral
                referral = Referral(
                    patient=patient,
                    referring_doctor=referring_doctor,
                    referred_to=referred_to,
                    reason=reason,
                    notes=notes,
                    status='pending',
                    referral_date=timezone.now() if not referral_date else referral_date
                )

                # Create a consultation if it doesn't exist
                consultation = Consultation.objects.filter(
                    patient=patient,
                    doctor=referring_doctor,
                    consultation_date__date=timezone.now().date()
                ).first()

                if not consultation:
                    consultation = Consultation.objects.create(
                        patient=patient,
                        doctor=referring_doctor,
                        chief_complaint="Referral to specialist",
                        symptoms="See referral notes",
                        diagnosis="Requires specialist consultation",
                        consultation_notes=f"Patient referred to Dr. {referred_to.get_full_name()} for {reason}",
                        status='completed'
                    )

                referral.consultation = consultation
                referral.save()

                messages.success(request, f"Referral for {patient.get_full_name()} created successfully.")
            except (Patient.DoesNotExist, User.DoesNotExist) as e:
                messages.error(request, f"Error creating referral: {str(e)}")
        else:
            messages.error(request, "Missing required fields for referral.")

        return redirect('patients:detail', patient_id=patient_id)

    return redirect('dashboard:dashboard')

@login_required
@doctor_required
def update_referral_status(request, referral_id):
    """View for updating referral status"""
    referral = get_object_or_404(Referral, id=referral_id)

    # Check if the logged-in doctor is the one who received the referral
    if referral.referred_to != request.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to update this referral.")
        return redirect('consultations:referral_list')

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Referral.STATUS_CHOICES):
            referral.status = status
            referral.save()
            messages.success(request, "Referral status updated successfully.")
        else:
            messages.error(request, "Invalid status.")

    return redirect('consultations:referral_list')

# Consulting Room Views
@login_required
def consulting_room_list(request):
    """View for listing all consulting rooms"""
    consulting_rooms = ConsultingRoom.objects.all().order_by('room_number')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        consulting_rooms = consulting_rooms.filter(
            Q(room_number__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by department
    department = request.GET.get('department', '')
    if department:
        consulting_rooms = consulting_rooms.filter(department__id=department)

    # Filter by status
    is_active = request.GET.get('is_active', '')
    if is_active:
        is_active = is_active == 'true'
        consulting_rooms = consulting_rooms.filter(is_active=is_active)

    # Pagination
    paginator = Paginator(consulting_rooms, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'department': department,
        'is_active': is_active,
    }

    return render(request, 'consultations/consulting_room_list.html', context)

@login_required
def create_consulting_room(request):
    """View for creating a new consulting room"""
    if request.method == 'POST':
        form = ConsultingRoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Consulting room created successfully.")
            return redirect('consultations:consulting_room_list')
    else:
        form = ConsultingRoomForm()

    context = {
        'form': form,
        'title': 'Create Consulting Room',
    }

    return render(request, 'consultations/consulting_room_form.html', context)

@login_required
def edit_consulting_room(request, room_id):
    """View for editing a consulting room"""
    consulting_room = get_object_or_404(ConsultingRoom, id=room_id)

    if request.method == 'POST':
        form = ConsultingRoomForm(request.POST, instance=consulting_room)
        if form.is_valid():
            form.save()
            messages.success(request, "Consulting room updated successfully.")
            return redirect('consultations:consulting_room_list')
    else:
        form = ConsultingRoomForm(instance=consulting_room)

    context = {
        'form': form,
        'consulting_room': consulting_room,
        'title': 'Edit Consulting Room',
    }

    return render(request, 'consultations/consulting_room_form.html', context)

@login_required
def delete_consulting_room(request, room_id):
    """View for deleting a consulting room"""
    consulting_room = get_object_or_404(ConsultingRoom, id=room_id)

    if request.method == 'POST':
        # Check if there are any waiting patients or consultations
        if consulting_room.waiting_patients.exists() or consulting_room.consultations.exists():
            messages.error(request, "Cannot delete consulting room with associated patients or consultations.")
        else:
            consulting_room.delete()
            messages.success(request, "Consulting room deleted successfully.")
        return redirect('consultations:consulting_room_list')

    context = {
        'consulting_room': consulting_room,
    }

    return render(request, 'consultations/delete_consulting_room.html', context)

# Waiting List Views
@login_required
@receptionist_required
def waiting_list(request):
    """View for displaying the patient waiting list"""
    waiting_entries = WaitingList.objects.filter(
        status__in=['waiting', 'in_progress']
    ).order_by('priority', 'check_in_time')

    # Filter by doctor
    doctor = request.GET.get('doctor', '')
    if doctor:
        waiting_entries = waiting_entries.filter(doctor__id=doctor)

    # Filter by consulting room
    consulting_room = request.GET.get('consulting_room', '')
    if consulting_room:
        waiting_entries = waiting_entries.filter(consulting_room__id=consulting_room)

    # Filter by priority
    priority = request.GET.get('priority', '')
    if priority:
        waiting_entries = waiting_entries.filter(priority=priority)

    # Search by patient name or ID
    search_query = request.GET.get('search', '')
    if search_query:
        waiting_entries = waiting_entries.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )

    # Get all doctors and consulting rooms for filters
    doctors = CustomUser.objects.filter(is_active=True, profile__role='doctor')
    consulting_rooms = ConsultingRoom.objects.filter(is_active=True)

    context = {
        'waiting_entries': waiting_entries,
        'doctors': doctors,
        'consulting_rooms': consulting_rooms,
        'doctor': doctor,
        'consulting_room': consulting_room,
        'priority': priority,
        'search_query': search_query,
    }

    return render(request, 'consultations/waiting_list.html', context)

@login_required
@receptionist_required
def add_to_waiting_list(request, patient_id=None):
    """View for adding a patient to the waiting list"""
    initial_data = {}
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
        initial_data['patient'] = patient

    if request.method == 'POST':
        form = WaitingListForm(request.POST, initial=initial_data)
        # Ensure all patients are available for selection
        form.fields['patient'].queryset = Patient.objects.all()
        if form.is_valid():
            waiting_entry = form.save(commit=False)
            waiting_entry.created_by = request.user
            waiting_entry.save()

            messages.success(request, f"{waiting_entry.patient.get_full_name()} added to waiting list for Dr. {waiting_entry.doctor.get_full_name()} in Room {waiting_entry.consulting_room.room_number}.")
            return redirect('consultations:waiting_list')
    else:
        form = WaitingListForm(initial=initial_data)
        # Ensure all patients are available for selection
        form.fields['patient'].queryset = Patient.objects.all()

    context = {
        'form': form,
        'title': 'Add Patient to Waiting List',
    }

    return render(request, 'consultations/waiting_list_form.html', context)

@login_required
def update_waiting_status(request, entry_id):
    """View for updating waiting list entry status"""
    waiting_entry = get_object_or_404(WaitingList, id=entry_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(WaitingList.STATUS_CHOICES):
            waiting_entry.status = status
            waiting_entry.save()

            # If status is 'in_progress', create a consultation if it doesn't exist
            if status == 'in_progress' and not hasattr(waiting_entry, 'consultation'):
                consultation = Consultation.objects.create(
                    patient=waiting_entry.patient,
                    doctor=waiting_entry.doctor,
                    consulting_room=waiting_entry.consulting_room,
                    waiting_list_entry=waiting_entry,
                    appointment=waiting_entry.appointment,
                    chief_complaint="",
                    symptoms="",
                    status='in_progress'
                )

                # Get the latest vitals if they exist
                latest_vitals = Vitals.objects.filter(patient=waiting_entry.patient).order_by('-date_time').first()
                if latest_vitals:
                    consultation.vitals = latest_vitals
                    consultation.save()

            messages.success(request, f"Status updated to {waiting_entry.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")

    # Redirect based on user role
    if hasattr(request.user, 'profile') and request.user.profile.role == 'doctor':
        return redirect('consultations:doctor_waiting_list')
    else:
        return redirect('consultations:waiting_list')

@login_required
@doctor_required
def doctor_waiting_list(request):
    """View for doctors to see their waiting patients"""
    doctor = request.user

    # Get waiting patients for this doctor
    waiting_entries = WaitingList.objects.filter(
        doctor=doctor,
        status__in=['waiting', 'in_progress']
    ).order_by('priority', 'check_in_time')

    # Filter by consulting room
    consulting_room = request.GET.get('consulting_room', '')
    if consulting_room:
        waiting_entries = waiting_entries.filter(consulting_room__id=consulting_room)

    # Get consulting rooms for this doctor
    consulting_rooms = ConsultingRoom.objects.filter(
        is_active=True,
        waiting_patients__doctor=doctor
    ).distinct()

    context = {
        'waiting_entries': waiting_entries,
        'consulting_rooms': consulting_rooms,
        'consulting_room': consulting_room,
    }

    return render(request, 'consultations/doctor_waiting_list.html', context)

@login_required
@doctor_required
def start_consultation(request, entry_id):
    """View for starting a consultation from the waiting list"""
    waiting_entry = get_object_or_404(WaitingList, id=entry_id, doctor=request.user)

    # Update waiting entry status
    waiting_entry.status = 'in_progress'
    waiting_entry.save()

    # Check if a consultation already exists
    try:
        consultation = waiting_entry.consultation
    except Consultation.DoesNotExist:
        # Create a new consultation
        consultation = Consultation.objects.create(
            patient=waiting_entry.patient,
            doctor=waiting_entry.doctor,
            consulting_room=waiting_entry.consulting_room,
            waiting_list_entry=waiting_entry,
            appointment=waiting_entry.appointment,
            chief_complaint="",
            symptoms="",
            status='in_progress'
        )

        # Get the latest vitals if they exist
        latest_vitals = Vitals.objects.filter(patient=waiting_entry.patient).order_by('-date_time').first()
        if latest_vitals:
            consultation.vitals = latest_vitals
            consultation.save()

    return redirect('consultations:doctor_consultation', consultation_id=consultation.id)

@login_required
@doctor_required
def doctor_consultation(request, consultation_id):
    """View for doctors to conduct consultations"""
    consultation = get_object_or_404(Consultation, id=consultation_id, doctor=request.user)

    # Check if the consultation is assigned to the logged-in doctor
    if consultation.doctor != request.user:
        messages.error(request, "You don't have permission to view this consultation.")
        return redirect('consultations:doctor_dashboard')

    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            consultation = form.save()

            # If the consultation is completed, update the waiting list entry
            if consultation.status == 'completed' and consultation.waiting_list_entry:
                consultation.waiting_list_entry.status = 'completed'
                consultation.waiting_list_entry.save()

            messages.success(request, "Consultation updated successfully.")

            # Check if we need to create a prescription
            if 'create_prescription' in request.POST:
                return redirect('consultations:create_prescription', consultation_id=consultation.id)

            # Check if we need to create a lab test request
            if 'create_lab_request' in request.POST:
                return redirect('consultations:create_lab_request', consultation_id=consultation.id)

            # Check if we need to create a radiology order
            if 'create_radiology_order' in request.POST:
                return redirect('consultations:create_radiology_order', consultation_id=consultation.id)

            # Check if we need to create a referral
            if 'create_referral' in request.POST:
                return redirect('consultations:create_referral_from_consultation', consultation_id=consultation.id)

            return redirect('consultations:doctor_consultation', consultation_id=consultation.id)
    else:
        form = ConsultationForm(instance=consultation)

    # Get patient's vitals
    vitals = Vitals.objects.filter(patient=consultation.patient).order_by('-date_time')[:5]

    # Get patient's medical history
    medical_history = consultation.patient.medical_histories.all().order_by('-date')[:5]

    # Get patient's prescriptions
    prescriptions = Prescription.objects.filter(patient=consultation.patient).order_by('-prescription_date')[:5]

    # Get patient's lab tests
    lab_tests = TestRequest.objects.filter(patient=consultation.patient).order_by('-request_date')[:5]

    # Get patient's radiology orders
    radiology_orders = RadiologyOrder.objects.filter(patient=consultation.patient).order_by('-order_date')[:5]

    context = {
        'consultation': consultation,
        'form': form,
        'vitals': vitals,
        'medical_history': medical_history,
        'prescriptions': prescriptions,
        'lab_tests': lab_tests,
        'radiology_orders': radiology_orders,
    }

    return render(request, 'consultations/doctor_consultation.html', context)

@login_required
@doctor_required
def create_prescription(request, consultation_id):
    """View for creating a prescription from a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id, doctor=request.user)

    # Create a new prescription
    prescription = Prescription.objects.create(
        patient=consultation.patient,
        doctor=request.user,
        prescription_date=timezone.now().date(),
        diagnosis=consultation.diagnosis,
        status='pending',
        notes=f"Prescription created from consultation on {consultation.consultation_date.strftime('%Y-%m-%d')}"
    )

    messages.success(request, "Prescription created. Please add medications.")
    return redirect('pharmacy:edit_prescription', prescription_id=prescription.id)

@login_required
@doctor_required
def create_lab_request(request, consultation_id):
    """View for creating a lab test request from a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id, doctor=request.user)

    # Create a new test request
    test_request = TestRequest.objects.create(
        patient=consultation.patient,
        doctor=request.user,
        request_date=timezone.now().date(),
        status='pending',
        priority='normal',
        notes=f"Test request created from consultation on {consultation.consultation_date.strftime('%Y-%m-%d')}"
    )

    messages.success(request, "Lab test request created. Please select tests.")
    return redirect('laboratory:edit_test_request', request_id=test_request.id)

@login_required
@doctor_required
def create_radiology_order(request, consultation_id):
    """View for creating a radiology order from a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id, doctor=request.user)

    # Create a new radiology order
    radiology_order = RadiologyOrder.objects.create(
        patient=consultation.patient,
        referring_doctor=request.user,
        order_date=timezone.now(),
        status='pending',
        priority='normal',
        clinical_information=consultation.diagnosis or consultation.symptoms,
        notes=f"Radiology order created from consultation on {consultation.consultation_date.strftime('%Y-%m-%d')}"
    )

    messages.success(request, "Radiology order created. Please select tests.")
    return redirect('radiology:edit_order', order_id=radiology_order.id)

@login_required
@doctor_required
def create_referral_from_consultation(request, consultation_id):
    """View for creating a referral from a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id, doctor=request.user)

    if request.method == 'POST':
        form = ReferralForm(request.POST)
        if form.is_valid():
            referral = form.save(commit=False)
            referral.consultation = consultation
            referral.patient = consultation.patient
            referral.referring_doctor = request.user
            referral.save()

            messages.success(request, "Referral created successfully.")
            return redirect('consultations:doctor_consultation', consultation_id=consultation.id)
    else:
        form = ReferralForm()

    context = {
        'form': form,
        'consultation': consultation,
    }

    return render(request, 'consultations/referral_form.html', context)

@login_required
@doctor_required
def add_soap_note(request, consultation_id):
    """View for adding a SOAP note to a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    if request.method == 'POST':
        # form = SOAPNoteForm(request.POST)
        form = None  # SOAPNoteForm does not exist
        if form.is_valid():
            soap_note = form.save(commit=False)
            soap_note.consultation = consultation
            soap_note.created_by = request.user
            soap_note.save()
            # Audit log
            log_audit_action(request.user, 'create', soap_note, f"Created SOAP note for consultation {consultation.id}")
            # Internal notification to doctor
            InternalNotification.objects.create(
                user=consultation.doctor,
                message=f"A new SOAP note was added for consultation with {consultation.patient.get_full_name()}"
            )
            # Email notification to doctor
            send_notification_email(
                subject="New SOAP Note Added",
                message=f"A new SOAP note was added for your consultation with {consultation.patient.get_full_name()}.",
                recipient_list=[consultation.doctor.email]
            )
            messages.success(request, "SOAP note added successfully.")
            return redirect('consultations:consultation_detail', consultation_id=consultation.id)
    else:
        # form = SOAPNoteForm()
        form = None  # SOAPNoteForm does not exist
    context = {
        'form': form,
        'consultation': consultation,
    }
    return render(request, 'consultations/soap_note_form.html', context)