import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.core.paginator import Paginator
from .models import Consultation, ConsultationNote, Referral, SOAPNote, ConsultationOrder, ConsultingRoom, WaitingList
from .forms import QuickLabOrderForm, QuickRadiologyOrderForm, QuickPrescriptionForm, ConsultingRoomForm, WaitingListForm, ReferralForm, ConsultationForm, VitalsSelectionForm
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from pharmacy.models import Prescription
from accounts.models import CustomUser, Department
from patients.models import Patient, Vitals, ClinicalNote
from patients.utils import get_safe_vitals_for_patient, get_latest_safe_vitals_for_patient
from appointments.models import Appointment
from core.audit_utils import log_audit_action
from core.models import send_notification_email, send_notification_sms, InternalNotification


@login_required
def unified_dashboard(request):
    """Unified dashboard combining waiting list and consultations"""
    # Superusers and admins see all consultations
    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role in ['admin', 'health_record_officer', 'receptionist']):
        consultations = Consultation.objects.all().order_by('-consultation_date')
        waiting_entries = WaitingList.objects.filter(
            status__in=['waiting', 'in_progress']
        ).order_by('priority', 'check_in_time')
    elif hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role == 'doctor':
        # Doctors see only their consultations
        consultations = Consultation.objects.filter(doctor=request.user).order_by('-consultation_date')
        waiting_entries = WaitingList.objects.filter(
            doctor=request.user,
            status__in=['waiting', 'in_progress']
        ).order_by('priority', 'check_in_time')
    else:
        # Default: show all
        consultations = Consultation.objects.all().order_by('-consultation_date')
        waiting_entries = WaitingList.objects.filter(
            status__in=['waiting', 'in_progress']
        ).order_by('priority', 'check_in_time')
    
    # Calculate statistics
    total_waiting = waiting_entries.filter(status='waiting').count()
    in_progress_count = waiting_entries.filter(status='in_progress').count()
    completed_today = consultations.filter(
        status='completed',
        consultation_date__date=timezone.now().date()
    ).count()
    
    context = {
        'consultations': consultations[:10],  # Show recent consultations
        'waiting_entries': waiting_entries,
        'total_waiting': total_waiting,
        'in_progress_count': in_progress_count,
        'completed_today': completed_today,
        'is_unified_view': True,
    }
    return render(request, 'consultations/unified_dashboard.html', context)

@login_required
def consultation_list(request):
    """View to list consultations for the logged-in doctor with waiting list integration"""
    # Superusers and admins see all consultations
    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role in ['admin', 'health_record_officer', 'receptionist']):
        consultations = Consultation.objects.all().order_by('-consultation_date')
        waiting_entries = WaitingList.objects.filter(
            status__in=['waiting', 'in_progress']
        ).order_by('priority', 'check_in_time')
    elif hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role == 'doctor':
        # Doctors see only their consultations
        consultations = Consultation.objects.filter(doctor=request.user).order_by('-consultation_date')
        waiting_entries = WaitingList.objects.filter(
            doctor=request.user,
            status__in=['waiting', 'in_progress']
        ).order_by('priority', 'check_in_time')
    else:
        # Default: show all
        consultations = Consultation.objects.all().order_by('-consultation_date')
        waiting_entries = WaitingList.objects.filter(
            status__in=['waiting', 'in_progress']
        ).order_by('priority', 'check_in_time')
    
    context = {
        'consultations': consultations,
        'waiting_entries': waiting_entries,
        'show_waiting_list': True,
    }
    return render(request, 'consultations/consultation_list.html', context)


@login_required
def bulk_start_consultations(request):
    """Start multiple consultations from waiting list"""
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'message': 'Bulk start endpoint is accessible'
        })
    
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role == 'doctor')):
        return JsonResponse({
            'success': False,
            'message': 'Only doctors and superusers can start consultations.'
        })
    
    try:
        entry_ids = request.POST.getlist('entry_ids')
        if not entry_ids:
            return JsonResponse({
                'success': False,
                'message': 'No entries selected.'
            })
        
        started_consultations = []
        errors = []
        
        for entry_id in entry_ids:
            try:
                waiting_entry = get_object_or_404(WaitingList, id=entry_id, doctor=request.user)
                
                # Check if a consultation already exists
                try:
                    consultation = waiting_entry.consultation
                    if consultation.status == 'completed':
                        # Create new consultation if previous one is completed
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
                        started_consultations.append({
                            'patient': waiting_entry.patient.get_full_name(),
                            'consultation_id': consultation.id
                        })
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
                    started_consultations.append({
                        'patient': waiting_entry.patient.get_full_name(),
                        'consultation_id': consultation.id
                    })
                
                # Update waiting entry status
                waiting_entry.status = 'in_progress'
                waiting_entry.save()
                
            except Exception as e:
                errors.append(f"Error with entry {entry_id}: {str(e)}")
        
        return JsonResponse({
            'success': len(started_consultations) > 0,
            'message': f"Started {len(started_consultations)} consultations.",
            'started': started_consultations,
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error starting consultations: {str(e)}'
        })

