# Pharmacy Prescription UnboundLocalError Fix

## Issue Description
**Error:** `UnboundLocalError: cannot access local variable 'preselected_patient' where it is not associated with a value`

**Location:** `pharmacy/views.py`, line 1665, in `pharmacy_create_prescription` function

**URL Pattern:** `/pharmacy/prescriptions/pharmacy-create/6/` (POST request)

## Root Cause Analysis

The error occurred because the `preselected_patient` variable was only defined within the `else` block (GET requests) but was being used in the `context` dictionary that exists outside both the `if` and `else` blocks.

### Problem Flow:
1. **GET Request**: `preselected_patient` is defined in the `else` block ✅
2. **POST Request**: `else` block doesn't execute, so `preselected_patient` is never defined ❌
3. **Context Creation**: Tries to use undefined `preselected_patient` variable → **UnboundLocalError**

### Original Problematic Code:
```python
def pharmacy_create_prescription(request, patient_id=None):
    if request.method == 'POST':
        # ... POST handling code ...
        # preselected_patient NOT defined here
    else:
        # ... GET handling code ...
        preselected_patient = None  # Only defined in else block
        # ...
    
    context = {
        # ...
        'selected_patient': preselected_patient,  # ❌ UnboundLocalError on POST
        'patient': preselected_patient,           # ❌ UnboundLocalError on POST
    }
```

## Solution Implemented

### 1. Variable Initialization at Function Start
Moved the `preselected_patient` initialization to the very beginning of the function, ensuring it's always defined regardless of request method.

### 2. Improved Patient Resolution Logic
Enhanced the patient object resolution with proper error handling.

### 3. Better Form Validation Handling
Improved the POST request handling to properly render forms with validation errors.

### Fixed Code:
```python
@login_required
def pharmacy_create_prescription(request, patient_id=None):
    """View for pharmacy creating a prescription"""
    # Initialize preselected_patient at the beginning to avoid UnboundLocalError
    preselected_patient = None
    if patient_id:
        try:
            preselected_patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            preselected_patient = None
    
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request=request, current_user=request.user)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.doctor = request.user
            prescription.save()
            form.save_m2m()
            messages.success(request, f'Prescription #{prescription.id} created successfully.')
            return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
        # If form is not valid, we continue to render the form with errors
    else:
        # Preselect patient if patient_id is provided
        initial_data = {'doctor': request.user}
        if preselected_patient:
            initial_data['patient'] = preselected_patient
        elif patient_id:
            initial_data['patient'] = patient_id
        form = PrescriptionForm(request=request, initial=initial_data, preselected_patient=preselected_patient, current_user=request.user)

    context = {
        'form': form,
        'title': 'Create Prescription (Pharmacy)',
        'active_nav': 'pharmacy',
        'selected_patient': preselected_patient,  # ✅ Always defined
        'patient': preselected_patient,           # ✅ Always defined
        'current_user': request.user,
    }

    return render(request, 'pharmacy/prescription_form.html', context)
```

## Key Improvements

### ✅ **Variable Scope Fix**
- `preselected_patient` is now initialized at function start
- Available in both GET and POST request paths
- Eliminates UnboundLocalError completely

### ✅ **Better Error Handling**
- Proper exception handling for patient lookup
- Graceful fallback when patient doesn't exist
- No crashes on invalid patient IDs

### ✅ **Improved Form Validation**
- POST requests with validation errors now properly re-render the form
- Error messages are preserved and displayed to users
- Better user experience for form corrections

### ✅ **Code Consistency**
- Cleaner variable initialization pattern
- More predictable code flow
- Easier to maintain and debug

## Testing Results

### Test Scenarios Validated:
1. ✅ **GET Request with Valid Patient ID** - Works correctly
2. ✅ **GET Request without Patient ID** - Handles gracefully  
3. ✅ **POST Request with Valid Data** - Creates prescription successfully
4. ✅ **POST Request with Invalid Data** - Shows validation errors (no crash)
5. ✅ **POST Request with Invalid Patient ID** - Handles gracefully
6. ✅ **POST Request without Patient ID** - Works correctly

### Pre-Fix vs Post-Fix:
- **Before**: UnboundLocalError on POST requests ❌
- **After**: All request types handled properly ✅

## Files Modified
- `pharmacy/views.py` - Fixed `pharmacy_create_prescription` function

## Impact
- **User Experience**: No more crash errors when creating prescriptions
- **System Stability**: Eliminated a critical runtime error
- **Development**: More robust error handling patterns
- **Maintenance**: Cleaner, more predictable code structure

## Verification
The fix has been tested with multiple scenarios and confirmed to resolve the UnboundLocalError while maintaining all existing functionality.

**Status: ✅ RESOLVED**