from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class PediatricsRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='pediatrics_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Pediatrics specific fields
    age_category = models.CharField(max_length=20, blank=True, null=True, help_text='Infant, Toddler, Preschool, School-age, Adolescent')
    birth_weight = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text='Birth weight in kg')
    gestational_age = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True, help_text='Gestational age in weeks')
    
    # Growth Parameters
    current_weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Current weight in kg')
    current_height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Current height in cm')
    head_circumference = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Head circumference in cm')
    weight_for_age_percentile = models.IntegerField(blank=True, null=True)
    height_for_age_percentile = models.IntegerField(blank=True, null=True)
    weight_for_height_percentile = models.IntegerField(blank=True, null=True)
    
    # Vital Signs
    temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    respiratory_rate = models.IntegerField(blank=True, null=True, help_text='Breaths per minute (age-appropriate)')
    heart_rate = models.IntegerField(blank=True, null=True, help_text='Beats per minute (age-appropriate)')
    blood_pressure = models.CharField(max_length=20, blank=True, null=True, help_text='BP (if applicable)')
    
    # Developmental Assessment
    developmental_milestones = models.TextField(blank=True, null=True)
    developmental_concerns = models.TextField(blank=True, null=True)
    immunization_status = models.TextField(blank=True, null=True)
    
    # Nutrition
    feeding_pattern = models.TextField(blank=True, null=True)
    nutritional_status = models.CharField(max_length=50, blank=True, null=True, help_text='Normal, Underweight, Overweight, Obese')
    
    # Chief Complaint and History
    chief_complaint = models.TextField(blank=True, null=True)
    history_of_present_illness = models.TextField(blank=True, null=True)
    
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
        return f"Pediatrics Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Pediatrics Record'
        verbose_name_plural = 'Pediatrics Records'


class PediatricsClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for pediatrics records"""
    pediatrics_record = models.ForeignKey(PediatricsRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pediatrics_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.pediatrics_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pediatrics Clinical Note"
        verbose_name_plural = "Pediatrics Clinical Notes"
