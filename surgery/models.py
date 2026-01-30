from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class SurgeryRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='surgery_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgery_doctor')
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Surgery specific fields
    surgery_type = models.CharField(max_length=100, blank=True, null=True)
    surgery_date = models.DateTimeField(blank=True, null=True)
    procedure_code = models.CharField(max_length=50, blank=True, null=True)
    
    # Pre-operative assessment
    preop_diagnosis = models.TextField(blank=True, null=True, help_text='Pre-operative diagnosis')
    preop_assessment = models.TextField(blank=True, null=True)
    anesthesia_type = models.CharField(max_length=50, blank=True, null=True, help_text='General, Spinal, Local, etc.')
    
    # Surgical team
    surgeon = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_surgeon')
    assistant_surgeon = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='assistant_surgeon')
    anesthesiologist = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='anesthesiologist_doctor')
    
    # Operative findings
    operative_findings = models.TextField(blank=True, null=True)
    procedure_performed = models.TextField(blank=True, null=True)
    implants_used = models.TextField(blank=True, null=True, help_text='List of implants/prosthetics used')
    complications = models.TextField(blank=True, null=True)
    estimated_blood_loss = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text='Blood loss in mL')
    
    # Post-operative
    postop_diagnosis = models.TextField(blank=True, null=True)
    postop_instructions = models.TextField(blank=True, null=True)
    discharge_summary = models.TextField(blank=True, null=True)
    
    # Recovery tracking
    postop_day = models.IntegerField(blank=True, null=True, help_text='Post-operative day')
    wound_status = models.CharField(max_length=50, blank=True, null=True, help_text='Clean, Infected, etc.')
    pain_level = models.IntegerField(blank=True, null=True, help_text='Pain scale 1-10')
    mobility_status = models.CharField(max_length=50, blank=True, null=True)
    
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Surgery Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Surgery Record'
        verbose_name_plural = 'Surgery Records'


class SurgeryClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for surgery records"""
    surgery_record = models.ForeignKey(SurgeryRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='surgery_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.surgery_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Surgery Clinical Note"
        verbose_name_plural = "Surgery Clinical Notes"
