import os

# Define the modules
modules = [
    'ent',
    'oncology',
    'scbu',
    'anc',
    'labor',
    'icu',
    'family_planning',
    'gynae_emergency'
]

# Define the base path
base_path = os.getcwd()

# Update models.py for each module
for module in modules:
    models_path = os.path.join(base_path, module, 'models.py')
    
    # Read the existing models.py file
    with open(models_path, 'r') as f:
        content = f.read()
    
    # Find the position to insert the authorization_code field
    insert_pos = content.rfind('notes = models.TextField(blank=True, null=True)')
    
    # Create the authorization_code field content
    auth_field_content = '''
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    notes = models.TextField(blank=True, null=True)
'''
    
    # Insert the authorization_code field
    new_content = content[:insert_pos] + auth_field_content + content[insert_pos + len('notes = models.TextField(blank=True, null=True)'):]
    
    # Write the updated content back to the file
    with open(models_path, 'w') as f:
        f.write(new_content)

print("Authorization code support added to all modules successfully!")