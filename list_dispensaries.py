#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary

def list_dispensaries():
    """List all dispensaries"""
    print('Available dispensaries:')
    for d in Dispensary.objects.all():
        print(f'{d.id}: {d.name}')

if __name__ == '__main__':
    list_dispensaries()