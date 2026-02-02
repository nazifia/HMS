from django import forms
from django.db import models
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import (
    OperationTheatre, 
    SurgeryType, 
    Surgery, 
    SurgicalTeam, 
    SurgicalEquipment,
    EquipmentUsage,
    SurgerySchedule,
    PostOperativeNote,
    PreOperativeChecklist,
    EquipmentMaintenanceLog
)
from patients.models import Patient
from accounts.models import CustomUser

# Import AuthorizationCode, handle case where nhia app might not be available
# Fixed UnboundLocalError issue
try:
    from nhia.models import AuthorizationCode
except ImportError:
    AuthorizationCode = None


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class OperationTheatreForm(forms.ModelForm):
    class Meta:
        model = OperationTheatre
        fields = ['name', 'theatre_number', 'floor', 'capacity', 'is_available', 'description', 'equipment_list', 'last_sanitized']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'equipment_list': forms.Textarea(attrs={'rows': 3}),
            'last_sanitized': DateTimeInput(),
        }


class SurgeryTypeForm(forms.ModelForm):
    class Meta:
        model = SurgeryType
        fields = ['name', 'description', 'average_duration', 'preparation_time', 'recovery_time', 'risk_level', 'instructions', 'fee']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'average_duration': forms.TextInput(attrs={'placeholder': 'HH:MM'}),
            'preparation_time': forms.TextInput(attrs={'placeholder': 'HH:MM'}),
            'recovery_time': forms.TextInput(attrs={'placeholder': 'HH:MM'}),
        }


