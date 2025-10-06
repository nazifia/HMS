# 🔧 Cart Payment Status Fix

## Problem Identified

When payment was made for a prescription cart, the invoice status was updated to 'paid', but the **cart status remained 'invoiced'**. This caused the cart to still show the "Process Payment" button even though payment was already completed.

---

## Root Cause

In the `prescription_payment` view (`pharmacy/views.py`), when payment was processed:

1. ✅ Invoice status was updated to 'paid'
2. ✅ Prescription payment_status was updated to 'paid'
3. ❌ **Cart status was NOT updated** - remained 'invoiced'

This caused a mismatch between invoice status and cart status.

---

## Solution Implemented

### 1. **Update Cart Status on Payment** (`pharmacy/views.py`)

**Added code to update cart status when invoice is fully paid:**

```python
# Update invoice
pharmacy_invoice.amount_paid += amount
if pharmacy_invoice.amount_paid >= pharmacy_invoice.total_amount:
    pharmacy_invoice.status = 'paid'
    prescription.payment_status = 'paid'
    prescription.save(update_fields=['payment_status'])
    
    # NEW: Update cart status to 'paid' if invoice is fully paid
    from pharmacy.cart_models import PrescriptionCart
    carts = PrescriptionCart.objects.filter(
        invoice=pharmacy_invoice,
        status='invoiced'
    )
    for cart in carts:
        cart.status = 'paid'
        cart.save(update_fields=['status'])
else:
    pharmacy_invoice.status = 'partially_paid'

pharmacy_invoice.save()
```

**What this does:**
- When invoice is fully paid, finds all carts linked to that invoice
- Updates cart status from 'invoiced' to 'paid'
- Allows dispensing to proceed

---

### 2. **Smart Button Display** (`pharmacy/templates/pharmacy/cart/_cart_summary_widget.html`)

**Added fallback logic to check invoice status:**

```django
{% elif cart.status == 'invoiced' %}
    {% if cart.invoice and cart.invoice.status == 'paid' %}
        {# Invoice is paid but cart status not updated - show dispensing button #}
        <div class="alert alert-success mb-3">
            <i class="fas fa-check-circle"></i> 
            <strong>Payment Completed</strong><br>
            <small>Ready to dispense</small>
        </div>
        <form method="post" action="{% url 'pharmacy:complete_dispensing_from_cart' cart.id %}">
            {% csrf_token %}
            <button type="submit" class="btn btn-success w-100">
                <i class="fas fa-pills"></i> Dispense Available Items
            </button>
        </form>
    {% else %}
        {# Invoice not paid - show payment button #}
        <a href="{% url 'pharmacy:prescription_payment' cart.prescription.id %}" class="btn btn-warning w-100">
            <i class="fas fa-credit-card"></i> Process Payment
        </a>
    {% endif %}
{% elif cart.status == 'paid' %}
    ...
{% endif %}
```

**What this does:**
- Checks if cart status is 'invoiced'
- If invoice is paid, shows "Dispense" button instead of "Payment" button
- Provides fallback for carts that weren't auto-updated

---

### 3. **Auto-Update in Dispensing Check** (`pharmacy/cart_models.py`)

**Modified `can_complete_dispensing()` method:**

```python
def can_complete_dispensing(self):
    """Check if dispensing can be completed (allows partial dispensing)"""
    # Allow dispensing if cart is paid, partially_dispensed, or invoiced with paid invoice
    if self.status not in ['paid', 'partially_dispensed', 'invoiced']:
        return False, f'Cart status is {self.get_status_display()}, must be Paid, Partially Dispensed, or Invoiced'
    
    if not self.invoice:
        return False, 'No invoice associated with this cart'
    
    # Check if invoice is paid
    if self.invoice.status != 'paid':
        return False, 'Invoice is not paid'
    
    # NEW: If invoice is paid but cart status is still 'invoiced', auto-update cart status
    if self.status == 'invoiced' and self.invoice.status == 'paid':
        self.status = 'paid'
        self.save(update_fields=['status'])
    
    # Check if there are any items with remaining quantity
    has_items_to_dispense = any(
        item.get_remaining_quantity() > 0 
        for item in self.items.all()
    )
    
    if not has_items_to_dispense:
        return False, 'All items have been fully dispensed'
    
    return True, 'Cart is ready for dispensing'
```

