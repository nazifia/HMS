#!/usr/bin/env python
"""
Simple test for dispensary selection fix
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def main():
    print("🔧 Testing Dispensary Selection Fix")
    print("=" * 40)
    
    try:
        from pharmacy.models import Dispensary, Prescription
        from pharmacy.forms import DispenseItemForm
        
        # Find Theatre-ph dispensary
        theatre_dispensary = Dispensary.objects.filter(name='Theatre-ph').first()
        if theatre_dispensary:
            print(f"✅ Found Theatre-ph dispensary (ID: {theatre_dispensary.id})")
        else:
            print("❌ Theatre-ph dispensary not found")
            return 1
        
        # Test with a prescription
        prescription = Prescription.objects.first()
        if prescription:
            print(f"✅ Found test prescription (ID: {prescription.id})")
            
            prescription_item = prescription.items.first()
            if prescription_item:
                print(f"✅ Found prescription item (ID: {prescription_item.id})")
                
                # Test form validation with Theatre-ph
                form_data = {
                    'item_id': prescription_item.id,
                    'dispense_this_item': True,
                    'quantity_to_dispense': 1,
                    'dispensary': theatre_dispensary.id
                }
                
                form = DispenseItemForm(
                    data=form_data,
                    selected_dispensary=theatre_dispensary
                )
                form.prescription_item = prescription_item
                
                if form.is_valid():
                    print("✅ Form validation PASSED with Theatre-ph dispensary")
                    print("🎉 Dispensary selection fix is working!")
                    return 0
                else:
                    print("❌ Form validation FAILED:")
                    for field, errors in form.errors.items():
                        print(f"   {field}: {errors}")
                    return 1
            else:
                print("❌ No prescription items found")
                return 1
        else:
            print("❌ No prescriptions found")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
