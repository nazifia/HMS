from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class LaborRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='labor_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for labor module here
    # Specific fields
    onset_time = models.DateTimeField(blank=True, null=True)
    presentation = models.CharField(max_length=50, blank=True, null=True)
    fetal_heart_rate = models.IntegerField(blank=True, null=True)
    cervical_dilation = models.IntegerField(blank=True, null=True, help_text='Cervical dilation in cm')
    effacement = models.IntegerField(blank=True, null=True, help_text='Effacement in percentage')
    rupture_of_membranes = models.BooleanField(default=False)
    rupture_time = models.DateTimeField(blank=True, null=True)
    mode_of_delivery = models.CharField(max_length=50, blank=True, null=True)
    duration_first_stage = models.DurationField(blank=True, null=True)
    placenta_delivery_time = models.DateTimeField(blank=True, null=True)

    
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
        return f"Labor Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Labor Record'
        verbose_name_plural = 'Labor Records'


class LaborClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for labor records"""
    labor_record = models.ForeignKey(LaborRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='labor_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.labor_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Labor Clinical Note"
        verbose_name_plural = "Labor Clinical Notes"
