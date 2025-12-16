import os

# Define the modules with their specific fields
modules = {
    'ophthalmic': {
        'fields': [
            ('visual_acuity_right', "models.CharField(max_length=50, blank=True, null=True)"),
            ('visual_acuity_left', "models.CharField(max_length=50, blank=True, null=True)"),
            ('refraction_right_sphere', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)"),
            ('refraction_right_cylinder', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)"),
            ('refraction_right_axis', "models.IntegerField(blank=True, null=True)"),
            ('refraction_left_sphere', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)"),
            ('refraction_left_cylinder', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)"),
            ('refraction_left_axis', "models.IntegerField(blank=True, null=True)"),
            ('iop_right', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Intraocular Pressure (mmHg)')"),
            ('iop_left', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Intraocular Pressure (mmHg)')"),
            ('clinical_findings', "models.TextField(blank=True, null=True)"),
        ]
    },
    'ent': {
        'fields': [
            ('external_ear_right', "models.TextField(blank=True, null=True, help_text='External ear examination - Right')"),
            ('external_ear_left', "models.TextField(blank=True, null=True, help_text='External ear examination - Left')"),
            ('ear_canal_right', "models.TextField(blank=True, null=True, help_text='Ear canal examination - Right')"),
            ('ear_canal_left', "models.TextField(blank=True, null=True, help_text='Ear canal examination - Left')"),
            ('tympanic_membrane_right', "models.TextField(blank=True, null=True, help_text='Tympanic membrane examination - Right')"),
            ('tympanic_membrane_left', "models.TextField(blank=True, null=True, help_text='Tympanic membrane examination - Left')"),
            ('nose_examination', "models.TextField(blank=True, null=True, help_text='Nasal examination')"),
            ('throat_examination', "models.TextField(blank=True, null=True, help_text='Throat examination')"),
            ('neck_examination', "models.TextField(blank=True, null=True, help_text='Neck examination')"),
            ('audio_test_right', "models.TextField(blank=True, null=True, help_text='Audio test results - Right')"),
            ('audio_test_left', "models.TextField(blank=True, null=True, help_text='Audio test results - Left')"),
        ]
    },
    'oncology': {
        'fields': [
            ('cancer_type', "models.CharField(max_length=100, blank=True, null=True)"),
            ('stage', "models.CharField(max_length=20, blank=True, null=True)"),
            ('tumor_size', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Tumor size in cm')"),
            ('metastasis', "models.BooleanField(default=False)"),
            ('treatment_protocol', "models.TextField(blank=True, null=True)"),
            ('chemotherapy_cycle', "models.IntegerField(blank=True, null=True)"),
            ('radiation_dose', "models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text='Radiation dose in Gy')"),
            ('surgery_details', "models.TextField(blank=True, null=True)"),
            ('biopsy_results', "models.TextField(blank=True, null=True)"),
            ('oncology_marker', "models.TextField(blank=True, null=True)"),
        ]
    },
    'scbu': {
        'fields': [
            ('gestational_age', "models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True, help_text='Gestational age in weeks')"),
            ('birth_weight', "models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text='Birth weight in kg')"),
            ('apgar_score_1min', "models.IntegerField(blank=True, null=True, help_text='APGAR score at 1 minute')"),
            ('apgar_score_5min', "models.IntegerField(blank=True, null=True, help_text='APGAR score at 5 minutes')"),
            ('respiratory_support', "models.BooleanField(default=False)"),
            ('ventilation_type', "models.CharField(max_length=50, blank=True, null=True)"),
            ('feeding_method', "models.CharField(max_length=50, blank=True, null=True)"),
            ('infection_status', "models.BooleanField(default=False)"),
            ('antibiotic_name', "models.CharField(max_length=100, blank=True, null=True)"),
            ('discharge_weight', "models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text='Discharge weight in kg')"),
        ]
    },
    'anc': {
        'fields': [
            ('gravida', "models.IntegerField(blank=True, null=True)"),
            ('para', "models.IntegerField(blank=True, null=True)"),
            ('abortions', "models.IntegerField(blank=True, null=True)"),
            ('lmp', "models.DateField(blank=True, null=True, help_text='Last Menstrual Period')"),
            ('edd', "models.DateField(blank=True, null=True, help_text='Expected Date of Delivery')"),
            ('fundal_height', "models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Fundal height in cm')"),
            ('fetal_heartbeat', "models.BooleanField(default=False)"),
            ('fetal_position', "models.CharField(max_length=50, blank=True, null=True)"),
            ('blood_pressure', "models.CharField(max_length=20, blank=True, null=True)"),
            ('urine_protein', "models.CharField(max_length=20, blank=True, null=True)"),
        ]
    },
    'labor': {
        'fields': [
            ('onset_time', "models.DateTimeField(blank=True, null=True)"),
            ('presentation', "models.CharField(max_length=50, blank=True, null=True)"),
            ('fetal_heart_rate', "models.IntegerField(blank=True, null=True)"),
            ('cervical_dilation', "models.IntegerField(blank=True, null=True, help_text='Cervical dilation in cm')"),
            ('effacement', "models.IntegerField(blank=True, null=True, help_text='Effacement in percentage')"),
            ('rupture_of_membranes', "models.BooleanField(default=False)"),
            ('rupture_time', "models.DateTimeField(blank=True, null=True)"),
            ('mode_of_delivery', "models.CharField(max_length=50, blank=True, null=True)"),
            ('duration_first_stage', "models.DurationField(blank=True, null=True)"),
            ('placenta_delivery_time', "models.DateTimeField(blank=True, null=True)"),
        ]
    },
    'icu': {
        'fields': [
            ('gcs_score', "models.IntegerField(blank=True, null=True, help_text='Glasgow Coma Scale Score')"),
            ('respiratory_rate', "models.IntegerField(blank=True, null=True)"),
            ('oxygen_saturation', "models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Oxygen saturation in percentage')"),
            ('blood_pressure_systolic', "models.IntegerField(blank=True, null=True)"),
            ('blood_pressure_diastolic', "models.IntegerField(blank=True, null=True)"),
            ('heart_rate', "models.IntegerField(blank=True, null=True)"),
            ('body_temperature', "models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Body temperature in Celsius')"),
            ('mechanical_ventilation', "models.BooleanField(default=False)"),
            ('vasopressor_use', "models.BooleanField(default=False)"),
            ('dialysis_required', "models.BooleanField(default=False)"),
        ]
    },
    'family_planning': {
        'fields': [
            ('method_used', "models.CharField(max_length=100, blank=True, null=True)"),
            ('start_date', "models.DateField(blank=True, null=True)"),
            ('end_date', "models.DateField(blank=True, null=True)"),
            ('side_effects', "models.TextField(blank=True, null=True)"),
            ('compliance', "models.BooleanField(default=True)"),
            ('refill_date', "models.DateField(blank=True, null=True)"),
            ('partner_involvement', "models.BooleanField(default=False)"),
            ('education_provided', "models.TextField(blank=True, null=True)"),
            ('follow_up_date', "models.DateField(blank=True, null=True)"),
            ('discontinuation_reason', "models.TextField(blank=True, null=True)"),
        ]
    },
    'gynae_emergency': {
        'fields': [
            ('emergency_type', "models.CharField(max_length=100, blank=True, null=True)"),
            ('pain_level', "models.IntegerField(blank=True, null=True, help_text='Pain level on scale of 1-10')"),
            ('bleeding_amount', "models.CharField(max_length=50, blank=True, null=True)"),
            ('contractions', "models.BooleanField(default=False)"),
            ('contraction_frequency', "models.CharField(max_length=50, blank=True, null=True)"),
            ('rupture_of_membranes', "models.BooleanField(default=False)"),
            ('fetal_movement', "models.CharField(max_length=50, blank=True, null=True)"),
            ('vaginal_discharge', "models.TextField(blank=True, null=True)"),
            ('emergency_intervention', "models.TextField(blank=True, null=True)"),
            ('stabilization_status', "models.CharField(max_length=50, blank=True, null=True)"),
        ]
    }
}

# Define the base path
base_path = os.getcwd()

# Update models.py for each module
for module, details in modules.items():
    models_path = os.path.join(base_path, module, 'models.py')
    
    # Read the existing models.py file
    with open(models_path, 'r') as f:
        content = f.read()
    
    # Find the position to insert the new fields
    insert_pos = content.find('# Add specific fields for') + len('# Add specific fields for') + len(f' {module} module here')
    
    # Create the new fields content
    fields_content = '\n    # Specific fields\n'
    for field_name, field_def in details['fields']:
        fields_content += f'    {field_name} = {field_def}\n'
    
    # Insert the new fields
    new_content = content[:insert_pos] + fields_content + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(models_path, 'w') as f:
        f.write(new_content)

print("Models updated successfully for all modules!")