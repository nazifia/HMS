import os

# Define the modules with their specific fields
modules = {
    'ophthalmic': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'visual_acuity_right', 'visual_acuity_left',
            'refraction_right_sphere', 'refraction_right_cylinder', 'refraction_right_axis',
            'refraction_left_sphere', 'refraction_left_cylinder', 'refraction_left_axis',
            'iop_right', 'iop_left',
            'clinical_findings', 'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'ent': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'external_ear_right', 'external_ear_left',
            'ear_canal_right', 'ear_canal_left',
            'tympanic_membrane_right', 'tympanic_membrane_left',
            'nose_examination', 'throat_examination',
            'neck_examination',
            'audio_test_right', 'audio_test_left',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'oncology': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'cancer_type', 'stage', 'tumor_size',
            'metastasis',
            'treatment_protocol',
            'chemotherapy_cycle', 'radiation_dose',
            'surgery_details', 'biopsy_results',
            'oncology_marker',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'scbu': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'gestational_age', 'birth_weight',
            'apgar_score_1min', 'apgar_score_5min',
            'respiratory_support', 'ventilation_type',
            'feeding_method',
            'infection_status', 'antibiotic_name',
            'discharge_weight',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'anc': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'gravida', 'para', 'abortions',
            'lmp', 'edd',
            'fundal_height',
            'fetal_heartbeat', 'fetal_position',
            'blood_pressure', 'urine_protein',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'labor': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'onset_time', 'presentation',
            'fetal_heart_rate',
            'cervical_dilation', 'effacement',
            'rupture_of_membranes', 'rupture_time',
            'mode_of_delivery',
            'duration_first_stage', 'placenta_delivery_time',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'icu': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'gcs_score',
            'respiratory_rate', 'oxygen_saturation',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'body_temperature',
            'mechanical_ventilation',
            'vasopressor_use', 'dialysis_required',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
    },
    'family_planning': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
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
        ]
    },
    'gynae_emergency': {
        'fields': [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
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
        ]
    }
}

# Define the base path
base_path = os.getcwd()

# Update forms.py for each module
for module, details in modules.items():
    forms_path = os.path.join(base_path, module, 'forms.py')
    
    # Read the existing forms.py file
    with open(forms_path, 'r') as f:
        content = f.read()
    
    # Find the position to replace the fields
    fields_start = content.find('fields = [')
    fields_end = content.find(']', fields_start) + 1
    
    # Create the new fields content
    fields_content = 'fields = [\n'
    for field in details['fields']:
        fields_content += f"            '{field}',\n"
    fields_content += '        ]'
    
    # Replace the fields
    new_content = content[:fields_start] + fields_content + content[fields_end:]
    
    # Write the updated content back to the file
    with open(forms_path, 'w') as f:
        f.write(new_content)

print("Forms updated successfully for all modules!")