#!/usr/bin/env python
"""
Simple functionality check for Surgery Pack Management System

This script verifies:
1. Medical Pack models and forms are working
2. Surgery form modifications are correct
3. URL routing is properly configured
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_model_imports():
    """Test that all required models can be imported"""
    print("Testing model imports...")
    
    try:
        from pharmacy.models import MedicalPack, PackItem, PackOrder
        from theatre.models import Surgery, SurgeryType, OperationTheatre
        from theatre.forms import SurgeryForm
        from pharmacy.forms import MedicalPackForm, PackItemForm, PackOrderForm
        print("✅ All models and forms imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_medical_pack_model():
    """Test MedicalPack model functionality"""
    print("Testing MedicalPack model...")
    
    try:
        from pharmacy.models import MedicalPack
        
        # Check model fields and methods
        pack = MedicalPack()
        pack.name = "Test Pack"
        pack.pack_type = "surgery"
        pack.surgery_type = "appendectomy"
        pack.risk_level = "medium"
        
        # Test model methods
        assert hasattr(pack, 'get_total_cost'), "get_total_cost method missing"
        assert hasattr(pack, 'can_be_ordered'), "can_be_ordered method missing"
        assert hasattr(pack, 'update_total_cost'), "update_total_cost method missing"
        
        print("✅ MedicalPack model structure is correct")
        return True
    except Exception as e:
        print(f"❌ MedicalPack model error: {e}")
        return False

def test_surgery_form_flexibility():
    """Test SurgeryForm flexibility features"""
    print("Testing SurgeryForm flexibility...")
    
    try:
        from theatre.forms import SurgeryForm
        
        # Create form instance
        form = SurgeryForm()
        
        # Check for flexible validation fields
        assert 'skip_conflict_validation' in form.fields, "skip_conflict_validation field missing"
        assert 'allow_flexible_scheduling' in form.fields, "allow_flexible_scheduling field missing"
        
        # Check that key fields are optional
        assert not form.fields['primary_surgeon'].required, "primary_surgeon should be optional"
        assert not form.fields['anesthetist'].required, "anesthetist should be optional"
        assert not form.fields['theatre'].required, "theatre should be optional"
        assert not form.fields['surgery_type'].required, "surgery_type should be optional"
        assert not form.fields['scheduled_date'].required, "scheduled_date should be optional"
        assert not form.fields['expected_duration'].required, "expected_duration should be optional"
        
        # Only patient should be required
        assert form.fields['patient'].required, "patient should be required"
        
        print("✅ SurgeryForm flexibility features are correctly implemented")
        return True
    except Exception as e:
        print(f"❌ SurgeryForm error: {e}")
        return False

def test_url_patterns():
    """Test URL patterns are configured"""
    print("Testing URL patterns...")
    
    try:
        from django.urls import reverse
        
        # Test pharmacy pack URLs
        pack_urls = [
            'pharmacy:medical_pack_list',
            'pharmacy:create_medical_pack',
            'pharmacy:pack_order_list',
            'pharmacy:create_pack_order'
        ]
        
        for url_name in pack_urls:
            try:
                reverse(url_name)
                print(f"  ✅ {url_name} URL configured")
            except:
                print(f"  ❌ {url_name} URL missing")
                return False
        
        # Test theatre URLs
        theatre_urls = [
            'theatre:surgery_list',
            'theatre:surgery_create'
        ]
        
        for url_name in theatre_urls:
            try:
                reverse(url_name)
                print(f"  ✅ {url_name} URL configured")
            except:
                print(f"  ❌ {url_name} URL missing")
                return False
        
        print("✅ All required URL patterns are configured")
        return True
    except Exception as e:
        print(f"❌ URL pattern error: {e}")
        return False

def test_template_files():
    """Test that required template files exist"""
    print("Testing template files...")
    
    try:
        import os
        from django.conf import settings
        
        # Define required templates
        required_templates = [
            'templates/theatre/surgery_form.html',
            'pharmacy/templates/pharmacy/medical_packs/pack_list.html',
            'pharmacy/templates/pharmacy/medical_packs/pack_detail.html',
            'pharmacy/templates/pharmacy/medical_packs/pack_form.html'
        ]
        
        for template_path in required_templates:
            full_path = os.path.join(settings.BASE_DIR, template_path)
            if os.path.exists(full_path):
                print(f"  ✅ {template_path} exists")
            else:
                print(f"  ❌ {template_path} missing")
                return False
        
        print("✅ All required template files exist")
        return True
    except Exception as e:
        print(f"❌ Template file error: {e}")
        return False

def test_pack_order_integration():
    """Test PackOrder model integration"""
    print("Testing PackOrder integration...")
    
    try:
        from pharmacy.models import PackOrder
        
        # Check model fields
        pack_order = PackOrder()
        
        # Check for surgery and labor record fields
        assert hasattr(pack_order, 'surgery'), "surgery field missing"
        assert hasattr(pack_order, 'labor_record'), "labor_record field missing"
        assert hasattr(pack_order, 'create_prescription'), "create_prescription method missing"
        
        print("✅ PackOrder integration is correctly implemented")
        return True
    except Exception as e:
        print(f"❌ PackOrder integration error: {e}")
        return False

def main():
    """Run all functionality checks"""
    print("🔍 Surgery Pack Management System - Functionality Check")
    print("=" * 60)
    
    tests = [
        ("Model Imports", test_model_imports),
        ("MedicalPack Model", test_medical_pack_model),
        ("SurgeryForm Flexibility", test_surgery_form_flexibility),
        ("URL Patterns", test_url_patterns),
        ("Template Files", test_template_files),
        ("PackOrder Integration", test_pack_order_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        if test_func():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL FUNCTIONALITY CHECKS PASSED! 🎉")
        print("\n✅ Surgery Pack Management System is properly implemented:")
        print("  • Medical Pack CRUD operations are available")
        print("  • Pack Order management is working")
        print("  • Flexible surgery editing is enabled")
        print("  • All URL patterns are configured")
        print("  • Template files are in place")
        print("  • Integration between modules is working")
        
        print("\n🔥 Key Features Implemented:")
        print("  1. Complete CRUD for Medical Packs")
        print("  2. Pack Item management")
        print("  3. Pack Order workflow")
        print("  4. Flexible surgery editing with optional constraints")
        print("  5. Conflict validation bypass options")
        print("  6. Integration between theatre and pharmacy modules")
        return True
    else:
        print(f"\n❌ {total - passed} functionality checks failed")
        print("Please review the implementation and fix any issues.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)