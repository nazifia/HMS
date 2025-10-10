#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.template import loader, Context
from django.contrib.auth import get_user_model
import datetime

# Test template rendering
try:
    # Create a mock user
    User = get_user_model()
    mock_user = User(username='testuser', is_staff=False, is_superuser=False)
    mock_user.id = 1
    
    # Create a mock dispensary
    class MockDispensary:
        def __init__(self):
            self.id = 1
            self.name = "Test Dispensary"
            self.location = "Test Location"
            self.description = "Test Description"
            self.manager = None
            self.is_active = True
            self.created_at = datetime.date(2025, 1, 1)
    
    class MockMedication:
        def __init__(self):
            self.id = 1
            self.name = "Test Medication"
            self.generic_name = "Generic"
            self.strength = "500mg"
    
    class MockInventoryItem:
        def __init__(self):
            self.id = 1
            self.medication = MockMedication()
            self.stock_quantity = 10
            self.reorder_level = 5
            self.expiry_date = datetime.date(2025, 12, 31)
            self.batch_number = "BATCH001"
    
    dispensary = MockDispensary()
    
    # Test dispensary inventory template
    context = {
        'dispensary': dispensary,
        'inventory_items': [MockInventoryItem()],
        'can_edit_inventory': False,
        'current_user': mock_user,
        'total_items': 1,
        'in_stock_count': 1,
        'low_stock_count': 0,
        'out_of_stock_count': 0,
        'today': datetime.date(2025, 1, 15),
    }
    
    # Test both templates
    templates_to_test = [
        'pharmacy/dispensary_list.html',
        'pharmacy/dispensary_inventory.html'
    ]
    
    for template_name in templates_to_test:
        try:
            template = loader.get_template(template_name)
            rendered = template.render(context)
            print(f"[OK] {template_name} rendered successfully!")
        except Exception as e:
            print(f"[ERROR] {template_name} error: {e}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"General error: {e}")
    import traceback
    traceback.print_exc()
