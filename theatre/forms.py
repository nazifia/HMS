from django import forms
from django.forms import inlineformset_factory
from .models import (
    OperationTheatre, 
    SurgeryType, 
    Surgery, 
    SurgicalTeam, 
    SurgicalEquipment,
    EquipmentUsage,
    SurgerySchedule,
    PostOperativeNote,
    PreOperativeChecklist
)
from patients.models import Patient
from accounts.models import CustomUser


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class DurationInput(forms.TextInput):
    input_type = 'text'


class OperationTheatreForm(forms.ModelForm):
    class Meta:
        model = OperationTheatre
        fields = '__all__'
        widgets = {
            'last_sanitized': DateTimeInput(),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class SurgeryTypeForm(forms.ModelForm):
    class Meta:
        model = SurgeryType
        fields = '__all__'
        widgets = {
            'average_duration': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'preparation_time': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'recovery_time': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'average_duration': 'Format: HH:MM:SS',
            'preparation_time': 'Format: HH:MM:SS',
            'recovery_time': 'Format: HH:MM:SS',
        }


class SurgeryForm(forms.ModelForm):
    patient_search = forms.CharField(
        required=False,
        label="Search Patient",
        widget=forms.TextInput(attrs={'placeholder': 'Search by name or ID'})
    )

    class Meta:
        model = Surgery
        fields = [
            'patient', 'surgery_type', 'theatre', 'primary_surgeon', 
            'anesthetist', 'scheduled_date', 'expected_duration', 
            'pre_surgery_notes', 'status'
        ]
        widgets = {
            'scheduled_date': DateTimeInput(),
            'expected_duration': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'pre_surgery_notes': forms.Textarea(attrs={'rows': 3}),
            'patient': forms.HiddenInput(),
        }
        help_texts = {
            'expected_duration': 'Format: HH:MM:SS',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter surgeons and anesthetists
        self.fields['primary_surgeon'].queryset = CustomUser.objects.filter(
            profile__specialization__icontains='surgeon'
        )
        self.fields['anesthetist'].queryset = CustomUser.objects.filter(
            profile__specialization__icontains='anesthetist'
        )
        
        # If editing an existing surgery, populate the patient search field
        if self.instance and self.instance.pk and self.instance.patient:
            self.fields['patient_search'].initial = str(self.instance.patient)

    def clean(self):
        cleaned_data = super().clean()
        theatre = cleaned_data.get('theatre')
        scheduled_date = cleaned_data.get('scheduled_date')
        expected_duration = cleaned_data.get('expected_duration')
        primary_surgeon = cleaned_data.get('primary_surgeon')
        anesthetist = cleaned_data.get('anesthetist')

        if theatre and scheduled_date and expected_duration:
            end_time = scheduled_date + expected_duration

            # Check for theatre conflicts
            conflicting_surgeries = Surgery.objects.filter(
                theatre=theatre,
                scheduled_date__lt=end_time,
                scheduled_date__gte=scheduled_date
            ).exclude(pk=self.instance.pk if self.instance else None)

            if conflicting_surgeries.exists():
                raise forms.ValidationError("The selected theatre is already booked for an overlapping surgery.")

            # Check for surgeon conflicts
            if primary_surgeon:
                conflicting_surgeon_surgeries = Surgery.objects.filter(
                    primary_surgeon=primary_surgeon,
                    scheduled_date__lt=end_time,
                    scheduled_date__gte=scheduled_date
                ).exclude(pk=self.instance.pk if self.instance else None)
                if conflicting_surgeon_surgeries.exists():
                    raise forms.ValidationError("The primary surgeon is already booked for an overlapping surgery.")

            # Check for anesthetist conflicts
            if anesthetist:
                conflicting_anesthetist_surgeries = Surgery.objects.filter(
                    anesthetist=anesthetist,
                    scheduled_date__lt=end_time,
                    scheduled_date__gte=scheduled_date
                ).exclude(pk=self.instance.pk if self.instance else None)
                if conflicting_anesthetist_surgeries.exists():
                    raise forms.ValidationError("The anesthetist is already booked for an overlapping surgery.")

        return cleaned_data


class SurgicalTeamForm(forms.ModelForm):
    class Meta:
        model = SurgicalTeam
        fields = ['staff', 'role', 'usage_notes']
        widgets = {
            'usage_notes': forms.Textarea(attrs={'rows': 2}),
        }


SurgicalTeamFormSet = inlineformset_factory(
    Surgery, SurgicalTeam,
    form=SurgicalTeamForm,
    extra=1,
    can_delete=True,
    fk_name='surgery'
)


class SurgicalEquipmentForm(forms.ModelForm):
    class Meta:
        model = SurgicalEquipment
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'last_maintenance_date': DateInput(),
            'next_maintenance_date': DateInput(),
            'last_calibration_date': DateInput(),
            'calibration_frequency': DurationInput(attrs={'placeholder': 'DD HH:MM:SS'}),
        }
        help_texts = {
            'calibration_frequency': 'Format: DD HH:MM:SS (e.g., 365 00:00:00 for annual)',
        }


class EquipmentUsageForm(forms.ModelForm):
    class Meta:
        model = EquipmentUsage
        fields = ['equipment', 'quantity_used', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


EquipmentUsageFormSet = inlineformset_factory(
    Surgery, EquipmentUsage,
    form=EquipmentUsageForm,
    extra=1,
    can_delete=True,
    fk_name='surgery'
)


class SurgeryScheduleForm(forms.ModelForm):
    class Meta:
        model = SurgerySchedule
        fields = [
            'start_time', 'end_time', 'pre_op_preparation_start',
            'post_op_recovery_end', 'status', 'delay_reason'
        ]
        widgets = {
            'start_time': DateTimeInput(),
            'end_time': DateTimeInput(),
            'pre_op_preparation_start': DateTimeInput(),
            'post_op_recovery_end': DateTimeInput(),
            'delay_reason': forms.Textarea(attrs={'rows': 2}),
        }


class PostOperativeNoteForm(forms.ModelForm):
    class Meta:
        model = PostOperativeNote
        fields = ['notes', 'complications', 'follow_up_instructions']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'complications': forms.Textarea(attrs={'rows': 3}),
            'follow_up_instructions': forms.Textarea(attrs={'rows': 3}),
        }


class PreOperativeChecklistForm(forms.ModelForm):
    class Meta:
        model = PreOperativeChecklist
        fields = [
            'patient_identified', 'site_marked', 'anesthesia_safety_check_completed',
            'surgical_safety_checklist_completed', 'consent_confirmed', 'allergies_reviewed',
            'imaging_available', 'blood_products_available', 'antibiotics_administered', 'notes'
        ]
        widgets = {
            'patient_identified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'site_marked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anesthesia_safety_check_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'surgical_safety_checklist_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consent_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allergies_reviewed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'imaging_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'blood_products_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'antibiotics_administered': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class SurgeryFilterForm(forms.Form):
    STATUS_CHOICES = (
        ('', 'All Statuses'),
    ) + Surgery.STATUS_CHOICES
    
    start_date = forms.DateField(
        required=False,
        widget=DateInput(),
        label="From Date"
    )
    end_date = forms.DateField(
        required=False,
        widget=DateInput(),
        label="To Date"
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label="Status"
    )
    surgeon = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(profile__specialization__icontains='surgeon'),
        required=False,
        label="Surgeon"
    )
    theatre = forms.ModelChoiceField(
        queryset=OperationTheatre.objects.all(),
        required=False,
        label="Theatre"
    )
    surgery_type = forms.ModelChoiceField(
        queryset=SurgeryType.objects.all(),
        required=False,
        label="Surgery Type"
    )
    patient_name = forms.CharField(
        required=False,
        label="Patient Name"
    )