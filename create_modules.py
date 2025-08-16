import os
import sys

# Define the modules to create
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

# Define the base path (current directory)
base_path = os.getcwd()

# Create each module
for module in modules:
    # Create module directory
    module_path = os.path.join(base_path, module)
    os.makedirs(module_path, exist_ok=True)
    
    # Create subdirectories
    os.makedirs(os.path.join(module_path, 'migrations'), exist_ok=True)
    os.makedirs(os.path.join(module_path, 'templates', module), exist_ok=True)
    
    # Create __init__.py
    with open(os.path.join(module_path, '__init__.py'), 'w') as f:
        pass
    
    # Create apps.py
    with open(os.path.join(module_path, 'apps.py'), 'w') as f:
        class_name = ''.join(word.capitalize() for word in module.split('_'))
        f.write(f'''from django.apps import AppConfig


class {class_name}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{module}'
''')
    
    # Create models.py (basic template)
    with open(os.path.join(module_path, 'models.py'), 'w') as f:
        f.write(f'''from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class {module.capitalize()}Record(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='{module}_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for {module} module here
    
    diagnosis = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{module.capitalize()} Record for {{self.patient.get_full_name()}} - {{self.visit_date.strftime('%Y-%m-%d')}}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = '{module.capitalize()} Record'
        verbose_name_plural = '{module.capitalize()} Records'
''')
    
    # Create urls.py
    with open(os.path.join(module_path, 'urls.py'), 'w') as f:
        f.write(f'''from django.urls import path
from . import views

app_name = '{module}'

urlpatterns = [
    path('', views.{module}_records_list, name='{module}_records_list'),
    path('create/', views.create_{module}_record, name='create_{module}_record'),
    path('<int:record_id>/', views.{module}_record_detail, name='{module}_record_detail'),
    path('<int:record_id>/edit/', views.edit_{module}_record, name='edit_{module}_record'),
    path('<int:record_id>/delete/', views.delete_{module}_record, name='delete_{module}_record'),
]
''')

print("All modules created successfully!")