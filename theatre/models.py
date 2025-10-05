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
    
    # Authorization code for NHIA patients
    authorization_code = models.ForeignKey('nhia.AuthorizationCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries')
    
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
        }
        status_display = status_display_map.get(self.status, self.status)
        return f"Surgery for {self.patient} - {self.surgery_type} ({status_display})"
    
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