**What this does:**
- When checking if dispensing can proceed, also checks invoice status
- If invoice is paid but cart is still 'invoiced', auto-updates cart to 'paid'
- Ensures cart status is always in sync with invoice status

---

### 4. **Management Command to Fix Existing Carts**

**Created:** `pharmacy/management/commands/fix_cart_payment_status.py`

**Usage:**
```bash
python manage.py fix_cart_payment_status
```

**What it does:**
- Finds all carts with status 'invoiced' but invoice status 'paid'
- Updates cart status to 'paid'
- Shows progress and count of fixed carts

**Example output:**
```
Checking for carts with paid invoices...
Found 3 cart(s) with paid invoices but invoiced status
  ✓ Updated Cart #5 to paid status
  ✓ Updated Cart #7 to paid status
  ✓ Updated Cart #9 to paid status

Successfully updated 3 cart(s)!
```

---

## How to Apply the Fix

### Step 1: Fix Existing Carts

Run the management command to update any existing carts:

```bash
python manage.py fix_cart_payment_status
```

This will update all carts that have paid invoices but are still showing 'invoiced' status.

### Step 2: Restart Server

```bash
python manage.py runserver
```

### Step 3: Test

1. Go to a cart that was previously showing "Process Payment" button
2. Refresh the page
3. You should now see "Dispense Available Items" button
4. Click to dispense medications

---

## What Changed

### Files Modified

✅ **pharmacy/views.py** (Line ~2513-2532)
- Added cart status update when payment is completed

✅ **pharmacy/cart_models.py** (Line ~129-156)
- Modified `can_complete_dispensing()` to auto-update cart status

✅ **pharmacy/templates/pharmacy/cart/_cart_summary_widget.html** (Line ~253-277)
- Added smart button display based on invoice status

### Files Created

✅ **pharmacy/management/commands/fix_cart_payment_status.py**
- Management command to fix existing carts

✅ **CART_PAYMENT_STATUS_FIX.md**
- This documentation file

---

## Testing Checklist

### Test Case 1: New Payment
- [ ] Create cart from prescription
- [ ] Generate invoice
- [ ] Process payment
- [ ] Cart status automatically updates to 'paid'
- [ ] "Dispense Available Items" button shows
- [ ] Can dispense medications

### Test Case 2: Existing Paid Cart
- [ ] Find cart with paid invoice but 'invoiced' status
- [ ] Run `python manage.py fix_cart_payment_status`
- [ ] Cart status updates to 'paid'
- [ ] Refresh cart page
- [ ] "Dispense Available Items" button shows

### Test Case 3: Fallback Logic
- [ ] Cart with status 'invoiced' and paid invoice
- [ ] View cart page
- [ ] Shows "Payment Completed" alert
- [ ] Shows "Dispense Available Items" button
- [ ] Click button - cart status auto-updates
- [ ] Dispensing proceeds normally

---

## Benefits

✅ **Automatic Sync**: Cart status automatically updates when payment is made
✅ **Fallback Protection**: Smart button display checks invoice status
✅ **Auto-Correction**: Cart status auto-updates when dispensing is attempted
✅ **Fix Tool**: Management command to fix existing carts
✅ **Better UX**: Correct buttons show based on actual payment status

---

## Status Flow

### Before Fix
```
Cart: invoiced → (payment made) → invoiced ❌ (stuck)
Invoice: unpaid → (payment made) → paid ✅
```

### After Fix
```
Cart: invoiced → (payment made) → paid ✅
Invoice: unpaid → (payment made) → paid ✅
```

---

## Summary

The issue where carts showed "Process Payment" button even after payment was made has been fixed with:

1. **Automatic cart status update** when payment is completed
2. **Smart button display** that checks invoice status
3. **Auto-correction** when dispensing is attempted
4. **Management command** to fix existing carts

All future payments will automatically update cart status, and existing carts can be fixed with the management command.

**Problem Solved!** ✅

