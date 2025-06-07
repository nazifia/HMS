from django.db import models
from django.utils import timezone
from django.conf import settings
User = settings.AUTH_USER_MODEL
from patients.models import Patient, Vitals
from appointments.models import Appointment

class ConsultingRoom(models.Model):
    """Model for hospital consulting rooms"""
    room_number = models.CharField(max_length=20, unique=True)
    floor = models.CharField(max_length=20)
    department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, related_name='consulting_rooms')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Room {self.room_number} - {self.department.name if self.department else 'Unassigned'}"

    class Meta:
        ordering = ['room_number']

class WaitingList(models.Model):
    """Model for patient waiting list"""
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='waiting_entries')
    consulting_room = models.ForeignKey(ConsultingRoom, on_delete=models.CASCADE, related_name='waiting_patients')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_patients')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='waiting_entry')
    check_in_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    priority = models.CharField(max_length=20, choices=(
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ), default='normal')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_waiting_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.get_full_name()} - Room {self.consulting_room.room_number} - {self.get_status_display()}"

    class Meta:
        ordering = ['priority', 'check_in_time']
        verbose_name_plural = "Waiting List Entries"

class Consultation(models.Model):
    """Model for doctor consultations"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='consultations')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_consultations')
    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation')
    consulting_room = models.ForeignKey(ConsultingRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultations')
    waiting_list_entry = models.OneToOneField(WaitingList, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation')
    vitals = models.ForeignKey(Vitals, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultations')
    consultation_date = models.DateTimeField(default=timezone.now)
    chief_complaint = models.TextField()
    symptoms = models.TextField()
    diagnosis = models.TextField(blank=True, null=True)
    consultation_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consultation for {self.patient.get_full_name()} by Dr. {self.doctor.get_full_name()} on {self.consultation_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-consultation_date']

class ConsultationNote(models.Model):
    """Model for additional consultation notes"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.consultation} by {self.created_by.get_full_name()}"

    class Meta:
        ordering = ['-created_at']

class Referral(models.Model):
    """Model for patient referrals to other doctors/specialists"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='referrals')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='referrals')
    referring_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_made')
    referred_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_received')
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    referral_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Referral for {self.patient.get_full_name()} from Dr. {self.referring_doctor.get_full_name()} to Dr. {self.referred_to.get_full_name()}"

    class Meta:
        ordering = ['-referral_date']

class SOAPNote(models.Model):
    """Model for SOAP (Subjective, Objective, Assessment, Plan) clinical notes"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='soap_notes', db_index=True)
    subjective = models.TextField()
    objective = models.TextField()
    assessment = models.TextField()
    plan = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_soap_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"SOAP Note for {self.consultation} by {self.created_by.get_full_name() if self.created_by else 'Unknown'} on {self.created_at.strftime('%Y-%m-%d')}"
