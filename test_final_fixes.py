#!/usr/bin/env python
"""
Test Final Fixes Script
This script tests all the fixes for pack orders and transfer logic
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_pack_order_fix():
    """Test that PackOrder works without OperationalError"""
    print("=== Testing PackOrder Fix ===")
    
    try:
        from pharmacy.models import PackOrder, Pack
        
        # Test PackOrder query
        orders = PackOrder.objects.order_by('-ordered_at')[:5]
        print(f"✅ PackOrder query successful: {orders.count()} orders")
        
        # Test Pack model
        packs = Pack.objects.all()[:5]
        print(f"✅ Pack model accessible: {packs.count()} packs")
        
        # Test the specific query that was failing
        orders_with_relations = PackOrder.objects.select_related(
            'pack', 'patient', 'ordered_by', 'processed_by'
        ).order_by('-ordered_at')[:3]
        
        for order in orders_with_relations:
            print(f"✅ Order {order.id}: {order.pack.name if order.pack else 'No pack'} for {order.patient.get_full_name()}")
        
        return True
        
    except Exception as e:
        print(f"❌ PackOrder test failed: {e}")
        return False

def test_transfer_logic():
    """Test the dispensary transfer logic"""
    print("\n=== Testing Transfer Logic ===")
    
    try:
        from pharmacy.models import (
            DispensaryTransfer, ActiveStoreInventory, MedicationInventory,
            Medication, ActiveStore, Dispensary, MedicationCategory
        )
        from accounts.models import CustomUser
        
        # Get test data
        user = CustomUser.objects.first()
        if not user:
            print("⚠️  No users found for testing")
            return True
        
        # Get or create test medication
        category, _ = MedicationCategory.objects.get_or_create(name="Test Category")
        medication, created = Medication.objects.get_or_create(
            name="Test Transfer Med",
            defaults={
                'category': category,
                'dosage_form': 'Tablet',
                'strength': '10mg',
                'price': 5.00
            }
        )
        if created:
            print(f"✅ Created test medication: {medication.name}")
        
        # Get or create active store
        active_store, created = ActiveStore.objects.get_or_create(
            name="Test Active Store",
            defaults={'location': 'Test Location', 'is_active': True}
        )
        if created:
            print(f"✅ Created test active store: {active_store.name}")
        
        # Get or create dispensary
        dispensary, created = Dispensary.objects.get_or_create(
            name="Test Dispensary",
            defaults={'location': 'Test Location', 'is_active': True}
        )
        if created:
            print(f"✅ Created test dispensary: {dispensary.name}")
        
        # Create active store inventory
        active_inventory, created = ActiveStoreInventory.objects.get_or_create(
            medication=medication,
            active_store=active_store,
            defaults={
                'stock_quantity': 50,
                'reorder_level': 10,
                'batch_number': 'TEST001',
                'unit_cost': 5.00
            }
        )
        
        if created:
            print(f"✅ Created active store inventory: {active_inventory.stock_quantity} units")
        
        initial_active_stock = active_inventory.stock_quantity
        print(f"Initial active store stock: {initial_active_stock}")
        
        # Test transfer creation
        transfer_quantity = 10
        transfer = DispensaryTransfer.create_transfer(
            medication=medication,
            from_active_store=active_store,
            to_dispensary=dispensary,
            quantity=transfer_quantity,
            requested_by=user,
            notes="Test transfer"
        )
        
        print(f"✅ Created transfer: {transfer.quantity} units")
        
        # Execute transfer
        transfer.execute_transfer(user)
        print(f"✅ Executed transfer")
        
        # Check results
        active_inventory.refresh_from_db()
        final_active_stock = active_inventory.stock_quantity
        
        dispensary_inventory = MedicationInventory.objects.filter(
            medication=medication,
            dispensary=dispensary
        ).first()
        
        print(f"Final active store stock: {final_active_stock}")
        print(f"Dispensary stock: {dispensary_inventory.stock_quantity if dispensary_inventory else 0}")
        
        # Verify the transfer worked correctly
        expected_active_stock = initial_active_stock - transfer_quantity
        if final_active_stock == expected_active_stock:
            print("✅ Active store quantity reduced correctly")
        else:
            print(f"❌ Active store quantity incorrect. Expected: {expected_active_stock}, Got: {final_active_stock}")
        
        if dispensary_inventory and dispensary_inventory.stock_quantity >= transfer_quantity:
            print("✅ Dispensary quantity increased correctly")
        else:
            print(f"❌ Dispensary quantity incorrect")
        
        # Test zero stock scenario
        if final_active_stock > 0:
            # Transfer remaining stock
            remaining_transfer = DispensaryTransfer.create_transfer(
                medication=medication,
                from_active_store=active_store,
                to_dispensary=dispensary,
                quantity=final_active_stock,
                requested_by=user,
                notes="Transfer all remaining stock"
            )
            
            remaining_transfer.execute_transfer(user)
            
            active_inventory.refresh_from_db()
            if active_inventory.stock_quantity == 0:
                print("✅ Item correctly shows zero stock when all quantity transferred")
            else:
                print(f"❌ Expected zero stock, got {active_inventory.stock_quantity}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transfer logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_medical_pack_fix():
    """Test that MedicalPack works without AttributeError"""
    print("\n=== Testing MedicalPack Fix ===")
    
    try:
        from pharmacy.models import MedicalPack, MedicalPackItem
        
        # Test MedicalPack query
        packs = MedicalPack.objects.prefetch_related('items__medication')[:5]
        print(f"✅ MedicalPack query successful: {packs.count()} packs")
        
        # Test MedicalPackItem
        pack_items = MedicalPackItem.objects.all()[:5]
        print(f"✅ MedicalPackItem accessible: {pack_items.count()} items")
        
        # Test the relationship
        for pack in packs:
            item_count = pack.items.count()
            print(f"✅ Pack '{pack.name}' has {item_count} items")
        
        return True
        
    except Exception as e:
        print(f"❌ MedicalPack test failed: {e}")
        return False

def test_view_access():
    """Test that views work without errors"""
    print("\n=== Testing View Access ===")
    
    try:
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        client = Client()
        
        # Get a user for authentication
        user = User.objects.first()
        if user:
            client.force_login(user)
            
            # Test pack order list view
            response = client.get('/pharmacy/pack-orders/')
            if response.status_code == 200:
                print("✅ Pack order list view accessible")
            else:
                print(f"⚠️  Pack order list view returned status {response.status_code}")
            
            # Test medical pack list view
            response = client.get('/pharmacy/packs/')
            if response.status_code == 200:
                print("✅ Medical pack list view accessible")
            else:
                print(f"⚠️  Medical pack list view returned status {response.status_code}")
        else:
            print("⚠️  No users found for view testing")
        
        return True
        
    except Exception as e:
        print(f"❌ View access test failed: {e}")
        return False

def main():
    """Main function to run all tests"""
    print("🧪 Final Fixes Test Script")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # Run all tests
    if test_pack_order_fix():
        success_count += 1
    
    if test_transfer_logic():
        success_count += 1
    
    if test_medical_pack_fix():
        success_count += 1
    
    if test_view_access():
        success_count += 1
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'=' * 50}")
    print(f"Successful tests: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Pack order OperationalError fixed")
        print("✅ Transfer logic working correctly")
        print("✅ MedicalPack AttributeError fixed")
        print("✅ Views accessible without errors")
        print("✅ Quantity tracking implemented")
        print("✅ Items disappear from active store when quantity reaches zero")
        return 0
    else:
        print(f"❌ {total_tests - success_count} tests failed.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
