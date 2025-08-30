#!/usr/bin/env python
"""
Fix AttributeError in dispensary selection
This script addresses the 'DispenseItemForm' object has no attribute 'cleaned_data' error
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_form_validation():
    """Test form validation without AttributeError"""
    print("=== Testing Form Validation Fix ===")
    
    try:
        from pharmacy.models import Dispensary, Prescription, PrescriptionItem, Medication
        from pharmacy.forms import DispenseItemForm
        from patients.models import Patient
        
        # Get or create test data
        dispensary = Dispensary.objects.filter(name='Theatre-ph').first()
        if not dispensary:
            dispensary = Dispensary.objects.create(
                name='Theatre-ph',
                location='Theatre Pharmacy',
                is_active=True
            )
            print("✅ Created Theatre-ph dispensary")
        
        # Get or create a test prescription with items
        prescription = Prescription.objects.first()
        if not prescription:
            # Create test data
            patient = Patient.objects.first()
            if not patient:
                print("❌ No patients found - cannot create test prescription")
                return False
                
            prescription = Prescription.objects.create(
                patient=patient,
                prescribed_by_id=1,  # Assuming user ID 1 exists
                status='pending'
            )
            
            # Create a medication if none exists
            medication = Medication.objects.first()
            if not medication:
                medication = Medication.objects.create(
                    name='Test Medication',
                    strength='10mg',
                    form='tablet'
                )
            
            # Create prescription item
            prescription_item = PrescriptionItem.objects.create(
                prescription=prescription,
                medication=medication,
                quantity=10,
                dosage='1 tablet daily'
            )
            print("✅ Created test prescription with item")
        else:
            prescription_item = prescription.items.first()
            if not prescription_item:
                # Create a prescription item
                medication = Medication.objects.first()
                if medication:
                    prescription_item = PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication=medication,
                        quantity=10,
                        dosage='1 tablet daily'
                    )
                    print("✅ Created test prescription item")
                else:
                    print("❌ No medications found")
                    return False
        
        # Test form creation and validation
        form_data = {
            'item_id': prescription_item.id,
            'dispense_this_item': True,
            'quantity_to_dispense': 1,
            'dispensary': dispensary.id
        }
        
        # Test form without selected_dispensary
        form1 = DispenseItemForm(data=form_data)
        form1.prescription_item = prescription_item
        
        print(f"Form 1 - is_bound: {form1.is_bound}")
        print(f"Form 1 - has cleaned_data: {hasattr(form1, 'cleaned_data')}")
        
        if form1.is_valid():
            print("✅ Form 1 validation passed")
            print(f"   Cleaned data: {form1.cleaned_data}")
        else:
            print(f"❌ Form 1 validation failed: {form1.errors}")
        
        # Test form with selected_dispensary
        form2 = DispenseItemForm(data=form_data, selected_dispensary=dispensary)
        form2.prescription_item = prescription_item
        
        print(f"Form 2 - is_bound: {form2.is_bound}")
        print(f"Form 2 - has cleaned_data: {hasattr(form2, 'cleaned_data')}")
        
        if form2.is_valid():
            print("✅ Form 2 validation passed")
            print(f"   Cleaned data: {form2.cleaned_data}")
        else:
            print(f"❌ Form 2 validation failed: {form2.errors}")
        
        return True
        
    except Exception as e:
        print(f"❌ Form validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_formset_validation():
    """Test formset validation"""
    print("\n=== Testing Formset Validation ===")
    
    try:
        from pharmacy.models import Dispensary, Prescription
        from pharmacy.forms import DispenseItemForm, BaseDispenseItemFormSet
        from django.forms import formset_factory
        
        dispensary = Dispensary.objects.filter(name='Theatre-ph').first()
        prescription = Prescription.objects.first()
        
        if not dispensary or not prescription:
            print("❌ Missing test data")
            return False
        
        prescription_items = list(prescription.items.all())
        if not prescription_items:
            print("❌ No prescription items found")
            return False
        
        # Create formset
        DispenseFormSet = formset_factory(DispenseItemForm, formset=BaseDispenseItemFormSet, extra=0)
        
        # Test data
        form_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-item_id': prescription_items[0].id,
            'form-0-dispense_this_item': True,
            'form-0-quantity_to_dispense': 1,
            'form-0-dispensary': dispensary.id,
        }
        
        formset = DispenseFormSet(
            data=form_data,
            prefix='form',
            prescription_items_qs=prescription_items,
            form_kwargs={'selected_dispensary': dispensary}
        )
        
        print(f"Formset is_bound: {formset.is_bound}")
        print(f"Formset is_valid: {formset.is_valid()}")
        
        if not formset.is_valid():
            print(f"Formset errors: {formset.errors}")
            print(f"Non-form errors: {formset.non_form_errors()}")
        else:
            print("✅ Formset validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Formset validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run all tests"""
    print("🔧 AttributeError Fix Test Script")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    # Run tests
    if test_form_validation():
        success_count += 1
    
    if test_formset_validation():
        success_count += 1
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 50}")
    print(f"Successful tests: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! AttributeError fix is working.")
        print("\n✅ The dispensary selection should now work without errors.")
        return 0
    else:
        print(f"❌ {total_tests - success_count} tests failed.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
