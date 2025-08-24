#!/usr/bin/env python
"""
Test script to validate the formset validation improvements for surgical team and equipment forms.
This script tests the custom clean methods and validation logic in the formsets.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

# Add the project directory to the Python path
sys.path.insert(0, r'c:\Users\dell\Desktop\MY_PRODUCTS\HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

# Setup Django
django.setup()

from theatre.models import Surgery, SurgeryType, OperationTheatre, SurgicalTeam, SurgicalEquipment, EquipmentUsage
from theatre.forms import SurgicalTeamFormSet, EquipmentUsageFormSet, SurgicalTeamForm, EquipmentUsageForm
from patients.models import Patient
from accounts.models import CustomUser
from datetime import datetime, timedelta

def test_surgical_team_form_validation():
    """Test that SurgicalTeamForm validates properly with partial data."""
    print("Testing SurgicalTeamForm validation...")
    
    # Test valid form
    form_data = {
        'staff': 1,  # Assuming user ID 1 exists
        'role': 'surgeon',
        'usage_notes': 'Test notes'
    }
    
    try:
        form = SurgicalTeamForm(data=form_data)
        print(f"Valid form test - Is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"Errors: {form.errors}")
    except Exception as e:
        print(f"Error in valid form test: {e}")
    
    # Test form with missing staff (should be invalid if role is provided)
    form_data_incomplete = {
        'role': 'surgeon',
        'usage_notes': 'Test notes'
    }
    
    try:
        form_incomplete = SurgicalTeamForm(data=form_data_incomplete)
        is_valid = form_incomplete.is_valid()
        print(f"Incomplete form test (missing staff) - Is valid: {is_valid}")
        if not is_valid:
            print(f"Errors: {form_incomplete.errors}")
    except Exception as e:
        print(f"Error in incomplete form test: {e}")
    
    # Test completely empty form (should be valid as it's optional)
    form_data_empty = {}
    
    try:
        form_empty = SurgicalTeamForm(data=form_data_empty)
        is_valid = form_empty.is_valid()
        print(f"Empty form test - Is valid: {is_valid}")
        if not is_valid:
            print(f"Errors: {form_empty.errors}")
    except Exception as e:
        print(f"Error in empty form test: {e}")

def test_equipment_usage_form_validation():
    """Test that EquipmentUsageForm validates properly with partial data."""
    print("\nTesting EquipmentUsageForm validation...")
    
    # Test valid form
    form_data = {
        'equipment': 1,  # Assuming equipment ID 1 exists
        'quantity_used': 2,
        'notes': 'Test notes'
    }
    
    try:
        form = EquipmentUsageForm(data=form_data)
        print(f"Valid form test - Is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"Errors: {form.errors}")
    except Exception as e:
        print(f"Error in valid form test: {e}")
    
    # Test form with missing equipment (should be invalid if quantity is provided)
    form_data_incomplete = {
        'quantity_used': 2,
        'notes': 'Test notes'
    }
    
    try:
        form_incomplete = EquipmentUsageForm(data=form_data_incomplete)
        is_valid = form_incomplete.is_valid()
        print(f"Incomplete form test (missing equipment) - Is valid: {is_valid}")
        if not is_valid:
            print(f"Errors: {form_incomplete.errors}")
    except Exception as e:
        print(f"Error in incomplete form test: {e}")
    
    # Test form with invalid quantity
    form_data_invalid = {
        'equipment': 1,
        'quantity_used': 0,  # Invalid quantity
        'notes': 'Test notes'
    }
    
    try:
        form_invalid = EquipmentUsageForm(data=form_data_invalid)
        is_valid = form_invalid.is_valid()
        print(f"Invalid quantity form test - Is valid: {is_valid}")
        if not is_valid:
            print(f"Errors: {form_invalid.errors}")
    except Exception as e:
        print(f"Error in invalid quantity test: {e}")

def test_formset_validation():
    """Test formset validation behavior."""
    print("\nTesting formset validation...")
    
    try:
        # Test empty formset (should be valid)
        formset_data = {
            'team_members-TOTAL_FORMS': '1',
            'team_members-INITIAL_FORMS': '0',
            'team_members-MIN_NUM_FORMS': '0',
            'team_members-MAX_NUM_FORMS': '1000',
            'team_members-0-staff': '',
            'team_members-0-role': '',
            'team_members-0-usage_notes': '',
        }
        
        formset = SurgicalTeamFormSet(data=formset_data)
        is_valid = formset.is_valid()
        print(f"Empty formset test - Is valid: {is_valid}")
        if not is_valid:
            print(f"Formset errors: {formset.errors}")
            print(f"Non-form errors: {formset.non_form_errors()}")
    except Exception as e:
        print(f"Error in formset test: {e}")

def main():
    """Run all validation tests."""
    print("=== Formset Validation Test Suite ===")
    print("Testing the enhanced validation logic for surgical team and equipment formsets.\n")
    
    test_surgical_team_form_validation()
    test_equipment_usage_form_validation()
    test_formset_validation()
    
    print("\n=== Test Suite Complete ===")
    print("If you see validation errors above, they are expected for incomplete forms.")
    print("The important thing is that the forms handle partial data gracefully.")

if __name__ == "__main__":
    main()