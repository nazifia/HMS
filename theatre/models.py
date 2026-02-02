from django.db import models
from django.conf import settings
from patients.models import Patient
from accounts.models import CustomUser

# Set app_label explicitly
app_label = 'theatre'

class OperationTheatre(models.Model):
    """Model representing an operation theatre in the hospital."""
    name = models.CharField(max_length=100)
    theatre_number = models.CharField(max_length=20, unique=True)
    floor = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(default=1)
    equipment_list = models.TextField(blank=True, null=True)
    last_sanitized = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.theatre_number})"
    
    class Meta:
        app_label = 'theatre'
        verbose_name = "Operation Theatre"
        verbose_name_plural = "Operation Theatres"
        ordering = ['theatre_number']


class SurgeryType(models.Model):
    """Model representing different types of surgeries."""
    RISK_LEVELS = (
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    average_duration = models.DurationField(help_text="Expected duration of surgery (HH:MM:SS)")
    preparation_time = models.DurationField(help_text="Time needed for preparation before surgery")
    recovery_time = models.DurationField(help_text="Expected recovery time after surgery")
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='medium')
    instructions = models.TextField(blank=True, null=True, help_text="Special instructions for this surgery type")
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Surgery fee in Naira (₦)")

    def __str__(self):
        return self.name

    def get_fee_display(self):
        """Return formatted fee with Naira symbol"""
        return f"₦{self.fee:,.2f}"

    class Meta:
        app_label = 'theatre'
        verbose_name = "Surgery Type"
        verbose_name_plural = "Surgery Types"
        ordering = ['name']


class Surgery(models.Model):
    """Model representing a scheduled or completed surgery."""
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
        ('pending', 'Pending'),
    )

    AUTHORIZATION_STATUS_CHOICES = (
        ('not_required', 'Not Required'),
        ('required', 'Required'),
        ('pending', 'Pending Authorization'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='surgeries')
    surgery_type = models.ForeignKey(SurgeryType, on_delete=models.PROTECT, related_name='surgeries')
    theatre = models.ForeignKey(OperationTheatre, on_delete=models.SET_NULL, null=True, related_name='surgeries')
    primary_surgeon = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='primary_surgeries',
        limit_choices_to={'profile__specialization__icontains': 'surgeon'}
    )
    anesthetist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='anesthetist_surgeries',
        limit_choices_to={'profile__specialization__icontains': 'anesthetist'}
    )
    scheduled_date = models.DateTimeField()
    expected_duration = models.DurationField()
    pre_surgery_notes = models.TextField(blank=True, null=True)
    post_surgery_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # NHIA Authorization fields
    requires_authorization = models.BooleanField(
        default=False,
        help_text="True if this NHIA patient surgery requires desk office authorization"
    )
    authorization_status = models.CharField(
        max_length=20,
        choices=AUTHORIZATION_STATUS_CHOICES,
        default='not_required',
        help_text="Status of authorization for this surgery"
    )
    authorization_code = models.ForeignKey(
        'nhia.AuthorizationCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='surgeries',
        help_text="Authorization code from desk office for NHIA patient surgery"
    )

    # Link to billing invoice
    invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='surgery_invoices')

    def __str__(self):
        # Create a mapping for status display values to avoid using get_status_display()
        status_display_map = {
            'scheduled': 'Scheduled',
            'in_progress': 'In Progress',
            'completed': 'Completed',
            'cancelled': 'Cancelled',
            'postponed': 'Postponed',
            'pending': 'Pending',
        }
        status_display = status_display_map.get(self.status, self.status)
        return f"Surgery for {self.patient} - {self.surgery_type} ({status_display})"

    def is_nhia_patient(self):
        """Check if the patient is an NHIA patient"""
        return hasattr(self.patient, 'nhia_info') and self.patient.nhia_info is not None

    def check_authorization_requirement(self):
        """
        Check if this surgery requires authorization.
        All NHIA patient surgeries require authorization.
        """
        if self.is_nhia_patient():
            self.requires_authorization = True
            if not self.authorization_code:
                self.authorization_status = 'required'
            else:
                self.authorization_status = 'authorized'
            return True
        else:
            self.requires_authorization = False
            self.authorization_status = 'not_required'
            return False

    def can_be_performed(self):
        """Check if surgery can be performed based on authorization"""
        # Check authorization requirement for NHIA patients
        if self.requires_authorization:
            if not self.authorization_code:
                return False, 'Desk office authorization required for NHIA patient surgery. Please obtain authorization code before proceeding.'
            elif not self.authorization_code.is_valid():
                return False, f'Authorization code is {self.authorization_code.status}. Please obtain a valid authorization code.'

        # Check if already completed or cancelled
        if self.status in ['completed', 'cancelled']:
            return False, f'Surgery is already {self.status}'

        return True, 'Surgery can be performed'

    def save(self, *args, **kwargs):
        # Auto-check authorization requirement on save
        self.check_authorization_requirement()
        super().save(*args, **kwargs)

    class Meta:
        app_label = 'theatre'
        verbose_name = "Surgery"
        verbose_name_plural = "Surgeries"
        ordering = ['-scheduled_date']


