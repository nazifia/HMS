#!/usr/bin/env python
"""
Test script to render the template with test data
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_template_rendering():
    """Test template rendering with test data"""
    print("🔍 Testing template rendering...")
    
    try:
        from django.template.loader import render_to_string
        from pharmacy.models import Dispensary, ActiveStore, ActiveStoreInventory
        
        # Get dispensary
        dispensary = Dispensary.objects.get(id=58)
        print(f"Dispensary: {dispensary.name}")
        
        # Get active store
        active_store = getattr(dispensary, 'active_store', None)
        if not active_store:
            print("❌ No active store found")
            return False
            
        print(f"Active Store: {active_store.name}")
        
        # Get inventory items
        inventory_items = ActiveStoreInventory.objects.filter(
            active_store=active_store
        ).select_related('medication', 'active_store')[:3]  # Just first 3 for testing
        
        print(f"Inventory items count: {inventory_items.count()}")
        
        # Create context
        context = {
            'active_store': active_store,
            'dispensary': dispensary,
            'inventory_items': inventory_items,
            'page_title': f'Active Store - {active_store.name}',
            'active_nav': 'pharmacy',
        }
        
        # Render template
        rendered = render_to_string('pharmacy/active_store_detail.html', context)
        
        # Check if key elements are in the rendered template
        print(f"Template contains 'transfer-btn': {'transfer-btn' in rendered}")
        print(f"Template contains 'transferModal': {'transferModal' in rendered}")
        print(f"Template contains 'Transfer Medication': {'Transfer Medication' in rendered}")
        
        if 'transfer-btn' in rendered:
            print("✅ Transfer buttons found in rendered template")
        else:
            print("❌ Transfer buttons NOT found in rendered template")
            # Show part of the rendered template
            print(f"Last 1000 characters of rendered template:\n{rendered[-1000:]}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_template_rendering()