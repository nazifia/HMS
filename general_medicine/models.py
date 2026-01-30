from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class GeneralMedicineRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='general_medicine_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # General Medicine specific fields
    chief_complaint = models.TextField(blank=True, null=True, help_text='Primary reason for visit')
    history_of_present_illness = models.TextField(blank=True, null=True)
    past_medical_history = models.TextField(blank=True, null=True)
    family_history = models.TextField(blank=True, null=True)
    social_history = models.TextField(blank=True, null=True)
    
    # Vital Signs
    temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Temperature in Celsius')
    blood_pressure_systolic = models.IntegerField(blank=True, null=True)
    blood_pressure_diastolic = models.IntegerField(blank=True, null=True)
    pulse_rate = models.IntegerField(blank=True, null=True, help_text='Beats per minute')
    respiratory_rate = models.IntegerField(blank=True, null=True, help_text='Breaths per minute')
    oxygen_saturation = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='SpO2 percentage')
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Weight in kg')
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Height in meters')
    bmi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Body Mass Index')
    
    # Physical Examination
    general_appearance = models.TextField(blank=True, null=True)
    cardiovascular_exam = models.TextField(blank=True, null=True)
    respiratory_exam = models.TextField(blank=True, null=True)
    gastrointestinal_exam = models.TextField(blank=True, null=True)
    neurological_exam = models.TextField(blank=True, null=True)
    
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
        return f"General Medicine Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'General Medicine Record'
        verbose_name_plural = 'General Medicine Records'


class GeneralMedicineClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for general medicine records"""
    general_medicine_record = models.ForeignKey(GeneralMedicineRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='general_medicine_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.general_medicine_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "General Medicine Clinical Note"
        verbose_name_plural = "General Medicine Clinical Notes"
