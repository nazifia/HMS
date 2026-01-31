from django import forms
from django import forms
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
    PreOperativeChecklist
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


class DurationInput(forms.TextInput):
    input_type = 'text'


class OperationTheatreForm(forms.ModelForm):
    class Meta:
        model = OperationTheatre
        fields = '__all__'
        widgets = {
            'last_sanitized': DateTimeInput(),
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class SurgeryTypeForm(forms.ModelForm):
    class Meta:
        model = SurgeryType
        fields = '__all__'
        widgets = {
            'average_duration': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'preparation_time': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'recovery_time': DurationInput(attrs={'placeholder': 'HH:MM:SS'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'instructions': forms.Textarea(attrs={'rows': 2}),
            'fee': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }
        help_texts = {
            'average_duration': 'Format: HH:MM:SS',
            'preparation_time': 'Format: HH:MM:SS',
            'recovery_time': 'Format: HH:MM:SS',
            'fee': 'Surgery fee in Naira (₦)',
        }


class SurgeryForm(forms.ModelForm):
    patient_search = forms.CharField(
        required=False,
        label="Search Patient",
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name or ID',
            'class': 'form-control',
            'id': 'id_patient_search'
        })
    )
    
    # Flexible validation control options
    skip_conflict_validation = forms.BooleanField(
        required=False,
        label="Skip Conflict Validation",
        help_text="Allow overlapping bookings (override scheduling conflicts)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    allow_flexible_scheduling = forms.BooleanField(
        required=False,
        label="Flexible Scheduling Mode",
        help_text="Enable flexible scheduling with optional constraints",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add authorization code field if AuthorizationCode model is available
        if AuthorizationCode is not None:
            self.fields['authorization_code'] = forms.ModelChoiceField(
                queryset=AuthorizationCode.objects.none(),  # Empty queryset by default
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'}),
                empty_label="Select Authorization Code (Optional)"
            )
            
            # Set authorization code queryset based on patient
            patient_id = self.initial.get('patient') or self.data.get('patient')
            if patient_id:
                try:
                    patient_instance = Patient.objects.get(id=patient_id)
                    if hasattr(patient_instance, 'patient_type') and patient_instance.patient_type == 'nhia':
                        self.fields['authorization_code'].queryset = AuthorizationCode.objects.filter(
                            patient=patient_instance,
                            status='active'
                        ).order_by('-generated_at')
                except Patient.DoesNotExist:
                    pass  # Keep empty queryset
        
        # Filter surgeons and anesthetists
        self.fields['primary_surgeon'].queryset = CustomUser.objects.filter(
            profile__specialization__icontains='surgeon'
        )
        self.fields['anesthetist'].queryset = CustomUser.objects.filter(
            profile__specialization__icontains='anesthetist'
        )
        
        # Enhance theatre dropdown with detailed labels
        self.fields['theatre'].queryset = OperationTheatre.objects.all()
        def get_theatre_label(obj):
            status = "✓ Available" if obj.is_available else "✗ Occupied"
            equipment = obj.equipment_list[:30] + "..." if obj.equipment_list and len(obj.equipment_list) > 30 else obj.equipment_list or "No equipment listed"
            last_clean = obj.last_sanitized.strftime("%d/%m/%Y %H:%M") if obj.last_sanitized else "Not recorded"
            return (
                f"🏥 {obj.name} | Room {obj.theatre_number} | Floor {obj.floor} | "
                f"{status} | Capacity: {obj.capacity} | "
                f"🧼 Last sanitized: {last_clean}"
            )
        self.fields['theatre'].label_from_instance = get_theatre_label
        
        # Enhance surgery type dropdown with detailed labels
        self.fields['surgery_type'].queryset = SurgeryType.objects.all()
        def get_surgery_type_label(obj):
            prep_time = obj.preparation_time
            recovery_time = obj.recovery_time
            desc = obj.description[:40] + "..." if obj.description and len(obj.description) > 40 else obj.description or "No description"
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(obj.risk_level, "⚪")
            return (
                f"{obj.name} | {risk_emoji} Risk: {obj.get_risk_level_display()} | "
                f"⏱️ Surgery: {obj.average_duration} | 📝 Prep: {prep_time} | 🏥 Recovery: {recovery_time} | "
                f"💰 ₦{obj.fee:,.2f}"
            )
        self.fields['surgery_type'].label_from_instance = get_surgery_type_label
        
        # Make all key fields optional for flexible editing
        self.fields['primary_surgeon'].required = False
        self.fields['anesthetist'].required = False
        self.fields['theatre'].required = False
        self.fields['surgery_type'].required = False
        self.fields['scheduled_date'].required = False
        self.fields['expected_duration'].required = False
        
        # Update field labels and help text for flexible editing
        self.fields['primary_surgeon'].empty_label = "Select Surgeon (Optional)"
        self.fields['anesthetist'].empty_label = "Select Anesthetist (Optional)"
        self.fields['theatre'].empty_label = "Select Theatre (Optional)"
        self.fields['surgery_type'].empty_label = "Select Surgery Type (Optional)"
        
        # Add helpful labels and help text
        self.fields['primary_surgeon'].label = "Primary Surgeon"
        self.fields['anesthetist'].label = "Anesthetist"
        self.fields['theatre'].label = "Operation Theatre"
        self.fields['surgery_type'].label = "Surgery Type"
        self.fields['scheduled_date'].label = "Scheduled Date/Time"
        self.fields['expected_duration'].label = "Expected Duration"
        
        self.fields['primary_surgeon'].help_text = "Can be assigned later - not required"
        self.fields['anesthetist'].help_text = "Can be assigned later - not required"
        self.fields['theatre'].help_text = "Can be assigned later - not required"
        self.fields['surgery_type'].help_text = "Can be specified later - not required"
        self.fields['scheduled_date'].help_text = "Can be scheduled later - not required"
        self.fields['expected_duration'].help_text = "Can be estimated later - not required"
        
        # If editing an existing surgery, populate the patient search field
        if self.instance and self.instance.pk and self.instance.patient:
            self.fields['patient_search'].initial = str(self.instance.patient)
            
        # Patient is the only required field
        self.fields['patient'].required = True

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
            'pre_surgery_notes': forms.Textarea(attrs={'rows': 2}),
            'patient': forms.HiddenInput(),
        }
        help_texts = {
            'expected_duration': 'Format: HH:MM:SS (optional)',
            'scheduled_date': 'When the surgery is planned (optional)',
            'theatre': 'Which operating theatre to use (optional)',
            'surgery_type': 'Type of surgical procedure (optional)',
        }

    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure patient is selected (only hard requirement)
        patient = cleaned_data.get('patient')
        if not patient:
            raise forms.ValidationError("Please search and select a patient before submitting the form.")
        
        # Get validation control flags
        skip_conflict_validation = cleaned_data.get('skip_conflict_validation', False)
        allow_flexible_scheduling = cleaned_data.get('allow_flexible_scheduling', False)
        
        theatre = cleaned_data.get('theatre')
        scheduled_date = cleaned_data.get('scheduled_date')
        expected_duration = cleaned_data.get('expected_duration')
        primary_surgeon = cleaned_data.get('primary_surgeon')
        anesthetist = cleaned_data.get('anesthetist')

        # Only perform conflict validation if user hasn't opted to skip it
        if not skip_conflict_validation and theatre and scheduled_date and expected_duration:
            end_time = scheduled_date + expected_duration
            warnings = []
            
            # Check for theatre conflicts (soft warning in flexible mode)
            conflicting_surgeries = Surgery.objects.filter(
                theatre=theatre,
                scheduled_date__lt=end_time,
                scheduled_date__gte=scheduled_date
            ).exclude(pk=self.instance.pk if self.instance else None)

            if conflicting_surgeries.exists():
                conflict_msg = f"Warning: The selected theatre is already booked for {conflicting_surgeries.count()} overlapping surgery(ies)."
                if allow_flexible_scheduling:
                    warnings.append(conflict_msg)
                else:
                    raise forms.ValidationError(conflict_msg + " Check 'Skip Conflict Validation' to proceed anyway.")

            # Check for surgeon conflicts (soft warning in flexible mode)
            if primary_surgeon:
                conflicting_surgeon_surgeries = Surgery.objects.filter(
                    primary_surgeon=primary_surgeon,
                    scheduled_date__lt=end_time,
                    scheduled_date__gte=scheduled_date
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if conflicting_surgeon_surgeries.exists():
                    conflict_msg = f"Warning: The primary surgeon is already booked for {conflicting_surgeon_surgeries.count()} overlapping surgery(ies)."
                    if allow_flexible_scheduling:
                        warnings.append(conflict_msg)
                    else:
                        raise forms.ValidationError(conflict_msg + " Check 'Skip Conflict Validation' to proceed anyway.")

            # Check for anesthetist conflicts (soft warning in flexible mode)
            if anesthetist:
                conflicting_anesthetist_surgeries = Surgery.objects.filter(
                    anesthetist=anesthetist,
                    scheduled_date__lt=end_time,
                    scheduled_date__gte=scheduled_date
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if conflicting_anesthetist_surgeries.exists():
                    conflict_msg = f"Warning: The anesthetist is already booked for {conflicting_anesthetist_surgeries.count()} overlapping surgery(ies)."
                    if allow_flexible_scheduling:
                        warnings.append(conflict_msg)
                    else:
                        raise forms.ValidationError(conflict_msg + " Check 'Skip Conflict Validation' to proceed anyway.")
            
            # Store warnings for display in template if any
            if warnings:
                cleaned_data['_warnings'] = warnings

        return cleaned_data


class SurgicalTeamForm(forms.ModelForm):
    class Meta:
        model = SurgicalTeam
        fields = ['staff', 'role', 'usage_notes']
        widgets = {
            'usage_notes': forms.Textarea(attrs={'rows': 1}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        role = cleaned_data.get('role')
        
        # If this is not marked for deletion and has data, validate required fields
        if not self.cleaned_data.get('DELETE', False):
            # Check if form has any data (not completely empty)
            has_data = any([staff, role, cleaned_data.get('usage_notes')])
            
            if has_data:
                if not staff:
                    self.add_error('staff', 'Please select a staff member.')
                if not role:
                    self.add_error('role', 'Please select a role.')
        
        return cleaned_data


class SurgicalTeamFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """Validate that at least one form has valid data if any forms are submitted."""
        if any(self.errors):
            return
        
        has_valid_forms = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # Check if form has meaningful data
                staff = form.cleaned_data.get('staff')
                role = form.cleaned_data.get('role')
                if staff and role:
                    has_valid_forms = True
                    break
        
        # Allow surgeries without team members (they can be added later)
        # Just ensure that if data is provided, it's complete

SurgicalTeamFormSet = inlineformset_factory(
    Surgery, SurgicalTeam,
    form=SurgicalTeamForm,
    formset=SurgicalTeamFormSet,
    extra=1,
    can_delete=True,
    fk_name='surgery'
)


class SurgicalEquipmentForm(forms.ModelForm):
    class Meta:
        model = SurgicalEquipment
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
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
            'notes': forms.Textarea(attrs={'rows': 1}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get('equipment')
        quantity_used = cleaned_data.get('quantity_used')
        
        # If this is not marked for deletion and has data, validate required fields
        if not self.cleaned_data.get('DELETE', False):
            # Check if form has any data (not completely empty)
            has_data = any([equipment, quantity_used, cleaned_data.get('notes')])
            
            if has_data:
                if not equipment:
                    self.add_error('equipment', 'Please select equipment.')
                if not quantity_used or quantity_used <= 0:
                    self.add_error('quantity_used', 'Please enter a valid quantity (greater than 0).')
        
        return cleaned_data


class EquipmentUsageFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """Validate that at least one form has valid data if any forms are submitted."""
        if any(self.errors):
            return
        
        has_valid_forms = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # Check if form has meaningful data
                equipment = form.cleaned_data.get('equipment')
                quantity_used = form.cleaned_data.get('quantity_used')
                if equipment and quantity_used:
                    has_valid_forms = True
                    break
        
        # Allow surgeries without equipment (they can be added later)
        # Just ensure that if data is provided, it's complete

EquipmentUsageFormSet = inlineformset_factory(
    Surgery, EquipmentUsage,
    form=EquipmentUsageForm,
    formset=EquipmentUsageFormSet,
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
            'delay_reason': forms.Textarea(attrs={'rows': 1}),
        }


class PostOperativeNoteForm(forms.ModelForm):
    class Meta:
        model = PostOperativeNote
        fields = ['notes', 'complications', 'follow_up_instructions']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'complications': forms.Textarea(attrs={'rows': 2}),
            'follow_up_instructions': forms.Textarea(attrs={'rows': 2}),
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
            'notes': forms.Textarea(attrs={'rows': 2}),
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