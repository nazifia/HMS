import os

# Define the modules with their specific fields
modules = {
    'ophthalmic': {
        'fields': [
            ('visual_acuity_right', 'Visual Acuity Right'),
            ('visual_acuity_left', 'Visual Acuity Left'),
            ('refraction_right_sphere', 'Refraction Right Sphere'),
            ('refraction_right_cylinder', 'Refraction Right Cylinder'),
            ('refraction_right_axis', 'Refraction Right Axis'),
            ('refraction_left_sphere', 'Refraction Left Sphere'),
            ('refraction_left_cylinder', 'Refraction Left Cylinder'),
            ('refraction_left_axis', 'Refraction Left Axis'),
            ('iop_right', 'IOP Right (mmHg)'),
            ('iop_left', 'IOP Left (mmHg)'),
            ('clinical_findings', 'Clinical Findings'),
        ]
    },
    'ent': {
        'fields': [
            ('external_ear_right', 'External Ear Right'),
            ('external_ear_left', 'External Ear Left'),
            ('ear_canal_right', 'Ear Canal Right'),
            ('ear_canal_left', 'Ear Canal Left'),
            ('tympanic_membrane_right', 'Tympanic Membrane Right'),
            ('tympanic_membrane_left', 'Tympanic Membrane Left'),
            ('nose_examination', 'Nose Examination'),
            ('throat_examination', 'Throat Examination'),
            ('neck_examination', 'Neck Examination'),
            ('audio_test_right', 'Audio Test Right'),
            ('audio_test_left', 'Audio Test Left'),
        ]
    },
    'oncology': {
        'fields': [
            ('cancer_type', 'Cancer Type'),
            ('stage', 'Stage'),
            ('tumor_size', 'Tumor Size (cm)'),
            ('metastasis', 'Metastasis'),
            ('treatment_protocol', 'Treatment Protocol'),
            ('chemotherapy_cycle', 'Chemotherapy Cycle'),
            ('radiation_dose', 'Radiation Dose (Gy)'),
            ('surgery_details', 'Surgery Details'),
            ('biopsy_results', 'Biopsy Results'),
            ('oncology_marker', 'Oncology Marker'),
        ]
    },
    'scbu': {
        'fields': [
            ('gestational_age', 'Gestational Age (weeks)'),
            ('birth_weight', 'Birth Weight (kg)'),
            ('apgar_score_1min', 'APGAR Score 1min'),
            ('apgar_score_5min', 'APGAR Score 5min'),
            ('respiratory_support', 'Respiratory Support'),
            ('ventilation_type', 'Ventilation Type'),
            ('feeding_method', 'Feeding Method'),
            ('infection_status', 'Infection Status'),
            ('antibiotic_name', 'Antibiotic Name'),
            ('discharge_weight', 'Discharge Weight (kg)'),
        ]
    },
    'anc': {
        'fields': [
            ('gravida', 'Gravida'),
            ('para', 'Para'),
            ('abortions', 'Abortions'),
            ('lmp', 'Last Menstrual Period'),
            ('edd', 'Expected Date of Delivery'),
            ('fundal_height', 'Fundal Height (cm)'),
            ('fetal_heartbeat', 'Fetal Heartbeat'),
            ('fetal_position', 'Fetal Position'),
            ('blood_pressure', 'Blood Pressure'),
            ('urine_protein', 'Urine Protein'),
        ]
    },
    'labor': {
        'fields': [
            ('onset_time', 'Onset Time'),
            ('presentation', 'Presentation'),
            ('fetal_heart_rate', 'Fetal Heart Rate'),
            ('cervical_dilation', 'Cervical Dilation (cm)'),
            ('effacement', 'Effacement (%)'),
            ('rupture_of_membranes', 'Rupture of Membranes'),
            ('rupture_time', 'Rupture Time'),
            ('mode_of_delivery', 'Mode of Delivery'),
            ('duration_first_stage', 'Duration First Stage'),
            ('placenta_delivery_time', 'Placenta Delivery Time'),
        ]
    },
    'icu': {
        'fields': [
            ('gcs_score', 'GCS Score'),
            ('respiratory_rate', 'Respiratory Rate'),
            ('oxygen_saturation', 'Oxygen Saturation (%)'),
            ('blood_pressure_systolic', 'Blood Pressure Systolic'),
            ('blood_pressure_diastolic', 'Blood Pressure Diastolic'),
            ('heart_rate', 'Heart Rate'),
            ('body_temperature', 'Body Temperature (°C)'),
            ('mechanical_ventilation', 'Mechanical Ventilation'),
            ('vasopressor_use', 'Vasopressor Use'),
            ('dialysis_required', 'Dialysis Required'),
        ]
    },
    'family_planning': {
        'fields': [
            ('method_used', 'Method Used'),
            ('start_date', 'Start Date'),
            ('end_date', 'End Date'),
            ('side_effects', 'Side Effects'),
            ('compliance', 'Compliance'),
            ('refill_date', 'Refill Date'),
            ('partner_involvement', 'Partner Involvement'),
            ('education_provided', 'Education Provided'),
            ('follow_up_date', 'Follow Up Date'),
            ('discontinuation_reason', 'Discontinuation Reason'),
        ]
    },
    'gynae_emergency': {
        'fields': [
            ('emergency_type', 'Emergency Type'),
            ('pain_level', 'Pain Level (1-10)'),
            ('bleeding_amount', 'Bleeding Amount'),
            ('contractions', 'Contractions'),
            ('contraction_frequency', 'Contraction Frequency'),
            ('rupture_of_membranes', 'Rupture of Membranes'),
            ('fetal_movement', 'Fetal Movement'),
            ('vaginal_discharge', 'Vaginal Discharge'),
            ('emergency_intervention', 'Emergency Intervention'),
            ('stabilization_status', 'Stabilization Status'),
        ]
    }
}

