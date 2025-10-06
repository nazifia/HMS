# 💊 Pharmacist Dispense Quantity Input Feature

## Overview

Enhanced the cart dispensing workflow to allow pharmacists to manually input the quantity they wish to dispense for each medication. This provides more control and flexibility while maintaining all existing automatic dispensing functionalities.

---

## 🎯 Key Features

### **1. Manual Quantity Input**

**What It Does:**
- Pharmacists can now specify exactly how much of each medication to dispense
- Input fields appear in the cart when status is 'paid' or 'partially_dispensed'
- Validates quantities against available stock
- Prevents over-dispensing

**How It Works:**
1. Cart status is 'paid' or 'partially_dispensed'
2. "To Dispense" column appears in cart table
3. Pharmacist enters desired quantity for each item
4. System validates against available stock
5. Click "Dispense Medications" button
6. System dispenses the specified quantities

---

### **2. Smart Validation**

**Validates:**
- ✅ Quantity must be greater than 0
- ✅ Quantity cannot exceed available stock
- ✅ Quantity cannot exceed remaining quantity to dispense
- ✅ At least one item must have a quantity > 0

**Error Messages:**
- "Invalid quantities: Item X: Entered Y, but only Z available"
- "Please enter at least one quantity to dispense"
- "Cannot dispense X of [medication]. Only Y available"

---

### **3. Maintains Existing Functionality**

**Backward Compatible:**
- ✅ If no quantities entered, uses automatic logic (dispense all available)
- ✅ Partial dispensing still works
- ✅ Stock checking still works
- ✅ NHIA pricing still works
- ✅ All existing features preserved

---

## 🎨 User Interface

### **Cart Table - Paid Status**

```
┌────────────────────────────────────────────────────────────────────┐
│ Medication  │ Prescribed │ Quantity │ To Dispense │ Stock Status  │
├────────────────────────────────────────────────────────────────────┤
│ Paracetamol │     20     │    20    │   [15]      │ ✅ In Stock   │
│             │            │          │   Max: 15   │               │
├────────────────────────────────────────────────────────────────────┤
│ Amoxicillin │     30     │    30    │   [30]      │ ✅ In Stock   │
│             │            │          │   Max: 30   │               │
└────────────────────────────────────────────────────────────────────┘

[Dispense Medications] ← Click to dispense
```

### **Cart Table - Partially Dispensed**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Medication  │ Prescribed │ Qty │ To Dispense │ Dispensed │ Remaining │ Stock │
├──────────────────────────────────────────────────────────────────────────────┤
│ Paracetamol │     20     │ 20  │   [5]       │    15     │     5     │ ✅ 10 │
│             │            │     │   Max: 5    │           │           │       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Amoxicillin │     30     │ 30  │ Fully Disp. │    30     │     0     │ ✅    │
└──────────────────────────────────────────────────────────────────────────────┘

[Dispense Remaining Items] ← Click to dispense
```

---

## 🔄 Workflow

### **Scenario 1: Full Dispensing with Custom Quantities**

```
1. Payment complete → Cart status = 'paid'
   ↓
2. Pharmacist opens cart
   ↓
3. "To Dispense" column appears
   ↓
4. Pharmacist enters quantities:
   - Paracetamol: 15 (out of 20 available)
   - Amoxicillin: 30 (all available)
   ↓
5. Click "Dispense Medications"
   ↓
6. System validates quantities
   ↓
7. Confirmation dialog appears
   ↓
8. Pharmacist confirms
   ↓
9. Medications dispensed
   ↓
10. Cart status → 'partially_dispensed' (Paracetamol has 5 remaining)
```

### **Scenario 2: Partial Dispensing - Remaining Items**

```
1. Cart status = 'partially_dispensed'
   ↓
2. Pharmacist opens cart
   ↓
3. "To Dispense" column shows remaining items
   ↓
4. Pharmacist enters quantity for Paracetamol: 5
   ↓
5. Click "Dispense Remaining Items"
   ↓
6. System validates
   ↓
7. Pharmacist confirms
   ↓
8. Remaining medications dispensed
   ↓
9. Cart status → 'completed' (all items fully dispensed)
```

### **Scenario 3: Automatic Dispensing (No Input)**

```
1. Cart status = 'paid'
   ↓
