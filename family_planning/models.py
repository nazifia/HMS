from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class Family_planningRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='family_planning_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for family_planning module here
    # Specific fields
    method_used = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    compliance = models.BooleanField(default=True)
    refill_date = models.DateField(blank=True, null=True)
    partner_involvement = models.BooleanField(default=False)
    education_provided = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    discontinuation_reason = models.TextField(blank=True, null=True)

    
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
        return f"Family_planning Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Family_planning Record'
        verbose_name_plural = 'Family_planning Records'


class FamilyPlanningClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for family_planning records"""
    family_planning_record = models.ForeignKey(Family_planningRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='family_planning_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.family_planning_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Family_Planning Clinical Note"
        verbose_name_plural = "Family_Planning Clinical Notes"
