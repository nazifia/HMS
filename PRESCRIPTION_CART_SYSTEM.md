# Prescription Cart System - Complete Implementation Guide

## Overview

The Prescription Cart System provides a shopping cart-like workflow for prescription dispensing. This allows pharmacists to:
1. **Create a cart** from prescription items
2. **Review and adjust quantities** based on availability
3. **Select dispensary** for stock checking
4. **Generate invoice** from cart
5. **Process payment**
6. **Complete dispensing** after payment

This separates the billing/invoice creation from the actual dispensing, providing better control and accuracy.

## Architecture

### Database Models

#### PrescriptionCart
- **Purpose**: Container for prescription items being prepared for billing
- **Fields**:
  - `prescription` - FK to Prescription
  - `created_by` - FK to User (pharmacist)
  - `dispensary` - FK to Dispensary (selected for dispensing)
  - `status` - active, invoiced, paid, completed, cancelled
  - `invoice` - FK to pharmacy_billing.Invoice (created from cart)
  - `notes` - Optional notes
  - `created_at`, `updated_at` - Timestamps

#### PrescriptionCartItem
- **Purpose**: Individual medication item in cart
- **Fields**:
  - `cart` - FK to PrescriptionCart
  - `prescription_item` - FK to PrescriptionItem
  - `quantity` - Quantity to dispense/bill
  - `unit_price` - Price at time of adding to cart
  - `available_stock` - Cached stock availability
  - `created_at`, `updated_at` - Timestamps

### Key Features

1. **Real-time Stock Checking**
   - Updates when dispensary is selected
   - Shows available, partial, or out-of-stock status
   - Color-coded indicators

2. **NHIA Support**
   - Automatic 10% patient / 90% NHIA calculation
   - Clear breakdown in cart summary
   - Applied to actual cart quantities

3. **Quantity Adjustment**
   - AJAX-based quantity updates
   - Real-time total recalculation
   - Validation against prescribed quantities

4. **Invoice Generation**
   - Creates invoice based on cart items
   - Uses actual quantities in cart
   - Applies NHIA discount if applicable

5. **Dispensing Completion**
   - Only after payment is completed
   - Updates inventory
   - Creates dispensing logs
   - Updates prescription status

## Complete Workflow

### Step 1: Create Cart from Prescription

**URL**: `/pharmacy/cart/create/<prescription_id>/`

**Process**:
1. Pharmacist clicks "Create Billing Cart" on prescription detail page
2. System creates new `PrescriptionCart`
3. Adds all undispensed prescription items to cart
4. Redirects to cart view

**Code**:
```python
cart = PrescriptionCart.objects.create(
    prescription=prescription,
    created_by=request.user
)

for p_item in prescription.items.filter(is_dispensed=False):
    PrescriptionCartItem.objects.create(
        cart=cart,
        prescription_item=p_item,
        quantity=p_item.remaining_quantity_to_dispense,
        unit_price=p_item.medication.price
    )
```

### Step 2: View and Manage Cart

**URL**: `/pharmacy/cart/<cart_id>/`

**Features**:
- View all cart items
- Select dispensary
- Adjust quantities
- Remove items
- See real-time totals
- Check stock availability

**Actions Available**:
- Update dispensary (triggers stock check)
- Update item quantities (AJAX)
- Remove items
- Generate invoice
- Cancel cart

### Step 3: Select Dispensary

**Process**:
1. Pharmacist selects dispensary from dropdown
2. System updates cart.dispensary
3. Updates available_stock for all cart items
4. Shows stock status for each item

**Stock Status Indicators**:
- 🟢 **Available** - Sufficient stock
- 🟡 **Partial** - Some stock available
- 🔴 **Out of Stock** - No stock

### Step 4: Adjust Quantities

**AJAX Endpoint**: `/pharmacy/cart/item/<item_id>/update-quantity/`

**Process**:
1. Pharmacist changes quantity in input field
2. AJAX call updates quantity
3. System recalculates:
   - Item subtotal
   - Item patient pays (10% if NHIA)
   - Item NHIA covers (90% if NHIA)
   - Cart subtotal
   - Cart patient payable
   - Cart NHIA coverage
4. Updates displayed totals without page reload

