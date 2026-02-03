from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUser
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.core.cache import cache
from datetime import datetime, timedelta, time
from calendar import monthrange
from .models import Appointment, AppointmentFollowUp, DoctorSchedule, DoctorLeave
from .forms import AppointmentForm, AppointmentFollowUpForm, DoctorScheduleForm, DoctorLeaveForm, AppointmentSearchForm
from patients.models import Patient
from core.utils import send_notification_email, send_sms_notification

@login_required
def appointment_list(request):
    """View for listing all appointments with search and filter functionality"""
    search_form = AppointmentSearchForm(request.GET)
    appointments = Appointment.objects.select_related('patient', 'doctor').all().order_by('-appointment_date', '-appointment_time')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        doctor = search_form.cleaned_data.get('doctor')
        status = search_form.cleaned_data.get('status')
        priority = search_form.cleaned_data.get('priority')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            appointments = appointments.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query)
            )

        if doctor:
            appointments = appointments.filter(doctor=doctor)

        if status:
            appointments = appointments.filter(status=status)

        if priority:
            appointments = appointments.filter(priority=priority)

        if date_from:
            appointments = appointments.filter(appointment_date__gte=date_from)

        if date_to:
            appointments = appointments.filter(appointment_date__lte=date_to)

    # Build cache key for computed data only
    cache_key = f'appointment_list_data_{hash(request.GET.urlencode())}' if request.GET else 'appointment_list_data_all'
    cached_data = cache.get(cache_key)

    if cached_data:
        # Reconstruct queryset from cached IDs
        appointment_ids = cached_data['appointment_ids']
        appointments = Appointment.objects.filter(id__in=appointment_ids).select_related('patient', 'doctor').order_by('-appointment_date', '-appointment_time')
    else:
        # Cache the data for future use
        cache_data = {
            'appointment_ids': list(appointments.values_list('id', flat=True)),
        }
        cache.set(cache_key, cache_data, 60)

    # Pagination
    paginator = Paginator(appointments, 10)  # Show 10 appointments per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts for different statuses using a single aggregate query
    today = timezone.now().date()
    status_counts = Appointment.objects.aggregate(
        upcoming_count=Count('id', filter=Q(appointment_date__gte=today, status__in=['scheduled', 'confirmed'])),
        completed_count=Count('id', filter=Q(status='completed')),
        cancelled_count=Count('id', filter=Q(status='cancelled')),
        no_show_count=Count('id', filter=Q(status='no_show'))
    )
    upcoming_count = status_counts['upcoming_count']
    completed_count = status_counts['completed_count']
    cancelled_count = status_counts['cancelled_count']
    no_show_count = status_counts['no_show_count']

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_appointments': appointments.count(),
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'no_show_count': no_show_count,
    }

    return render(request, 'appointments/appointment_list.html', context)

@login_required
def create_appointment(request):
    """View for creating a new appointment"""
    # Pre-fill patient_id and doctor_id if provided in GET parameters
    patient_id = request.GET.get('patient_id')
    doctor_id = request.GET.get('doctor_id')
    initial_data = {}

    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
            initial_data['patient'] = patient
        except Patient.DoesNotExist:
            pass

    if doctor_id:
        try:
            doctor = CustomUser.objects.get(id=doctor_id)
            initial_data['doctor'] = doctor
        except CustomUser.DoesNotExist:
            pass

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        # Ensure all patients are available for selection
        form.fields['patient'].queryset = Patient.objects.all()
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.save()
            # Send appointment reminder notification (stub)
            if appointment.patient.email:
                send_notification_email(
                    subject="Appointment Scheduled",
                    message=f"Dear {appointment.patient.get_full_name()}, your appointment with Dr. {appointment.doctor.get_full_name()} is scheduled for {appointment.appointment_date} at {appointment.appointment_time}.",
                    recipient_list=[appointment.patient.email]
                )
            if appointment.patient.phone_number:
                send_sms_notification(
                    phone_number=appointment.patient.phone_number,
                    message=f"Appointment with Dr. {appointment.doctor.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}."
                )
            messages.success(request, f'Appointment scheduled successfully for {appointment.patient.get_full_name()} with Dr. {appointment.doctor.get_full_name()}')
            return redirect('appointments:detail', appointment_id=appointment.id)
    else:
        form = AppointmentForm(initial=initial_data)
        # Ensure all patients are available for selection
        form.fields['patient'].queryset = Patient.objects.all()

    # Get all doctors for the template
    doctors = CustomUser.objects.filter(
        is_active=True,
        profile__role='doctor',
        profile__specialization__isnull=False
    ).order_by('last_name', 'first_name')

    context = {
        'form': form,
        'title': 'Schedule New Appointment',
        'doctors': doctors,
    }

    return render(request, 'appointments/appointment_form.html', context)

