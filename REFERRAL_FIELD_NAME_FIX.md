# Referral Field Name Fix - AttributeError Resolution

## Issues Summary

### Issue 1: Template Field Name Error
**Error**: `AttributeError: 'str' object has no attribute 'as_widget'`
**Location**: `core/templatetags/core_form_tags.py`, line 11
**URL**: `http://127.0.0.1:8000/consultations/referrals/create/42/`
**Status**: ✅ **FIXED**

### Issue 2: Missing View Function
**Error**: `AttributeError: module 'consultations.views' has no attribute 'test_referral_form'`
**Location**: `consultations/urls.py`, line 32
**Status**: ✅ **FIXED**

## Root Cause
The templates were using the old field name `referred_to` which was removed in migration `0007_add_department_referral_system.py`. The field was replaced with `referred_to_doctor` to support the new multi-type referral system (department, specialty, unit, doctor).

When Django tries to access a non-existent form field like `form.referred_to`, it returns an empty string. The `add_class` template filter then tries to call `.as_widget()` on this string, causing the AttributeError.

## Migration History
In migration `consultations/migrations/0007_add_department_referral_system.py`:
- **Removed**: `referred_to` field
- **Added**: 
  - `referred_to_doctor` (for specific doctor referrals)
  - `referred_to_department` (for department referrals)
  - `referred_to_specialty` (for specialty referrals)
  - `referred_to_unit` (for unit referrals)
  - `assigned_doctor` (for tracking who accepted the referral)

## Files Fixed

### 1. `consultations/urls.py`
**Issue**: Debug route referencing non-existent view function
**Changes Made**: 1 line removed

#### Removed Debug Route (Line 32)
```python
# BEFORE (caused AttributeError on server startup)
path('referrals/test/<int:patient_id>/', views.test_referral_form, name='test_referral_form'),  # Debug route

# AFTER (removed - view function doesn't exist)
# Line removed completely
```

### 2. `templates/consultations/referral_form.html`
**Changes Made**: 4 occurrences updated

#### Change 1: Form Field Label and Input (Lines 110-122)
```html
<!-- BEFORE -->
<label for="{{ form.referred_to.id_for_label }}" class="form-label">
{{ form.referred_to|add_class:"form-select select2" }}
{% if form.referred_to.errors %}

<!-- AFTER -->
<label for="{{ form.referred_to_doctor.id_for_label }}" class="form-label">
{{ form.referred_to_doctor|add_class:"form-select select2" }}
{% if form.referred_to_doctor.errors %}
```

#### Change 2: Referral History Display (Line 216)
```html
<!-- BEFORE -->
To: Dr. {{ referral.referred_to.get_full_name }}

<!-- AFTER -->
To: {{ referral.get_referral_destination }}
```
*Note: Using the model method `get_referral_destination()` which handles all referral types properly*

#### Change 3: JavaScript Form Validation (Lines 314-324)
```javascript
// BEFORE
const referredTo = $('#{{ form.referred_to.id_for_label }}').val();
$('#{{ form.referred_to.id_for_label }}').focus();

// AFTER
const referredTo = $('#{{ form.referred_to_doctor.id_for_label }}').val();
$('#{{ form.referred_to_doctor.id_for_label }}').focus();
```

#### Change 4: Authorization Check Event Listener (Line 352)
```javascript
// BEFORE
$('#{{ form.patient.id_for_label }}, #{{ form.referred_to.id_for_label }}').change(checkAuthorizationRequirement);

// AFTER
$('#{{ form.patient.id_for_label }}, #{{ form.referred_to_doctor.id_for_label }}').change(checkAuthorizationRequirement);
```

### 3. `templates/includes/referral_modal.html`
**Changes Made**: 3 occurrences updated

#### Change 1: Form Field (Lines 42-54)
```html
<!-- BEFORE -->
<label for="referred_to" class="form-label">
<select class="form-select" id="referred_to" name="referred_to" required>

<!-- AFTER -->
<label for="referred_to_doctor" class="form-label">
<select class="form-select" id="referred_to_doctor" name="referred_to_doctor" required>
```

#### Change 2: Load Doctors Function (Line 115)
```javascript
// BEFORE
const doctorsSelect = document.getElementById('referred_to');

// AFTER
const doctorsSelect = document.getElementById('referred_to_doctor');
```

#### Change 3: Form Validation (Line 210)
```javascript
// BEFORE
const doctorSelect = document.getElementById('referred_to');

// AFTER
const doctorSelect = document.getElementById('referred_to_doctor');
```

## Current Referral Model Structure

### Fields in `consultations/models.py`:
```python
class Referral(models.Model):
    # Referral destination fields
    referral_type = models.CharField(max_length=20, choices=REFERRAL_TYPE_CHOICES, default='department')
    referred_to_department = models.ForeignKey('accounts.Department', ...)
    referred_to_specialty = models.CharField(max_length=100, ...)
    referred_to_unit = models.CharField(max_length=100, ...)
    referred_to_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    assigned_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    
    # Other fields
    patient = models.ForeignKey(Patient, ...)
    referring_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, ...)
    # ... NHIA authorization fields
```

### Helper Method:
```python
def get_referral_destination(self):
    """Get a formatted string of the referral destination"""
    if self.referral_type == 'doctor' and self.referred_to_doctor:
        return f"Dr. {self.referred_to_doctor.get_full_name()}"
    elif self.referral_type == 'department' and self.referred_to_department:
        # Returns formatted department/specialty/unit string
    # ... handles all referral types
```

## Form Structure

### Fields in `consultations/forms.py`:
```python
class ReferralForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = [
            'patient', 
            'referral_type', 
            'referred_to_department', 
            'referred_to_specialty', 
            'referred_to_unit', 
            'referred_to_doctor',  # ← Correct field name
            'reason', 
            'notes'
        ]
```

## Testing Checklist
- [x] Django server starts without errors
- [x] URLs load without AttributeError
- [x] Navigate to `/consultations/referrals/create/42/`
- [x] Page loads without AttributeError
- [x] Doctor dropdown displays correctly
- [x] Form validation works (JavaScript)
- [x] Form submission works
- [x] Referral history displays correctly
- [x] Authorization check triggers on doctor change
- [x] Modal form works (from patient detail page)

## Prevention
To prevent similar issues in the future:
1. **Always update templates** when model fields are renamed in migrations
2. **Search for all occurrences** of old field names across templates and JavaScript
3. **Use model methods** like `get_referral_destination()` instead of direct field access when displaying data
4. **Test all forms** after migrations that change field names

## Related Files
- `consultations/models.py` - Referral model definition
- `consultations/forms.py` - ReferralForm definition
- `consultations/views.py` - create_referral view
- `consultations/migrations/0007_add_department_referral_system.py` - Migration that changed field names
- `core/templatetags/core_form_tags.py` - Template filter that raised the error

## Summary

### Issue 1: Template Field Names
**Before**: Templates used `form.referred_to` which no longer exists
**After**: Templates use `form.referred_to_doctor` which is the correct field name
**Result**: Referral form now loads and works correctly ✅

### Issue 2: Debug Route
**Before**: URL pattern referenced non-existent `test_referral_form` view
**After**: Debug route removed from `consultations/urls.py`
**Result**: Django server starts without errors ✅

### Overall Status
All referral functionality is now working correctly! 🎉

