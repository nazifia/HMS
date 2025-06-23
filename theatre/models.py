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
    
    def __str__(self):
        return self.name
    
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
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='primary_surgeries',
        limit_choices_to={'custom_profile__specialization__icontains': 'surgeon'}
    )
    anesthetist = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='anesthetist_surgeries',
        limit_choices_to={'custom_profile__specialization__icontains': 'anesthetist'}
    )
    scheduled_date = models.DateTimeField()
    expected_duration = models.DurationField()
    pre_surgery_notes = models.TextField(blank=True, null=True)
    post_surgery_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Surgery for {self.patient} - {self.surgery_type} ({self.get_status_display()})"
    
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
        return f"{self.staff} - {self.get_role_display()} for {self.surgery}"
    
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
    
    def __str__(self):
        return f"{self.name} ({self.get_equipment_type_display()})"
    
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