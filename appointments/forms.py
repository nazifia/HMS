from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
User = get_user_model()
from django.utils import timezone
from .models import Appointment, AppointmentFollowUp, DoctorSchedule, DoctorLeave, SLOT_MINUTES
from patients.models import Patient
from core.patient_search_forms import PatientSearchForm
import datetime

# ponytail: two role systems live side by side - legacy profile.role CharField
# and the newer roles M2M. A doctor may be tagged in either, so match both.
DOCTOR_Q = Q(profile__role__iexact='doctor') | Q(roles__name__iexact='doctor')


def doctor_queryset(manager=None):
    """Active doctors, tenant-scoped by default."""
    manager = manager or User.tenant_objects
    return manager.filter(DOCTOR_Q, is_active=True).distinct().order_by(
        'first_name', 'last_name'
    )

class AppointmentForm(forms.ModelForm):
    """Form for creating and editing appointments with patient search"""
    
    # Add patient search field
    patient_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control patient-search',
            'placeholder': 'Search patient by name, ID, or phone...',
            'autocomplete': 'off'
        }),
        help_text='Search for a patient by name, ID, or phone number'
    )
    
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all().order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-select select2 patient-select'}),
        empty_label="Select Patient"
    )
    
    def _format_patient_label(self, obj):
        """Format patient label with type information"""
        if not obj:
            return str(obj)
        
        label = f"{obj.get_full_name()} ({obj.patient_id})"
        patient_type = obj.get_patient_type_display()
        
        # Add type-specific information
        if hasattr(obj, 'nhia_info') and obj.nhia_info and obj.nhia_info.is_active:
            label += f" [NHIA: {obj.nhia_info.nhia_reg_number}]"
        elif hasattr(obj, 'retainership_info') and obj.retainership_info and obj.retainership_info.is_active:
            label += f" [Retainership: {obj.retainership_info.retainership_reg_number}]"
        elif patient_type != 'regular':
            label += f" [{patient_type}]"
            
        return label
    
    doctor = forms.ModelChoiceField(
        queryset=doctor_queryset(User.objects),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Doctor"
    )
    
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()})
    )
    
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False
    )
    
    class Meta:
        model = Appointment
        # appointment_date and appointment_time are declared above as plain form
        # fields; save() combines them into the model's appointment_date datetime.
        fields = ['patient', 'doctor', 'end_time', 'reason', 'status', 'priority', 'notes']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        patient_id = None
        if request:
            patient_id = request.GET.get('patient')
        if not patient_id:
            patient_id = self.initial.get('patient')
        if patient_id:
            self.fields['patient'].initial = patient_id
            # Keep patient field visible but pre-selected for user convenience
        # Ensure all patients are available for selection
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).select_related('nhia_info', 'retainership_info').order_by('first_name', 'last_name')
        # Scope doctor picker to the current hospital (per-request, not import-time).
        self.fields['doctor'].queryset = doctor_queryset()

        # Show patient ID / NHIA / Retainership in the dropdown labels.
        self.fields['patient'].label_from_instance = self._format_patient_label

        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"

        # The model stores one datetime; split it back out for the two form fields.
        if self.instance and self.instance.pk and self.instance.appointment_date:
            local = timezone.localtime(self.instance.appointment_date)
            self.initial['appointment_date'] = local.date()
            self.initial['appointment_time'] = local.time()
    
    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')
        end_time = cleaned_data.get('end_time')
        doctor = cleaned_data.get('doctor')

        # Check if appointment date is in the past
        now = timezone.localtime()
        if appointment_date and appointment_date < now.date():
            raise forms.ValidationError("Appointment date cannot be in the past.")

        # A time earlier today is just as much in the past as yesterday.
        if (appointment_date == now.date() and appointment_time
                and not self.instance.pk and appointment_time < now.time()):
            raise forms.ValidationError("Appointment time cannot be in the past.")

        # Check if end time is after start time
        if appointment_time and end_time and end_time <= appointment_time:
            raise forms.ValidationError("End time must be after appointment time.")

        # Check if doctor is available on the selected date and time
        if appointment_date and appointment_time and doctor:
            # Check if doctor is on leave
            # start_date/end_date are DateTimeFields; compare on the date part so a
            # leave that starts mid-day still covers the whole day.
            doctor_leaves = DoctorLeave.objects.filter(
                doctor=doctor,
                start_date__date__lte=appointment_date,
                end_date__date__gte=appointment_date,
                is_approved=True
            )

            if doctor_leaves.exists():
                raise forms.ValidationError(f"Doctor {doctor.get_full_name()} is on leave on the selected date.")

            # Check doctor's schedule for the day of the week
            weekday = appointment_date.weekday()
            doctor_schedule = DoctorSchedule.objects.filter(
                doctor=doctor,
                weekday=weekday,
                is_available=True
            ).first()

            if not doctor_schedule:
                raise forms.ValidationError(f"Doctor {doctor.get_full_name()} is not available on this day.")

            # Check if appointment time is within doctor's schedule
            # The slot must start within the shift and finish by the end of it.
            slot_end = end_time or (
                datetime.datetime.combine(appointment_date, appointment_time)
                + datetime.timedelta(minutes=SLOT_MINUTES)
            ).time()
            if (appointment_time < doctor_schedule.start_time
                    or appointment_time >= doctor_schedule.end_time
                    or slot_end > doctor_schedule.end_time):
                raise forms.ValidationError(
                    f"Doctor {doctor.get_full_name()} is only available from "
                    f"{doctor_schedule.start_time.strftime('%I:%M %p')} to "
                    f"{doctor_schedule.end_time.strftime('%I:%M %p')} on this day."
                )

            # Check for overlapping appointments
            # Get all appointments for this doctor on this date with scheduled/confirmed status
            overlapping_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__date=appointment_date,
                status__in=['scheduled', 'confirmed']
            ).exclude(id=self.instance.id if self.instance else None)

            # Build new appointment datetime range
            appointment_start = timezone.make_aware(
                datetime.datetime.combine(appointment_date, appointment_time)
            )
            appointment_end = None
            if end_time:
                appointment_end = timezone.make_aware(
                    datetime.datetime.combine(appointment_date, end_time)
                )
            else:
                appointment_end = appointment_start + datetime.timedelta(minutes=SLOT_MINUTES)

            for existing_appt in overlapping_appointments:
                # Existing appointment start is stored as appointment_date (datetime)
                existing_start = existing_appt.appointment_date

                # Existing appointment end time - check if end_time field is set
                if existing_appt.end_time:
                    # existing_appt.appointment_date is a datetime, we need to combine its date with its end_time
                    existing_end = timezone.make_aware(
                        datetime.datetime.combine(
                            existing_appt.appointment_date.date(),
                            existing_appt.end_time
                        )
                    )
                else:
                    existing_end = existing_start + datetime.timedelta(minutes=SLOT_MINUTES)

                # Check for overlap: A overlaps B if A.start < B.end AND A.end > B.start
                if appointment_start < existing_end and appointment_end > existing_start:
                    raise forms.ValidationError(
                        f"This appointment overlaps with an existing appointment for "
                        f"{doctor.get_full_name()} at {existing_appt.appointment_time.strftime('%I:%M %p')}."
                    )

        return cleaned_data

    def save(self, commit=True):
        """Override save to combine date and time into timezone-aware datetime"""
        instance = super().save(commit=False)
        appointment_date = self.cleaned_data.get('appointment_date')
        appointment_time = self.cleaned_data.get('appointment_time')

        if appointment_date and appointment_time:
            # Combine date and time into a timezone-aware datetime
            naive_datetime = datetime.datetime.combine(appointment_date, appointment_time)
            instance.appointment_date = timezone.make_aware(naive_datetime)

        if commit:
            instance.save()

        return instance

