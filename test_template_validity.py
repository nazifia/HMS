#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.insert(0, os.path.dirname(__file__file__))

django.setup()

from django.template import loader, Context

def test_template_parsing():
    """Test template parsing for syntax errors"""
    try:
        template = loader.get_template('pharmacy/dispensary_inventory.html')
        print("✅ Template parsed successfully!")
        return True
    except Exception as e:
        print(f"❌ Template parsing error: {e}")
        return False

def test_template_rendering():
    """Test template rendering with mock data"""
    try:
        template = loader.get_template('pharmacy/dispensary_inventory.html')
        
        # Create mock context
        context = {
            'dispensary': {'name': 'Test Dispensary'},
            'inventory_items': [],
            'can_edit_inventory': False,
            'current_user': None,
        }
        
        from django.template import RequestContext
        request = type('DummyRequest', {}, {})
        
        try:
            rendered = template.render(context)
            print("[OK] Template renders successfully!")
            return True
        except Exception as e:
            print(f"[ERROR] Template rendering error: {e}")
            return False

def get_mock_context():
    """Create a mock context for testing"""
    from django.contrib.auth import get_user_model
    import datetime
    
    User = get_user_model()
    
    User = User(username='testuser', is_staff=False, is_superuser=False)
    User.id = 1
    
    class MockMedication:
        def __init__(self):
            self.id = 1
            self.name = "Test Medication"
            self.generic_name = "Generic"
            self.strength = "500mg"
            self.batch_number = "BATCH001"
    
    class MockInventoryItem:
        def __init__(self):
            self.id = 1
            self.medication = MockMedication()
            self.stock_quantity = 10
            self.reorder_level = 5
            self.expiry_date = datetime.date(2025, 12, 31)
            self.batch_number = "BATCH001"
            self.item.source = 'active_store'
    
    class MockDispensary:
        def __init__(self):
            self.id = 1
            self.name = "Test Dispensary"
            self.location = "Test Location"
            self.manager = None
            self.is_active = True
    
    context = {
        'dispensary': MockDispensary(),
        'inventory_items': [MockInventoryItem()],
        'can_edit_inventory': False,
        'current_user': User,
        'total_items': 1,
        'in_stock_count': 1,
        'low_stock_count': 0,
        'out_of_stock_count': 0,
        'today': datetime.date(2025, 1, 15),
    }
    
    return context

def test_template_parsing():
    """Test template parsing for syntax errors"""
    return test_template_parsing()

def test_template_rendering():
    """Test template rendering with mock view data"""
    context = get_mock_context()
    return test_template_rendering()

if __name__main__ == '__main__':
    print("Testing template syntax...")
    
    parsing_ok = test_template_parsing()
    
    if parsing_ok:
        print("\nTesting template rendering with mock data...")
        rendering_ok = test_template_rendering()
        
        if rendering_ok:
            print("\n✅ All template syntax errors fixed!")
        else:
            print(f"\n❌ Rendering issues found!")
    else:
        print(f"\n❌ Template parsing issues found!")
        
    print("\nTest completed.")