@login_required
def appointment_detail(request, appointment_id):
    """View for displaying appointment details"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    follow_ups = appointment.follow_ups.all().order_by('-follow_up_date')

    # Handle adding new follow-up
    if request.method == 'POST' and 'add_follow_up' in request.POST:
        follow_up_form = AppointmentFollowUpForm(request.POST)
        if follow_up_form.is_valid():
            follow_up = follow_up_form.save(commit=False)
            follow_up.appointment = appointment
            follow_up.created_by = request.user
            follow_up.save()
            messages.success(request, 'Follow-up added successfully.')
            return redirect('appointments:detail', appointment_id=appointment.id)
    else:
        follow_up_form = AppointmentFollowUpForm()

    context = {
        'appointment': appointment,
        'follow_ups': follow_ups,
        'follow_up_form': follow_up_form,
    }

    return render(request, 'appointments/appointment_detail.html', context)

@login_required
def edit_appointment(request, appointment_id):
    """View for editing an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Check if appointment is in the past
    if appointment.appointment_date < timezone.now().date():
        messages.error(request, 'Cannot edit past appointments.')
        return redirect('appointments:detail', appointment_id=appointment.id)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully.')
            return redirect('appointments:detail', appointment_id=appointment.id)
    else:
        form = AppointmentForm(instance=appointment)

    context = {
        'form': form,
        'appointment': appointment,
        'title': 'Edit Appointment'
    }

    return render(request, 'appointments/appointment_form.html', context)

