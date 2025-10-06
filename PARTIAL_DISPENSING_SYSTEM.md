# 🎯 Partial Dispensing System - Complete Implementation

## Overview

The Prescription Cart System now supports **partial dispensing**, allowing pharmacists to dispense medications as they become available, rather than requiring all items to be in stock at once.

---

## 🆕 What's New

### Key Features

1. **Partial Dispensing Support**
   - Dispense available items immediately
   - Keep cart active for pending items
   - Track dispensing progress per item
   - Multiple dispensing sessions from same cart

2. **Enhanced Cart Status**
   - New status: `partially_dispensed`
   - Cart remains active until all items dispensed
   - Auto-completes when fully dispensed

3. **Item-Level Tracking**
   - Quantity prescribed
   - Quantity dispensed so far
   - Quantity remaining
   - Dispensing progress percentage

4. **Smart Stock Handling**
   - Dispenses what's available
   - Skips out-of-stock items
   - Shows clear status indicators
   - Allows future dispensing when stock arrives

---

## 📊 Cart Status Flow

### Old Flow (Before)
```
Active → Invoiced → Paid → Completed
```

### New Flow (With Partial Dispensing)
```
Active → Invoiced → Paid → Partially Dispensed → Completed
                              ↑                    ↑
                              └────────────────────┘
                         (Can dispense multiple times)
```

---

## 🔄 Workflow Example

### Scenario: Prescription with 3 Medications

**Prescribed Items:**
1. Paracetamol - 30 tablets
2. Amoxicillin - 20 capsules
3. Vitamin C - 50 tablets

**Stock Availability:**
1. Paracetamol - 30 available ✅
2. Amoxicillin - 0 available ❌
3. Vitamin C - 25 available ⚠️ (partial)

### Step-by-Step Process

#### **Step 1: Create Cart**
- Pharmacist creates cart from prescription
- All 3 items added to cart

#### **Step 2: Select Dispensary**
- Choose dispensary
- System checks stock availability
- Shows status for each item

#### **Step 3: Generate Invoice**
- Invoice created for all items
- Patient pays for full amount

#### **Step 4: First Dispensing Session**
- Click "Dispense Available Items"
- System dispenses:
  - ✅ Paracetamol: 30 tablets (fully dispensed)
  - ❌ Amoxicillin: 0 capsules (skipped - no stock)
  - ⚠️ Vitamin C: 25 tablets (partially dispensed)
- Cart status: `partially_dispensed`
- Progress: 55/100 items = 55%

#### **Step 5: Wait for Stock**
- Amoxicillin arrives in stock
- Vitamin C restocked

#### **Step 6: Second Dispensing Session**
- Pharmacist returns to cart
- Clicks "Dispense Remaining Items"
- System dispenses:
  - ✅ Amoxicillin: 20 capsules (now available)
  - ✅ Vitamin C: 25 tablets (remaining quantity)
- Cart status: `completed`
- Progress: 100/100 items = 100%

---

## 🗄️ Database Changes

### PrescriptionCart Model

**New Status:**
```python
STATUS_CHOICES = (
    ('active', 'Active'),
    ('invoiced', 'Invoiced'),
    ('paid', 'Paid'),
    ('partially_dispensed', 'Partially Dispensed'),  # NEW!
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
)
```

**New Methods:**
- `get_dispensing_progress()` - Overall cart progress
- `is_fully_dispensed()` - Check if all items dispensed
- `has_pending_items()` - Check if items still pending

### PrescriptionCartItem Model

**New Field:**
```python
quantity_dispensed = models.IntegerField(
    default=0,
    help_text="Quantity already dispensed from this cart item"
)
```

**New Methods:**
- `get_remaining_quantity()` - Quantity left to dispense
- `is_fully_dispensed()` - Check if item fully dispensed
- `is_partially_dispensed()` - Check if item partially dispensed
- `get_dispensing_progress_percentage()` - Progress as %
- `get_available_to_dispense_now()` - Max dispensable now

---

## 💻 Code Changes

### 1. Models (`pharmacy/cart_models.py`)

**Added:**
- `quantity_dispensed` field to track dispensed quantity
- `partially_dispensed` status
- Helper methods for tracking progress

### 2. Views (`pharmacy/cart_views.py`)

**Modified: `complete_dispensing_from_cart()`**

**Old Logic:**
```python
# Dispense all items or fail
for item in cart.items.all():
    if not has_stock:
        return error
    dispense(item.quantity)
cart.status = 'completed'
```

**New Logic:**
```python
# Dispense what's available, skip rest
for item in cart.items.all():
    remaining = item.get_remaining_quantity()
    available = item.get_available_to_dispense_now()
    
    if available > 0:
        dispense(available)
        item.quantity_dispensed += available
    else:
        skip_item()

# Update cart status
if cart.is_fully_dispensed():
    cart.status = 'completed'
else:
    cart.status = 'partially_dispensed'
```

### 3. Templates

**Updated: `view_cart.html`**
- Added "Dispensed" and "Remaining" columns
- Color-coded rows (green=fully dispensed, yellow=partial)
- Progress badges on items

**Updated: `_cart_summary_widget.html`**
- Added dispensing progress bar
- Shows fully/partially/pending counts
- Different buttons for partial vs complete status

---

## 🎨 UI Enhancements

### Cart Items Table

**New Columns:**
- **Dispensed**: Shows quantity already dispensed
- **Remaining**: Shows quantity still pending
- **Progress**: Percentage dispensed

**Row Colors:**
- 🟢 **Green**: Fully dispensed items
- 🟡 **Yellow**: Partially dispensed items
- ⚪ **White**: Pending items

