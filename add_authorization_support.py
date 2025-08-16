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

# Update forms.py for each module
for module in modules:
    forms_path = os.path.join(base_path, module, 'forms.py')
    
    # Read the existing forms.py file
    with open(forms_path, 'r') as f:
        content = f.read()
    
    # Update the fields list to include authorization_code
    fields_start = content.find('fields = [')
    fields_end = content.find(']', fields_start) + 1
    
    # Add authorization_code to the fields list
    fields_content = content[fields_start:fields_end]
    if 'authorization_code' not in fields_content:
        fields_content = fields_content[:-1] + "            'authorization_code',
        ]"
    
    # Update the widgets to include authorization_code
    widgets_start = content.find('widgets = {')
    widgets_end = content.find('}', widgets_start) + 1
    
    # Add authorization_code widget
    widgets_content = content[widgets_start:widgets_end]
    if 'authorization_code' not in widgets_content:
        widgets_insert_pos = widgets_content.rfind('}')
        widgets_content = widgets_content[:widgets_insert_pos] + "            'authorization_code': forms.TextInput(attrs={'class': 'form-control'}),
" + widgets_content[widgets_insert_pos:]
    
    # Replace the fields and widgets
    new_content = content[:fields_start] + fields_content + content[fields_end:widgets_start] + widgets_content + content[widgets_end:]
    
    # Write the updated content back to the file
    with open(forms_path, 'w') as f:
        f.write(new_content)

# Update views.py for each module
for module in modules:
    views_path = os.path.join(base_path, module, 'views.py')
    
    # Read the existing views.py file
    with open(views_path, 'r') as f:
        content = f.read()
    
    # Add imports for AuthorizationCode and billing models
    imports_insert_pos = content.find('from nhia.models import AuthorizationCode')
    if imports_insert_pos == -1:
        imports_insert_pos = content.find('from doctors.models import Doctor')
        imports_content = '''from doctors.models import Doctor
from billing.models import Invoice, Service, Payment
from nhia.models import AuthorizationCode
'''
        new_content = content[:imports_insert_pos] + imports_content + content[imports_insert_pos:]
    else:
        new_content = content
    
    # Add authorization code handling to create view
    create_view_start = new_content.find(f'def create_{module}_record(request):')
    if create_view_start != -1:
        create_view_end = new_content.find('context = {', create_view_start)
        create_view_content = new_content[create_view_start:create_view_end]
        
        # Add authorization code handling
        auth_handling = '''
        if form.is_valid():
            # Handle authorization code if provided
            authorization_code = None
            authorization_code_input = form.cleaned_data.get('authorization_code')
            
            if authorization_code_input:
                try:
                    # Try to get the authorization code
                    authorization_code = AuthorizationCode.objects.get(code=authorization_code_input)
                    
                    # Check if the authorization code is valid
                    if not authorization_code.is_valid():
                        messages.error(request, 'The provided authorization code is not valid or has expired.')
                        return render(request, \'''' + module + '/' + module + '''_record_form.html', {'form': form, 'title': 'Create ''' + module.capitalize() + ''' Record'})
                    
                    # Check if the authorization code is for the correct service
                    if authorization_code.service_type not in ['''' + module + '''', 'general']:
                        messages.error(request, 'The provided authorization code is not valid for ''' + module + ''' services.')
                        return render(request, \'''' + module + '/' + module + '''_record_form.html', {'form': form, 'title': 'Create ''' + module.capitalize() + ''' Record'})
                        
                except AuthorizationCode.DoesNotExist:
                    messages.error(request, 'The provided authorization code does not exist.')
                    return render(request, \'''' + module + '/' + module + '''_record_form.html', {'form': form, 'title': 'Create ''' + module.capitalize() + ''' Record'})
            
            # Save the record
            record = form.save()
            
            # Mark authorization code as used if provided
            if authorization_code:
                authorization_code.mark_as_used("''' + module.capitalize() + ''' Record #" + str(record.id))
                messages.success(request, f''' + module.capitalize() + ''' record created successfully. Authorization code {authorization_code.code} has been marked as used.')
            else:
                messages.success(request, ''' + module.capitalize() + ''' record created successfully.')
            
            return redirect(\'''' + module + ':' + module + '''_record_detail', record_id=record.id)
'''
        
        new_content = new_content[:create_view_start] + create_view_content.replace('if form.is_valid():', auth_handling) + new_content[create_view_end:]
    
    # Add authorization code handling to edit view
    edit_view_start = new_content.find(f'def edit_{module}_record(request, record_id):')
    if edit_view_start != -1:
        edit_view_end = new_content.find('context = {', edit_view_start)
        edit_view_content = new_content[edit_view_start:edit_view_end]
        
        # Add authorization code handling
        auth_handling = '''
        if form.is_valid():
            # Handle authorization code if provided
            authorization_code = None
            authorization_code_input = form.cleaned_data.get('authorization_code')
            
            if authorization_code_input and authorization_code_input != record.authorization_code:
                try:
                    # Try to get the authorization code
                    authorization_code = AuthorizationCode.objects.get(code=authorization_code_input)
                    
                    # Check if the authorization code is valid
                    if not authorization_code.is_valid():
                        messages.error(request, 'The provided authorization code is not valid or has expired.')
                        return render(request, \'''' + module + '/' + module + '''_record_form.html', {'form': form, 'record': record, 'title': 'Edit ''' + module.capitalize() + ''' Record'})
                    
                    # Check if the authorization code is for the correct service
                    if authorization_code.service_type not in ['''' + module + '''', 'general']:
                        messages.error(request, 'The provided authorization code is not valid for ''' + module + ''' services.')
                        return render(request, \'''' + module + '/' + module + '''_record_form.html', {'form': form, 'record': record, 'title': 'Edit ''' + module.capitalize() + ''' Record'})
                        
                except AuthorizationCode.DoesNotExist:
                    messages.error(request, 'The provided authorization code does not exist.')
                    return render(request, \'''' + module + '/' + module + '''_record_form.html', {'form': form, 'record': record, 'title': 'Edit ''' + module.capitalize() + ''' Record'})
            
            # Save the record
            form.save()
            
            # Mark authorization code as used if provided and different from existing
            if authorization_code and authorization_code_input != record.authorization_code:
                authorization_code.mark_as_used("''' + module.capitalize() + ''' Record #" + str(record.id) + " (updated)")
                messages.success(request, f''' + module.capitalize() + ''' record updated successfully. Authorization code {authorization_code.code} has been marked as used.')
            else:
                messages.success(request, ''' + module.capitalize() + ''' record updated successfully.')
            
            return redirect(\'''' + module + ':' + module + '''_record_detail', record_id=record.id)
'''
        
        new_content = new_content[:edit_view_start] + edit_view_content.replace('if form.is_valid():', auth_handling) + new_content[edit_view_end:]
    
    # Write the updated content back to the file
    with open(views_path, 'w') as f:
        f.write(new_content)

