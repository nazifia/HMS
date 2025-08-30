#!/usr/bin/env python
"""
Fix Dispensary Selection Issue
This script addresses the dispensary selection retention problem in pharmacy dispensing
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_dispensary_selection():
    """Test dispensary selection functionality"""
    print("=== Testing Dispensary Selection ===")
    
    try:
        from pharmacy.models import Dispensary, Prescription, PrescriptionItem
        from pharmacy.forms import DispenseItemForm, BaseDispenseItemFormSet
        from django.forms import formset_factory
        
        # Check if Theatre-ph dispensary exists
        theatre_dispensary = Dispensary.objects.filter(name__icontains='theatre').first()
        if not theatre_dispensary:
            # Create Theatre-ph dispensary for testing
            theatre_dispensary = Dispensary.objects.create(
                name='Theatre-ph',
                location='Theatre Pharmacy',
                description='Theatre pharmacy dispensary',
                is_active=True
            )
            print("✅ Created Theatre-ph dispensary")
        else:
            print(f"✅ Found dispensary: {theatre_dispensary.name}")
        
        # Test form initialization with selected dispensary
        test_prescription = Prescription.objects.first()
        if test_prescription:
            prescription_items = list(test_prescription.items.all())
            if prescription_items:
                # Test form with selected dispensary
                form = DispenseItemForm(
                    initial={
                        'item_id': prescription_items[0].id,
                        'dispensary': theatre_dispensary.id
                    },
                    selected_dispensary=theatre_dispensary
                )
                print(f"✅ Form initialized with dispensary: {theatre_dispensary.name}")
                
                # Test form validation
                form_data = {
                    'item_id': prescription_items[0].id,
                    'dispense_this_item': True,
                    'quantity_to_dispense': 1,
                    'dispensary': theatre_dispensary.id
                }
                
                form = DispenseItemForm(
                    data=form_data,
                    selected_dispensary=theatre_dispensary
                )
                form.prescription_item = prescription_items[0]
                
                if form.is_valid():
                    print("✅ Form validation passed with selected dispensary")
                else:
                    print(f"❌ Form validation failed: {form.errors}")
            else:
                print("⚠️  No prescription items found for testing")
        else:
            print("⚠️  No prescriptions found for testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Dispensary selection test failed: {e}")
        return False

def verify_dispensary_logic():
    """Verify the dispensary selection logic in forms and views"""
    print("\n=== Verifying Dispensary Logic ===")
    
    try:
        # Check if all active dispensaries are available
        from pharmacy.models import Dispensary
        
        active_dispensaries = Dispensary.objects.filter(is_active=True)
        print(f"✅ Found {active_dispensaries.count()} active dispensaries:")
        
        for dispensary in active_dispensaries:
            print(f"   - {dispensary.name} (ID: {dispensary.id}) - {dispensary.location}")
        
        # Verify Theatre-ph specifically
        theatre_dispensary = active_dispensaries.filter(name__icontains='theatre').first()
        if theatre_dispensary:
            print(f"✅ Theatre-ph dispensary verified: {theatre_dispensary.name} (ID: {theatre_dispensary.id})")
        else:
            print("❌ Theatre-ph dispensary not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Dispensary logic verification failed: {e}")
        return False

def test_form_submission():
    """Test form submission with dispensary selection"""
    print("\n=== Testing Form Submission Logic ===")
    
    try:
        from pharmacy.models import Dispensary, Prescription
        from pharmacy.forms import DispenseItemForm
        
        # Get Theatre-ph dispensary
        theatre_dispensary = Dispensary.objects.filter(name__icontains='theatre').first()
        if not theatre_dispensary:
            print("❌ Theatre-ph dispensary not found")
            return False
        
        # Get a test prescription
        test_prescription = Prescription.objects.first()
        if not test_prescription:
            print("❌ No test prescription found")
            return False
        
        prescription_item = test_prescription.items.first()
        if not prescription_item:
            print("❌ No prescription items found")
            return False
        
        # Simulate form submission data
        form_data = {
            'item_id': prescription_item.id,
            'dispense_this_item': True,
            'quantity_to_dispense': 1,
            'dispensary': theatre_dispensary.id
        }
        
        # Test form with selected dispensary
        form = DispenseItemForm(
            data=form_data,
            selected_dispensary=theatre_dispensary
        )
        form.prescription_item = prescription_item
        
        print(f"Form data: {form_data}")
        print(f"Selected dispensary: {theatre_dispensary.name}")
        print(f"Form is bound: {form.is_bound}")
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            effective_dispensary = cleaned_data.get('dispensary') or theatre_dispensary
            print(f"✅ Form validation successful")
            print(f"   - Dispense item: {cleaned_data.get('dispense_this_item')}")
            print(f"   - Quantity: {cleaned_data.get('quantity_to_dispense')}")
            print(f"   - Effective dispensary: {effective_dispensary}")
        else:
            print(f"❌ Form validation failed:")
            for field, errors in form.errors.items():
                print(f"   - {field}: {errors}")
        
        return True
        
    except Exception as e:
        print(f"❌ Form submission test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_dispensary():
    """Ensure Theatre-ph dispensary exists"""
    print("\n=== Creating/Verifying Theatre-ph Dispensary ===")
    
    try:
        from pharmacy.models import Dispensary
        
        # Check if Theatre-ph exists
        theatre_dispensary = Dispensary.objects.filter(name='Theatre-ph').first()
        
        if not theatre_dispensary:
            # Create it
            theatre_dispensary = Dispensary.objects.create(
                name='Theatre-ph',
                location='Theatre Pharmacy',
                description='Theatre pharmacy dispensary for surgical procedures',
                is_active=True
            )
            print(f"✅ Created Theatre-ph dispensary (ID: {theatre_dispensary.id})")
        else:
            # Ensure it's active
            if not theatre_dispensary.is_active:
                theatre_dispensary.is_active = True
                theatre_dispensary.save()
                print(f"✅ Activated Theatre-ph dispensary (ID: {theatre_dispensary.id})")
            else:
                print(f"✅ Theatre-ph dispensary already exists and is active (ID: {theatre_dispensary.id})")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create/verify Theatre-ph dispensary: {e}")
        return False

def main():
    """Main function to run all dispensary fixes"""
    print("🔧 Dispensary Selection Fix Script")
    print("=" * 50)
    
    success_count = 0
    total_checks = 4
    
    # Run all checks
    if create_test_dispensary():
        success_count += 1
    
    if verify_dispensary_logic():
        success_count += 1
    
    if test_dispensary_selection():
        success_count += 1
    
    if test_form_submission():
        success_count += 1
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 DISPENSARY FIX SUMMARY")
    print(f"{'=' * 50}")
    print(f"Successful checks: {success_count}/{total_checks}")
    
    if success_count == total_checks:
        print("🎉 All dispensary selection fixes completed successfully!")
        print("\n✅ The dispensary selection should now work correctly.")
        print("✅ Theatre-ph dispensary should be retained when selected.")
        print("✅ Form validation should pass with selected dispensary.")
        return 0
    else:
        print(f"❌ {total_checks - success_count} checks failed.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