**Badges:**
- ✅ "Fully Dispensed" (green)
- ⚠️ "Partially Dispensed" (yellow)

### Summary Widget

**Progress Section:**
```
┌─────────────────────────────────┐
│ Dispensing Progress             │
├─────────────────────────────────┤
│ [████████░░] 80%                │
│                                 │
│ Fully: 2  Partial: 1  Pending: 0│
│ Dispensed: 80 / 100 items       │
└─────────────────────────────────┘
```

**Action Buttons:**
- **Paid**: "Dispense Available Items"
- **Partially Dispensed**: "Dispense Remaining Items"
- **Completed**: "View Receipt"

---

## 📝 User Messages

### Success Messages

**Full Dispensing:**
```
✅ Successfully dispensed all items! Cart completed.
```

**Partial Dispensing:**
```
✅ Dispensed 2 items. Progress: 55% complete. 45 items still pending.
ℹ️ Cart remains active for pending items. You can dispense remaining items when stock becomes available.
```

### Info Messages

**Item Skipped:**
```
⚠️ No stock available for Amoxicillin. Will dispense when stock arrives.
```

**Partial Item:**
```
ℹ️ Partially dispensed Vitamin C: 25 of 50 remaining
```

---

## 🔧 Migration

**File:** `pharmacy/migrations/0023_partial_dispensing_support.py`

**Changes:**
1. Add `quantity_dispensed` field to `PrescriptionCartItem`
2. Add `partially_dispensed` status to `PrescriptionCart`

**Run Migration:**
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 📋 Testing Checklist

### Test Case 1: Full Stock Available
- [ ] Create cart with 3 items
- [ ] All items have sufficient stock
- [ ] Dispense all items
- [ ] Cart status: `completed`
- [ ] All items show "Fully Dispensed"

### Test Case 2: Partial Stock
- [ ] Create cart with 3 items
- [ ] 1 item has full stock
- [ ] 1 item has partial stock
- [ ] 1 item has no stock
- [ ] First dispensing: 1 full + 1 partial
- [ ] Cart status: `partially_dispensed`
- [ ] Progress bar shows correct %

### Test Case 3: Multiple Dispensing Sessions
- [ ] Create cart with pending items
- [ ] Dispense available items
- [ ] Wait for stock to arrive
- [ ] Return to cart
- [ ] Dispense remaining items
- [ ] Cart status: `completed`

### Test Case 4: NHIA Patient
- [ ] Create cart for NHIA patient
- [ ] Partial dispensing
- [ ] Verify 10% patient payment
- [ ] Verify 90% NHIA coverage
- [ ] Check invoice amounts

---

## 🎯 Benefits

### For Pharmacists
✅ **Flexibility**: Don't wait for all stock to arrive
✅ **Efficiency**: Dispense what's available immediately
✅ **Tracking**: Clear view of what's dispensed and pending
✅ **Control**: Multiple dispensing sessions from same cart

### For Patients
✅ **Faster Service**: Get available medications immediately
✅ **Transparency**: See what's dispensed and what's pending
✅ **Convenience**: Don't need to return for payment
✅ **Accuracy**: Only pay once for all items

### For Hospital
✅ **Better Workflow**: Handle stock shortages gracefully
✅ **Audit Trail**: Complete history of dispensing sessions
✅ **Compliance**: Proper tracking for NHIA claims
✅ **Inventory**: Accurate stock management

---

## 🚀 Usage Guide

### For Pharmacists

#### Creating and Dispensing a Cart

1. **Create Cart**
   - Go to prescription detail page
   - Click "Create Billing Cart"

2. **Select Dispensary**
   - Choose dispensary from dropdown
   - Stock status updates automatically

3. **Review Items**
   - Check stock status (green/yellow/red)
   - Adjust quantities if needed

4. **Generate Invoice**
   - Click "Generate Invoice"
   - Patient pays for all items

5. **First Dispensing**
   - Click "Dispense Available Items"
   - System dispenses what's in stock
   - Skips out-of-stock items
   - Cart stays active if items pending

6. **Future Dispensing**
   - Return to cart when stock arrives
   - Click "Dispense Remaining Items"
   - Cart completes when all items dispensed

---

## 📊 Reports & Analytics

### Dispensing Progress Report

**Available Data:**
- Total carts
- Fully dispensed carts
- Partially dispensed carts
- Pending items count
- Average dispensing time
- Stock shortage frequency

### Cart Metrics

**Per Cart:**
- Total items
- Fully dispensed items
- Partially dispensed items
- Pending items
- Progress percentage
- Dispensing sessions count

---

## 🔐 Permissions

**Required Permissions:**
- `pharmacy.view_prescriptioncart`
- `pharmacy.add_prescriptioncart`
- `pharmacy.change_prescriptioncart`
- `pharmacy.delete_prescriptioncart`

**Dispensing Permission:**
- `pharmacy.can_dispense_medications`

---

## 📞 Support

### Common Issues

**Q: Cart stuck in "partially_dispensed" status?**
A: Check if all items are fully dispensed. Use "Dispense Remaining Items" button.

**Q: Can't dispense remaining items?**
A: Verify stock is available and cart status is "paid" or "partially_dispensed".

**Q: Progress bar not updating?**
A: Refresh page or check if `quantity_dispensed` field is updating.

---

## 🎉 Summary

The Partial Dispensing System provides:

✅ **Flexible dispensing** - Handle stock shortages gracefully
✅ **Progress tracking** - Know exactly what's dispensed
✅ **Multiple sessions** - Dispense as stock becomes available
✅ **Better UX** - Clear status indicators and messages
✅ **Audit trail** - Complete history of all dispensing

**Result**: Faster service, better workflow, happier patients! 🚀