class SurgicalTeam(models.Model):
    """Model representing staff members assigned to a surgery."""
    ROLE_CHOICES = (
        ('surgeon', 'Surgeon'),
        ('assistant_surgeon', 'Assistant Surgeon'),
        ('anesthetist', 'Anesthetist'),
        ('nurse', 'Nurse'),
        ('technician', 'Technician'),
        ('other', 'Other'),
    )
    
    surgery = models.ForeignKey(Surgery, on_delete=models.CASCADE, related_name='team_members')
    staff = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='surgical_assignments')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    usage_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        # Create a mapping for role display values to avoid using get_role_display()
        role_display_map = {
            'surgeon': 'Surgeon',
            'assistant_surgeon': 'Assistant Surgeon',
            'anesthetist': 'Anesthetist',
            'nurse': 'Nurse',
            'technician': 'Technician',
            'other': 'Other',
        }
        role_display = role_display_map.get(self.role, self.role)
        return f"{self.staff} - {role_display} for {self.surgery}"
    
    class Meta:
        app_label = 'theatre'
        verbose_name = "Surgical Team Member"
        verbose_name_plural = "Surgical Team Members"
        unique_together = ('surgery', 'staff', 'role')


class SurgicalEquipment(models.Model):
    """Model representing equipment used in surgeries."""
    EQUIPMENT_TYPES = (
        ('instrument', 'Surgical Instrument'),
        ('monitor', 'Monitoring Equipment'),
        ('anesthesia', 'Anesthesia Equipment'),
        ('imaging', 'Imaging Equipment'),
        ('other', 'Other Equipment'),
    )
    
    name = models.CharField(max_length=100)
    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_TYPES)
    description = models.TextField(blank=True, null=True)
    quantity_available = models.PositiveIntegerField(default=1)
    is_available = models.BooleanField(default=True)
    last_maintenance_date = models.DateField(blank=True, null=True)
    next_maintenance_date = models.DateField(blank=True, null=True)
    last_calibration_date = models.DateField(blank=True, null=True)
    calibration_frequency = models.DurationField(blank=True, null=True, help_text="e.g., '365 00:00:00' for annual calibration")
    
    def __str__(self):
        # Create a mapping for equipment type display values to avoid using get_equipment_type_display()
        equipment_type_display_map = {
            'instrument': 'Surgical Instrument',
            'monitor': 'Monitoring Equipment',
            'anesthesia': 'Anesthesia Equipment',
            'imaging': 'Imaging Equipment',
            'other': 'Other Equipment',
        }
        equipment_type_display = equipment_type_display_map.get(self.equipment_type, self.equipment_type)
        return f"{self.name} ({equipment_type_display})"
    
    class Meta:
        app_label = 'theatre'
        verbose_name = "Surgical Equipment"
        verbose_name_plural = "Surgical Equipment"
        ordering = ['name']


class EquipmentUsage(models.Model):
    """Model representing equipment used in a specific surgery."""
    surgery = models.ForeignKey(Surgery, on_delete=models.CASCADE, related_name='equipment_used')
    equipment = models.ForeignKey(SurgicalEquipment, on_delete=models.CASCADE, related_name='usage_records')
    quantity_used = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.equipment} used in {self.surgery}"
    
    class Meta:
        verbose_name = "Equipment Usage"
        verbose_name_plural = "Equipment Usage Records"


class SurgerySchedule(models.Model):
    """Model representing the detailed schedule of a surgery."""
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
    )
    
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, related_name='schedule')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    pre_op_preparation_start = models.DateTimeField()
    post_op_recovery_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    delay_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Schedule for {self.surgery}"
    
    class Meta:
        verbose_name = "Surgery Schedule"
        verbose_name_plural = "Surgery Schedules"
        ordering = ['start_time']


class PostOperativeNote(models.Model):
    """Model representing post-operative notes for a surgery."""
    surgery = models.ForeignKey(Surgery, on_delete=models.CASCADE, related_name='post_op_notes')
    notes = models.TextField()
    complications = models.TextField(blank=True, null=True)
    follow_up_instructions = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='post_op_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Post-Op Notes for {self.surgery}"
    
    class Meta:
        verbose_name = "Post-Operative Note"
        verbose_name_plural = "Post-Operative Notes"
        ordering = ['-created_at']