**Validation**:
- Quantity must be > 0
- Quantity must not exceed remaining quantity to dispense
- Stock availability checked

### Step 5: Generate Invoice

**URL**: `/pharmacy/cart/<cart_id>/generate-invoice/`

**Pre-conditions**:
- Cart status must be 'active'
- Cart must have items
- Dispensary must be selected
- All items must have sufficient stock

**Process**:
1. Calculate patient payable amount from cart
2. Create `pharmacy_billing.Invoice` using `create_pharmacy_invoice()`
3. Update cart status to 'invoiced'
4. Link invoice to cart
5. Redirect to payment page

**Invoice Amount Calculation**:
```python
# Calculate total from cart items
subtotal = sum(item.get_subtotal() for item in cart.items.all())

# Apply NHIA discount if applicable
if cart.prescription.patient.is_nhia_patient():
    patient_payable = subtotal * Decimal('0.10')  # 10%
else:
    patient_payable = subtotal  # 100%

# Create invoice
invoice = create_pharmacy_invoice(request, cart.prescription, patient_payable)
```

### Step 6: Process Payment

**URL**: `/pharmacy/prescriptions/<prescription_id>/payment/`

**Process**:
1. Patient/billing office processes payment
2. Invoice status updated to 'paid'
3. Cart status updated to 'paid'
4. Ready for dispensing

### Step 7: Complete Dispensing

**URL**: `/pharmacy/cart/<cart_id>/complete-dispensing/`

**Pre-conditions**:
- Cart status must be 'paid'
- Invoice must be paid

**Process**:
1. For each cart item:
   - Check stock availability (final check)
   - Create `DispensingLog`
   - Update inventory (deduct stock)
   - Update `PrescriptionItem` quantities
   - Mark as dispensed if fully dispensed

2. Update prescription status:
   - 'dispensed' if all items dispensed
   - 'partially_dispensed' if some items dispensed

3. Update cart status to 'completed'

**Inventory Update**:
```python
# Try ActiveStoreInventory first
if active_store:
    inventory = ActiveStoreInventory.objects.filter(
        medication=medication,
        active_store=active_store,
        stock_quantity__gte=quantity
    ).first()
    
    if inventory:
        inventory.stock_quantity -= quantity
        inventory.save()

# Fallback to legacy MedicationInventory
else:
    legacy_inv = MedicationInventory.objects.filter(
        medication=medication,
        dispensary=dispensary,
        stock_quantity__gte=quantity
    ).first()
    
    if legacy_inv:
        legacy_inv.stock_quantity -= quantity
        legacy_inv.save()
```

## Cart Status Flow

```
active → invoiced → paid → completed
   ↓
cancelled
```

- **active**: Cart being prepared, can edit items
- **invoiced**: Invoice created, awaiting payment
- **paid**: Payment completed, ready to dispense
- **completed**: Dispensing completed
- **cancelled**: Cart cancelled

## User Interface

### Cart View Features

1. **Header Section**
   - Cart ID and status
   - Patient information
   - Prescription reference
   - Created by information

2. **NHIA Info Banner** (if applicable)
   - Shows NHIA patient status
   - Explains 10%/90% split

3. **Dispensary Selection**
   - Dropdown with all active dispensaries
   - Update button
   - Shows selected dispensary

4. **Cart Items Table**
   - Medication name and strength
   - Prescribed quantity
   - Adjustable quantity input
   - Unit price
   - Stock status badge
   - Subtotal
   - Patient pays (if NHIA)
   - NHIA covers (if NHIA)
   - Remove button

5. **Cart Summary**
   - Subtotal
   - NHIA coverage (if applicable)
   - Patient payable amount
   - Generate invoice button

6. **Action Buttons**
   - Back to prescription
   - Cancel cart
   - Generate invoice
   - Go to payment (if invoiced)
   - Complete dispensing (if paid)

### Color Coding

- **Primary (Blue)**: Cart actions, totals
- **Success (Green)**: Available stock, completed status
- **Warning (Yellow)**: Partial stock, payment pending
- **Danger (Red)**: Out of stock, cancelled
- **Info (Light Blue)**: NHIA information

## API Endpoints

### Update Cart Item Quantity (AJAX)

**Endpoint**: `POST /pharmacy/cart/item/<item_id>/update-quantity/`

