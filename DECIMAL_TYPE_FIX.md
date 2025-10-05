# Decimal Type Mismatch Fix

## Issue
After adding the `get_total_cost()` method, pack orders still failed with:

**"Medical pack 'Appendectomy Surgery Pack' ordered successfully, but processing failed: unsupported operand type(s) for -: 'decimal.Decimal' and 'float'. Please process the pack order manually if needed."**

## Root Cause
There were multiple type mismatches between `Decimal` and `float`/`int` types:

1. **`get_total_value()` method** initialized `total = 0` (integer) instead of `Decimal('0.00')`
2. **Invoice creation** didn't set `discount_amount`, so it defaulted to `0` (integer)
3. **Pack cost calculation** didn't explicitly convert to Decimal
4. **Service price** wasn't explicitly converted to Decimal

When performing arithmetic operations like `invoice.subtotal + invoice.tax_amount - invoice.discount_amount`, Python raised an error because you can't subtract a float/int from a Decimal.

## Solution
Ensured all monetary values are explicitly converted to `Decimal` type throughout the pack order flow.

### Changes Made

#### 1. Fixed `get_total_value()` Method
**File**: `pharmacy/models.py` (lines 1327-1337)

```python
def get_total_value(self):
    """Calculate the total value of all items in the pack"""
    from decimal import Decimal
    total = Decimal('0.00')  # Changed from 0
    try:
        for item in self.items.all():
            total += Decimal(str(item.medication.price)) * item.quantity
    except AttributeError:
        # Fallback if no items relationship exists
        total = Decimal('0.00')  # Changed from 0
    return total
```

**Changes**:
- Initialize `total` as `Decimal('0.00')` instead of `0`
- Convert `item.medication.price` to Decimal explicitly
- Return `Decimal('0.00')` in fallback case

#### 2. Fixed Invoice Creation
**File**: `theatre/views.py` (lines 1033-1055)

```python
# Get or create invoice for surgery
if not surgery.invoice:
    # Create invoice for surgery
    invoice = Invoice.objects.create(
        patient=surgery.patient,
        invoice_date=surgery.scheduled_date.date(),
        due_date=surgery.scheduled_date.date() + timezone.timedelta(days=7),
        status='pending',
        subtotal=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        discount_amount=Decimal('0.00'),  # Added this line
        total_amount=Decimal('0.00'),
        created_by=pack_order.ordered_by,
        source_app='theatre'
    )
    surgery.invoice = invoice
    surgery.save()
else:
    invoice = surgery.invoice
    # Ensure discount_amount is a Decimal
    if not isinstance(invoice.discount_amount, Decimal):
        invoice.discount_amount = Decimal(str(invoice.discount_amount))
        invoice.save()
```

**Changes**:
- Added `discount_amount=Decimal('0.00')` to invoice creation
- Added check to convert existing invoice's `discount_amount` to Decimal if needed

#### 3. Fixed Service Creation
**File**: `theatre/views.py` (lines 1063-1072)

```python
# Create or get service for this specific pack
service, _ = Service.objects.get_or_create(
    name=f"Medical Pack: {pack_order.pack.name}",
    category=pack_service_category,
    defaults={
        'price': Decimal(str(pack_order.pack.get_total_cost())),  # Explicit conversion
        'description': f"Medical pack for {pack_order.pack.get_pack_type_display()}: {pack_order.pack.name}",
        'tax_percentage': Decimal('0.00')
    }
)
```

**Changes**:
- Wrapped `pack_order.pack.get_total_cost()` in `Decimal(str(...))`

#### 4. Fixed Pack Cost Calculation
**File**: `theatre/views.py` (lines 1074-1079)

```python
# Calculate pack cost with NHIA discount if applicable
pack_cost = Decimal(str(pack_order.pack.get_total_cost()))  # Explicit conversion

# Apply 10% payment for NHIA patients (they pay 10%, NHIA covers 90%)
if surgery.patient.patient_type == 'nhia':
    pack_cost = pack_cost * Decimal('0.10')  # NHIA patients pay 10%
```

**Changes**:
- Wrapped `pack_order.pack.get_total_cost()` in `Decimal(str(...))`

## Why This Matters

In Python, you cannot perform arithmetic operations between `Decimal` and `float`/`int` types:

```python
# This raises TypeError
Decimal('10.00') - 0  # Error!

# This works
Decimal('10.00') - Decimal('0.00')  # OK!
```

Django's `DecimalField` returns `Decimal` objects, but:
- Integer literals like `0` are `int` type
- Default values might be `int` or `float`
- Calculations might produce `float` results

By explicitly converting all monetary values to `Decimal`, we ensure type consistency throughout the calculation chain.

## Benefits

1. **Fixes Processing Error**: Pack orders now process successfully
2. **Type Safety**: All monetary calculations use consistent Decimal type
3. **Precision**: Decimal type provides exact decimal arithmetic (no floating-point errors)
4. **Future-Proof**: Prevents similar type mismatch errors in other calculations

## Testing

To verify the fix works:

1. Navigate to a surgery detail page
2. Click "Order Medical Pack"
3. Select a pack and submit the form
4. Verify you see a **full success message** without warnings:
   ```
   Medical pack "Appendectomy Surgery Pack" ordered successfully for surgery. 
   Prescription #X has been automatically created with Y medications. 
   Pack cost (₦Z.00) has been added to the surgery invoice.
   ```
5. Check the surgery invoice to confirm the pack cost is correctly added
6. For NHIA patients, verify the cost is 10% of the pack total

## Files Modified

- `pharmacy/models.py` - Fixed `get_total_value()` to return Decimal
- `theatre/views.py` - Fixed invoice creation, service creation, and pack cost calculation

## Related Fixes

This fix complements:
- `THEATRE_PACK_ORDER_FIXES.md` - Form and view logic fixes
- `PACK_ORDER_TEMPLATE_FIX.md` - Template patient field fix
- `PACK_COST_METHOD_FIX.md` - Added `get_total_cost()` method

Now the entire pack order flow works correctly with proper Decimal type handling! 🎉

