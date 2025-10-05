"""
Simple verification script for pack order fixes
"""

from pharmacy.models import PackOrder

# Test 1: Check if labor_record field exists
print("Test 1: Checking if labor_record field exists in PackOrder model...")
pack_order = PackOrder()

if hasattr(pack_order, 'labor_record'):
    print("PASS: labor_record field exists")
else:
    print("FAIL: labor_record field missing")

if hasattr(pack_order, 'surgery'):
    print("PASS: surgery field exists")
else:
    print("FAIL: surgery field missing")

if hasattr(pack_order, 'patient'):
    print("PASS: patient field exists")
else:
    print("FAIL: patient field missing")

# Test 2: Check if form can be imported
print("\nTest 2: Checking if PackOrderForm can be imported...")
try:
    from pharmacy.forms import PackOrderForm
    print("PASS: PackOrderForm imported successfully")
except Exception as e:
    print(f"FAIL: Could not import PackOrderForm - {e}")

# Test 3: Check if form can be initialized
print("\nTest 3: Checking if PackOrderForm can be initialized...")
try:
    form = PackOrderForm()
    print("PASS: PackOrderForm initialized successfully")
except Exception as e:
    print(f"FAIL: Could not initialize PackOrderForm - {e}")

print("\nAll basic tests completed!")

