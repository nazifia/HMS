from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class EntRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ent_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for ent module here
    # Specific fields
    external_ear_right = models.TextField(blank=True, null=True, help_text='External ear examination - Right')
    external_ear_left = models.TextField(blank=True, null=True, help_text='External ear examination - Left')
    ear_canal_right = models.TextField(blank=True, null=True, help_text='Ear canal examination - Right')
    ear_canal_left = models.TextField(blank=True, null=True, help_text='Ear canal examination - Left')
    tympanic_membrane_right = models.TextField(blank=True, null=True, help_text='Tympanic membrane examination - Right')
    tympanic_membrane_left = models.TextField(blank=True, null=True, help_text='Tympanic membrane examination - Left')
    nose_examination = models.TextField(blank=True, null=True, help_text='Nasal examination')
    throat_examination = models.TextField(blank=True, null=True, help_text='Throat examination')
    neck_examination = models.TextField(blank=True, null=True, help_text='Neck examination')
    audio_test_right = models.TextField(blank=True, null=True, help_text='Audio test results - Right')
    audio_test_left = models.TextField(blank=True, null=True, help_text='Audio test results - Left')
    
    chief_complaint = models.TextField(blank=True, null=True, help_text='Chief complaint from patient')
    history_of_present_illness = models.TextField(blank=True, null=True, help_text='History of present illness')
    
    diagnosis = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    notes = models.TextField(blank=True, null=True)

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ent Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Ent Record'
        verbose_name_plural = 'Ent Records'


class EntClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for ent records"""
    ent_record = models.ForeignKey(EntRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ent_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.ent_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Ent Clinical Note"
        verbose_name_plural = "Ent Clinical Notes"
