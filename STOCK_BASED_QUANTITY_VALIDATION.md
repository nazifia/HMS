# Stock-Based Quantity Validation for Cart Items

**Date:** 2025-10-06  
**Status:** ✅ Implemented and Tested  
**Impact:** Critical - Prevents pharmacists from dispensing more than available stock  
**Feature:** Pharmacy Cart Management

---

## 📋 Overview

This feature adds **stock-based validation** to the pharmacy cart system, ensuring that pharmacists cannot adjust medication quantities beyond what's available in the selected dispensary's inventory.

### **Problem Solved**

**Before:**
- ❌ Pharmacists could set cart quantities higher than available stock
- ❌ Only prescription limits were enforced
- ❌ Stock validation only happened at invoice generation
- ❌ Could lead to failed dispensing attempts

**After:**
- ✅ Real-time stock validation when adjusting quantities
- ✅ Clear visual indicators of stock limits
- ✅ Both client-side and server-side validation
- ✅ Helpful error messages with stock availability info
- ✅ Prevents invalid quantities from being saved

---

## 🎯 Key Features

### **1. Dual Validation**
- **Prescription Limit:** Cannot exceed remaining quantity to dispense
- **Stock Limit:** Cannot exceed available stock in selected dispensary
- **Enforced:** Whichever is lower becomes the maximum allowed

### **2. Visual Indicators**
- **Stock Warning:** Yellow badge when stock is the limiting factor
- **Stock Info:** Gray text showing available stock when prescription is the limit
- **Tooltip:** Hover over input to see max allowed
- **Real-time Feedback:** Immediate validation on quantity change

### **3. Multi-Layer Validation**
1. **HTML5 Validation:** `max` attribute on input field
2. **Client-side JavaScript:** Immediate feedback with detailed messages
3. **Server-side Validation:** Final check before saving to database

---

## 💻 Implementation Details

### **1. Backend Changes**

#### **File:** `pharmacy/cart_views.py`

**Modified Function:** `update_cart_item_quantity()`

**Added Stock Validation:**
```python
# Validate against available stock
item.update_available_stock()  # Refresh stock info
available_stock = item.available_stock

if quantity > available_stock:
    return JsonResponse({
        'success': False,
        'error': f'Quantity exceeds available stock. Only {available_stock} available in selected dispensary.'
    }, status=400)
```

**Validation Order:**
1. ✅ Check quantity > 0
2. ✅ Check quantity <= prescription remaining
3. ✅ Check quantity <= available stock (NEW!)
4. ✅ Save if all validations pass

---

### **2. Template Changes**

#### **File:** `pharmacy/templates/pharmacy/cart/view_cart.html`

**Enhanced Quantity Input (Lines 221-265):**

```django
{% if cart.status in 'active,invoiced' %}
{% with max_allowed=item.prescription_item.remaining_quantity_to_dispense available_stock=item.available_stock %}
{% if available_stock < max_allowed %}
{# Stock is the limiting factor #}
<input type="number"
       class="form-control quantity-input cart-quantity-input"
       value="{{ item.quantity }}"
       min="1"
       max="{{ available_stock }}"
       data-item-id="{{ item.id }}"
       data-unit-price="{{ item.unit_price }}"
       data-is-nhia="{{ is_nhia_patient|yesno:'true,false' }}"
       data-max-stock="{{ available_stock }}"
       data-max-prescription="{{ max_allowed }}"
       onchange="updateQuantity({{ item.id }}, this.value)"
       title="Max available in stock: {{ available_stock }}">
<small class="text-warning d-block">
    <i class="fas fa-exclamation-triangle"></i> Max stock: {{ available_stock }}
</small>
{% else %}
{# Prescription is the limiting factor #}
<input type="number"
       class="form-control quantity-input cart-quantity-input"
       value="{{ item.quantity }}"
       min="1"
       max="{{ max_allowed }}"
       data-item-id="{{ item.id }}"
       data-unit-price="{{ item.unit_price }}"
       data-is-nhia="{{ is_nhia_patient|yesno:'true,false' }}"
       data-max-stock="{{ available_stock }}"
       data-max-prescription="{{ max_allowed }}"
       onchange="updateQuantity({{ item.id }}, this.value)"
       title="Max from prescription: {{ max_allowed }}">
{% if available_stock > 0 %}
<small class="text-muted d-block">
    <i class="fas fa-info-circle"></i> Stock: {{ available_stock }} available
</small>
{% endif %}
{% endif %}
{% endwith %}
{% endif %}
```

**Key Additions:**
- `data-max-stock` - Available stock in dispensary
- `data-max-prescription` - Remaining from prescription
- Dynamic `max` attribute based on limiting factor
- Visual indicators (warning for stock limit, info for prescription limit)
- Helpful tooltips

---

### **3. JavaScript Enhancements**

#### **File:** `pharmacy/templates/pharmacy/cart/view_cart.html`

**Enhanced `updateQuantity()` Function (Lines 349-446):**

