from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class AncRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='anc_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for anc module here
    # Specific fields
    gravida = models.IntegerField(blank=True, null=True)
    para = models.IntegerField(blank=True, null=True)
    abortions = models.IntegerField(blank=True, null=True)
    lmp = models.DateField(blank=True, null=True, help_text='Last Menstrual Period')
    edd = models.DateField(blank=True, null=True, help_text='Expected Date of Delivery')
    fundal_height = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Fundal height in cm')
    fetal_heartbeat = models.BooleanField(default=False)
    fetal_position = models.CharField(max_length=50, blank=True, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True, null=True)
    urine_protein = models.CharField(max_length=20, blank=True, null=True)

    
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
        return f"Anc Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Anc Record'
        verbose_name_plural = 'Anc Records'


class AncClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for anc records"""
    anc_record = models.ForeignKey(AncRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='anc_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.anc_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Anc Clinical Note"
        verbose_name_plural = "Anc Clinical Notes"
