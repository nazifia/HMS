"""
Script to automatically implement clinical notes for all medical specialty modules
Run this script from the HMS root directory: python implement_clinical_notes.py
"""

import os
import re

# Define module configurations
MODULES = [
    {'name': 'ophthalmic', 'record_model': 'OphthalmicRecord', 'title': 'Ophthalmic'},
    {'name': 'ent', 'record_model': 'EntRecord', 'title': 'ENT'},
    {'name': 'oncology', 'record_model': 'OncologyRecord', 'title': 'Oncology'},
    {'name': 'scbu', 'record_model': 'ScbuRecord', 'title': 'SCBU'},
    {'name': 'anc', 'record_model': 'AncRecord', 'title': 'ANC'},
    {'name': 'labor', 'record_model': 'LaborRecord', 'title': 'Labor'},
    {'name': 'icu', 'record_model': 'IcuRecord', 'title': 'ICU'},
    {'name': 'family_planning', 'record_model': 'FamilyPlanningRecord', 'title': 'Family Planning'},
    {'name': 'gynae_emergency', 'record_model': 'GynaeEmergencyRecord', 'title': 'Gynae Emergency'},
]


def get_clinical_note_model(module_name, record_model):
    """Generate clinical note model code"""
    model_name = f"{record_model.replace('Record', '')}ClinicalNote"
    return f'''

class {model_name}(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for {module_name} records"""
    {module_name}_record = models.ForeignKey({record_model}, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='{module_name}_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {{self.{module_name}_record.patient.get_full_name()}} - {{self.created_at.strftime('%Y-%m-%d %H:%M')}}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "{module_name.title()} Clinical Note"
        verbose_name_plural = "{module_name.title()} Clinical Notes"
'''


def add_model_to_file(module_path, model_code):
    """Add clinical note model to models.py"""
    models_file = os.path.join(module_path, 'models.py')

    if not os.path.exists(models_file):
        print(f"Warning: {models_file} does not exist")
        return False

    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if model already exists
    if 'ClinicalNote' in content:
        print(f"  - Clinical note model already exists in {models_file}")
        return True

    # Append the model to the end of the file
    with open(models_file, 'a', encoding='utf-8') as f:
        f.write(model_code)

    print(f"  [OK] Added clinical note model to {models_file}")
    return True


def get_form_class(module_name, record_model):
    """Generate form class code"""
    model_name = f"{record_model.replace('Record', '')}ClinicalNote"
    form_name = f"{record_model.replace('Record', '')}ClinicalNoteForm"

    return f'''

class {form_name}(forms.ModelForm):
    """Form for creating and editing {module_name} clinical notes (SOAP format)"""

    class Meta:
        model = {model_name}
        fields = ['subjective', 'objective', 'assessment', 'plan']
        widgets = {{
            'subjective': forms.Textarea(attrs={{
                'class': 'form-control',
                'rows': 3,
                'placeholder': "Patient's description of symptoms, concerns, and history..."
            }}),
            'objective': forms.Textarea(attrs={{
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observable findings, examination results, measurements...'
            }}),
            'assessment': forms.Textarea(attrs={{
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Clinical assessment, diagnosis, and interpretation...'
            }}),
            'plan': forms.Textarea(attrs={{
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Treatment plan, interventions, follow-up...'
            }}),
        }}
        labels = {{
            'subjective': 'Subjective (S)',
            'objective': 'Objective (O)',
            'assessment': 'Assessment (A)',
            'plan': 'Plan (P)',
        }}
'''