# Define the base path
base_path = os.getcwd()

# Update form templates for each module
for module, details in modules.items():
    templates_path = os.path.join(base_path, module, 'templates', module)
    
    # Read the existing form template
    form_template = os.path.join(templates_path, f'{module}_record_form.html')
    with open(form_template, 'r') as f:
        content = f.read()
    
    # Find the position to insert the new fields
    insert_pos = content.find('<div class="form-group">')  # After the visit_date field
    
    # Create the new fields content
    fields_content = '\n'
    for field_name, field_label in details['fields']:
        fields_content += f'''                <div class="form-group">
                    <label for="{{{{ form.{field_name}.id_for_label }}}}">{field_label}</label>
                    {{{{ form.{field_name}|add_class:"form-control" }}}}
                </div>
                
'''
    
    # Insert the new fields
    new_content = content[:insert_pos] + fields_content + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(form_template, 'w') as f:
        f.write(new_content)
    
    # Update detail template
    detail_template = os.path.join(templates_path, f'{module}_record_detail.html')
    with open(detail_template, 'r') as f:
        content = f.read()
    
    # Find the position to insert the new fields
    insert_pos = content.find('<!-- Chief Complaint -->')
    
    # Create the new fields content
    fields_content = f'''    <!-- Specific Fields -->
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">{module.capitalize()} Specific Fields</h6>
        </div>
        <div class="card-body">
'''
    for field_name, field_label in details['fields']:
        fields_content += f'''            <div class="row">
                <div class="col-md-4">
                    <p><strong>{field_label}:</strong></p>
                </div>
                <div class="col-md-8">
                    <p>{{{{ record.{field_name}|default:"Not recorded" }}}}</p>
                </div>
            </div>
'''
    
    fields_content += '''        </div>
    </div>
'''
    
    # Insert the new fields
    new_content = content[:insert_pos] + fields_content + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(detail_template, 'w') as f:
        f.write(new_content)

print("Templates updated successfully for all modules!")