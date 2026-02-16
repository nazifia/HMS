#!/usr/bin/env python
import os
import sys
import django

sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import call_command

# Create migration for billing app
call_command('makemigrations', 'billing', verbosity=2)