2. Pharmacist opens cart
   ↓
3. Pharmacist leaves quantity fields as default
   ↓
4. Click "Dispense Medications"
   ↓
5. System uses automatic logic
   ↓
6. Dispenses all available quantities
   ↓
7. Works exactly as before ✅
```

---

## 🛠️ Technical Implementation

### **Files Modified**

#### **1. pharmacy/templates/pharmacy/cart/view_cart.html**

**Changes:**
- Added "To Dispense" column header (Line ~186-188)
- Added quantity input fields for each item (Line ~233-248)
- Added JavaScript function `prepareDispenseForm()` (Line ~354-403)

**Code - Input Field:**
```html
{% if cart.status in 'paid,partially_dispensed' %}
<td>
    {% with remaining=item.get_remaining_quantity available=item.get_available_to_dispense_now %}
    {% if remaining > 0 %}
    <input type="number"
           class="form-control quantity-input dispense-quantity-input"
           id="dispense-qty-{{ item.id }}"
           value="{{ available }}"
           min="0"
           max="{{ available }}"
           data-item-id="{{ item.id }}"
           data-max-available="{{ available }}"
           title="Max available: {{ available }}">
    <small class="text-muted d-block">Max: {{ available }}</small>
    {% else %}
    <span class="badge bg-success">Fully Dispensed</span>
    {% endif %}
    {% endwith %}
</td>
{% endif %}
```

**Code - JavaScript:**
```javascript
function prepareDispenseForm(cartId) {
    // Get all dispense quantity inputs
    const dispenseInputs = document.querySelectorAll('.dispense-quantity-input');
    const container = document.getElementById(`dispense-quantities-container-${cartId}`);
    
    // Clear container
    container.innerHTML = '';
    
    let hasQuantities = false;
    let invalidQuantities = [];
    
    // Collect quantities and add hidden inputs
    dispenseInputs.forEach(input => {
        const itemId = input.dataset.itemId;
        const quantity = parseInt(input.value) || 0;
        const maxAvailable = parseInt(input.dataset.maxAvailable) || 0;
        
        // Validate quantity
        if (quantity > maxAvailable) {
            invalidQuantities.push({
                itemId: itemId,
                quantity: quantity,
                maxAvailable: maxAvailable
            });
        }
        
        if (quantity > 0) {
            hasQuantities = true;
            // Create hidden input for this item's dispense quantity
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = `dispense_qty_${itemId}`;
            hiddenInput.value = quantity;
            container.appendChild(hiddenInput);
        }
    });
    
    // Validation and confirmation
    if (invalidQuantities.length > 0) {
        alert('Invalid quantities...');
        return false;
    }
    
    if (!hasQuantities) {
        alert('Please enter at least one quantity to dispense.');
        return false;
    }
    
    return confirm('Are you sure you want to dispense these medications?');
}
```

---

#### **2. pharmacy/templates/pharmacy/cart/_cart_summary_widget.html**

**Changes:**
- Updated dispense button to call `prepareDispenseForm()` (Line ~261-270, 277-287, 297-308)
- Added hidden container for quantity inputs
- Updated help text

**Code:**
```html
<form method="post" action="{% url 'pharmacy:complete_dispensing_from_cart' cart.id %}" id="dispense-form-{{ cart.id }}">
    {% csrf_token %}
    <div id="dispense-quantities-container-{{ cart.id }}"></div>
    <button type="submit" class="btn btn-success w-100" onclick="return prepareDispenseForm({{ cart.id }})">
        <i class="fas fa-pills"></i> Dispense Medications
    </button>
</form>
<small class="text-muted d-block text-center mt-2">
    <i class="fas fa-info-circle"></i> Enter quantities to dispense in the table above
</small>
```

---

#### **3. pharmacy/cart_views.py**

**Changes:**
- Modified `complete_dispensing_from_cart()` to check for custom quantities (Line ~293-346)
- Added validation for custom quantities
- Maintains backward compatibility

**Code:**
```python
# Check if pharmacist specified a custom quantity
custom_qty_key = f'dispense_qty_{cart_item.id}'
custom_quantity = request.POST.get(custom_qty_key)

