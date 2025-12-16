import os
from datetime import datetime

# Define the modules with their specific fields
modules = {
    'ophthalmic': {
        'fields': [
            ('visual_acuity_right', "models.CharField(blank=True, max_length=50, null=True)"),
            ('visual_acuity_left', "models.CharField(blank=True, max_length=50, null=True)"),
            ('refraction_right_sphere', "models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)"),
            ('refraction_right_cylinder', "models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)"),
            ('refraction_right_axis', "models.IntegerField(blank=True, null=True)"),
            ('refraction_left_sphere', "models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)"),
            ('refraction_left_cylinder', "models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)"),
            ('refraction_left_axis', "models.IntegerField(blank=True, null=True)"),
            ('iop_right', "models.DecimalField(blank=True, decimal_places=2, help_text='Intraocular Pressure (mmHg)', max_digits=5, null=True)"),
            ('iop_left', "models.DecimalField(blank=True, decimal_places=2, help_text='Intraocular Pressure (mmHg)', max_digits=5, null=True)"),
            ('clinical_findings', "models.TextField(blank=True, null=True)"),
        ]
    },
    'ent': {
        'fields': [
            ('external_ear_right', "models.TextField(blank=True, help_text='External ear examination - Right', null=True)"),
            ('external_ear_left', "models.TextField(blank=True, help_text='External ear examination - Left', null=True)"),
            ('ear_canal_right', "models.TextField(blank=True, help_text='Ear canal examination - Right', null=True)"),
            ('ear_canal_left', "models.TextField(blank=True, help_text='Ear canal examination - Left', null=True)"),
            ('tympanic_membrane_right', "models.TextField(blank=True, help_text='Tympanic membrane examination - Right', null=True)"),
            ('tympanic_membrane_left', "models.TextField(blank=True, help_text='Tympanic membrane examination - Left', null=True)"),
            ('nose_examination', "models.TextField(blank=True, help_text='Nasal examination', null=True)"),
            ('throat_examination', "models.TextField(blank=True, help_text='Throat examination', null=True)"),
            ('neck_examination', "models.TextField(blank=True, help_text='Neck examination', null=True)"),
            ('audio_test_right', "models.TextField(blank=True, help_text='Audio test results - Right', null=True)"),
            ('audio_test_left', "models.TextField(blank=True, help_text='Audio test results - Left', null=True)"),
        ]
    },
    'oncology': {
        'fields': [
            ('cancer_type', "models.CharField(blank=True, max_length=100, null=True)"),
            ('stage', "models.CharField(blank=True, max_length=20, null=True)"),
            ('tumor_size', "models.DecimalField(blank=True, decimal_places=2, help_text='Tumor size in cm', max_digits=5, null=True)"),
            ('metastasis', "models.BooleanField(default=False)"),
            ('treatment_protocol', "models.TextField(blank=True, null=True)"),
            ('chemotherapy_cycle', "models.IntegerField(blank=True, null=True)"),
            ('radiation_dose', "models.DecimalField(blank=True, decimal_places=2, help_text='Radiation dose in Gy', max_digits=6, null=True)"),
            ('surgery_details', "models.TextField(blank=True, null=True)"),
            ('biopsy_results', "models.TextField(blank=True, null=True)"),
            ('oncology_marker', "models.TextField(blank=True, null=True)"),
        ]
    },
    'scbu': {
        'fields': [
            ('gestational_age', "models.DecimalField(blank=True, decimal_places=1, help_text='Gestational age in weeks', max_digits=3, null=True)"),
            ('birth_weight', "models.DecimalField(blank=True, decimal_places=2, help_text='Birth weight in kg', max_digits=4, null=True)"),
            ('apgar_score_1min', "models.IntegerField(blank=True, help_text='APGAR score at 1 minute', null=True)"),
            ('apgar_score_5min', "models.IntegerField(blank=True, help_text='APGAR score at 5 minutes', null=True)"),
            ('respiratory_support', "models.BooleanField(default=False)"),
            ('ventilation_type', "models.CharField(blank=True, max_length=50, null=True)"),
            ('feeding_method', "models.CharField(blank=True, max_length=50, null=True)"),
            ('infection_status', "models.BooleanField(default=False)"),
            ('antibiotic_name', "models.CharField(blank=True, max_length=100, null=True)"),
            ('discharge_weight', "models.DecimalField(blank=True, decimal_places=2, help_text='Discharge weight in kg', max_digits=4, null=True)"),
        ]
    },
    'anc': {
        'fields': [
            ('gravida', "models.IntegerField(blank=True, null=True)"),
            ('para', "models.IntegerField(blank=True, null=True)"),
            ('abortions', "models.IntegerField(blank=True, null=True)"),
            ('lmp', "models.DateField(blank=True, help_text='Last Menstrual Period', null=True)"),
            ('edd', "models.DateField(blank=True, help_text='Expected Date of Delivery', null=True)"),
            ('fundal_height', "models.DecimalField(blank=True, decimal_places=1, help_text='Fundal height in cm', max_digits=4, null=True)"),
            ('fetal_heartbeat', "models.BooleanField(default=False)"),
            ('fetal_position', "models.CharField(blank=True, max_length=50, null=True)"),
            ('blood_pressure', "models.CharField(blank=True, max_length=20, null=True)"),
            ('urine_protein', "models.CharField(blank=True, max_length=20, null=True)"),
        ]
    },
    'labor': {
        'fields': [
            ('onset_time', "models.DateTimeField(blank=True, null=True)"),
            ('presentation', "models.CharField(blank=True, max_length=50, null=True)"),
            ('fetal_heart_rate', "models.IntegerField(blank=True, null=True)"),
            ('cervical_dilation', "models.IntegerField(blank=True, help_text='Cervical dilation in cm', null=True)"),
            ('effacement', "models.IntegerField(blank=True, help_text='Effacement in percentage', null=True)"),
            ('rupture_of_membranes', "models.BooleanField(default=False)"),
            ('rupture_time', "models.DateTimeField(blank=True, null=True)"),
            ('mode_of_delivery', "models.CharField(blank=True, max_length=50, null=True)"),
            ('duration_first_stage', "models.DurationField(blank=True, null=True)"),
            ('placenta_delivery_time', "models.DateTimeField(blank=True, null=True)"),
        ]
    },
    'icu': {
        'fields': [
            ('gcs_score', "models.IntegerField(blank=True, help_text='Glasgow Coma Scale Score', null=True)"),
            ('respiratory_rate', "models.IntegerField(blank=True, null=True)"),
            ('oxygen_saturation', "models.DecimalField(blank=True, decimal_places=2, help_text='Oxygen saturation in percentage', max_digits=5, null=True)"),
            ('blood_pressure_systolic', "models.IntegerField(blank=True, null=True)"),
            ('blood_pressure_diastolic', "models.IntegerField(blank=True, null=True)"),
            ('heart_rate', "models.IntegerField(blank=True, null=True)"),
            ('body_temperature', "models.DecimalField(blank=True, decimal_places=1, help_text='Body temperature in Celsius', max_digits=4, null=True)"),
            ('mechanical_ventilation', "models.BooleanField(default=False)"),
            ('vasopressor_use', "models.BooleanField(default=False)"),
            ('dialysis_required', "models.BooleanField(default=False)"),
        ]
    },
    'family_planning': {
        'fields': [
            ('method_used', "models.CharField(blank=True, max_length=100, null=True)"),
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
            ('emergency_type', "models.CharField(blank=True, max_length=100, null=True)"),
            ('pain_level', "models.IntegerField(blank=True, help_text='Pain level on scale of 1-10', null=True)"),
            ('bleeding_amount', "models.CharField(blank=True, max_length=50, null=True)"),
            ('contractions', "models.BooleanField(default=False)"),
            ('contraction_frequency', "models.CharField(blank=True, max_length=50, null=True)"),
            ('rupture_of_membranes', "models.BooleanField(default=False)"),
            ('fetal_movement', "models.CharField(blank=True, max_length=50, null=True)"),
            ('vaginal_discharge', "models.TextField(blank=True, null=True)"),
            ('emergency_intervention', "models.TextField(blank=True, null=True)"),
            ('stabilization_status', "models.CharField(blank=True, max_length=50, null=True)"),
        ]
    }
}

# Define the base path
base_path = os.getcwd()

# Get current timestamp
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

# Update migration files for each module
for module, details in modules.items():
    migrations_path = os.path.join(base_path, module, 'migrations')
    
    # Read the existing migration file
    migration_file = os.path.join(migrations_path, '0001_initial.py')
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Find the position to insert the new fields
    insert_pos = content.find('chief_complaint = models.TextField(blank=True, null=True)')
    if insert_pos == -1:
        insert_pos = content.find('fields=[') + len('fields=[')
    
    # Create the new fields content
    fields_content = ''
    for field_name, field_def in details['fields']:
        fields_content += f"                ('{field_name}', {field_def}),\n"
    
    # Insert the new fields
    new_content = content[:insert_pos] + fields_content + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(migration_file, 'w') as f:
        f.write(new_content)

print("Migration files updated successfully for all modules!")