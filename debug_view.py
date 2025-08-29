#!/usr/bin/env python
"""
Debug script to check what's happening in the active_store_detail view
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def debug_view():
    """Debug the active_store_detail view"""
    print("🔍 Debugging active_store_detail view...")
    
    try:
        from pharmacy.views import active_store_detail
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
        ).select_related('medication', 'active_store')
        
        print(f"Inventory items count: {inventory_items.count()}")
        
        # Show first few items
        for item in inventory_items[:3]:
            print(f"  - {item.medication.name} (Batch: {item.batch_number}, Quantity: {item.stock_quantity})")
            
        # Check if inventory_items has data
        if inventory_items.exists():
            print("✅ Inventory items found")
        else:
            print("❌ No inventory items found")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    debug_view()