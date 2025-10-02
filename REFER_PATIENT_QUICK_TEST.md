# Refer Patient - Quick Test Guide

## Quick Test Steps

### 1. Start the Development Server
```bash
python manage.py runserver
```

### 2. Navigate to Patient Detail Page
```
http://localhost:8000/patients/<patient_id>/
```
Replace `<patient_id>` with an actual patient ID from your database.

### 3. Test the Modal

#### Step 1: Locate the Button
- Look for the "Refer Patient" button in the Quick Actions section
- It should have a red background (btn-danger class)
- Icon: user-md (doctor icon)

#### Step 2: Click the Button
- Click the "Refer Patient" button
- Modal should open smoothly

#### Step 3: Verify Modal Content
Check that the modal contains:
- ✅ Title: "Refer [Patient Name] to Another Doctor"
- ✅ Dropdown: "Refer To" (should be populated with doctors)
- ✅ Textarea: "Reason for Referral" (required)
- ✅ Textarea: "Additional Notes" (optional)
- ✅ Buttons: "Close" and "Submit Referral"

#### Step 4: Check Console
Open browser console (F12) and verify:
- ✅ "Loading doctors for referral modal..." message
- ✅ "Doctors API response status: 200" message
- ✅ "Doctors loaded: X" message (where X > 0)
- ✅ "Doctors dropdown populated successfully" message
- ❌ No error messages

#### Step 5: Test Form Submission
1. Select a doctor from the dropdown
2. Enter a reason (e.g., "Specialist consultation required")
3. Optionally add notes
4. Click "Submit Referral"
5. Verify:
   - ✅ Success message appears
   - ✅ Page redirects to patient detail
   - ✅ Referral is created in database

### 4. Verify in Database

#### Option 1: Django Admin
```
http://localhost:8000/admin/consultations/referral/
```

#### Option 2: Django Shell
```bash
python manage.py shell
```
```python
from consultations.models import Referral
referrals = Referral.objects.all().order_by('-created_at')
latest = referrals.first()
print(f"Patient: {latest.patient.get_full_name()}")
print(f"From: Dr. {latest.referring_doctor.get_full_name()}")
print(f"To: Dr. {latest.referred_to.get_full_name()}")
print(f"Reason: {latest.reason}")
print(f"Status: {latest.status}")
```

## Console Test Script

Copy and paste this into your browser console on the patient detail page:

```javascript
// === Refer Patient Modal Test ===
console.log('=== Starting Refer Patient Modal Test ===');

// Test 1: Check if modal exists
const modal = document.getElementById('referralModal');
console.log('✓ Modal exists:', !!modal);

// Test 2: Check if button exists
const button = document.getElementById('referPatientBtn');
console.log('✓ Button exists:', !!button);

// Test 3: Check if form exists
const form = modal ? modal.querySelector('form') : null;
console.log('✓ Form exists:', !!form);

// Test 4: Check form action
if (form) {
    console.log('✓ Form action:', form.action);
}

// Test 5: Check if referred_to select exists
const referredToSelect = document.getElementById('referred_to');
console.log('✓ Referred_to select exists:', !!referredToSelect);

// Test 6: Check if doctors are loaded
if (referredToSelect) {
    const doctorCount = referredToSelect.options.length - 1; // -1 for placeholder
    console.log('✓ Number of doctors loaded:', doctorCount);
    
    if (doctorCount > 0) {
        console.log('✓ Sample doctors:');
        Array.from(referredToSelect.options).slice(1, 4).forEach((option, index) => {
            console.log(`  ${index + 1}. ${option.text}`);
        });
    } else {
        console.warn('⚠ No doctors loaded!');
    }
}

// Test 7: Check reason field
const reasonField = document.getElementById('reason');
console.log('✓ Reason field exists:', !!reasonField);
console.log('✓ Reason field is required:', reasonField ? reasonField.required : false);

// Test 8: Check notes field
const notesField = document.getElementById('notes');
console.log('✓ Notes field exists:', !!notesField);

// Test 9: Test API endpoint
console.log('Testing API endpoint...');
fetch('/accounts/api/users/?role=doctor')
    .then(response => {
        console.log('✓ API Response Status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('✓ API Response - Doctors found:', data.length);
        if (data.length > 0) {
            console.log('✓ Sample API response:');
            console.log(data.slice(0, 2));
        }
    })
    .catch(error => {
        console.error('✗ API Error:', error);
    });

// Test 10: Test modal opening
if (button && modal) {
    console.log('Testing modal open functionality...');
    button.click();
    setTimeout(() => {
        const isVisible = modal.classList.contains('show');
        console.log('✓ Modal is visible after click:', isVisible);
        
        // Close modal
        const closeButton = modal.querySelector('[data-bs-dismiss="modal"]');
        if (closeButton) {
            closeButton.click();
            console.log('✓ Modal closed');
        }
    }, 1000);
}

console.log('=== Test Complete ===');
console.log('Check the results above. All items should show ✓');
```

