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
    PostOperativeNote
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