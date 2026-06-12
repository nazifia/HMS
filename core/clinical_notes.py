"""Shared Nigerian clinical clerking (proforma) building blocks.

Nigerian medical practice documents an encounter using the full clerking
proforma rather than the American SOAP (Subjective/Objective/Assessment/Plan)
format. This module centralises that structure so every clinical-note model,
form and migration in the project stays consistent.

Clerking order:
    Presenting Complaint (PC)
    History of Presenting Complaint (HPC)
    Past Medical & Surgical History
    Drug History & Allergies
    Family & Social History
    Review of Systems (ROS)
    General Examination
    Systemic Examination
    Summary
    Provisional Diagnosis
    Differential Diagnosis
    Investigations
    Management / Treatment Plan
"""

from django import forms
from django.db import models


# Canonical clerking field order. Forms and templates iterate this list so the
# proforma always renders in the correct clinical sequence.
CLERKING_FIELDS = [
    'presenting_complaint',
    'history_of_presenting_complaint',
    'past_medical_surgical_history',
    'drug_history_allergies',
    'family_social_history',
    'review_of_systems',
    'general_examination',
    'systemic_examination',
    'summary',
    'provisional_diagnosis',
    'differential_diagnosis',
    'investigations',
    'management_plan',
]

CLERKING_LABELS = {
    'presenting_complaint': 'Presenting Complaint (PC)',
    'history_of_presenting_complaint': 'History of Presenting Complaint (HPC)',
    'past_medical_surgical_history': 'Past Medical & Surgical History',
    'drug_history_allergies': 'Drug History & Allergies',
    'family_social_history': 'Family & Social History',
    'review_of_systems': 'Review of Systems (ROS)',
    'general_examination': 'General Examination',
    'systemic_examination': 'Systemic Examination',
    'summary': 'Summary',
    'provisional_diagnosis': 'Provisional Diagnosis',
    'differential_diagnosis': 'Differential Diagnosis',
    'investigations': 'Investigations',
    'management_plan': 'Management / Treatment Plan',
}

_CLERKING_PLACEHOLDERS = {
    'presenting_complaint': 'Main complaint(s) in the patient\'s own words, with duration...',
    'history_of_presenting_complaint': 'Onset, course, associated symptoms, aggravating/relieving factors...',
    'past_medical_surgical_history': 'Previous illnesses, hospital admissions, surgeries, transfusions...',
    'drug_history_allergies': 'Current/recent medications, adherence and known allergies...',
    'family_social_history': 'Relevant family illnesses, occupation, lifestyle, social circumstances...',
    'review_of_systems': 'Systematic enquiry across body systems (CVS, RS, GIT, GUS, CNS, MSK)...',
    'general_examination': 'General condition, vital signs, pallor, jaundice, cyanosis, oedema...',
    'systemic_examination': 'Findings per system examined...',
    'summary': 'Brief summary of the case...',
    'provisional_diagnosis': 'Most likely diagnosis...',
    'differential_diagnosis': 'Other diagnoses being considered...',
    'investigations': 'Investigations requested and results where available...',
    'management_plan': 'Treatment, interventions, follow-up and patient education...',
}

# Number of textarea rows per field (larger for the narrative sections).
_CLERKING_ROWS = {
    'history_of_presenting_complaint': 4,
    'review_of_systems': 4,
    'general_examination': 3,
    'systemic_examination': 3,
    'management_plan': 4,
}


def clerking_widgets():
    """Return Bootstrap textarea widgets for every clerking field."""
    return {
        name: forms.Textarea(attrs={
            'class': 'form-control',
            'rows': _CLERKING_ROWS.get(name, 2),
            'placeholder': _CLERKING_PLACEHOLDERS[name],
        })
        for name in CLERKING_FIELDS
    }


class NigerianClerkingNote(models.Model):
    """Abstract base providing the full Nigerian clerking proforma fields.

    All fields are optional so notes can be written incrementally (e.g. a
    review visit may only update the management plan). Concrete models add
    their own record/consultation foreign key plus authorship/timestamps.
    """

    presenting_complaint = models.TextField(
        blank=True, default='', help_text="Main complaint(s) and duration")
    history_of_presenting_complaint = models.TextField(
        blank=True, default='', help_text="Detailed history of the presenting complaint")
    past_medical_surgical_history = models.TextField(
        blank=True, default='', help_text="Previous illnesses, admissions and surgeries")
    drug_history_allergies = models.TextField(
        blank=True, default='', help_text="Current medications and known allergies")
    family_social_history = models.TextField(
        blank=True, default='', help_text="Family illnesses and social circumstances")
    review_of_systems = models.TextField(
        blank=True, default='', help_text="Systematic enquiry across body systems")
    general_examination = models.TextField(
        blank=True, default='', help_text="General condition and vital signs")
    systemic_examination = models.TextField(
        blank=True, default='', help_text="System-by-system examination findings")
    summary = models.TextField(
        blank=True, default='', help_text="Brief case summary")
    provisional_diagnosis = models.TextField(
        blank=True, default='', help_text="Most likely diagnosis")
    differential_diagnosis = models.TextField(
        blank=True, default='', help_text="Other diagnoses under consideration")
    investigations = models.TextField(
        blank=True, default='', help_text="Investigations requested and results")
    management_plan = models.TextField(
        blank=True, default='', help_text="Treatment, interventions and follow-up")

    class Meta:
        abstract = True

    @property
    def has_clerking_content(self):
        return any(getattr(self, name) for name in CLERKING_FIELDS)


# Mapping used by data migrations to preserve legacy SOAP content when a model
# is converted from SOAP to the clerking proforma.
SOAP_TO_CLERKING = {
    'subjective': 'history_of_presenting_complaint',
    'objective': 'general_examination',
    'assessment': 'provisional_diagnosis',
    'plan': 'management_plan',
}


def migrate_soap_to_clerking(apps, app_label, model_name):
    """RunPython helper: copy legacy SOAP fields into clerking fields.

    Safe to call from a migration that has already added the clerking fields
    but not yet removed the SOAP fields.
    """
    Model = apps.get_model(app_label, model_name)
    for note in Model.objects.all():
        changed = False
        for soap_field, clerking_field in SOAP_TO_CLERKING.items():
            value = getattr(note, soap_field, '') or ''
            if value and not getattr(note, clerking_field, ''):
                setattr(note, clerking_field, value)
                changed = True
        if changed:
            note.save()