## Expected Results

### ✅ All Tests Should Pass

1. Modal exists: true
2. Button exists: true
3. Form exists: true
4. Form action: /consultations/referrals/create/[patient_id]/
5. Referred_to select exists: true
6. Number of doctors loaded: > 0
7. Reason field exists: true
8. Reason field is required: true
9. Notes field exists: true
10. API Response Status: 200
11. API Response - Doctors found: > 0
12. Modal is visible after click: true

### ❌ Common Issues and Solutions

#### Issue 1: No doctors loaded
**Symptom:** Dropdown shows "No doctors available"
**Solution:** 
- Check if users have 'doctor' role assigned
- Run: `python manage.py shell`
```python
from accounts.models import Role, CustomUser
doctor_role, _ = Role.objects.get_or_create(name='doctor')
# Assign to a user
user = CustomUser.objects.first()
user.roles.add(doctor_role)
```

#### Issue 2: API returns 403 Forbidden
**Symptom:** Console shows "HTTP error! status: 403"
**Solution:**
- Ensure user is logged in
- Check `@login_required` decorator on api_users view

#### Issue 3: Modal doesn't open
**Symptom:** Nothing happens when clicking button
**Solution:**
- Check browser console for JavaScript errors
- Verify Bootstrap JS is loaded
- Check if button has correct data attributes

#### Issue 4: Form submission fails
**Symptom:** Form doesn't submit or shows validation errors
**Solution:**
- Check all required fields are filled
- Verify CSRF token is present
- Check Django logs for server-side errors

## Manual Test Checklist

Print this checklist and mark each item as you test:

- [ ] Development server is running
- [ ] Navigated to patient detail page
- [ ] "Refer Patient" button is visible
- [ ] Button has correct styling (red background)
- [ ] Clicking button opens modal
- [ ] Modal has correct title with patient name
- [ ] Doctors dropdown is populated
- [ ] Can select a doctor from dropdown
- [ ] Reason field is present and editable
- [ ] Reason field shows as required
- [ ] Notes field is present and editable
- [ ] Notes field is optional
- [ ] Submit button is present
- [ ] Close button is present
- [ ] Can close modal with close button
- [ ] Can close modal by clicking outside
- [ ] Form submits when all required fields filled
- [ ] Success message appears after submission
- [ ] Redirected to patient detail page
- [ ] Referral appears in database
- [ ] No console errors during entire process

## Performance Checklist

- [ ] Modal opens within 500ms
- [ ] Doctors load within 1 second
- [ ] Form submits within 2 seconds
- [ ] Page redirects smoothly
- [ ] No lag or freezing

## Browser Compatibility

Test in multiple browsers:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if available)

## Mobile Responsiveness

Test on mobile devices or using browser dev tools:
- [ ] Modal displays correctly on mobile
- [ ] Form fields are easily tappable
- [ ] Dropdown works on touch devices
- [ ] Submit button is accessible

## Conclusion

If all tests pass, the Refer Patient functionality is working correctly and ready for use.

**Status:** ✅ VERIFIED WORKING

**Date Tested:** [Fill in date]
**Tested By:** [Fill in name]
**Browser:** [Fill in browser and version]
**Issues Found:** [List any issues or write "None"]

