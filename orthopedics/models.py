from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class OrthopedicsRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='orthopedics_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Orthopedics-specific fields
    injury_type = models.CharField(max_length=50, blank=True, null=True, help_text='Type of injury (e.g., Fracture, Dislocation, Sprain, Strain)')
    affected_body_part = models.CharField(max_length=50, blank=True, null=True, help_text='Affected body part (e.g., Spine, Hip, Knee, Shoulder, Wrist, Ankle)')
    fracture_type = models.CharField(max_length=50, blank=True, null=True, help_text='Type of fracture if applicable')
    fracture_classification = models.CharField(max_length=50, blank=True, null=True, help_text='Fracture classification (e.g., Simple, Compound, Comminuted, Greenstick)')
    pain_score = models.IntegerField(blank=True, null=True, help_text='Pain score (0-10 scale)')
    range_of_motion = models.TextField(blank=True, null=True, help_text='Range of motion assessment')
    neurovascular_status = models.TextField(blank=True, null=True, help_text='Neurovascular status assessment')
    imaging_results = models.TextField(blank=True, null=True, help_text='Imaging results (X-ray, CT, MRI findings)')
    procedure_done = models.TextField(blank=True, null=True, help_text='Procedure or surgery performed')
    implant_used = models.CharField(max_length=200, blank=True, null=True, help_text='Implant or fixation device used')
    rehabilitation_plan = models.TextField(blank=True, null=True, help_text='Rehabilitation and physiotherapy plan')
    weight_bearing_status = models.CharField(max_length=50, blank=True, null=True, help_text='Weight bearing status (e.g., Non-weight bearing, Partial, Full)')
    
    diagnosis = models.CharField(max_length=100, blank=True, null=True, help_text='Primary diagnosis')
    treatment_plan = models.TextField(blank=True, null=True, help_text='Treatment plan and recommendations')
    
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orthopedics Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Orthopedics Record'
        verbose_name_plural = 'Orthopedics Records'


class OrthopedicsClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for orthopedics records"""
    orthopedics_record = models.ForeignKey(OrthopedicsRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='orthopedics_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.orthopedics_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Orthopedics Clinical Note"
        verbose_name_plural = "Orthopedics Clinical Notes"