**Request**:
```json
{
    "quantity": 15
}
```

**Response**:
```json
{
    "success": true,
    "item_subtotal": 750.00,
    "item_patient_pays": 75.00,
    "item_nhia_covers": 675.00,
    "cart_subtotal": 2500.00,
    "cart_patient_payable": 250.00,
    "cart_nhia_coverage": 2250.00,
    "stock_status": {
        "status": "available",
        "message": "20 available",
        "css_class": "success",
        "icon": "check-circle"
    }
}
```

## Examples

### Example 1: Regular Patient, Full Dispensing

**Prescription**:
- Paracetamol 500mg × 30 @ ₦50 = ₦1,500
- Amoxicillin 250mg × 20 @ ₦100 = ₦2,000

**Cart**:
- Both items added with full quantities
- Dispensary selected
- Stock available for both

**Invoice**:
- Subtotal: ₦3,500
- Patient pays: ₦3,500 (100%)
- NHIA covers: ₦0

### Example 2: NHIA Patient, Partial Dispensing

**Prescription**:
- Paracetamol 500mg × 30 @ ₦50 = ₦1,500
- Amoxicillin 250mg × 20 @ ₦100 = ₦2,000

**Cart** (only 20 Paracetamol available):
- Paracetamol × 20 @ ₦50 = ₦1,000
- Amoxicillin removed (out of stock)

**Invoice**:
- Subtotal: ₦1,000
- Patient pays: ₦100 (10%)
- NHIA covers: ₦900 (90%)

**Later** (when Amoxicillin arrives):
- Create new cart for remaining items
- Add Amoxicillin × 20
- Generate new invoice for ₦200 (10% of ₦2,000)

## Benefits

### For Pharmacists
✅ Review items before billing
✅ Adjust quantities based on availability
✅ Clear stock visibility
✅ Flexible workflow
✅ Better control over dispensing

### For Patients
✅ Pay for what they receive
✅ No overpayment for unavailable items
✅ Clear pricing breakdown
✅ Accurate NHIA billing

### For Hospital
✅ Accurate inventory management
✅ Proper revenue tracking
✅ Reduced billing disputes
✅ Better audit trail
✅ Compliance with NHIA requirements

## Installation & Setup

### 1. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Verify Models

```bash
python manage.py shell
>>> from pharmacy.cart_models import PrescriptionCart, PrescriptionCartItem
>>> PrescriptionCart.objects.count()
0
```

### 3. Test Cart Creation

1. Go to any prescription detail page
2. Click "Create Billing Cart"
3. Verify cart is created with all items
4. Select dispensary
5. Adjust quantities
6. Generate invoice
7. Process payment
8. Complete dispensing

## Troubleshooting

### Issue: Cart not created
**Check**: Prescription has undispensed items
**Solution**: Verify prescription items exist and are not fully dispensed

### Issue: Stock not showing
**Check**: Dispensary selected, inventory exists
**Solution**: Select dispensary, verify inventory records exist

### Issue: Cannot generate invoice
**Check**: All items have sufficient stock, dispensary selected
**Solution**: Review cart items, ensure stock availability

### Issue: Cannot complete dispensing
**Check**: Payment completed, invoice paid
**Solution**: Verify payment status, check invoice

## Future Enhancements

1. **Multi-prescription carts** - Add items from multiple prescriptions
2. **Cart templates** - Save common item combinations
3. **Stock reservation** - Reserve stock when cart created
4. **Expiry tracking** - Show medication expiry dates
5. **Batch processing** - Process multiple carts at once
6. **Analytics** - Cart abandonment, popular items, etc.

## Related Files

- `pharmacy/cart_models.py` - Cart models
- `pharmacy/cart_views.py` - Cart views
- `pharmacy/templates/pharmacy/cart/view_cart.html` - Cart template
- `pharmacy/urls.py` - Cart URLs
- `pharmacy/admin.py` - Cart admin
- `pharmacy/migrations/0022_prescription_cart.py` - Migration

## Conclusion

The Prescription Cart System provides a robust, flexible, and user-friendly workflow for prescription dispensing. It separates billing from dispensing, ensures accurate inventory management, and provides better control for pharmacists while ensuring patients pay only for what they receive.

