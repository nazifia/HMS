"""Fix missing settings import in models.py files"""
import os

MODULES = ['anc', 'labor', 'icu', 'family_planning', 'gynae_emergency']

for module in MODULES:
    models_file = f'{module}/models.py'
    if not os.path.exists(models_file):
        print(f"Skipping {models_file} - file not found")
        continue

    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'from django.conf import settings' in content:
        print(f"Skipping {module} - settings already imported")
        continue

    # Add the import after the first django.db import
    content = content.replace(
        'from django.db import models',
        'from django.db import models\nfrom django.conf import settings',
        1  # Only replace first occurrence
    )

    with open(models_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed {module}/models.py")

print("\nAll files fixed!")
