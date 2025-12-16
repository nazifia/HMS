import os

# Define the modules
modules = [
    'ophthalmic',
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

# Update system_overview.html
system_overview_path = os.path.join(base_path, 'templates', 'dashboard', 'system_overview.html')

# Read the existing system_overview.html file
with open(system_overview_path, 'r') as f:
    content = f.read()

# Find the position to insert the new module statistics
insert_pos = content.find('<!-- Inpatient App -->')  # After the inpatient section

# Create the new module statistics content
module_stats_content = ''
for module in modules:
    class_name = module.capitalize() if module != 'gynae_emergency' else 'GynaeEmergency'
    model_name = f"{class_name}Record" if module != 'gynae_emergency' else 'GynaeEmergencyRecord'
    
    module_stats_content += f'''                    <tr>
                        <td>{module.capitalize()} Records</td>
                        <td>{{{{ {module}_records_count }}}}</td>
                    </tr>
'''

# Insert the new module statistics
new_content = content[:insert_pos] + module_stats_content + content[insert_pos:]

# Write the updated content back to the file
with open(system_overview_path, 'w') as f:
    f.write(new_content)

# Update views.py to include the new module counts
views_path = os.path.join(base_path, 'dashboard', 'views.py')

# Read the existing views.py file
with open(views_path, 'r') as f:
    content = f.read()

# Find the position to insert the new imports
imports_pos = content.find('# Import models for new modules') + len('# Import models for new modules')

# Find the position to insert the new context variables
context_pos = content.find('context = {') + len('context = {')

# Create the new imports content
imports_content = ''
for module in modules:
    class_name = module.capitalize() if module != 'gynae_emergency' else 'GynaeEmergency'
    model_name = f"{class_name}Record" if module != 'gynae_emergency' else 'GynaeEmergencyRecord'
    imports_content += f'from {module}.models import {model_name}\n'

# Create the new context variables content
context_content = ''
for module in modules:
    class_name = module.capitalize() if module != 'gynae_emergency' else 'GynaeEmergency'
    model_name = f"{class_name}Record" if module != 'gynae_emergency' else 'GynaeEmergencyRecord'
    context_content += f"    {module}_records_count = {model_name}.objects.count()\n"

# Insert the new imports
content = content[:imports_pos] + imports_content + content[imports_pos:]

# Insert the new context variables
content = content[:context_pos] + context_content + content[context_pos:]

# Write the updated content back to the file
with open(views_path, 'w') as f:
    f.write(content)

print("System overview dashboard updated successfully!")