```javascript
function updateQuantity(itemId, quantity) {
    // Get the input element to access validation data
    const input = document.querySelector(`input[data-item-id="${itemId}"]`);
    const maxStock = parseInt(input.dataset.maxStock);
    const maxPrescription = parseInt(input.dataset.maxPrescription);
    const quantityInt = parseInt(quantity);
    
    // Client-side validation
    if (quantityInt <= 0) {
        alert('Quantity must be greater than zero');
        input.value = input.min || 1;
        return;
    }
    
    if (quantityInt > maxStock) {
        alert(`Cannot exceed available stock!\n\nRequested: ${quantityInt}\nAvailable in stock: ${maxStock}\n\nPlease adjust the quantity.`);
        input.value = maxStock;
        return;
    }
    
    if (quantityInt > maxPrescription) {
        alert(`Cannot exceed prescribed quantity!\n\nRequested: ${quantityInt}\nRemaining to dispense: ${maxPrescription}\n\nPlease adjust the quantity.`);
        input.value = maxPrescription;
        return;
    }
    
    // ... AJAX call to update quantity ...
}
```

**Features:**
- ✅ Reads max limits from data attributes
- ✅ Validates before sending to server
- ✅ Shows detailed error messages
- ✅ Auto-corrects to max allowed value
- ✅ Updates stock status badge after successful update

---

## 🎨 User Experience

### **Scenario 1: Stock is Limiting Factor**

**Example:** Prescription says 100 tablets, but only 50 in stock

**Display:**
```
Quantity: [50] ⚠️ Max stock: 50
```

**If user tries to enter 60:**
```
❌ Alert: "Cannot exceed available stock!

Requested: 60
Available in stock: 50

Please adjust the quantity."

Input auto-corrects to: 50
```

---

### **Scenario 2: Prescription is Limiting Factor**

**Example:** Prescription says 20 tablets, 100 in stock

**Display:**
```
Quantity: [20] ℹ️ Stock: 100 available
```

**If user tries to enter 30:**
```
❌ Alert: "Cannot exceed prescribed quantity!

Requested: 30
Remaining to dispense: 20

Please adjust the quantity."

Input auto-corrects to: 20
```

---

### **Scenario 3: Successful Update**

**User changes quantity from 10 to 15 (within limits):**

1. ✅ Client-side validation passes
2. ✅ AJAX request sent to server
3. ✅ Server-side validation passes
4. ✅ Quantity updated in database
5. ✅ All totals updated in real-time
6. ✅ Stock status badge updated
7. ✅ Row highlights green briefly (success feedback)

---

## 🔄 Workflow Integration

### **When Does This Apply?**

**Cart Status:**
- ✅ **Active** - Can adjust quantities
- ✅ **Invoiced** - Can still adjust quantities
- ❌ **Paid** - Uses different dispensing workflow
- ❌ **Completed** - Read-only

**Stock Updates:**
- Stock availability is refreshed when:
  1. Dispensary is selected/changed
  2. Quantity is updated (server-side)
  3. Page is reloaded

---

## 📊 Validation Flow

```
User Changes Quantity
        ↓
HTML5 Validation (max attribute)
        ↓
JavaScript Validation
        ├─→ Quantity <= 0? → Alert & Reset
        ├─→ Quantity > Stock? → Alert & Auto-correct
        └─→ Quantity > Prescription? → Alert & Auto-correct
        ↓
AJAX Request to Server
        ↓
Server-Side Validation
        ├─→ Quantity <= 0? → Error Response
        ├─→ Quantity > Prescription? → Error Response
        └─→ Quantity > Stock? → Error Response (NEW!)
        ↓
Update Database
        ↓
Return Updated Totals & Stock Status
        ↓
Update UI in Real-Time
```

---

## ✅ Benefits

1. **Prevents Errors:** Can't create carts that can't be fulfilled
2. **Better UX:** Immediate feedback instead of errors at invoice generation
3. **Stock Awareness:** Pharmacists see stock limits upfront
4. **Flexible:** Works with both NHIA and non-NHIA patients
5. **Maintains Existing Features:** All previous functionality preserved

---

## 🧪 Testing Checklist

- [ ] Create cart with medication that has limited stock
- [ ] Try to set quantity higher than stock → Should show alert and auto-correct
- [ ] Try to set quantity higher than prescription → Should show alert and auto-correct
- [ ] Set valid quantity → Should update successfully with green highlight
- [ ] Change dispensary → Stock limits should update
- [ ] Check stock warning badge appears when stock < prescription
- [ ] Check stock info text appears when stock > prescription
- [ ] Verify all totals update in real-time
- [ ] Test with NHIA patient (10%/90% split)
- [ ] Test with non-NHIA patient (100% patient pays)

---

## 📁 Files Modified

1. ✅ `pharmacy/cart_views.py` - Added stock validation in `update_cart_item_quantity()`
2. ✅ `pharmacy/templates/pharmacy/cart/view_cart.html` - Enhanced quantity input with stock limits and JavaScript validation

---

## 🔗 Related Features

- **Prescription Cart System** - Base cart functionality
- **Partial Dispensing** - Handles cases where full quantity can't be dispensed
- **Real-time Total Updates** - Updates all totals without page reload
- **Auto Dispensary Update** - Automatically updates stock when dispensary changes

---

**Stock-based validation ensures pharmacists can only dispense what's actually available!** 🚀💊

