# Modal Fixes Summary

**Date:** 2025-10-01  
**Status:** ✅ Complete

---

## Issues Fixed

### 1. Transfer Medication to Dispensary Modal Not Working

**Problem:**
- The modal form fields (Medication, Available Quantity, Transfer Quantity, To Dispensary) were not being populated when the "Transfer" button was clicked
- The modal would open but show empty or incorrect data

**Root Cause:**
- The button had `data-bs-toggle="modal"` which caused Bootstrap to open the modal immediately
- The JavaScript click handler was trying to populate fields on button click, but there was a timing issue
- The data attribute name in JavaScript (`medicationName`) didn't match the exact attribute name (`data-medication-name`)

**Solution:**
- Removed reliance on button click event for populating form fields
- Used Bootstrap 5's modal events (`show.bs.modal`) to populate fields when modal is about to be shown
- Fixed data attribute access to use exact attribute names
- Added modal cleanup on `hidden.bs.modal` event

**Files Changed:**
- `pharmacy/templates/pharmacy/active_store_detail.html`

**Changes Made:**
```javascript
// Store clicked button's data
var currentTransferData = {};

// Capture data on button click
$(document).on('click', '.transfer-btn', function() {
    currentTransferData = {
        medicationId: $(this).data('medication'),
        medicationName: $(this).data('medication-name'),  // Fixed: use exact attribute name
        batchNumber: $(this).data('batch'),
        availableQuantity: $(this).data('quantity')
    };
});

// Populate form when modal is shown
$('#transferModal').on('show.bs.modal', function (e) {
    $('#medicationId').val(currentTransferData.medicationId);
    $('#medicationName').val(currentTransferData.medicationName);
    $('#batchNumber').val(currentTransferData.batchNumber);
    $('#availableQuantity').val(currentTransferData.availableQuantity);
    $('#transferQuantity').attr('max', currentTransferData.availableQuantity);
    $('#transferQuantity').val(''); // Clear previous quantity
});

// Clear form when modal is hidden
$('#transferModal').on('hidden.bs.modal', function (e) {
    $('#transferQuantity').val('');
    currentTransferData = {};
});
```

---

### 2. Superuser Can't Refer Patients

**Problem:**
- Superuser (and other users) couldn't successfully create patient referrals
- The referral modal would open but form submission would fail

**Root Causes:**
1. **Extra form fields:** The modal had `urgency` and `referral_date` fields that don't exist in the `ReferralForm` model fields
2. **Missing patient field:** The form expected a `patient` field but it wasn't included in the modal form
3. **Form validation failing:** Due to the above issues, form validation was failing silently

**Solution:**
1. **Removed non-existent fields:** Removed `urgency` and `referral_date` fields from the modal (these don't exist in the Referral model)
2. **Added hidden patient field:** Added `<input type="hidden" name="patient" value="{{ patient.id }}">` to the form
3. **Improved view handling:** Updated `create_referral` view to properly handle patient_id from URL and add it to form data
4. **Enhanced doctor loading:** Improved the JavaScript to reload doctors when modal opens and added department info to doctor names
5. **Better error handling:** Added comprehensive error messages for debugging

**Files Changed:**
- `templates/patients/patient_detail.html`
- `consultations/views.py`

**Changes Made:**

**In patient_detail.html:**
```html
<!-- Added hidden patient field -->
<input type="hidden" name="patient" value="{{ patient.id }}">

<!-- Removed urgency and referral_date fields that don't exist in model -->
<!-- Only kept: referred_to, reason, notes -->
```

```javascript
// Improved doctor loading function
function loadDoctorsForReferral() {
    fetch('/accounts/api/users/?role=doctor')
        .then(response => response.json())
        .then(data => {
            const doctorsSelect = document.getElementById('referred_to');
            doctorsSelect.innerHTML = '<option value="">Select Doctor</option>';
            
            data.forEach(doctor => {
                const option = document.createElement('option');
                option.value = doctor.id;
                option.textContent = `Dr. ${doctor.first_name} ${doctor.last_name}`;
                if (doctor.department) {
                    option.textContent += ` (${doctor.department})`;
                }
                doctorsSelect.appendChild(option);
            });
        });
}

// Reload doctors when modal opens
referralModal.addEventListener('show.bs.modal', function (event) {
    loadDoctorsForReferral();
});
```

**In consultations/views.py:**
```python
@login_required
def create_referral(request, patient_id=None):
    if request.method == 'POST':
        # Create a mutable copy of POST data
        post_data = request.POST.copy()
        
        # If patient_id is provided in URL, add it to POST data
        if patient_id and 'patient' not in post_data:
            post_data['patient'] = patient_id
        
        form = ReferralForm(post_data)
        
        if form.is_valid():
            referral = form.save(commit=False)
            
            # Ensure patient is set from URL if not in form
            if patient and not referral.patient:
                referral.patient = patient
            
            referral.referring_doctor = request.user
            # ... rest of the code
```

---

## Testing Instructions

### Test Transfer Modal:
1. Navigate to a dispensary's active store page: `/pharmacy/dispensaries/{dispensary_id}/active-store/`
2. Click on any "Transfer" button in the stock table
3. Verify the modal opens with:
   - ✅ Medication name populated
   - ✅ Available quantity populated
   - ✅ Dispensary name shown
   - ✅ Transfer quantity field is empty and ready for input
4. Enter a transfer quantity
5. Click "Transfer" button
6. Verify the transfer is successful

### Test Referral Modal:
1. Navigate to any patient detail page: `/patients/{patient_id}/`
2. Click "Refer Patient" button
3. Verify the modal opens with:
   - ✅ Doctors dropdown is populated with active doctors
   - ✅ Doctor names show with department (if available)
4. Select a doctor from the dropdown
5. Enter reason for referral
6. Optionally add notes
7. Click "Submit Referral"
8. Verify:
   - ✅ Success message appears
   - ✅ Page redirects back to patient detail
   - ✅ Referral is created in the database

### Verify Superuser Access:
1. Log in as superuser
2. Navigate to patient detail page
3. Click "Refer Patient"
4. Complete and submit the referral form
5. Verify referral is created successfully

---

## Technical Details

### Bootstrap 5 Modal Events Used:
- `show.bs.modal` - Fired immediately when the show instance method is called
- `hidden.bs.modal` - Fired when the modal has finished being hidden from the user

### Form Fields in Referral Model:
- `patient` (ForeignKey) - Required
- `referred_to` (ForeignKey) - Required
- `reason` (TextField) - Required
- `notes` (TextField) - Optional
- `consultation` (ForeignKey) - Optional (can be null)
- `referring_doctor` (ForeignKey) - Set automatically from request.user
- `referral_date` (DateTimeField) - Has default value (timezone.now)

### API Endpoint:
- `/accounts/api/users/?role=doctor` - Returns JSON array of active doctors

---

## Benefits

1. **Better User Experience:**
   - Modals now work reliably
   - Form fields are properly populated
   - Clear error messages when validation fails

2. **Improved Code Quality:**
   - Uses Bootstrap 5 modal events properly
   - Better separation of concerns
   - More maintainable code

3. **Enhanced Debugging:**
   - Console logging for troubleshooting
   - Detailed error messages
   - Better form validation feedback

---

## Notes

- The `urgency` field was removed from the referral modal as it doesn't exist in the Referral model. If this field is needed, it should be added to the model first via a migration.
- The `referral_date` field has a default value in the model, so it doesn't need to be in the form.
- All changes maintain backward compatibility with existing functionality.