def update_forms_file(module_path, module_name, record_model):
    """Update forms.py with clinical note form"""
    forms_file = os.path.join(module_path, 'forms.py')

    if not os.path.exists(forms_file):
        # Create a new forms.py file
        model_name = f"{record_model.replace('Record', '')}ClinicalNote"
        content = f"""from django import forms
from .models import {record_model}, {model_name}
{get_form_class(module_name, record_model)}
"""
        with open(forms_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Created {forms_file}")
        return True

    with open(forms_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if form already exists
    if 'ClinicalNoteForm' in content:
        print(f"  - Clinical note form already exists in {forms_file}")
        return True

    # Update imports
    model_name = f"{record_model.replace('Record', '')}ClinicalNote"
    if model_name not in content:
        # Add to imports
        import_pattern = r'from \.models import (.+)'
        match = re.search(import_pattern, content)
        if match:
            existing_imports = match.group(1)
            new_imports = f"{existing_imports}, {model_name}"
            content = re.sub(import_pattern, f'from .models import {new_imports}', content)

    # Add form class
    content += get_form_class(module_name, record_model)

    with open(forms_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  [OK] Updated {forms_file}")
    return True


def get_views_code(module_name, record_model):
    """Generate views code"""
    model_name = f"{record_model.replace('Record', '')}ClinicalNote"
    form_name = f"{record_model.replace('Record', '')}ClinicalNoteForm"

    return f'''

# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to a {module_name} record"""
    record = get_object_or_404({record_model}, id=record_id)

    if request.method == 'POST':
        form = {form_name}(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.{module_name}_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('{module_name}:record_detail', record_id=record.pk)
    else:
        form = {form_name}()

    context = {{
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }}
    return render(request, '{module_name}/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404({model_name}, id=note_id)
    record = note.{module_name}_record

    if request.method == 'POST':
        form = {form_name}(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('{module_name}:record_detail', record_id=record.pk)
    else:
        form = {form_name}(instance=note)

    context = {{
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }}
    return render(request, '{module_name}/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404({model_name}, id=note_id)
    record_id = note.{module_name}_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('{module_name}:record_detail', record_id=record_id)

    context = {{
        'note': note
    }}
    return render(request, '{module_name}/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404({model_name}, id=note_id)

    context = {{
        'note': note,
        'record': note.{module_name}_record
    }}
    return render(request, '{module_name}/clinical_note_detail.html', context)
'''


def update_views_file(module_path, module_name, record_model):
    """Update views.py with clinical note views"""
    views_file = os.path.join(module_path, 'views.py')

    if not os.path.exists(views_file):
        print(f"Warning: {views_file} does not exist")
        return False

    with open(views_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if views already exist
    if 'def add_clinical_note' in content:
        print(f"  - Clinical note views already exist in {views_file}")
        return True

    # Update imports
    model_name = f"{record_model.replace('Record', '')}ClinicalNote"
    form_name = f"{record_model.replace('Record', '')}ClinicalNoteForm"

    # Add model import
    if f', {model_name}' not in content:
        content = content.replace(f'from .models import {record_model}',
                                 f'from .models import {record_model}, {model_name}')

    # Add form import
    if 'from .forms import' in content:
        forms_import_pattern = r'from \.forms import (.+)'
        match = re.search(forms_import_pattern, content)
        if match and form_name not in match.group(1):
            existing_imports = match.group(1)
            new_imports = f"{existing_imports}, {form_name}"
            content = re.sub(forms_import_pattern, f'from .forms import {new_imports}', content)

    # Add views code at the end
    content += get_views_code(module_name, record_model)

    with open(views_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  [OK] Updated {views_file}")
    return True


def update_urls_file(module_path, module_name):
    """Update urls.py with clinical note routes"""
    urls_file = os.path.join(module_path, 'urls.py')

    if not os.path.exists(urls_file):
        # Create a new urls.py file
        content = f"""from django.urls import path
from . import views

app_name = '{module_name}'

urlpatterns = [
    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),
]
"""
        with open(urls_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Created {urls_file}")
        return True

    with open(urls_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if routes already exist
    if 'add-clinical-note' in content:
        print(f"  - Clinical note routes already exist in {urls_file}")
        return True

    # Add routes before the closing bracket
    clinical_notes_routes = f"""
    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),
"""

    # Find the last path and insert before the closing bracket
    content = content.rstrip()
    if content.endswith(']'):
        content = content[:-1] + clinical_notes_routes + '\n]'

    with open(urls_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  [OK] Updated {urls_file}")
    return True


def create_templates(module_path, module_name, module_title):
    """Create template files for clinical notes"""
    templates_dir = os.path.join(module_path, 'templates', module_name)
    os.makedirs(templates_dir, exist_ok=True)

    # Template files content (simplified versions)
    templates = {
        'clinical_note_form.html': f'''{{%extends '{module_name}/base.html' %}}
{{%load crispy_forms_tags %}}

{{%block page_title %}}{{{{title}}}}{{%endblock%}}

{{%block {module_name}_content %}}
<div class="card">
    <div class="card-header">
        <h5>{{{{title}}}}</h5>
    </div>
    <div class="card-body">
        <form method="post">
            {{%csrf_token%}}
            {{{{form|crispy}}}}
            <button type="submit" class="btn btn-primary">Save</button>
            <a href="{{{{back_url}}}}" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
</div>
{{%endblock%}}
''',
        'clinical_note_detail.html': f'''{{%extends '{module_name}/base.html' %}}

{{%block page_title %}}Clinical Note{{%endblock%}}

{{%block {module_name}_content %}}
<div class="card">
    <div class="card-body">
        <h6>Subjective:</h6><p>{{{{note.subjective}}}}</p>
        <h6>Objective:</h6><p>{{{{note.objective}}}}</p>
        <h6>Assessment:</h6><p>{{{{note.assessment}}}}</p>
        <h6>Plan:</h6><p>{{{{note.plan}}}}</p>
    </div>
</div>
{{%endblock%}}
''',
        'clinical_note_confirm_delete.html': f'''{{%extends '{module_name}/base.html' %}}

{{%block page_title %}}Delete Clinical Note{{%endblock%}}

{{%block {module_name}_content %}}
<div class="card">
    <div class="card-body">
        <h5>Are you sure?</h5>
        <form method="post">
            {{%csrf_token%}}
            <button type="submit" class="btn btn-danger">Delete</button>
            <a href="{{{{back_url}}}}" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
</div>
{{%endblock%}}
'''
    }

    for filename, content in templates.items():
        filepath = os.path.join(templates_dir, filename)
        if os.path.exists(filepath):
            print(f"  - Template {filename} already exists")
            continue

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Created template {filename}")

    return True


def implement_module(module_config):
    """Implement clinical notes for a single module"""
    module_name = module_config['name']
    record_model = module_config['record_model']
    module_title = module_config['title']

    print(f"\n{'='*60}")
    print(f"Implementing clinical notes for {module_title} module")
    print(f"{'='*60}")

    module_path = os.path.join(os.getcwd(), module_name)

    if not os.path.exists(module_path):
        print(f"[ERROR] Module directory {module_path} does not exist")
        return False

    try:
        # 1. Add model
        model_code = get_clinical_note_model(module_name, record_model)
        add_model_to_file(module_path, model_code)

        # 2. Update forms
        update_forms_file(module_path, module_name, record_model)

        # 3. Update views
        update_views_file(module_path, module_name, record_model)

        # 4. Update URLs
        update_urls_file(module_path, module_name)

        # 5. Create templates
        create_templates(module_path, module_name, module_title)

        print(f"[SUCCESS] Successfully implemented clinical notes for {module_title}")
        return True

    except Exception as e:
        print(f"[ERROR] Error implementing {module_title}: {str(e)}")
        return False


def main():
    """Main function to implement clinical notes for all modules"""
    print("="*60)
    print("Clinical Notes Implementation Script")
    print("="*60)
    print(f"Current directory: {os.getcwd()}")
    print(f"Modules to process: {len(MODULES)}")

    successful = []
    failed = []

    for module_config in MODULES:
        if implement_module(module_config):
            successful.append(module_config['title'])
        else:
            failed.append(module_config['title'])

    print(f"\n{'='*60}")
    print("Implementation Summary")
    print(f"{'='*60}")
    print(f"[SUCCESS] Successful: {len(successful)} modules")
    for module in successful:
        print(f"   - {module}")

    if failed:
        print(f"\n[FAILED] Failed: {len(failed)} modules")
        for module in failed:
            print(f"   - {module}")

    print(f"\n{'='*60}")
    print("Next steps:")
    print("1. Run: python manage.py makemigrations")
    print("2. Run: python manage.py migrate")
    print("3. Test each module in the browser")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