# Update templates for each module
for module in modules:
    templates_path = os.path.join(base_path, module, 'templates', module)
    
    # Update form template
    form_template = os.path.join(templates_path, f'{module}_record_form.html')
    
    # Read the existing form template
    with open(form_template, 'r') as f:
        content = f.read()
    
    # Find the position to insert the authorization code field
    insert_pos = content.rfind('<div class="form-group">')
    insert_pos = content.rfind('</div>', insert_pos) + 6
    
    # Create the authorization code field content
    auth_field_content = f'''
                <div class="form-group">
                    <label for="{{{{ form.authorization_code.id_for_label }}}}">Authorization Code (Optional)</label>
                    {{{{ form.authorization_code|add_class:"form-control" }}}}
                    <small class="form-text text-muted">Enter authorization code from desk office if applicable</small>
                </div>
'''
    
    # Insert the authorization code field
    new_content = content[:insert_pos] + auth_field_content + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(form_template, 'w') as f:
        f.write(new_content)
    
    # Update detail template
    detail_template = os.path.join(templates_path, f'{module}_record_detail.html')
    
    # Read the existing detail template
    with open(detail_template, 'r') as f:
        content = f.read()
    
    # Find the position to insert the authorization code display
    insert_pos = content.rfind('<!-- Notes -->')
    
    # Create the authorization code display content
    auth_display_content = f'''    <!-- Authorization Code -->
    {% if record.authorization_code %}
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Authorization</h6>
        </div>
        <div class="card-body">
            <p><strong>Authorization Code:</strong> {{{{ record.authorization_code }}}}</p>
        </div>
    </div>
    {% endif %}
    
'''
    
    # Insert the authorization code display
    new_content = content[:insert_pos] + auth_display_content + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(detail_template, 'w') as f:
        f.write(new_content)

# Create migration files for each module
import datetime
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

for module in modules:
    migrations_path = os.path.join(base_path, module, 'migrations')
    
    # Create migration file
    migration_content = f'''# Generated by Django 5.2 on {timestamp}

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('{module}', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='{module}record',
            name='authorization_code',
            field=models.CharField(blank=True, help_text='Authorization code from desk office', max_length=50, null=True),
        ),
    ]
'''
    
    # Write the migration file
    migration_file = os.path.join(migrations_path, f'0002_{module}record_authorization_code.py')
    with open(migration_file, 'w') as f:
        f.write(migration_content)

print("Authorization code support added to all modules successfully!")