class AppointmentFollowUpForm(forms.ModelForm):
    """Form for creating appointment follow-ups"""
    
    follow_up_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()})
    )
    
    class Meta:
        model = AppointmentFollowUp
        fields = ['follow_up_date', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_follow_up_date(self):
        follow_up_date = self.cleaned_data.get('follow_up_date')
        if follow_up_date and follow_up_date < timezone.now().date():
            raise forms.ValidationError("Follow-up date cannot be in the past.")
        return follow_up_date

class DoctorScheduleForm(forms.ModelForm):
    """Form for managing doctor schedules"""
    
    class Meta:
        model = DoctorSchedule
        fields = ['doctor', 'weekday', 'start_time', 'end_time', 'is_available']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'weekday': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope doctor picker to the current hospital (per-request, not import-time).
        self.fields['doctor'].queryset = doctor_queryset()

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")
        
        return cleaned_data

class DoctorLeaveForm(forms.ModelForm):
    """Form for managing doctor leaves"""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()})
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()})
    )
    
    class Meta:
        model = DoctorLeave
        fields = ['doctor', 'start_date', 'end_date', 'reason', 'is_approved']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope doctor picker to the current hospital (per-request, not import-time).
        self.fields['doctor'].queryset = doctor_queryset()
        # Model stores datetimes; the widgets are date-only, so seed them from the date part.
        for field in ('start_date', 'end_date'):
            value = getattr(self.instance, field, None)
            if value:
                self.initial[field] = timezone.localtime(value).date()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")

        # start_date/end_date are DateTimeField columns but leave is day-granular.
        # Widen to the full local day so a date-only value never lands in a datetime
        # column (breaks admin date_hierarchy) and never shifts across midnight.
        if start_date:
            cleaned_data['start_date'] = timezone.make_aware(
                datetime.datetime.combine(start_date, datetime.time.min)
            )
        if end_date:
            cleaned_data['end_date'] = timezone.make_aware(
                datetime.datetime.combine(end_date, datetime.time.max)
            )

        return cleaned_data

class AppointmentSearchForm(forms.Form):
    """Form for searching appointments"""
    
    search = forms.CharField(required=False, label='Search',
                           widget=forms.TextInput(attrs={
                               'placeholder': 'Patient name or ID',
                               'class': 'form-control'
                           }))
    doctor = forms.ModelChoiceField(
        queryset=doctor_queryset(User.objects),
        required=False,
        empty_label="All Doctors",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + list(Appointment.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    priority = forms.ChoiceField(
        choices=[('', 'All')] + list(Appointment.PRIORITY_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope doctor filter to the current hospital (per-request).
        self.fields['doctor'].queryset = doctor_queryset()


class AppointmentsPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for appointments module"""
    pass
