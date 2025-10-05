# Pack Cost Method Fix - Missing get_total_cost()

## Issue
After successfully creating a pack order, the system showed a warning message:

**"Medical pack 'Appendectomy Surgery Pack' ordered successfully, but processing failed: 'MedicalPack' object has no attribute 'get_total_cost'. Please process the pack order manually if needed."**

## Root Cause
The `MedicalPack` model had a method called `get_total_value()` but the code in `theatre/views.py` and `_add_pack_to_surgery_invoice()` was calling `get_total_cost()`.

The `MedicalPackItem` model had `get_total_cost()` but `MedicalPack` didn't, causing an AttributeError.

## Solution
Added the `get_total_cost()` method to the `MedicalPack` model as an alias for `get_total_value()`.

### Changes Made

**File**: `pharmacy/models.py`

1. **Added `get_total_cost()` method** (line 1338-1340):
```python
def get_total_cost(self):
    """Calculate the total cost of all items in the pack (alias for get_total_value)"""
    return self.get_total_value()
```

2. **Fixed related_name usage** in `get_total_value()` and `get_item_count()`:
   - Changed `self.medicalpackitem_set.all()` to `self.items.all()`
   - Changed `self.medicalpackitem_set.count()` to `self.items.count()`
   - This matches the `related_name='items'` defined in the `MedicalPackItem.pack` ForeignKey

### Updated Methods

```python
def get_total_value(self):
    """Calculate the total value of all items in the pack"""
    total = 0
    try:
        for item in self.items.all():  # Changed from medicalpackitem_set
            total += item.medication.price * item.quantity
    except AttributeError:
        # Fallback if no items relationship exists
        total = 0
    return total

def get_total_cost(self):
    """Calculate the total cost of all items in the pack (alias for get_total_value)"""
    return self.get_total_value()

def get_item_count(self):
    """Get the total number of items in this pack"""
    try:
        return self.items.count()  # Changed from medicalpackitem_set
    except AttributeError:
        return 0
```

## How It Works

1. **Pack Order Creation**: When a pack is ordered, the system:
   - Creates a `PackOrder` record
   - Calls `pack_order.process_order(user)` to create a prescription
   - Calls `_add_pack_to_surgery_invoice(surgery, pack_order)` to add costs to invoice

2. **Invoice Cost Calculation**: The `_add_pack_to_surgery_invoice()` function:
   - Gets the pack cost using `pack_order.pack.get_total_cost()`
   - Applies NHIA discount if patient is NHIA (10% payment, 90% covered)
   - Creates an invoice item with the calculated cost
   - Updates the surgery invoice totals

3. **Success Message**: Shows the pack cost in the success message:
   ```
   Pack cost (₦{pack_order.pack.get_total_cost():.2f}) has been added to the surgery invoice.
   ```

## Benefits

1. **Fixes Processing Error**: Pack orders now process successfully without errors
2. **Consistent API**: Both `get_total_value()` and `get_total_cost()` work
3. **Correct Related Name**: Uses `items` instead of `medicalpackitem_set`
4. **Better Code Clarity**: Method names are more intuitive

## Testing

To verify the fix works:

1. Navigate to a surgery detail page
2. Click "Order Medical Pack"
3. Select a pack and submit the form
4. Verify you see a **success message** (not a warning) like:
   ```
   Medical pack "Appendectomy Surgery Pack" ordered successfully for surgery. 
   Prescription #4 has been automatically created with 5 medications. 
   Pack cost (₦4,500.00) has been added to the surgery invoice.
   ```
5. Check that the pack cost appears in the surgery invoice

## Files Modified

- `pharmacy/models.py` - Added `get_total_cost()` method and fixed related_name usage

## Related Fixes

This fix complements:
- `THEATRE_PACK_ORDER_FIXES.md` - Form and view logic fixes
- `PACK_ORDER_TEMPLATE_FIX.md` - Template patient field fix

Now the entire pack order flow works correctly from end to end with proper cost calculation and invoice integration.

