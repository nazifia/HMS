from django import forms
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from .models import Appointment, AppointmentFollowUp, DoctorSchedule, DoctorLeave
from patients.models import Patient

class AppointmentForm(forms.ModelForm):
    """Form for creating and editing appointments"""
    
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Patient"
    )
    
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, profile__specialization__isnull=False),
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
        fields = ['patient', 'doctor', 'appointment_date', 'appointment_time', 
                 'end_time', 'reason', 'status', 'priority', 'notes']
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
            self.fields['patient'].widget = forms.HiddenInput()
        # Ensure all patients are available for selection
        self.fields['patient'].queryset = Patient.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')
        end_time = cleaned_data.get('end_time')
        doctor = cleaned_data.get('doctor')
        
        # Check if appointment date is in the past
        if appointment_date and appointment_date < timezone.now().date():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        
        # Check if end time is after start time
        if appointment_time and end_time and end_time <= appointment_time:
            raise forms.ValidationError("End time must be after appointment time.")
        
        # Check if doctor is available on the selected date and time
        if appointment_date and appointment_time and doctor:
            # Check if doctor is on leave
            doctor_leaves = DoctorLeave.objects.filter(
                doctor=doctor,
                start_date__lte=appointment_date,
                end_date__gte=appointment_date,
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
            if appointment_time < doctor_schedule.start_time or appointment_time > doctor_schedule.end_time:
                raise forms.ValidationError(
                    f"Doctor {doctor.get_full_name()} is only available from "
                    f"{doctor_schedule.start_time.strftime('%I:%M %p')} to "
                    f"{doctor_schedule.end_time.strftime('%I:%M %p')} on this day."
                )
            
            # Check for overlapping appointments
            overlapping_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                status__in=['scheduled', 'confirmed']
            ).exclude(id=self.instance.id if self.instance else None)
            
            for existing_appt in overlapping_appointments:
                existing_end = existing_appt.end_time or (
                    # Default appointment duration of 30 minutes if end_time not specified
                    (datetime.datetime.combine(datetime.date.today(), existing_appt.appointment_time) 
                     + datetime.timedelta(minutes=30)).time()
                )
                
                new_end = end_time or (
                    # Default appointment duration of 30 minutes if end_time not specified
                    (datetime.datetime.combine(datetime.date.today(), appointment_time) 
                     + datetime.timedelta(minutes=30)).time()
                )
                
                # Check for overlap
                if (appointment_time < existing_end and new_end > existing_appt.appointment_time):
                    raise forms.ValidationError(
                        f"This appointment overlaps with an existing appointment for "
                        f"{doctor.get_full_name()} at {existing_appt.appointment_time.strftime('%I:%M %p')}."
                    )
        
        return cleaned_data

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
        }
    
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
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data

class AppointmentSearchForm(forms.Form):
    """Form for searching appointments"""
    
    search = forms.CharField(required=False, label='Search',
                           widget=forms.TextInput(attrs={'placeholder': 'Patient name or ID'}))
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, profile__specialization__isnull=False),
        required=False,
        empty_label="All Doctors"
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + list(Appointment.STATUS_CHOICES),
        required=False
    )
    priority = forms.ChoiceField(
        choices=[('', 'All')] + list(Appointment.PRIORITY_CHOICES),
        required=False
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