class SurgeryForm(forms.ModelForm):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]

    status = forms.ChoiceField(choices=STATUS_CHOICES, initial='scheduled')

    # Patient search field for enhanced UX
    patient_search = forms.CharField(
        required=False,
        label="Search Patient",
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name or patient ID',
            'class': 'form-control',
            'id': 'id_patient_search'
        })
    )

    # Scheduling options
    skip_conflict_validation = forms.BooleanField(
        required=False,
        label='Skip Conflict Validation',
        help_text='Allow scheduling even if there are conflicts (not recommended)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    allow_flexible_scheduling = forms.BooleanField(
        required=False,
        label='Allow Flexible Scheduling',
        help_text='Show warnings but allow saving with conflicts',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Surgery
        fields = [
            'patient', 'surgery_type', 'theatre', 'primary_surgeon', 'anesthetist',
            'scheduled_date', 'expected_duration', 'status', 'pre_surgery_notes',
            'post_surgery_notes', 'authorization_code'
        ]
        widgets = {
            'scheduled_date': DateTimeInput(),
            'expected_duration': forms.TextInput(attrs={'placeholder': 'HH:MM'}),
            'pre_surgery_notes': forms.Textarea(attrs={'rows': 3}),
            'post_surgery_notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self._warnings = []
        super().__init__(*args, **kwargs)

        # If editing an existing surgery, populate the patient search field
        if self.instance and self.instance.pk and self.instance.patient:
            self.fields['patient_search'].initial = str(self.instance.patient)

        # Set patient queryset
        if 'patient' in self.fields:
            self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        
        # Set theatre queryset
        if 'theatre' in self.fields:
            self.fields['theatre'].queryset = OperationTheatre.objects.filter(is_available=True)
        
        # Set surgery type queryset
        if 'surgery_type' in self.fields:
            self.fields['surgery_type'].queryset = SurgeryType.objects.all().order_by('name')
        
        # Set surgeon and anesthetist querysets
        # Include currently selected users to avoid validation errors
        if 'primary_surgeon' in self.fields:
            # Get currently selected surgeon ID from POST data or instance
            selected_surgeon_id = None
            raw_value = self.data.get('primary_surgeon')
            if raw_value:
                # Handle both single values and lists
                if isinstance(raw_value, list):
                    raw_value = raw_value[0] if raw_value else None
                if raw_value:
                    try:
                        selected_surgeon_id = int(raw_value)
                    except (ValueError, TypeError):
                        pass
            elif self.instance and self.instance.pk and self.instance.primary_surgeon_id:
                selected_surgeon_id = self.instance.primary_surgeon_id
            
            # Build base queryset of appropriate users
            base_qs = CustomUser.objects.filter(is_active=True)
            surgeon_qs = base_qs.filter(
                models.Q(profile__specialization__icontains='surgeon') |
                models.Q(profile__specialization__icontains='doctor') |
                models.Q(profile__role='doctor')
            ).order_by('first_name', 'last_name')
            
            if not surgeon_qs.exists():
                surgeon_qs = base_qs.order_by('first_name', 'last_name')
            
            # Union with selected surgeon if not already in queryset
            if selected_surgeon_id:
                selected_qs = CustomUser.objects.filter(pk=selected_surgeon_id)
                surgeon_qs = (surgeon_qs | selected_qs).distinct().order_by('first_name', 'last_name')
            
            self.fields['primary_surgeon'].queryset = surgeon_qs
            self.fields['primary_surgeon'].empty_label = "Select Surgeon (Optional)"
            self.fields['primary_surgeon'].required = False
        
        if 'anesthetist' in self.fields:
            # Get currently selected anesthetist ID from POST data or instance
            selected_anesthetist_id = None
            raw_value = self.data.get('anesthetist')
            if raw_value:
                # Handle both single values and lists
                if isinstance(raw_value, list):
                    raw_value = raw_value[0] if raw_value else None
                if raw_value:
                    try:
                        selected_anesthetist_id = int(raw_value)
                    except (ValueError, TypeError):
                        pass
            elif self.instance and self.instance.pk and self.instance.anesthetist_id:
                selected_anesthetist_id = self.instance.anesthetist_id
            
            # Build base queryset of appropriate users
            base_qs = CustomUser.objects.filter(is_active=True)
            anesthetist_qs = base_qs.filter(
                models.Q(profile__specialization__icontains='anesthetist') |
                models.Q(profile__specialization__icontains='anesthesia') |
                models.Q(profile__role='anesthetist')
            ).order_by('first_name', 'last_name')
            
            if not anesthetist_qs.exists():
                anesthetist_qs = base_qs.order_by('first_name', 'last_name')
            
            # Union with selected anesthetist if not already in queryset
            if selected_anesthetist_id:
                selected_qs = CustomUser.objects.filter(pk=selected_anesthetist_id)
                anesthetist_qs = (anesthetist_qs | selected_qs).distinct().order_by('first_name', 'last_name')
            
            self.fields['anesthetist'].queryset = anesthetist_qs
            self.fields['anesthetist'].empty_label = "Select Anesthetist (Optional)"
            self.fields['anesthetist'].required = False
        
        # Handle authorization code field
        if 'authorization_code' in self.fields:
            try:
                from nhia.models import AuthorizationCode
                self.fields['authorization_code'].queryset = AuthorizationCode.objects.filter(
                    status='active'
                ).order_by('-generated_at')
            except ImportError:
                # If nhia app is not available, remove the field
                del self.fields['authorization_code']

    def get_warnings(self):
        """Return list of validation warnings (not errors)"""
        return self._warnings

    def clean(self):
        cleaned_data = super().clean()

        # Handle missing surgeon/anesthetist users gracefully
        primary_surgeon = cleaned_data.get('primary_surgeon')
        anesthetist = cleaned_data.get('anesthetist')

        # If a user was selected but doesn't exist, clear it and add a warning
        if primary_surgeon:
            try:
                CustomUser.objects.get(pk=primary_surgeon.pk)
            except CustomUser.DoesNotExist:
                cleaned_data['primary_surgeon'] = None
                self.add_error('primary_surgeon', 'Selected surgeon no longer exists. Please select a different surgeon.')

        if anesthetist:
            try:
                CustomUser.objects.get(pk=anesthetist.pk)
            except CustomUser.DoesNotExist:
                cleaned_data['anesthetist'] = None
                self.add_error('anesthetist', 'Selected anesthetist no longer exists. Please select a different anesthetist.')

        # Check for scheduling conflicts
        theatre = cleaned_data.get('theatre')
        scheduled_date = cleaned_data.get('scheduled_date')
        expected_duration = cleaned_data.get('expected_duration')
        skip_conflict = cleaned_data.get('skip_conflict_validation', False)
        allow_flexible = cleaned_data.get('allow_flexible_scheduling', False)

        if theatre and scheduled_date and expected_duration:
            conflicts = self._check_scheduling_conflicts(
                theatre, scheduled_date, expected_duration
            )

            if conflicts:
                if skip_conflict:
                    # Just add warnings but don't prevent saving
                    for conflict in conflicts:
                        self._warnings.append(f"CONFLICT: {conflict}")
                elif allow_flexible:
                    # Add warnings but allow saving
                    for conflict in conflicts:
                        self._warnings.append(f"WARNING: {conflict}")
                else:
                    # Standard mode: prevent saving
                    for conflict in conflicts:
                        self.add_error('scheduled_date', f"Scheduling conflict: {conflict}")

        return cleaned_data

    def _check_scheduling_conflicts(self, theatre, scheduled_date, expected_duration):
        """Check for scheduling conflicts with other surgeries"""
        from django.db.models import Q
        from datetime import timedelta

        conflicts = []

        # Calculate end time
        end_time = scheduled_date + expected_duration

        # Find overlapping surgeries in the same theatre
        overlapping = Surgery.objects.filter(
            theatre=theatre,
            status__in=['scheduled', 'in_progress'],
            scheduled_date__lt=end_time
        ).exclude(
            pk=self.instance.pk if self.instance else None
        )

        for surgery in overlapping:
            surgery_end = surgery.scheduled_date + surgery.expected_duration
            if surgery_end > scheduled_date:
                conflicts.append(
                    f"{surgery.surgery_type.name} for {surgery.patient} "
                    f"({surgery.scheduled_date.strftime('%Y-%m-%d %H:%M')} - "
                    f"{surgery_end.strftime('%H:%M')})"
                )

        return conflicts


class SurgicalTeamForm(forms.ModelForm):
    class Meta:
        model = SurgicalTeam
        fields = ['surgery', 'staff', 'role', 'usage_notes']
        widgets = {
            'usage_notes': forms.Textarea(attrs={'rows': 2}),
        }


class SurgicalTeamFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        roles = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                role = form.cleaned_data.get('role')
                if role in roles:
                    raise forms.ValidationError(f"Duplicate role: {role}")
                roles.append(role)


SurgicalTeamInlineFormSet = inlineformset_factory(
    Surgery, 
    SurgicalTeam, 
    form=SurgicalTeamForm,
    formset=SurgicalTeamFormSet,
    extra=1,
    can_delete=True
)


class SurgicalEquipmentForm(forms.ModelForm):
    class Meta:
        model = SurgicalEquipment
        fields = [
            'name', 'equipment_type', 'description', 'quantity_available', 
            'is_available', 'last_maintenance_date', 'next_maintenance_date',
            'last_calibration_date', 'calibration_frequency'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'last_maintenance_date': DateInput(),
            'next_maintenance_date': DateInput(),
            'last_calibration_date': DateInput(),
        }


class EquipmentUsageForm(forms.ModelForm):
    class Meta:
        model = EquipmentUsage
        fields = ['surgery', 'equipment', 'quantity_used', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class EquipmentUsageFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        equipment_items = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                equipment = form.cleaned_data.get('equipment')
                if equipment in equipment_items:
                    raise forms.ValidationError(f"Duplicate equipment: {equipment}")
                equipment_items.append(equipment)


EquipmentUsageInlineFormSet = inlineformset_factory(
    Surgery,
    EquipmentUsage,
    form=EquipmentUsageForm,
    formset=EquipmentUsageFormSet,
    extra=1,
    can_delete=True
)


class SurgeryScheduleForm(forms.ModelForm):
    class Meta:
        model = SurgerySchedule
        fields = ['surgery', 'start_time', 'end_time', 'pre_op_preparation_start', 'post_op_recovery_end', 'status', 'delay_reason']
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
        fields = ['surgery', 'notes', 'complications', 'follow_up_instructions']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'complications': forms.Textarea(attrs={'rows': 3}),
            'follow_up_instructions': forms.Textarea(attrs={'rows': 3}),
        }


class PreOperativeChecklistForm(forms.ModelForm):
    class Meta:
        model = PreOperativeChecklist
        fields = [
            'surgery', 'patient_identified', 'site_marked', 
            'anesthesia_safety_check_completed', 'surgical_safety_checklist_completed',
            'consent_confirmed', 'allergies_reviewed', 'imaging_available',
            'blood_products_available', 'antibiotics_administered', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class SurgeryFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    start_date = forms.DateField(
        required=False, 
        widget=DateInput(),
        label="Start Date"
    )
    end_date = forms.DateField(
        required=False, 
        widget=DateInput(),
        label="End Date"
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


class EquipmentMaintenanceLogForm(forms.ModelForm):
    """Form for recording equipment maintenance and calibration."""
    
    class Meta:
        model = EquipmentMaintenanceLog
        fields = [
            'equipment', 'maintenance_type', 'scheduled_date', 'completed_date',
            'next_due_date', 'status', 'description', 'findings', 'parts_replaced',
            'cost', 'external_provider', 'external_technician', 'certificate_number',
            'document_file'
        ]
        widgets = {
            'scheduled_date': DateInput(),
            'completed_date': DateInput(),
            'next_due_date': DateInput(),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the work performed or to be performed'}),
            'findings': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any findings during maintenance'}),
            'parts_replaced': forms.Textarea(attrs={'rows': 2, 'placeholder': 'List any parts that were replaced'}),
            'external_provider': forms.TextInput(attrs={'placeholder': 'External service company name'}),
            'external_technician': forms.TextInput(attrs={'placeholder': 'Technician name'}),
            'certificate_number': forms.TextInput(attrs={'placeholder': 'Calibration certificate number'}),
        }
    
    def __init__(self, *args, equipment=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If equipment is provided, set it and make it read-only
        if equipment:
            self.fields['equipment'].initial = equipment
            self.fields['equipment'].widget.attrs['readonly'] = True
            self.fields['equipment'].widget.attrs['disabled'] = True
        
        # Set default scheduled date to today
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['scheduled_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        completed_date = cleaned_data.get('completed_date')
        next_due_date = cleaned_data.get('next_due_date')
        status = cleaned_data.get('status')
        
        # If completed, must have completed date
        if status == 'completed' and not completed_date:
            self.add_error('completed_date', 'Completed date is required when status is completed.')
        
        # Completed date cannot be before scheduled date
        if completed_date and scheduled_date and completed_date < scheduled_date:
            self.add_error('completed_date', 'Completed date cannot be before scheduled date.')
        
        # Next due date should be after completed date
        if next_due_date and completed_date and next_due_date <= completed_date:
            self.add_error('next_due_date', 'Next due date should be after completed date.')
        
        return cleaned_data
