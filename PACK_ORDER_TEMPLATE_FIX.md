# Pack Order Template Fix - Missing Patient Field

## Issue
When trying to order a medical pack from the surgery detail page, users received the error:
**"Please correct the form errors."**

## Root Cause
The theatre pack order template (`theatre/templates/theatre/order_medical_pack.html`) was missing the **patient field** entirely. 

The form requires a patient field (it's a required field in the PackOrder model), but the template only rendered:
- Pack field
- Scheduled date field
- Order notes field

When the form was submitted without the patient field, Django's form validation failed because the required patient field was missing from the POST data.

## Solution
Added the patient field to all pack order templates:

### 1. Theatre Pack Order Template
**File**: `theatre/templates/theatre/order_medical_pack.html`

Added patient field rendering before the pack field:
```html
<!-- Patient Field (Pre-selected and Disabled) -->
<div class="mb-3">
    <label for="{{ form.patient.id_for_label }}" class="form-label">
        Patient <span class="text-danger">*</span>
    </label>
    {{ form.patient }}
    {% if form.patient_hidden %}
        {{ form.patient_hidden }}
    {% endif %}
    {% if form.patient.errors %}
        <div class="invalid-feedback d-block">
            {{ form.patient.errors.0 }}
        </div>
    {% endif %}
    <div class="form-text">
        Patient is automatically selected from the surgery
    </div>
</div>
```

### 2. Labor Pack Order Template
**File**: `labor/templates/labor/order_medical_pack.html`

Replaced the hardcoded hidden input:
```html
<!-- OLD - Hardcoded -->
<input type="hidden" name="patient" value="{{ record.patient.id }}">
```

With proper form field rendering:
```html
<!-- NEW - Using form fields -->
<div class="mb-3">
    <label for="{{ form.patient.id_for_label }}" class="form-label">
        Patient <span class="text-danger">*</span>
    </label>
    {{ form.patient }}
    {% if form.patient_hidden %}
        {{ form.patient_hidden }}
    {% endif %}
    {% if form.patient.errors %}
        <div class="invalid-feedback d-block">
            {{ form.patient.errors.0 }}
        </div>
    {% endif %}
    <div class="form-text">
        Patient is automatically selected from the labor record
    </div>
</div>
```

### 3. Pharmacy Pack Order Template
**File**: `pharmacy/templates/pharmacy/pack_orders/pack_order_form.html`

Added patient_hidden field rendering (patient field was already present):
```html
{{ form.patient }}
{% if form.patient_hidden %}
    {{ form.patient_hidden }}
{% endif %}
```

## How It Works

1. **Form Initialization**: When the form is initialized with `preselected_patient=surgery.patient`, the form:
   - Sets the patient field to the surgery's patient
   - Disables the patient field (makes it read-only)
   - Creates a hidden `patient_hidden` field with the actual patient value

2. **Template Rendering**: The template now renders:
   - The visible patient field (disabled, showing patient name)
   - The hidden patient_hidden field (contains the actual patient ID for submission)

3. **Form Submission**: When the form is submitted:
   - The disabled patient field is ignored by the browser
   - The patient_hidden field value is submitted
   - The form's clean() method copies patient_hidden to patient
   - Validation passes because patient field now has a value

## Benefits

1. **Fixes Form Validation**: Pack orders can now be submitted successfully
2. **Better UX**: Users can see which patient the pack is for
3. **Prevents Errors**: Patient field is disabled, preventing accidental changes
4. **Consistent Behavior**: All pack order templates now work the same way
5. **Proper Error Display**: If there are patient field errors, they're now visible

## Testing

To verify the fix works:

1. Navigate to a surgery detail page
2. Click "Order Medical Pack"
3. Select a pack from the dropdown
4. Click "Order Pack"
5. Verify the pack order is created successfully (no "Please correct the form errors" message)

## Files Modified

- `theatre/templates/theatre/order_medical_pack.html` - Added patient field
- `labor/templates/labor/order_medical_pack.html` - Replaced hardcoded input with form field
- `pharmacy/templates/pharmacy/pack_orders/pack_order_form.html` - Added patient_hidden field

## Related Issues

This fix complements the previous fixes in `THEATRE_PACK_ORDER_FIXES.md`:
- The form logic was already correct (patient pre-selection working)
- The view logic was already correct (passing preselected_patient)
- Only the templates were missing the patient field rendering

Now the entire pack order flow works correctly from end to end.