@require_http_methods(["POST"])
@login_required
def update_consultation_status(request, consultation_id):
    """AJAX view to update consultation status"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check if user has permission to update this consultation
    if not (request.user == consultation.doctor or request.user.is_staff or request.user.is_superuser):
        return JsonResponse({
            'success': False, 
            'message': 'You don\'t have permission to update this consultation.'
        })
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        # Validate status
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'message': 'Invalid status provided.'
            })
        
        old_status = consultation.status
        consultation.status = new_status
        
        # We could add custom fields here if needed, for now just update status
        consultation.save()
        
        # Log the action
        log_audit_action(
            request.user, 
            'update', 
            consultation, 
            f"Updated consultation status from {old_status} to {new_status}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Consultation status updated to {new_status}.',
            'old_status': old_status,
            'new_status': new_status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        })


@login_required
def consultation_detail(request, consultation_id):
    """View to display consultation details"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check permissions
    if not (request.user == consultation.doctor or request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to view this consultation.")
        return redirect('consultations:consultation_list')
    
    # Get related objects
    notes = ConsultationNote.objects.filter(consultation=consultation)
    referrals = Referral.objects.filter(consultation=consultation)
    soap_notes = SOAPNote.objects.filter(consultation=consultation)
    clinical_notes = ClinicalNote.objects.filter(patient=consultation.patient).order_by('-date')[:10]

    # Get recent orders (limit to 5 for performance)
    orders = ConsultationOrder.objects.filter(consultation=consultation).select_related('content_type', 'created_by')[:5]

    # Get analytics
    analytics = {
        'note_count': notes.count(),
        'referral_count': referrals.count(),
        'soap_count': soap_notes.count(),
        'clinical_note_count': clinical_notes.count(),
    }

    # Get user notifications
    user_notifications = []  # This would be implemented based on your notification system

    context = {
        'consultation': consultation,
        'notes': notes,
        'referrals': referrals,
        'soap_notes': soap_notes,
        'clinical_notes': clinical_notes,
        'orders': orders,
        'analytics': analytics,
        'user_notifications': user_notifications,
        'lab_order_form': QuickLabOrderForm(consultation=consultation),
        'radiology_order_form': QuickRadiologyOrderForm(consultation=consultation),
        'prescription_form': QuickPrescriptionForm(consultation=consultation, user=request.user),
    }
    
    return render(request, 'consultations/consultation_detail.html', context)


@login_required
def doctor_consultation(request, consultation_id):
    """Doctor's view of a consultation"""
    return consultation_detail(request, consultation_id)


@login_required
def create_consultation_order(request, consultation_id):
    """View for creating orders from consultations"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check if user has permission to create orders for this consultation
    if not (request.user == consultation.doctor or request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to create orders for this consultation.")
        return redirect('consultations:consultation_detail', pk=consultation_id)
    
    if request.method == 'POST':
        order_type = request.POST.get('order_type')
        
        if order_type == 'lab_test':
            form = QuickLabOrderForm(request.POST, consultation=consultation)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        test_request = form.save()
                        messages.success(request, "Laboratory test order created successfully.")
                        return redirect('consultations:consultation_detail', pk=consultation_id)
                except Exception as e:
                    messages.error(request, f"Error creating laboratory test order: {str(e)}")
            else:
                messages.error(request, "Please correct the errors below.")
                
        elif order_type == 'radiology':
            form = QuickRadiologyOrderForm(request.POST, consultation=consultation)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        radiology_order = form.save()
                        messages.success(request, "Radiology order created successfully.")
                        return redirect('consultations:consultation_detail', pk=consultation_id)
                except Exception as e:
                    messages.error(request, f"Error creating radiology order: {str(e)}")
            else:
                messages.error(request, "Please correct the errors below.")
                
        elif order_type == 'prescription':
            form = QuickPrescriptionForm(request.POST, consultation=consultation, user=request.user)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        prescription = form.save()
                        messages.success(request, "Prescription created successfully.")
                        return redirect('consultations:consultation_detail', pk=consultation_id)
                except Exception as e:
                    messages.error(request, f"Error creating prescription: {str(e)}")
            else:
                messages.error(request, "Please correct the errors below.")
    
    # For GET requests, show the consultation detail page with order forms
    context = {
        'consultation': consultation,
        'lab_order_form': QuickLabOrderForm(consultation=consultation),
        'radiology_order_form': QuickRadiologyOrderForm(consultation=consultation),
        'prescription_form': QuickPrescriptionForm(consultation=consultation, user=request.user),
    }
    
    return render(request, 'consultations/consultation_detail.html', context)


@require_http_methods(["POST"])
@login_required
def create_lab_order_ajax(request, consultation_id):
    """AJAX view for creating lab orders"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check if user has permission
    if not (request.user == consultation.doctor or request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    form = QuickLabOrderForm(request.POST, consultation=consultation)
    if form.is_valid():
        try:
            with transaction.atomic():
                test_request = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Laboratory test order created successfully.',
                    'order_id': test_request.id
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        errors = form.errors.as_json()
        return JsonResponse({'success': False, 'errors': errors})


@require_http_methods(["POST"])
@login_required
def create_radiology_order_ajax(request, consultation_id):
    """AJAX view for creating radiology orders"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check if user has permission
    if not (request.user == consultation.doctor or request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    form = QuickRadiologyOrderForm(request.POST, consultation=consultation)
    if form.is_valid():
        try:
            with transaction.atomic():
                radiology_order = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Radiology order created successfully.',
                    'order_id': radiology_order.id
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        errors = form.errors.as_json()
        return JsonResponse({'success': False, 'errors': errors})


@require_http_methods(["POST"])
@login_required
def create_prescription_ajax(request, consultation_id):
    """AJAX view for creating prescriptions"""
    consultation = get_object_or_404(Consultation, id=consultation_id)

    # Check if user has permission
    if not (request.user == consultation.doctor or request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    form = QuickPrescriptionForm(request.POST, consultation=consultation, user=request.user)
    if form.is_valid():
        try:
            with transaction.atomic():
                prescription = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Prescription created successfully.',
                    'order_id': prescription.id
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        errors = form.errors.as_json()
        return JsonResponse({'success': False, 'errors': errors})


@login_required
def consultation_orders(request, consultation_id):
    """View to display all orders for a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check if user has permission to view this consultation
    if not (request.user == consultation.doctor or 
            request.user == consultation.patient or 
            request.user.is_staff or 
            request.user.is_superuser):
        messages.error(request, "You don't have permission to view this consultation.")
        return redirect('consultations:consultation_list')
    
    orders = ConsultationOrder.objects.filter(consultation=consultation).select_related('content_type', 'created_by')
    
    context = {
        'consultation': consultation,
        'orders': orders,
    }
    
    return render(request, 'consultations/consultation_orders.html', context)


# The following views would need to be implemented based on your existing codebase
# For now, I'll provide stub implementations

@login_required
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
        Q(assigned_doctor=doctor) |     # Assigned referrals
        (Q(referral_type='department') & Q(referred_to_department=doctor.profile.department) if hasattr(doctor, 'profile') and doctor.profile and doctor.profile.department else Q(pk=None)) |
        (Q(referral_type='specialty') & Q(referred_to_department=doctor.profile.department) & Q(referred_to_specialty__icontains=doctor.profile.specialization) if hasattr(doctor, 'profile') and doctor.profile and doctor.profile.department and doctor.profile.specialization else Q(pk=None)),
        status='pending'
    ).distinct().order_by('-referral_date')

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
    
    # Get waiting list statistics
    waiting_patients = WaitingList.objects.filter(
        doctor=request.user,
        status='waiting'
    )
    in_progress_patients = WaitingList.objects.filter(
        doctor=request.user,
        status='in_progress'
    )
    
    # Pre-calculate waiting status for each patient
    patient_waiting_status = {}
    for patient in page_obj:
        has_waiting_entry = WaitingList.objects.filter(
            patient=patient,
            doctor=request.user,
            status='waiting'
        ).exists()
        patient_waiting_status[patient.id] = has_waiting_entry
    
    # Get last consultation status for each patient
    patient_consultation_status = {}
    for patient in page_obj:
        last_consultation = Consultation.objects.filter(
            patient=patient,
            doctor=request.user
        ).order_by('-consultation_date').first()
        if last_consultation:
            patient_consultation_status[patient.id] = last_consultation.status
        else:
            patient_consultation_status[patient.id] = None
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'page_title': 'My Patients',
        'active_nav': 'patients',
        'waiting_patients': waiting_patients,
        'in_progress_count': in_progress_patients.count(),
        'patient_waiting_status': patient_waiting_status,
        'patient_consultation_status': patient_consultation_status,
    }

    return render(request, 'consultations/patient_list_clean.html', context)

