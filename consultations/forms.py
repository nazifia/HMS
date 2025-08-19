from django import forms
from django.contrib.auth import get_user_model
User = get_user_model()
from patients.models import Patient, Vitals
from appointments.models import Appointment
from .models import ConsultingRoom, WaitingList, Consultation, ConsultationNote, Referral, SOAPNote
from doctors.models import Specialization
from accounts.models import Department, CustomUser
from core.patient_search_forms import PatientSearchForm

def get_active_consulting_rooms():
    """Utility to get all active consulting rooms as choices for forms or views."""
    return ConsultingRoom.objects.filter(is_active=True)

class ConsultationForm(forms.ModelForm):
    """Form for creating and editing consultations with patient search"""

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
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2 patient-select'}),
        empty_label="Select Patient"
    )

    doctor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, profile__specialization__isnull=False),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Doctor (Optional)",
        required=False
    )

    consulting_room = forms.ModelChoiceField(
        queryset=ConsultingRoom.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Consulting Room",
        required=False
    )

    class Meta:
        model = Consultation
        fields = [
            'patient', 'doctor', 'consulting_room', 'vitals', 'chief_complaint',
            'symptoms', 'diagnosis', 'consultation_notes', 'status'
        ]
        widgets = {
            'chief_complaint': forms.Textarea(attrs={'rows': 3}),
            'symptoms': forms.Textarea(attrs={'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'consultation_notes': forms.Textarea(attrs={'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'vitals': forms.Select(attrs={'class': 'form-select select2'}),
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
            # Only hide if specifically needed
            # self.fields['patient'].widget = forms.HiddenInput()

        # Ensure all patients are available for selection
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"

class ConsultationNoteForm(forms.ModelForm):
    """Form for adding consultation notes"""

    class Meta:
        model = ConsultationNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }

class ReferralForm(forms.ModelForm):
    """Form for creating patient referrals with patient search"""

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

    referred_to = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, profile__specialization__isnull=False),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Doctor"
    )

    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2 patient-select'}),
        empty_label="Select Patient"
    )

    class Meta:
        model = Referral
        fields = ['patient', 'referred_to', 'reason', 'notes']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        if 'patient' in self.initial:
            self.fields['patient'].widget = forms.HiddenInput()
            self.fields['patient'].initial = self.initial['patient']
            
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"

class VitalsSelectionForm(forms.Form):
    """Form for selecting patient vitals for a consultation"""

    vitals = forms.ModelChoiceField(
        queryset=Vitals.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Vitals",
        required=False
    )

    def __init__(self, patient=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if patient:
            self.fields['vitals'].queryset = Vitals.objects.filter(patient=patient).order_by('-date_time')

class ConsultingRoomForm(forms.ModelForm):
    """Form for creating and editing consulting rooms"""

    specializations = forms.ModelMultipleChoiceField(
        queryset=Specialization.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2'}),
        required=False,
        help_text='Select all specializations relevant to this consulting room.'
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label='Select Department',
        required=False
    )

    class Meta:
        model = ConsultingRoom
        fields = ['room_number', 'floor', 'department', 'description', 'is_active', 'specializations']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class WaitingListForm(forms.ModelForm):
    """Form for adding patients to the waiting list with patient search"""

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
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2 patient-select'}),
        empty_label="Select Patient"
    )

    doctor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, profile__specialization__isnull=False),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Doctor (Optional)",
        required=False
    )

    consulting_room = forms.ModelChoiceField(
        queryset=ConsultingRoom.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Consulting Room"
    )

    appointment = forms.ModelChoiceField(
        queryset=Appointment.objects.filter(status__in=['scheduled', 'confirmed']),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Appointment (Optional)",
        required=False
    )

    class Meta:
        model = WaitingList
        fields = ['patient', 'doctor', 'consulting_room', 'appointment', 'priority', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # If we have a patient, filter appointments for that patient
        if 'initial' in kwargs and 'patient' in kwargs['initial']:
            patient = kwargs['initial']['patient']
            self.fields['appointment'].queryset = Appointment.objects.filter(
                patient=patient,
                status__in=['scheduled', 'confirmed']
            ).order_by('-appointment_date')
            
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"


class ConsultationsPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for consultations module"""
    pass