if custom_quantity:
    # Pharmacist specified a custom quantity
    try:
        quantity_to_dispense = int(custom_quantity)
        
        # Validate the custom quantity
        available_to_dispense = cart_item.get_available_to_dispense_now()
        
        if quantity_to_dispense <= 0:
            # Skip items with 0 quantity
            continue
        
        if quantity_to_dispense > available_to_dispense:
            messages.error(request, f'Cannot dispense {quantity_to_dispense} of {medication.name}. Only {available_to_dispense} available.')
            return redirect('pharmacy:view_cart', cart_id=cart.id)
        
    except (ValueError, TypeError):
        messages.error(request, f'Invalid quantity for {medication.name}.')
        return redirect('pharmacy:view_cart', cart_id=cart.id)
else:
    # No custom quantity specified, use automatic logic
    available_to_dispense = cart_item.get_available_to_dispense_now()
    
    if available_to_dispense <= 0:
        messages.warning(request, f'No stock available for {medication.name}.')
        skipped_count += 1
        continue
    
    quantity_to_dispense = available_to_dispense
```

---

## 💡 Benefits

### **For Pharmacists:**
✅ **Full control** - Decide exactly how much to dispense
✅ **Flexibility** - Can dispense partial quantities based on patient needs
✅ **Stock management** - Can reserve stock for other patients
✅ **Error prevention** - Validation prevents over-dispensing
✅ **Clear feedback** - Shows max available for each item

### **For Patients:**
✅ **Better service** - Get exactly what they need
✅ **Partial fulfillment** - Can get some medications now, rest later
✅ **Accurate billing** - Only charged for what's dispensed

### **For System:**
✅ **Backward compatible** - Existing functionality preserved
✅ **Flexible** - Works with automatic or manual quantities
✅ **Validated** - Prevents data integrity issues
✅ **Auditable** - All dispensing logged accurately

---

## 🧪 Testing Checklist

### **Test Case 1: Manual Quantity Input**
- [ ] Cart status is 'paid'
- [ ] "To Dispense" column appears
- [ ] Default values show max available
- [ ] Can change quantities
- [ ] Max value enforced
- [ ] Click "Dispense Medications"
- [ ] Confirmation dialog appears
- [ ] Medications dispensed with custom quantities

### **Test Case 2: Validation**
- [ ] Enter quantity > max available
- [ ] Click "Dispense Medications"
- [ ] Error message shows
- [ ] Form not submitted
- [ ] Can correct and resubmit

### **Test Case 3: Zero Quantities**
- [ ] Set all quantities to 0
- [ ] Click "Dispense Medications"
- [ ] Error: "Please enter at least one quantity"
- [ ] Form not submitted

### **Test Case 4: Partial Dispensing**
- [ ] Enter quantity less than max for some items
- [ ] Dispense successfully
- [ ] Cart status → 'partially_dispensed'
- [ ] Remaining quantities shown correctly
- [ ] Can dispense remaining later

### **Test Case 5: Automatic Mode (Backward Compatibility)**
- [ ] Don't change any quantities (leave as default)
- [ ] Click "Dispense Medications"
- [ ] All available quantities dispensed
- [ ] Works exactly as before ✅

### **Test Case 6: NHIA Patient**
- [ ] Cart for NHIA patient
- [ ] Enter custom quantities
- [ ] Dispense
- [ ] Pricing calculated correctly (10%/90% split)
- [ ] Invoice accurate

---

## 📖 Documentation

✅ **PHARMACIST_DISPENSE_QUANTITY_INPUT.md** - This file

---

## 🎯 Summary

**Feature:** Pharmacist can input custom dispense quantities

**Implementation:**
1. ✅ Added "To Dispense" column in cart table
2. ✅ Added quantity input fields for each item
3. ✅ Added JavaScript validation and form preparation
4. ✅ Updated backend to handle custom quantities
5. ✅ Maintained backward compatibility

**Result:** Pharmacists have full control over dispensing quantities while maintaining all existing automatic functionality! ✅

---

**Status:** ✅ Complete and Ready for Testing
**Impact:** High - Provides pharmacists with more control and flexibility
**Backward Compatible:** Yes - Existing workflows unchanged

