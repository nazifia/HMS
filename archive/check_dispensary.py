#!/usr/bin/env python
"""
Check if dispensary 58 has an active store
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary, ActiveStore

try:
    dispensary = Dispensary.objects.get(id=58)
    print(f'Dispensary: {dispensary.name}')
    
    active_store = getattr(dispensary, 'active_store', None)
    if active_store:
        print(f'Active Store: {active_store.name}')
        print(f'Active Store ID: {active_store.id}')
    else:
        print('No active store found for this dispensary')
        
    # Check if there are inventory items
    if active_store:
        from pharmacy.models import ActiveStoreInventory
        inventory_items = ActiveStoreInventory.objects.filter(active_store=active_store)
        print(f'Inventory items count: {inventory_items.count()}')
        for item in inventory_items[:5]:  # Show first 5 items
            print(f'  - {item.medication.name} (Batch: {item.batch_number}, Quantity: {item.stock_quantity})')
        
except Exception as e:
    print(f'Error: {e}')