@login_required
def patient_detail(request, patient_id):
    """View for doctors to see patient details and vitals"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Get patient's vitals using safe utility function
    vitals = get_safe_vitals_for_patient(patient)

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
        'page_title': 'Edit Consultation',
        'active_nav': 'consultations',
    }

    return render(request, 'consultations/consultation_form.html', context)

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

    # Get the latest vitals using safe utility function
    latest_vitals = get_latest_safe_vitals_for_patient(patient)

    if request.method == 'POST':
        form = ConsultationForm(request.POST, initial={'patient': patient, 'doctor': request.user})
        vitals_form = VitalsSelectionForm(patient, request.POST)

        if form.is_valid() and vitals_form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            # Only set doctor if not already set by the form
            if not consultation.doctor:
                consultation.doctor = request.user

            # Set the appointment if it exists
            if appointment:
                consultation.appointment = appointment

            # Set the latest vitals if they exist
            selected_vitals = vitals_form.cleaned_data.get('vitals')
            if selected_vitals:
                consultation.vitals = selected_vitals
            elif latest_vitals:
                consultation.vitals = latest_vitals

            consultation.save()

            messages.success(request, f"Consultation for {patient.get_full_name()} created successfully.")
            return redirect('patients:detail', patient_id=patient.id)
        else:
            messages.error(request, "Please correct the form errors.")
    else:
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

@login_required
def referral_list(request):
    """View for listing all referrals for a doctor"""
    doctor = request.user

    # Get referrals made by this doctor
    referrals_made = Referral.objects.filter(referring_doctor=doctor).order_by('-referral_date')

    # Get referrals received by this doctor (includes assignments)
    referrals_received = Referral.objects.filter(
        Q(assigned_doctor=doctor) |     # Assigned referrals
        (Q(referral_type='department') & Q(referred_to_department=doctor.profile.department) if hasattr(doctor, 'profile') and doctor.profile and doctor.profile.department else Q(pk=None)) |  # Department referrals
        (Q(referral_type='specialty') & Q(referred_to_department=doctor.profile.department) & Q(referred_to_specialty__icontains=doctor.profile.specialization) if hasattr(doctor, 'profile') and doctor.profile and doctor.profile.department and doctor.profile.specialization else Q(pk=None)) |  # Specialty referrals
        (Q(referral_type='unit') & Q(referred_to_department=doctor.profile.department) if hasattr(doctor, 'profile') and doctor.profile and doctor.profile.department else Q(pk=None))  # Unit referrals
    ).distinct().order_by('-referral_date') if hasattr(doctor, 'profile') and doctor.profile else Referral.objects.filter(
        Q(assigned_doctor=doctor)
    ).distinct().order_by('-referral_date')

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
def update_referral_status(request, referral_id):
    """View for updating referral status"""
    referral = get_object_or_404(Referral, id=referral_id)

    # Check if the logged-in user can update this referral
    can_update = False
    
    if referral.referral_type in ['department', 'specialty', 'unit']:
        # Department/specialty/unit referral - check if user can accept
        can_update = referral.can_be_accepted_by(request.user)
    
    # Admin and superuser can always update
    if request.user.is_superuser:
        can_update = True

    if not can_update:
        messages.error(request, "You don't have permission to update this referral.")
        return redirect('consultations:referral_list')

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Referral.STATUS_CHOICES):
            old_status = referral.status
            referral.status = status
            
            # If accepting a department/specialty/unit referral, assign the doctor
            if status == 'accepted' and referral.referral_type in ['department', 'specialty', 'unit']:
                referral.assigned_doctor = request.user
            
            referral.save()
            messages.success(request, "Referral status updated successfully.")
        else:
            messages.error(request, "Invalid status.")

    return redirect('consultations:referral_list')

@login_required
def referral_tracking(request):
    """Comprehensive referral tracking dashboard"""
    user_roles = list(request.user.roles.values_list('name', flat=True))

    # Base queryset
    referrals = Referral.objects.select_related(
        'patient', 'referring_doctor', 'referred_to_department', 'assigned_doctor', 'consultation'
    ).order_by('-referral_date')

    # Filter based on user role and permissions
    if 'admin' not in user_roles and not request.user.is_superuser:
        # Non-admin users see only their referrals
        referrals = referrals.filter(
            Q(referring_doctor=request.user) | 
            Q(assigned_doctor=request.user) |
            (Q(referral_type='department') & Q(referred_to_department=request.user.profile.department) if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.department else Q(pk=None)) |
            (Q(referral_type='specialty') & Q(referred_to_department=request.user.profile.department) & Q(referred_to_specialty__icontains=request.user.profile.specialization) if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.department and request.user.profile.specialization else Q(pk=None)) |
            (Q(referral_type='unit') & Q(referred_to_department=request.user.profile.department) if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.department else Q(pk=None))
        )

    # Apply filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        referrals = referrals.filter(status=status_filter)

    patient_search = request.GET.get('patient', '')
    if patient_search:
        referrals = referrals.filter(
            Q(patient__first_name__icontains=patient_search) |
            Q(patient__last_name__icontains=patient_search) |
            Q(patient__patient_id__icontains=patient_search)
        )

    doctor_filter = request.GET.get('doctor', '')
    if doctor_filter:
        referrals = referrals.filter(
            Q(referring_doctor__id=doctor_filter) |
            Q(assigned_doctor__id=doctor_filter)
        )

    date_from = request.GET.get('date_from', '')
    if date_from:
        referrals = referrals.filter(referral_date__date__gte=date_from)

    date_to = request.GET.get('date_to', '')
    if date_to:
        referrals = referrals.filter(referral_date__date__lte=date_to)

    # Statistics
    total_referrals = referrals.count()
    pending_referrals = referrals.filter(status='pending').count()
    completed_referrals = referrals.filter(status='completed').count()

    # Pagination
    paginator = Paginator(referrals, 20)
    page_number = request.GET.get('page')
    referrals = paginator.get_page(page_number)

    # Get doctors for filter dropdown
    doctors = CustomUser.objects.filter(
        is_active=True,
        profile__specialization__isnull=False
    ).order_by('first_name', 'last_name')

    context = {
        'referrals': referrals,
        'doctors': doctors,
        'status_filter': status_filter,
        'patient_search': patient_search,
        'doctor_filter': doctor_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_referrals': total_referrals,
        'pending_referrals': pending_referrals,
        'completed_referrals': completed_referrals,
        'title': 'Referral Tracking Dashboard'
    }

    return render(request, 'consultations/referral_tracking.html', context)

@login_required
def referral_detail(request, referral_id):
    """Detailed view of a referral with comprehensive tracking"""
    referral = get_object_or_404(Referral, id=referral_id)

    # Check permissions - referring doctor, assigned doctor, or admin can view
    can_view = False
    
    if (referral.referring_doctor == request.user or 
        request.user.is_superuser):
        can_view = True
    elif referral.assigned_doctor == request.user:
        can_view = True
    elif referral.referral_type in ['department', 'specialty', 'unit'] and referral.can_be_accepted_by(request.user):
        can_view = True
        
    if not can_view:
        messages.error(request, "You don't have permission to view this referral.")
        return redirect('consultations:referral_list')

    # Get related consultations from assigned doctor
    follow_up_consultations = Consultation.objects.filter(
        patient=referral.patient,
        doctor=referral.assigned_doctor,
        consultation_date__gte=referral.referral_date
    ).order_by('-consultation_date') if referral.assigned_doctor else Consultation.objects.none()

    # Get referral history for this patient
    patient_referrals = Referral.objects.filter(
        patient=referral.patient
    ).exclude(id=referral.id).order_by('-referral_date')[:5]

    context = {
        'referral': referral,
        'follow_up_consultations': follow_up_consultations,
        'patient_referrals': patient_referrals,
        'title': f'Referral Details - {referral.patient.get_full_name()}'
    }

    return render(request, 'consultations/referral_detail.html', context)

@login_required
def update_referral_status_detailed(request, referral_id):
    """Enhanced referral status update with notes and tracking"""
    referral = get_object_or_404(Referral, id=referral_id)

    # Check permissions
    can_update = False

    if referral.referral_type in ['department', 'specialty', 'unit']:
        # Department/specialty/unit referral
        can_update = (referral.can_be_accepted_by(request.user) or
                     referral.referring_doctor == request.user or
                     referral.assigned_doctor == request.user)

    # Admin and superuser can always update
    if request.user.is_superuser:
        can_update = True

    if not can_update:
        messages.error(request, "You don't have permission to update this referral.")
        return redirect('consultations:referral_tracking')

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('status_notes', '')
        
        if status in dict(Referral.STATUS_CHOICES):
            # **AUTHORIZATION CHECK**: Prevent accepting referrals that require authorization
            if status == 'accepted' and referral.requires_authorization:
                if referral.authorization_status not in ['authorized', 'not_required']:
                    messages.error(
                        request,
                        f"Cannot accept this referral. Authorization status is '{referral.get_authorization_status_display()}'. "
                        f"This NHIA patient referral requires desk office authorization before it can be accepted. "
                        f"Please contact the desk office to obtain authorization."
                    )
                    return redirect('consultations:referral_detail', referral_id=referral.id)

            old_status = referral.status
            referral.status = status

            # Add status update notes
            if notes:
                if referral.notes:
                    referral.notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}] Status changed from {old_status} to {status}: {notes}"
                else:
                    referral.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}] Status changed from {old_status} to {status}: {notes}"

            # If accepting a department/specialty/unit referral, assign the doctor
            if status == 'accepted' and referral.referral_type in ['department', 'specialty', 'unit']:
                referral.assigned_doctor = request.user

            referral.save()

            # Create notification for the other party
            if referral.referral_type in ['department', 'specialty', 'unit'] and referral.can_be_accepted_by(request.user):
                # Notify referring doctor
                from core.models import InternalNotification
                InternalNotification.objects.create(
                    user=referral.referring_doctor,
                    message=f"Referral for {referral.patient.get_full_name()} to {referral.get_referral_destination()} has been {status} by Dr. {request.user.get_full_name()}"
                )

            messages.success(request, f"Referral status updated to {status}.")
        else:
            messages.error(request, "Invalid status.")

    return redirect('consultations:referral_detail', referral_id=referral.id)


@login_required
def bulk_update_referral_status(request):
    """Bulk update status for multiple referrals"""
    if request.method == 'POST':
        referral_ids = request.POST.getlist('referral_ids')
        bulk_status = request.POST.get('bulk_status')
        
        if not referral_ids or not bulk_status:
            messages.error(request, 'Please select referrals and choose an action.')
            return redirect('consultations:referral_tracking')
        
        updated_count = 0
        for referral_id in referral_ids:
            try:
                referral = Referral.objects.get(id=referral_id)
                
                # Only update if authorization allows it
                if (referral.authorization_status == 'authorized' or 
                    referral.authorization_status == 'not_required' or 
                    bulk_status == 'cancelled'):
                    
                    referral.status = bulk_status
                    if bulk_status == 'accepted':
                        referral.accepted_at = timezone.now()
                    elif bulk_status == 'completed':
                        referral.completed_at = timezone.now()
                    elif bulk_status == 'cancelled':
                        referral.cancelled_at = timezone.now()
                    
                    referral.save()
                    updated_count += 1
                
            except Referral.DoesNotExist:
                continue
        
        if updated_count > 0:
            status_text = bulk_status.replace('_', ' ').title()
            messages.success(request, f'{updated_count} referrals have been {status_text.lower()}.')
        else:
            messages.warning(request, 'No referrals could be updated. Check authorization status.')
    
    return redirect('consultations:referral_tracking')

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('status_notes', '')
        
        if status in dict(Referral.STATUS_CHOICES):
            # **AUTHORIZATION CHECK**: Prevent accepting referrals that require authorization
            if status == 'accepted' and referral.requires_authorization:
                if referral.authorization_status not in ['authorized', 'not_required']:
                    messages.error(
                        request,
                        f"Cannot accept this referral. Authorization status is '{referral.get_authorization_status_display()}'. "
                        f"This NHIA patient referral requires desk office authorization before it can be accepted. "
                        f"Please contact the desk office to obtain authorization."
                    )
                    return redirect('consultations:referral_detail', referral_id=referral.id)

            old_status = referral.status
            referral.status = status

            # Add status update notes
            if notes:
                if referral.notes:
                    referral.notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}] Status changed from {old_status} to {status}: {notes}"
                else:
                    referral.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}] Status changed from {old_status} to {status}: {notes}"

            # If accepting a department/specialty/unit referral, assign the doctor
            if status == 'accepted' and referral.referral_type in ['department', 'specialty', 'unit']:
                referral.assigned_doctor = request.user

            referral.save()

            # Create notification for the other party
            if referral.referral_type in ['department', 'specialty', 'unit'] and referral.can_be_accepted_by(request.user):
                # Notify referring doctor
                from core.models import InternalNotification
                InternalNotification.objects.create(
                    user=referral.referring_doctor,
                    message=f"Referral for {referral.patient.get_full_name()} to {referral.get_referral_destination()} has been {status} by Dr. {request.user.get_full_name()}"
                )
            else:
                # Notify assigned doctor if different from current user
                target_doctor = referral.assigned_doctor
                if target_doctor and target_doctor != request.user:
                    from core.models import InternalNotification
                    InternalNotification.objects.create(
                        user=target_doctor,
                        message=f"Referral for {referral.patient.get_full_name()} status updated to {status} by Dr. {request.user.get_full_name()}"
                    )

            messages.success(request, f"Referral status updated to {status}.")
        else:
            messages.error(request, "Invalid status.")

    return redirect('consultations:referral_detail', referral_id=referral.id)

@login_required
def reject_referral(request, referral_id):
    """
    View to reject a referral from the destination department.
    Only authorized referrals can be rejected.
    """
    referral = get_object_or_404(Referral, id=referral_id)

    # Check permissions - user must be able to accept the referral to reject it
    can_reject = False

    if referral.referral_type in ['department', 'specialty', 'unit']:
        # Department/specialty/unit referral - check if user can accept it
        can_reject = referral.can_be_accepted_by(request.user)

    # Admin and superuser can always reject
    if request.user.is_superuser:
        can_reject = True

    if not can_reject:
        messages.error(request, "You don't have permission to reject this referral.")
        return redirect('consultations:referral_detail', referral_id=referral.id)

    # **AUTHORIZATION CHECK**: Can only reject if authorized or not requiring authorization
    if referral.requires_authorization:
        if referral.authorization_status not in ['authorized', 'not_required']:
            messages.error(
                request,
                f"Cannot reject this referral. Authorization status is '{referral.get_authorization_status_display()}'. "
                f"This NHIA patient referral requires desk office authorization before it can be accepted or rejected. "
                f"Please contact the desk office if you need to reject this referral."
            )
            return redirect('consultations:referral_detail', referral_id=referral.id)

    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        if not rejection_reason:
            messages.error(request, "Please provide a reason for rejecting this referral.")
            return redirect('consultations:referral_detail', referral_id=referral.id)

        # Update referral status to cancelled
        old_status = referral.status
        referral.status = 'cancelled'

        # Add rejection notes
        rejection_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}] Referral REJECTED by {referral.referred_to_department.name if referral.referred_to_department else 'destination'} department.\nReason: {rejection_reason}"

        if referral.notes:
            referral.notes += f"\n\n{rejection_note}"
        else:
            referral.notes = rejection_note

        referral.save()

        # Notify referring doctor
        from core.models import InternalNotification
        InternalNotification.objects.create(
            user=referral.referring_doctor,
            message=f"Your referral for {referral.patient.get_full_name()} to {referral.get_referral_destination()} has been REJECTED by Dr. {request.user.get_full_name()}. Reason: {rejection_reason}"
        )

        messages.success(request, f"Referral rejected successfully. The referring doctor has been notified.")
        return redirect('consultations:department_referral_dashboard')

    # GET request - show confirmation page or redirect to detail
    return redirect('consultations:referral_detail', referral_id=referral.id)


@login_required
def complete_referral(request, referral_id):
    """
    View to mark a referral as completed.
    Only the assigned doctor or department staff can complete a referral.
    """
    referral = get_object_or_404(Referral, id=referral_id)

    # Check permissions
    can_complete = False

    if referral.referral_type in ['department', 'specialty', 'unit']:
        # Department/specialty/unit referral - check if user is assigned or can accept
        can_complete = (referral.assigned_doctor == request.user or
                       referral.can_be_accepted_by(request.user))

    # Admin and superuser can always complete
    if request.user.is_superuser:
        can_complete = True

    if not can_complete:
        messages.error(request, "You don't have permission to complete this referral.")
        return redirect('consultations:referral_tracking')

    # Check if referral is in accepted status
    if referral.status != 'accepted':
        messages.error(request, f"Cannot complete referral. Current status is '{referral.get_status_display()}'. Only accepted referrals can be completed.")
        return redirect('consultations:referral_detail', referral_id=referral.id)

    if request.method == 'POST':
        completion_notes = request.POST.get('completion_notes', '').strip()

        # Update referral status to completed
        old_status = referral.status
        referral.status = 'completed'

        # Add completion notes
        completion_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}] Referral COMPLETED.\n"
        if completion_notes:
            completion_note += f"Completion Notes: {completion_notes}"

        if referral.notes:
            referral.notes += f"\n\n{completion_note}"
        else:
            referral.notes = completion_note

        referral.save()

        # Create audit log
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action="REFERRAL_COMPLETED",
                details=f"Completed referral for {referral.patient.get_full_name()} from Dr. {referral.referring_doctor.get_full_name()} to {referral.get_referral_destination()}"
            )
        except ImportError:
            pass

        # Notify referring doctor
        from core.models import InternalNotification
        InternalNotification.objects.create(
            user=referral.referring_doctor,
            message=f"Your referral for {referral.patient.get_full_name()} to {referral.get_referral_destination()} has been COMPLETED by Dr. {request.user.get_full_name()}."
        )

        messages.success(request, f"Referral completed successfully. The referring doctor has been notified.")
        return redirect('consultations:department_referral_dashboard')

    # GET request - show confirmation page or redirect to detail
    return redirect('consultations:referral_detail', referral_id=referral.id)


@login_required
def create_referral(request, patient_id=None):
    """View for creating a new referral directly from the patient detail page"""
    patient = None
    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, f"Patient with ID {patient_id} does not exist.")
            return redirect('patients:list')

    # Get referral history for this patient
    referral_history = []
    recent_consultations = []
    current_admissions = []
    
    if patient:
        # Get referral history (both sent and received)
        referral_history = Referral.objects.filter(
            patient=patient
        ).select_related('referring_doctor', 'referred_to_department', 'assigned_doctor').order_by('-referral_date')[:10]
        
        # Get recent consultations
        recent_consultations = Consultation.objects.filter(
            patient=patient
        ).select_related('doctor').order_by('-consultation_date')[:5]
        
        # Check for current admissions
        try:
            from inpatient.models import Admission
            current_admissions = Admission.objects.filter(
                patient=patient,
                status__in=['active', 'admitted']
            ).select_related('attending_doctor', 'bed')[:5]  # Fixed field names
        except (ImportError, Exception):
            current_admissions = []

    if request.method == 'POST':
        # Create a mutable copy of POST data
        post_data = request.POST.copy()

        # If patient_id is provided in URL, add it to POST data
        if patient_id and 'patient' not in post_data:
            post_data['patient'] = patient_id

        form = ReferralForm(post_data)

        if form.is_valid():
            referral = form.save(commit=False)

            # Ensure patient is set from URL if not in form
            if patient and not referral.patient:
                referral.patient = patient

            # Set referring doctor to current user
            referral.referring_doctor = request.user

            # Try to link to an existing consultation from today
            consultation = Consultation.objects.filter(
                patient=referral.patient,
                doctor=referral.referring_doctor,
                consultation_date__date=timezone.now().date()
            ).first()

            if consultation:
                referral.consultation = consultation
            # If no consultation exists, that's okay - consultation is now optional

            # Determine if authorization is required (for NHIA patients)
            if referral.patient.patient_type == 'nhia':
                # Check if referring from NHIA to non-NHIA unit
                referring_dept = getattr(referral.referring_doctor.profile, 'department', None) if hasattr(referral.referring_doctor, 'profile') else None
                
                # For department/specialty/unit referrals, check the department
                if referral.referral_type in ['department', 'specialty', 'unit'] and referral.referred_to_department:
                    referred_dept = referral.referred_to_department
                if referral.referral_type in ['department', 'specialty', 'unit'] and referral.referred_to_department:
                    referred_dept = referral.referred_to_department
                else:
                    referred_dept = None
                
                # This logic can be enhanced based on your NHIA authorization rules
                if referring_dept and referred_dept:
                    referral.requires_authorization = True
                    referral.authorization_status = 'required'

            referral.save()

            messages.success(request, f"Referral for {referral.patient.get_full_name()} created successfully.")
            return redirect('patients:detail', patient_id=referral.patient.id)
        else:
            # Show specific form errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            messages.error(request, "Form validation failed: " + "; ".join(error_messages))
            if patient:
                return redirect('patients:detail', patient_id=patient.id)
            else:
                return redirect('dashboard:dashboard')

    else:
        initial_data = {}
        if patient:
            initial_data['patient'] = patient
        form = ReferralForm(initial=initial_data)

    context = {
        'form': form,
        'patient': patient,
        'title': 'Create New Referral',
        'referral_history': referral_history,
        'recent_consultations': recent_consultations,
        'current_admissions': current_admissions,
    }
    return render(request, 'consultations/referral_form.html', context)

@login_required
def consulting_room_list(request):
    """View for listing all consulting rooms"""
    consulting_rooms = ConsultingRoom.objects.all().order_by('room_number')
    
    # Get all departments for the filter dropdown
    departments = Department.objects.all().order_by('name')

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
        'departments': departments,
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

@login_required
def waiting_list(request):
    """View for displaying the patient waiting list"""
    waiting_entries = WaitingList.objects.filter(
        status__in=['waiting', 'in_progress']
    ).order_by('priority', 'check_in_time')

    # Filter by doctor
    doctor = request.GET.get('doctor', '')
    if doctor:
        if doctor == 'unassigned':
            waiting_entries = waiting_entries.filter(doctor__isnull=True)
        else:
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

            if waiting_entry.doctor:
                messages.success(request, f"{waiting_entry.patient.get_full_name()} added to waiting list for Dr. {waiting_entry.doctor.get_full_name()} in Room {waiting_entry.consulting_room.room_number}.")
            else:
                messages.success(request, f"{waiting_entry.patient.get_full_name()} added to waiting list in Room {waiting_entry.consulting_room.room_number} (No specific doctor assigned).")
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
                if waiting_entry.doctor is not None:
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
                else:
                    messages.error(request, "Cannot start consultation: No doctor assigned to this waiting entry.")
                    return redirect('consultations:waiting_list')

            messages.success(request, f"Status updated to {waiting_entry.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")

    # Redirect based on user role
    if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role == 'doctor':
        return redirect('consultations:doctor_waiting_list')
    else:
        return redirect('consultations:waiting_list')

@login_required
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
def create_prescription(request, consultation_id):
    """View for creating a prescription from a consultation"""
    # Allow access to consultations without doctors or where current user is the doctor
    consultation = get_object_or_404(Consultation, id=consultation_id)

    # Check if user has permission to create prescription for this consultation
    if consultation.doctor and consultation.doctor != request.user:
        messages.error(request, "You can only create prescriptions for your own consultations.")
        return redirect('consultations:consultation_detail', consultation_id=consultation.id)

    # Create a new prescription
    prescription = Prescription.objects.create(
        patient=consultation.patient,
        doctor=consultation.doctor or request.user,  # Use consultation doctor or current user
        prescription_date=timezone.now().date(),
        diagnosis=consultation.diagnosis,
        status='pending',
        notes=f"Prescription created from consultation on {consultation.consultation_date.strftime('%Y-%m-%d')}"
    )

    messages.success(request, "Prescription created. Please add medications.")
    return redirect('pharmacy:edit_prescription', prescription_id=prescription.id)

@login_required
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
def department_referral_dashboard(request):
    """
    Dashboard for department staff to view referrals sent to their department.
    Shows authorization status and prevents actions on unauthorized referrals.
    """
    # Get user's department
    user_department = None
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.department:
        user_department = request.user.profile.department

    # Superusers can view all referrals without department assignment
    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department to view referrals.")
        return redirect('dashboard:dashboard')

    # Get referrals - all for superusers, department-specific for others
    if user_department:
        referrals = Referral.objects.filter(
            referred_to_department=user_department
        ).select_related(
            'patient', 'referring_doctor', 'referred_to_department',
            'assigned_doctor', 'consultation', 'authorization_code'
        ).order_by('-referral_date')
    else:
        # Superusers see all referrals
        referrals = Referral.objects.all().select_related(
            'patient', 'referring_doctor', 'referred_to_department',
            'assigned_doctor', 'consultation', 'authorization_code'
        ).order_by('-referral_date')

    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        referrals = referrals.filter(status=status_filter)

    # Apply authorization status filter
    auth_status_filter = request.GET.get('auth_status', '')
    if auth_status_filter:
        referrals = referrals.filter(authorization_status=auth_status_filter)

    # Apply search filter
    search_query = request.GET.get('search', '')
    if search_query:
        referrals = referrals.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    # Apply urgency filter
    urgency_filter = request.GET.get('urgency', '')
    if urgency_filter:
        referrals = referrals.filter(urgency_level=urgency_filter)

    # Categorize referrals using the utility function
    from core.department_dashboard_utils import categorize_referrals
    categorized = categorize_referrals(user_department)

    # Get counts for each category
    ready_to_accept_count = len(categorized['ready_to_accept'])
    awaiting_authorization_count = len(categorized['awaiting_authorization'])
    rejected_authorization_count = len(categorized['rejected_authorization'])
    under_care_count = len(categorized['under_care'])

    # Apply filters to categorized referrals
    if status_filter:
        if status_filter == 'pending':
            categorized['ready_to_accept'] = [r for r in categorized['ready_to_accept'] if r.status == 'pending']
            categorized['awaiting_authorization'] = [r for r in categorized['awaiting_authorization'] if r.status == 'pending']
            categorized['rejected_authorization'] = [r for r in categorized['rejected_authorization'] if r.status == 'pending']
        elif status_filter == 'accepted':
            categorized['under_care'] = [r for r in categorized['under_care'] if r.status == 'accepted']
        elif status_filter == 'completed':
            categorized['under_care'] = [r for r in categorized['under_care'] if r.status == 'completed']
        elif status_filter == 'cancelled':
            categorized['ready_to_accept'] = [r for r in categorized['ready_to_accept'] if r.status == 'cancelled']
            categorized['awaiting_authorization'] = [r for r in categorized['awaiting_authorization'] if r.status == 'cancelled']

    if auth_status_filter:
        if auth_status_filter == 'authorized':
            categorized['ready_to_accept'] = [r for r in categorized['ready_to_accept'] if r.authorization_status == 'authorized']
        elif auth_status_filter == 'not_required':
            categorized['ready_to_accept'] = [r for r in categorized['ready_to_accept'] if r.authorization_status == 'not_required']
        elif auth_status_filter == 'pending':
            categorized['awaiting_authorization'] = [r for r in categorized['awaiting_authorization'] if r.authorization_status == 'pending']
        elif auth_status_filter == 'required':
            categorized['awaiting_authorization'] = [r for r in categorized['awaiting_authorization'] if r.authorization_status == 'required']
        elif auth_status_filter == 'rejected':
            categorized['rejected_authorization'] = [r for r in categorized['rejected_authorization'] if r.authorization_status == 'rejected']

    context = {
        'user_department': user_department,
        'department_name': user_department.name if user_department else 'All Departments',
        
        # Categorized referrals
        'ready_to_accept_referrals': categorized['ready_to_accept'],
        'awaiting_authorization_referrals': categorized['awaiting_authorization'],
        'rejected_authorization_referrals': categorized['rejected_authorization'],
        'under_care_referrals': categorized['under_care'],
        
        # Counts
        'ready_to_accept_count': ready_to_accept_count,
        'awaiting_authorization_count': awaiting_authorization_count,
        'rejected_authorization_count': rejected_authorization_count,
        'under_care_count': under_care_count,
        
        # Filter states
        'status_filter': status_filter,
        'auth_status_filter': auth_status_filter,
        'search_query': search_query,
        'urgency_filter': urgency_filter,
        
        'page_title': f'{user_department.name} - Referrals Dashboard' if user_department else 'All Departments - Referrals Dashboard',
    }

    return render(request, 'consultations/department_referral_dashboard.html', context)