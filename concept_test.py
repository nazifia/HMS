#!/usr/bin/env python
"""
Concept test to demonstrate the transfer logic from active store to dispensary

This script demonstrates the concept of moving medications from the active store 
to the respective dispensary when processing pack orders.
"""

from decimal import Decimal
from datetime import datetime, timedelta

def demonstrate_transfer_logic():
    """Demonstrate the transfer logic concept"""
    print("🧪 Transfer Logic Concept Demonstration")
    print("=" * 40)
    
    # Initial inventory setup
    print("\n1️⃣ Initial Inventory Setup")
    inventory = {
        'bulk_store': {
            'Surgical Gauze': 100,
            'Antiseptic Solution': 50
        },
        'active_store': {
            'Surgical Gauze': 20,
            'Antiseptic Solution': 10
        },
        'dispensary': {
            'Surgical Gauze': 0,
            'Antiseptic Solution': 0
        }
    }
    
    # Print initial inventory
    print("   Initial Inventory:")
    print(f"   - Bulk Store: {inventory['bulk_store']}")
    print(f"   - Active Store: {inventory['active_store']}")
    print(f"   - Dispensary: {inventory['dispensary']}")
    
    # Medical pack requirements
    print("\n2️⃣ Medical Pack Requirements")
    pack_requirements = {
        'Surgical Gauze': 15,
        'Antiseptic Solution': 5
    }
    print(f"   Pack requires: {pack_requirements}")
    
    # Check if active store has enough inventory
    print("\n3️⃣ Checking Active Store Inventory")
    missing_items = []
    for medication, required_qty in pack_requirements.items():
        available_qty = inventory['active_store'][medication]
        if available_qty < required_qty:
            shortage = required_qty - available_qty
            missing_items.append({
                'medication': medication,
                'required': required_qty,
                'available': available_qty,
                'shortage': shortage
            })
            print(f"   - {medication}: Need {required_qty}, have {available_qty}, shortage: {shortage}")
        else:
            print(f"   - {medication}: Need {required_qty}, have {available_qty} ✓")
    
    # Transfer from bulk store to active store if needed
    print("\n4️⃣ Transferring from Bulk Store to Active Store")
    if missing_items:
        for item in missing_items:
            medication = item['medication']
            shortage = item['shortage']
            
            # Check if bulk store has enough
            if inventory['bulk_store'][medication] >= shortage:
                # Transfer medication
                inventory['bulk_store'][medication] -= shortage
                inventory['active_store'][medication] += shortage
                print(f"   - Transferred {shortage} {medication} from bulk store to active store")
            else:
                print(f"   - Insufficient {medication} in bulk store")
    else:
        print("   - No transfer needed from bulk store")
    
    # Update inventory after bulk to active transfer
    print("\n5️⃣ Inventory After Bulk to Active Transfer")
    print(f"   - Bulk Store: {inventory['bulk_store']}")
    print(f"   - Active Store: {inventory['active_store']}")
    print(f"   - Dispensary: {inventory['dispensary']}")
    
    # Now transfer from active store to dispensary
    print("\n6️⃣ Transferring from Active Store to Dispensary")
    for medication, required_qty in pack_requirements.items():
        # Check if dispensary already has enough
        if inventory['dispensary'][medication] < required_qty:
            # Calculate how much more is needed
            needed_qty = required_qty - inventory['dispensary'][medication]
            
            # Check if active store has enough
            if inventory['active_store'][medication] >= needed_qty:
                # Transfer medication
                inventory['active_store'][medication] -= needed_qty
                inventory['dispensary'][medication] += needed_qty
                print(f"   - Transferred {needed_qty} {medication} from active store to dispensary")
            else:
                print(f"   - Insufficient {medication} in active store")
    
    # Final inventory
    print("\n7️⃣ Final Inventory")
    print(f"   - Bulk Store: {inventory['bulk_store']}")
    print(f"   - Active Store: {inventory['active_store']}")
    print(f"   - Dispensary: {inventory['dispensary']}")
    
    # Verify that dispensary has enough for the pack
    print("\n8️⃣ Verification")
    all_available = True
    for medication, required_qty in pack_requirements.items():
        if inventory['dispensary'][medication] >= required_qty:
            print(f"   - {medication}: Required {required_qty}, Available {inventory['dispensary'][medication]} ✓")
        else:
            print(f"   - {medication}: Required {required_qty}, Available {inventory['dispensary'][medication]} ✗")
            all_available = False
    
    if all_available:
        print("\n✅ Transfer Logic Working Correctly!")
        print("   The system successfully moved medications from bulk store to active store,")
        print("   and then from active store to dispensary as needed.")
    else:
        print("\n❌ Transfer Logic Issues!")
        print("   The system was unable to ensure sufficient inventory in the dispensary.")
    
    return all_available

if __name__ == '__main__':
    try:
        success = demonstrate_transfer_logic()
        if success:
            print("\n🎉 Transfer logic concept is working!")
        else:
            print("\n❌ Transfer logic concept needs attention.")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()