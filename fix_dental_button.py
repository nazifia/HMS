#!/usr/bin/env python
"""
Fix script for dental request button logic.
This script updates the pending request check in dental_record_detail view
to use Record ID for more robust matching.
"""

import re

# Read the file
with open('dental/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

#Define the old pattern to replace
old_pattern = r'''    # Check for existing pending authorization request
    if is_nhia_patient and requires_authorization:
        from django\.db\.models import Q
        has_pending_request = InternalNotification\.objects\.filter\(
            Q\(message__icontains=f"Patient: \{record\.patient\.get_full_name\(\)\} \(ID: \{record\.patient\.patient_id\}\)"\) &
            Q\(message__icontains="Module: dental"\) &
            Q\(is_read=False\)
        \)\.exists\(\)'''

# Define the new pattern
new_pattern = '''    # Check for existing pending authorization request for this specific record
    if is_nhia_patient and requires_authorization:
        from django.db.models import Q
        has_pending_request = InternalNotification.objects.filter(
            Q(message__icontains=f"(ID: {record.patient.patient_id})") &
            Q(message__icontains="Module: dental") &
            Q(message__icontains=f"Record ID: {record.id}") &
            Q(is_read=False)
        ).exists()'''

# Replace the pattern
content = re.sub(old_pattern, new_pattern, content)

# Write back
with open('dental/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Updated dental/views.py")
print("The pending request check now uses Record ID for more accurate matching.")
