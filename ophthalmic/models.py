from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class OphthalmicRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ophthalmic_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for ophthalmic module here
    # Specific fields
    visual_acuity_right = models.CharField(max_length=50, blank=True, null=True, help_text='Visual acuity - Right eye')
    visual_acuity_left = models.CharField(max_length=50, blank=True, null=True, help_text='Visual acuity - Left eye')
    intraocular_pressure_right = models.CharField(max_length=50, blank=True, null=True, help_text='Intraocular pressure - Right eye')
    intraocular_pressure_left = models.CharField(max_length=50, blank=True, null=True, help_text='Intraocular pressure - Left eye')
    pupil_reaction_right = models.TextField(blank=True, null=True, help_text='Pupil reaction - Right eye')
    pupil_reaction_left = models.TextField(blank=True, null=True, help_text='Pupil reaction - Left eye')
    eyelid_exam_right = models.TextField(blank=True, null=True, help_text='Eyelid examination - Right eye')
    eyelid_exam_left = models.TextField(blank=True, null=True, help_text='Eyelid examination - Left eye')
    conjunctiva_exam_right = models.TextField(blank=True, null=True, help_text='Conjunctiva examination - Right eye')
    conjunctiva_exam_left = models.TextField(blank=True, null=True, help_text='Conjunctiva examination - Left eye')
    cornea_exam_right = models.TextField(blank=True, null=True, help_text='Cornea examination - Right eye')
    cornea_exam_left = models.TextField(blank=True, null=True, help_text='Cornea examination - Left eye')
    anterior_chamber_right = models.TextField(blank=True, null=True, help_text='Anterior chamber - Right eye')
    anterior_chamber_left = models.TextField(blank=True, null=True, help_text='Anterior chamber - Left eye')
    lens_exam_right = models.TextField(blank=True, null=True, help_text='Lens examination - Right eye')
    lens_exam_left = models.TextField(blank=True, null=True, help_text='Lens examination - Left eye')
    fundus_exam_right = models.TextField(blank=True, null=True, help_text='Fundus examination - Right eye')
    fundus_exam_left = models.TextField(blank=True, null=True, help_text='Fundus examination - Left eye')
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
        return f"Ophthalmic Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Ophthalmic Record'
        verbose_name_plural = 'Ophthalmic Records'

class OphthalmicClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for ophthalmic records"""
    ophthalmic_record = models.ForeignKey(OphthalmicRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ophthalmic_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.ophthalmic_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Ophthalmic Clinical Note"
        verbose_name_plural = "Ophthalmic Clinical Notes"
