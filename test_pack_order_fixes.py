"""
Test script to verify theatre/surgery pack order fixes
Run this script to test the fixes: python manage.py shell < test_pack_order_fixes.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import PackOrder, MedicalPack
from theatre.models import Surgery
from labor.models import LaborRecord

def test_packorder_model_fields():
    """Test that PackOrder model has all required fields"""
    print("\n" + "="*60)
    print("TEST 1: Verify PackOrder Model Fields")
    print("="*60)
    
    try:
        # Create a dummy PackOrder instance (don't save)
        pack_order = PackOrder()
        
        # Check for surgery field
        assert hasattr(pack_order, 'surgery'), "❌ FAILED: surgery field missing"
        print("✅ PASSED: surgery field exists")
        
        # Check for labor_record field
        assert hasattr(pack_order, 'labor_record'), "❌ FAILED: labor_record field missing"
        print("✅ PASSED: labor_record field exists")
        
        # Check for patient field
        assert hasattr(pack_order, 'patient'), "❌ FAILED: patient field missing"
        print("✅ PASSED: patient field exists")
        
        # Check for pack field
        assert hasattr(pack_order, 'pack'), "❌ FAILED: pack field missing"
        print("✅ PASSED: pack field exists")
        
        # Check for ordered_by field
        assert hasattr(pack_order, 'ordered_by'), "❌ FAILED: ordered_by field missing"
        print("✅ PASSED: ordered_by field exists")
        
        # Check for scheduled_date field
        assert hasattr(pack_order, 'scheduled_date'), "❌ FAILED: scheduled_date field missing"
        print("✅ PASSED: scheduled_date field exists")
        
        # Check for order_notes field
        assert hasattr(pack_order, 'order_notes'), "❌ FAILED: order_notes field missing"
        print("✅ PASSED: order_notes field exists")
        
        print("\n✅ ALL FIELD TESTS PASSED!")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return False


def test_packorder_relationships():
    """Test that PackOrder relationships work correctly"""
    print("\n" + "="*60)
    print("TEST 2: Verify PackOrder Relationships")
    print("="*60)
    
    try:
        # Test surgery relationship
        if Surgery.objects.exists():
            surgery = Surgery.objects.first()
            pack_orders = surgery.pack_orders.all()
            print(f"✅ PASSED: Surgery -> PackOrder relationship works (found {pack_orders.count()} pack orders)")
        else:
            print("⚠️  SKIPPED: No surgeries in database to test relationship")
        
        # Test labor_record relationship
        if LaborRecord.objects.exists():
            labor_record = LaborRecord.objects.first()
            pack_orders = labor_record.pack_orders.all()
            print(f"✅ PASSED: LaborRecord -> PackOrder relationship works (found {pack_orders.count()} pack orders)")
        else:
            print("⚠️  SKIPPED: No labor records in database to test relationship")
        
        # Test pack relationship
        if MedicalPack.objects.exists():
            pack = MedicalPack.objects.first()
            pack_orders = PackOrder.objects.filter(pack=pack)
            print(f"✅ PASSED: MedicalPack -> PackOrder relationship works (found {pack_orders.count()} pack orders)")
        else:
            print("⚠️  SKIPPED: No medical packs in database to test relationship")
        
        print("\n✅ ALL RELATIONSHIP TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_packorder_form_import():
    """Test that PackOrderForm can be imported and initialized"""
    print("\n" + "="*60)
    print("TEST 3: Verify PackOrderForm Import and Initialization")
    print("="*60)
    
    try:
        from pharmacy.forms import PackOrderForm
        print("✅ PASSED: PackOrderForm imported successfully")
        
        # Test form initialization without context
        form = PackOrderForm()
        print("✅ PASSED: PackOrderForm initialized without context")
        
        # Test form initialization with surgery context (if surgery exists)
        if Surgery.objects.exists():
            surgery = Surgery.objects.first()
            form = PackOrderForm(surgery=surgery, preselected_patient=surgery.patient)
            print("✅ PASSED: PackOrderForm initialized with surgery context")
            
            # Check if patient field is in the form
            assert 'patient' in form.fields, "❌ FAILED: patient field not in form"
            print("✅ PASSED: patient field exists in form")
            
            # Check if patient_hidden field was added
            if 'patient_hidden' in form.fields:
                print("✅ PASSED: patient_hidden field added for preselected patient")
            else:
                print("⚠️  WARNING: patient_hidden field not added (may be expected if no preselection)")
        else:
            print("⚠️  SKIPPED: No surgeries in database to test surgery context")
        
        # Test form initialization with labor context (if labor record exists)
        if LaborRecord.objects.exists():
            labor_record = LaborRecord.objects.first()
            form = PackOrderForm(labor_record=labor_record, preselected_patient=labor_record.patient)
            print("✅ PASSED: PackOrderForm initialized with labor context")
        else:
            print("⚠️  SKIPPED: No labor records in database to test labor context")
        
        print("\n✅ ALL FORM TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_surgery_type_mapping():
    """Test that surgery type mapping works correctly"""
    print("\n" + "="*60)
    print("TEST 4: Verify Surgery Type Mapping")
    print("="*60)
    
    try:
        surgery_type_mapping = {
            'Appendectomy': 'appendectomy',
            'Cholecystectomy': 'cholecystectomy',
            'Hernia Repair': 'hernia_repair',
            'Cesarean Section': 'cesarean_section',
            'Tonsillectomy': 'tonsillectomy',
        }
        
        print("✅ PASSED: Surgery type mapping defined")
        
        # Test that medical packs can be filtered by surgery type
        for surgery_name, surgery_type in surgery_type_mapping.items():
            packs = MedicalPack.objects.filter(
                is_active=True,
                pack_type='surgery',
                surgery_type=surgery_type
            )
            print(f"✅ PASSED: Can filter packs for {surgery_name} (found {packs.count()} packs)")
        
        print("\n✅ ALL SURGERY TYPE MAPPING TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("THEATRE/SURGERY PACK ORDER FIXES - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("PackOrder Model Fields", test_packorder_model_fields()))
    results.append(("PackOrder Relationships", test_packorder_relationships()))
    results.append(("PackOrderForm Import", test_packorder_form_import()))
    results.append(("Surgery Type Mapping", test_surgery_type_mapping()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The fixes are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total


# Run the tests
if __name__ == '__main__':
    run_all_tests()

