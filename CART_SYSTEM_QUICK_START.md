# Prescription Cart System - Quick Start Guide

## What is it?

A shopping cart-like system for prescription dispensing that separates billing from dispensing.

## Quick Workflow

```
1. Create Cart → 2. Review Items → 3. Select Dispensary → 4. Adjust Quantities → 
5. Generate Invoice → 6. Process Payment → 7. Complete Dispensing
```

## How to Use

### Step 1: Create Cart
1. Go to prescription detail page
2. Click **"Create Billing Cart"** button
3. Cart created with all prescription items

### Step 2: Review & Adjust
1. View cart at `/pharmacy/cart/<cart_id>/`
2. Select dispensary from dropdown
3. Adjust quantities as needed
4. Remove items if necessary
5. Check stock availability (color-coded)

### Step 3: Generate Invoice
1. Click **"Generate Invoice & Proceed to Payment"**
2. Invoice created based on cart items
3. Redirected to payment page

### Step 4: Process Payment
1. Patient/billing office pays invoice
2. Cart status updated to 'paid'

### Step 5: Complete Dispensing
1. Click **"Complete Dispensing"** button
2. Medications dispensed
3. Inventory updated
4. Prescription status updated

## Key Features

✅ **Real-time stock checking** - See availability before billing
✅ **Quantity adjustment** - Change quantities based on stock
✅ **NHIA support** - Automatic 10%/90% calculation
✅ **Accurate billing** - Invoice matches actual quantities
✅ **Flexible workflow** - Review before committing

## Stock Status Indicators

- 🟢 **Green** - Sufficient stock available
- 🟡 **Yellow** - Partial stock available
- 🔴 **Red** - Out of stock

## Cart Status

- **Active** - Being prepared, can edit
- **Invoiced** - Invoice created, awaiting payment
- **Paid** - Payment completed, ready to dispense
- **Completed** - Dispensing completed
- **Cancelled** - Cart cancelled

## Example

**Prescription**: Paracetamol × 30, Amoxicillin × 20

**Cart** (only 20 Paracetamol available):
- Adjust Paracetamol to 20
- Remove Amoxicillin (out of stock)

**Invoice** (NHIA patient):
- Subtotal: ₦1,000 (20 × ₦50)
- Patient pays: ₦100 (10%)
- NHIA covers: ₦900 (90%)

**Result**: Patient pays ₦100 for 20 tablets, not ₦150 for 30 tablets

## Installation

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Test
python manage.py runserver
# Go to prescription → Click "Create Billing Cart"
```

## URLs

- Create cart: `/pharmacy/cart/create/<prescription_id>/`
- View cart: `/pharmacy/cart/<cart_id>/`
- Update quantity: `/pharmacy/cart/item/<item_id>/update-quantity/` (AJAX)
- Generate invoice: `/pharmacy/cart/<cart_id>/generate-invoice/`
- Complete dispensing: `/pharmacy/cart/<cart_id>/complete-dispensing/`

## Files Created

1. `pharmacy/cart_models.py` - Models
2. `pharmacy/cart_views.py` - Views
3. `pharmacy/templates/pharmacy/cart/view_cart.html` - Template
4. `pharmacy/migrations/0022_prescription_cart.py` - Migration
5. Updated `pharmacy/urls.py` - URLs
6. Updated `pharmacy/admin.py` - Admin
7. Updated `pharmacy/templates/pharmacy/prescription_detail.html` - Button

## Benefits

**For Pharmacists**:
- Review before billing
- Adjust based on availability
- Clear stock visibility

**For Patients**:
- Pay for what they receive
- No overpayment
- Clear pricing

**For Hospital**:
- Accurate inventory
- Proper revenue tracking
- Better audit trail

## Next Steps

1. Run migrations
2. Test cart creation
3. Try adjusting quantities
4. Generate invoice
5. Complete dispensing

For detailed documentation, see `PRESCRIPTION_CART_SYSTEM.md`

