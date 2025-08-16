import os

# Define the modules with their specific fields
modules = {
    'ophthalmic': {
        'model': 'OphthalmicRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'visual_acuity_right', 'visual_acuity_left',
            'refraction_right_sphere', 'refraction_right_cylinder', 'refraction_right_axis',
            'refraction_left_sphere', 'refraction_left_cylinder', 'refraction_left_axis',
            'iop_right', 'iop_left',
            'clinical_findings', 'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'visual_acuity_right', 'visual_acuity_left',
            'clinical_findings', 'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'ent': {
        'model': 'EntRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'external_ear_right', 'external_ear_left',
            'ear_canal_right', 'ear_canal_left',
            'tympanic_membrane_right', 'tympanic_membrane_left',
            'nose_examination', 'throat_examination',
            'neck_examination',
            'audio_test_right', 'audio_test_left',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'external_ear_right', 'external_ear_left',
            'ear_canal_right', 'ear_canal_left',
            'tympanic_membrane_right', 'tympanic_membrane_left',
            'nose_examination', 'throat_examination',
            'neck_examination',
            'audio_test_right', 'audio_test_left',
            'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'oncology': {
        'model': 'OncologyRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'cancer_type', 'stage', 'tumor_size',
            'metastasis',
            'treatment_protocol',
            'chemotherapy_cycle', 'radiation_dose',
            'surgery_details', 'biopsy_results',
            'oncology_marker',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'treatment_protocol', 'surgery_details', 'biopsy_results',
            'oncology_marker', 'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'scbu': {
        'model': 'ScbuRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'gestational_age', 'birth_weight',
            'apgar_score_1min', 'apgar_score_5min',
            'respiratory_support', 'ventilation_type',
            'feeding_method',
            'infection_status', 'antibiotic_name',
            'discharge_weight',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'ventilation_type', 'feeding_method', 'antibiotic_name',
            'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'anc': {
        'model': 'AncRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'gravida', 'para', 'abortions',
            'lmp', 'edd',
            'fundal_height',
            'fetal_heartbeat', 'fetal_position',
            'blood_pressure', 'urine_protein',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'fetal_position', 'blood_pressure', 'urine_protein',
            'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'labor': {
        'model': 'LaborRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'onset_time', 'presentation',
            'fetal_heartbeat', 'fetal_heart_rate',
            'cervical_dilation', 'effacement',
            'rupture_of_membranes', 'rupture_time',
            'mode_of_delivery',
            'duration_first_stage', 'placenta_delivery_time',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'presentation', 'mode_of_delivery',
            'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'icu': {
        'model': 'IcuRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'gcs_score',
            'respiratory_rate', 'oxygen_saturation',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'body_temperature',
            'mechanical_ventilation',
            'vasopressor_use', 'dialysis_required',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'family_planning': {
        'model': 'Family_planningRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'method_used', 'start_date', 'end_date',
            'side_effects',
            'compliance',
            'refill_date',
            'partner_involvement',
            'education_provided',
            'follow_up_date',
            'discontinuation_reason',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'method_used', 'side_effects', 'education_provided',
            'discontinuation_reason', 'diagnosis', 'treatment_plan', 'notes'
        ]
    },
    'gynae_emergency': {
        'model': 'Gynae_emergencyRecord',
        'fields': [
            'patient', 'doctor', 'visit_date',
            'emergency_type',
            'pain_level',
            'bleeding_amount',
            'contractions', 'contraction_frequency',
            'rupture_of_membranes',
            'fetal_movement',
            'vaginal_discharge',
            'emergency_intervention',
            'stabilization_status',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ],
        'textareas': [
            'emergency_type', 'bleeding_amount', 'contraction_frequency',
            'fetal_movement', 'vaginal_discharge', 'emergency_intervention',
            'stabilization_status', 'diagnosis', 'treatment_plan', 'notes'
        ]
    }
}

# Define the base path
base_path = os.getcwd()

# Update forms.py for each module
for module, details in modules.items():
    forms_path = os.path.join(base_path, module, 'forms.py')
    
    # Create the textareas widgets
    textareas = ''
    for field in details['textareas']:
        if field in ['chief_complaint', 'history_of_present_illness', 'diagnosis', 'treatment_plan', 'notes']:
            textareas += f"            '{field}': forms.Textarea(attrs={{'rows': 3}}),\
"
        elif field in ['visual_acuity_right', 'visual_acuity_left']:
            textareas += f"            '{field}': forms.Textarea(attrs={{'rows': 2}}),\
"
        else:
            textareas += f"            '{field}': forms.Textarea(attrs={{'rows': 2}}),\
"
    
    # Create the form content
    form_content = f'''from django import forms
from .models import {details['model']}
from django.utils import timezone


class {details['model']}Form(forms.ModelForm):
    class Meta:
        model = {details['model']}
        fields = [
'''
    
    for field in details['fields']:
        form_content += f"            '{field}',\
"
    
    form_content += f'''        ]
        widgets = {{
            'visit_date': forms.DateTimeInput(attrs={{'type': 'datetime-local'}}),
            'follow_up_date': forms.DateInput(attrs={{'type': 'date'}}),
{textareas}        }}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
'''
    
    # Write the form content to the file
    with open(forms_path, 'w') as f:
        f.write(form_content)

print("Forms updated successfully for all modules!")