class PreOperativeChecklist(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, related_name='pre_op_checklist')
    patient_identified = models.BooleanField(default=False)
    site_marked = models.BooleanField(default=False)
    anesthesia_safety_check_completed = models.BooleanField(default=False)
    surgical_safety_checklist_completed = models.BooleanField(default=False)
    consent_confirmed = models.BooleanField(default=False)
    allergies_reviewed = models.BooleanField(default=False)
    imaging_available = models.BooleanField(default=False)
    blood_products_available = models.BooleanField(default=False)
    antibiotics_administered = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pre-operative Checklist for {self.surgery}"

    class Meta:
        verbose_name = "Pre-Operative Checklist"
        verbose_name_plural = "Pre-Operative Checklists"

class SurgeryTypeEquipment(models.Model):
    """Model representing equipment required for a specific surgery type."""
    surgery_type = models.ForeignKey(SurgeryType, on_delete=models.CASCADE, related_name='required_equipment')
    equipment = models.ForeignKey(SurgicalEquipment, on_delete=models.CASCADE, related_name='surgery_types_required')
    quantity_required = models.PositiveIntegerField(default=1, help_text="Quantity of this equipment needed for the surgery")
    is_mandatory = models.BooleanField(default=True, help_text="If true, this equipment must be available for the surgery to proceed")
    notes = models.TextField(blank=True, null=True, help_text="Special instructions for using this equipment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.equipment.name} for {self.surgery_type.name} (x{self.quantity_required})"

    class Meta:
        verbose_name = "Surgery Type Equipment Requirement"
        verbose_name_plural = "Surgery Type Equipment Requirements"
        unique_together = ('surgery_type', 'equipment')
        ordering = ['surgery_type', 'equipment__name']


class SurgeryLog(models.Model):
    surgery = models.ForeignKey(Surgery, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=100) # e.g., 'Surgery Started', 'Complication Noted', 'Equipment Used'
    details = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.event_type} for {self.surgery}"

    class Meta:
        verbose_name = "Surgery Log Entry"
        verbose_name_plural = "Surgery Log Entries"
        ordering = ['timestamp']


class EquipmentMaintenanceLog(models.Model):
    """Model for tracking equipment maintenance and calibration history."""
    
    MAINTENANCE_TYPE_CHOICES = [
        ('maintenance', 'Routine Maintenance'),
        ('calibration', 'Calibration'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('replacement', 'Part Replacement'),
        ('upgrade', 'Upgrade/Modification'),
        ('cleaning', 'Deep Cleaning'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    equipment = models.ForeignKey(SurgicalEquipment, on_delete=models.CASCADE, related_name='maintenance_logs')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES, default='maintenance')
    
    # Dates
    scheduled_date = models.DateField(help_text="When maintenance is scheduled")
    completed_date = models.DateField(blank=True, null=True, help_text="When maintenance was actually completed")
    next_due_date = models.DateField(blank=True, null=True, help_text="When next maintenance is due")
    
    # Details
    description = models.TextField(help_text="Description of work performed or to be performed")
    findings = models.TextField(blank=True, null=True, help_text="Findings during maintenance")
    parts_replaced = models.TextField(blank=True, null=True, help_text="Parts that were replaced")
    
    # Status and costs
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Cost of maintenance (₦)")
    
    # Personnel
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='performed_maintenance'
    )
    
    # External service provider
    external_provider = models.CharField(max_length=200, blank=True, null=True, help_text="External service company")
    external_technician = models.CharField(max_length=200, blank=True, null=True, help_text="Technician name")
    
    # Documents
    certificate_number = models.CharField(max_length=100, blank=True, null=True, help_text="Calibration certificate number")
    document_file = models.FileField(upload_to='maintenance_docs/%Y/%m/', blank=True, null=True)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_maintenance_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_maintenance_type_display()} - {self.equipment.name} ({self.scheduled_date})"
    
    class Meta:
        verbose_name = "Equipment Maintenance Log"
        verbose_name_plural = "Equipment Maintenance Logs"
        ordering = ['-scheduled_date', '-created_at']
    
    def is_overdue(self):
        """Check if maintenance is overdue."""
        from django.utils import timezone
        if self.status == 'scheduled' and self.scheduled_date < timezone.now().date():
            return True
        return False
    
    def get_status_badge(self):
        """Return status badge class for templates."""
        badge_classes = {
            'scheduled': 'bg-info',
            'in_progress': 'bg-warning text-dark',
            'completed': 'bg-success',
            'overdue': 'bg-danger',
            'cancelled': 'bg-secondary',
        }
        return badge_classes.get(self.status, 'bg-secondary')