@login_required
def cancel_appointment(request, appointment_id):
    """View for cancelling an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Check if appointment is in the past
    if appointment.appointment_date < timezone.now().date():
        messages.error(request, 'Cannot cancel past appointments.')
        return redirect('appointments:detail', appointment_id=appointment.id)

    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')
        return redirect('appointments:list')

    context = {
        'appointment': appointment
    }

    return render(request, 'appointments/cancel_appointment.html', context)

@login_required
def appointment_calendar(request):
    """View for displaying appointments in a calendar view"""
    # Get the month and year from the request, default to current month
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))

    # Get all doctors
    doctors = CustomUser.objects.filter(is_active=True, profile__role='doctor')
    selected_doctor_id = request.GET.get('doctor')

    # Filter appointments by doctor if selected
    if selected_doctor_id:
        try:
            selected_doctor = CustomUser.objects.get(id=selected_doctor_id)
            appointments = Appointment.objects.filter(
                doctor=selected_doctor,
                appointment_date__year=year,
                appointment_date__month=month
            )
        except User.DoesNotExist:
            appointments = Appointment.objects.filter(
                appointment_date__year=year,
                appointment_date__month=month
            )
            selected_doctor = None
    else:
        appointments = Appointment.objects.filter(
            appointment_date__year=year,
            appointment_date__month=month
        )
        selected_doctor = None

    # Create calendar data
    cal_data = []
    num_days = monthrange(year, month)[1]
    first_day_weekday = datetime(year, month, 1).weekday()  # Monday is 0

    # Add empty cells for days before the 1st of the month
    for i in range(first_day_weekday):
        cal_data.append({'day': '', 'appointments': []})

    # Add days of the month with their appointments
    for day in range(1, num_days + 1):
        day_appointments = [a for a in appointments if a.appointment_date.day == day]
        cal_data.append({
            'day': day,
            'appointments': day_appointments,
            'is_today': timezone.now().date() == datetime(year, month, day).date()
        })

    # Get previous and next month links
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    context = {
        'cal_data': cal_data,
        'month': month,
        'year': year,
        'month_name': datetime(year, month, 1).strftime('%B'),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'doctors': doctors,
        'selected_doctor': selected_doctor,
    }

    return render(request, 'appointments/appointment_calendar.html', context)

@login_required
def doctor_appointments(request, doctor_id):
    """View for displaying appointments for a specific doctor"""
    doctor = get_object_or_404(CustomUser, id=doctor_id)

    # Get date range from request, default to today
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # Get appointments for the selected date
    appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=selected_date
    ).order_by('appointment_time')

    # Get doctor's schedule for the selected date
    weekday = selected_date.weekday()
    schedule = DoctorSchedule.objects.filter(doctor=doctor, weekday=weekday).first()

    # Check if doctor is on leave
    is_on_leave = DoctorLeave.objects.filter(
        doctor=doctor,
        start_date__lte=selected_date,
        end_date__gte=selected_date,
        is_approved=True
    ).exists()

    context = {
        'doctor': doctor,
        'appointments': appointments,
        'selected_date': selected_date,
        'schedule': schedule,
        'is_on_leave': is_on_leave,
        'prev_date': selected_date - timedelta(days=1),
        'next_date': selected_date + timedelta(days=1),
        'today': timezone.now().date(),
    }

    return render(request, 'appointments/doctor_appointments.html', context)

@login_required
def manage_doctor_schedule(request, doctor_id=None):
    """View for managing doctor schedules"""
    edit_schedule_id = request.GET.get('edit_schedule_id')
    edit_schedule = None
    
    if edit_schedule_id:
        edit_schedule = get_object_or_404(DoctorSchedule, id=edit_schedule_id)
        # If we're editing, ensure doctor_id matches the schedule's doctor
        if not doctor_id:
            doctor_id = edit_schedule.doctor.id
            url = reverse('appointments:manage_doctor_schedule_for_doctor', kwargs={'doctor_id': doctor_id})
            return redirect(f'{url}?edit_schedule_id={edit_schedule_id}')
    
    if doctor_id:
        doctor = get_object_or_404(CustomUser, id=doctor_id)
        schedules = DoctorSchedule.objects.filter(doctor=doctor).order_by('weekday')
    else:
        doctor = None
        schedules = None

    if request.method == 'POST':
        # If editing, use the instance
        if edit_schedule:
            form = DoctorScheduleForm(request.POST, instance=edit_schedule)
        else:
            form = DoctorScheduleForm(request.POST)
            
        if form.is_valid():
            # Check for duplicates only if creating new or changing weekday
            if not edit_schedule:
                doctor_obj = form.cleaned_data['doctor']
                weekday = form.cleaned_data['weekday']
                existing_schedule = DoctorSchedule.objects.filter(doctor=doctor_obj, weekday=weekday).first()
                
                if existing_schedule:
                    # Logic to update existing if user didn't click edit but selected same day
                    existing_schedule.start_time = form.cleaned_data['start_time']
                    existing_schedule.end_time = form.cleaned_data['end_time']
                    existing_schedule.is_available = form.cleaned_data['is_available']
                    existing_schedule.save()
                    messages.success(request, f'Schedule updated for {doctor_obj.get_full_name()} on {existing_schedule.get_weekday_display()}')
                    return redirect('appointments:manage_doctor_schedule_for_doctor', doctor_id=doctor_obj.id)

            form.save()
            msg_action = "updated" if edit_schedule else "created"
            messages.success(request, f'Schedule {msg_action} for {form.cleaned_data["doctor"].get_full_name()} on {form.instance.get_weekday_display()}')
            return redirect('appointments:manage_doctor_schedule_for_doctor', doctor_id=form.cleaned_data['doctor'].id)
    else:
        if edit_schedule:
            form = DoctorScheduleForm(instance=edit_schedule)
        else:
            initial_data = {'doctor': doctor} if doctor else {}
            form = DoctorScheduleForm(initial=initial_data)

    # Get all doctors for the dropdown
    doctors = CustomUser.objects.filter(is_active=True, profile__role='doctor').order_by('last_name')

    context = {
        'form': form,
        'doctor': doctor,
        'schedules': schedules,
        'doctors': doctors,
        'edit_schedule': edit_schedule,
        'title': f'Manage Schedule: {doctor.get_full_name()}' if doctor else 'Manage Doctor Schedules'
    }

    return render(request, 'appointments/manage_doctor_schedule.html', context)

@login_required
def delete_doctor_schedule(request, schedule_id):
    """View for deleting a doctor schedule"""
    schedule = get_object_or_404(DoctorSchedule, id=schedule_id)
    doctor_id = schedule.doctor.id

    if request.method == 'POST':
        schedule.delete()
        messages.success(request, f'Schedule for {schedule.get_weekday_display()} has been deleted.')
        return redirect('appointments:manage_doctor_schedule_for_doctor', doctor_id=doctor_id)

    context = {
        'schedule': schedule
    }

    return render(request, 'appointments/delete_doctor_schedule.html', context)

@login_required
def manage_doctor_leaves(request):
    """View for managing doctor leaves"""
    leaves = DoctorLeave.objects.all().order_by('-start_date')

    if request.method == 'POST':
        form = DoctorLeaveForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Leave request submitted successfully.')
            return redirect('appointments:manage_doctor_leaves')
    else:
        form = DoctorLeaveForm()

    context = {
        'form': form,
        'leaves': leaves,
        'title': 'Manage Doctor Leaves'
    }

    return render(request, 'appointments/manage_doctor_leaves.html', context)

@login_required
def approve_doctor_leave(request, leave_id):
    """View for approving a doctor leave request"""
    leave = get_object_or_404(DoctorLeave, id=leave_id)

    if request.method == 'POST':
        leave.is_approved = True
        leave.save()
        messages.success(request, f'Leave for Dr. {leave.doctor.get_full_name()} has been approved.')
        return redirect('appointments:manage_doctor_leaves')

    context = {
        'leave': leave
    }

    return render(request, 'appointments/approve_doctor_leave.html', context)

@login_required
def delete_doctor_leave(request, leave_id):
    """View for deleting a doctor leave request"""
    leave = get_object_or_404(DoctorLeave, id=leave_id)

    if request.method == 'POST':
        leave.delete()
        messages.success(request, 'Leave request has been deleted.')
        return redirect('appointments:manage_doctor_leaves')

    context = {
        'leave': leave
    }

    return render(request, 'appointments/delete_doctor_leave.html', context)

@login_required
def get_available_slots(request):
    """AJAX view for getting available appointment slots for a doctor on a specific date"""
    date_str = request.GET.get('date')
    doctor_id = request.GET.get('doctor_id')

    if not date_str or not doctor_id:
        return JsonResponse({'error': 'Date and doctor are required'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        doctor = CustomUser.objects.get(id=doctor_id)
    except (ValueError, CustomUser.DoesNotExist):
        return JsonResponse({'error': 'Invalid date or doctor'}, status=400)

    # Check if doctor is on leave
    is_on_leave = DoctorLeave.objects.filter(
        doctor=doctor,
        start_date__lte=selected_date,
        end_date__gte=selected_date,
        is_approved=True
    ).exists()

    if is_on_leave:
        return JsonResponse({'available_slots': [], 'message': 'Doctor is on leave on this date'}, status=200)

    # Get doctor's schedule for the selected date
    weekday = selected_date.weekday()
    schedule = DoctorSchedule.objects.filter(doctor=doctor, weekday=weekday).first()

    if not schedule or not schedule.is_available:
        return JsonResponse({'available_slots': [], 'message': 'Doctor is not available on this date'}, status=200)

    # Generate time slots based on schedule (30-minute intervals)
    start_time = schedule.start_time
    end_time = schedule.end_time

    # Get existing appointments for this doctor on this date
    existing_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=selected_date,
        status__in=['scheduled', 'confirmed']
    ).values_list('appointment_time', flat=True)

    # Generate available slots
    available_slots = []
    current_time = start_time

    while current_time < end_time:
        # Check if this slot is already booked
        if current_time not in existing_appointments:
            slot_value = current_time.strftime('%H:%M')
            slot_text = current_time.strftime('%I:%M %p')
            available_slots.append({
                'value': slot_value,
                'text': slot_text
            })

        # Move to next slot (30 minutes later)
        current_time_dt = datetime.combine(datetime.today(), current_time)
        current_time_dt += timedelta(minutes=30)
        current_time = current_time_dt.time()

    return JsonResponse({'available_slots': available_slots}, status=200)

@login_required
def update_appointment_status(request, appointment_id):
    """AJAX view for updating appointment status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    appointment = get_object_or_404(Appointment, id=appointment_id)
    new_status = request.POST.get('status')

    if new_status not in dict(Appointment.STATUS_CHOICES).keys():
        return JsonResponse({'error': 'Invalid status'}, status=400)

    # Update appointment status
    appointment.status = new_status
    appointment.save()

    return JsonResponse({
        'success': True,
        'message': f'Appointment status updated to {appointment.get_status_display()}',
        'new_status': appointment.get_status_display()
    }, status=200)
