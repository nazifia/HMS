# NHIA Authorization System - UI Testing Guide

## Overview
This guide provides step-by-step instructions for testing all UI components of the NHIA Authorization System.

**Server Status:** ✅ Running at `http://localhost:8000`

---

## Pre-Testing Setup

### 1. Verify Test Data
```bash
# Test data should already be created
# If not, run:
python manage.py setup_nhia_test_data
```

### 2. Test User Credentials
All test users have password: `test123`

| Username | Role | Purpose |
|----------|------|---------|
| test_desk_office | Desk Office Staff | Test authorization dashboard |
| test_general_doctor | Doctor | Test creating consultations requiring authorization |
| test_nhia_doctor | Doctor | Test NHIA consultations (no authorization) |
| test_cardiology_doctor | Doctor | Test referrals |

### 3. Test Patients
- **NHIA Patients:** Test NHIA Patient One, Two, Three
- **Regular Patients:** Test Regular Patient One, Two

---

## UI Test Scenarios

## Scenario 1: Desk Office Dashboard UI

### Test 1.1: Access Dashboard
**Steps:**
1. Navigate to: `http://localhost:8000/accounts/login/`
2. Login as: `test_desk_office` / `test123`
3. Navigate to: `http://localhost:8000/desk-office/authorization-dashboard/`

**Expected UI Elements:**
- ✅ Page title: "NHIA Authorization Dashboard"
- ✅ Four statistics cards:
  - Total Pending Authorizations
  - Pending Consultations
  - Pending Referrals
  - Pending Services
- ✅ Each card has:
  - Icon (appropriate to the metric)
  - Number (count)
  - Label
  - Color coding (blue, green, yellow, red)
- ✅ "Pending Consultations" section with table
- ✅ "Pending Referrals" section with table
- ✅ "Recent Authorization Codes" section with table

**Visual Checks:**
- [ ] Cards are aligned horizontally
- [ ] Icons are visible and appropriate
- [ ] Numbers are large and readable
- [ ] Tables have headers
- [ ] Tables are responsive
- [ ] Action buttons are visible

**Screenshot:** Take screenshot of dashboard overview

---

### Test 1.2: Pending Consultations Table
**Steps:**
1. Scroll to "Pending Consultations" section
2. Examine table structure

**Expected UI Elements:**
- ✅ Table headers:
  - Patient
  - Doctor
  - Room
  - Date
  - Reason
  - Actions
- ✅ Each row has:
  - Patient name (clickable link)
  - Doctor name
  - Room number and department
  - Date and time
  - "Authorization Required" badge (yellow)
  - "Authorize" button (green)
- ✅ DataTables features:
  - Search box
  - Entries dropdown (10, 25, 50, 100)
  - Pagination controls
  - "Showing X to Y of Z entries"

**Visual Checks:**
- [ ] Table is sortable (click headers)
- [ ] Search box filters results
- [ ] Pagination works
- [ ] Buttons are styled correctly
- [ ] Badges are color-coded

**Screenshot:** Take screenshot of pending consultations table

---

### Test 1.3: Authorization Code Generation Form
**Steps:**
1. Click "Authorize" button for any pending consultation
2. Examine the authorization form

**Expected UI Elements:**
- ✅ Page title: "Authorize Consultation"
- ✅ Consultation details card:
  - Patient information
  - Doctor name
  - Consulting room
  - Date
  - Chief complaint
  - Why authorization is required
- ✅ Authorization form:
  - Amount Covered (input field with currency symbol)
  - Validity Period (dropdown: 7, 14, 30, 60, 90 days)
  - Notes (textarea)
  - "Generate Authorization Code" button (primary/blue)
  - "Cancel" button (secondary/gray)

**Visual Checks:**
- [ ] Form is well-organized
- [ ] Input fields are properly labeled
- [ ] Help text is visible
- [ ] Buttons are aligned
- [ ] Form is responsive

**Screenshot:** Take screenshot of authorization form

---

### Test 1.4: Generate Authorization Code
**Steps:**
1. Fill in the form:
   - Amount: `500.00`
   - Validity: `30 Days`
   - Notes: `Test authorization for UI testing`
2. Click "Generate Authorization Code"

**Expected UI Elements:**
- ✅ Success message appears (green alert):
  - "Authorization code generated successfully"
  - Shows the generated code (format: AUTH-YYYYMMDD-XXXXXX)
- ✅ Redirected to dashboard
- ✅ Consultation no longer in pending list
- ✅ Code appears in "Recent Authorization Codes" table

**Visual Checks:**
- [ ] Success message is prominent
- [ ] Code is displayed clearly
- [ ] Code can be copied
- [ ] Dashboard updates immediately

**Screenshot:** Take screenshot of success message and updated dashboard

---

## Scenario 2: Consultation Detail Page UI

### Test 2.1: Create Consultation Requiring Authorization
**Steps:**
1. Logout and login as: `test_general_doctor` / `test123`
2. Navigate to: `http://localhost:8000/consultations/create/`
3. Fill in form:
   - Patient: "Test NHIA Patient Two"
   - Consulting Room: "GEN-201 - General Medicine"
   - Chief Complaint: "Headache and fever"
   - Symptoms: "Patient reports severe headache for 3 days"
   - Diagnosis: "Suspected migraine"
4. Save consultation
5. View consultation detail page

**Expected UI Elements:**
- ✅ **Warning Banner** at top of page:
  - Yellow/warning background
  - Warning icon (⚠️)
  - Bold heading: "This consultation requires desk office authorization"
  - Explanation text
  - Collapsible "Why is this required?" section
  - "Action Required" message
- ✅ **Authorization Status Badge** in consultation info:
  - Yellow badge: "Authorization Required"
  - Below status field

**Visual Checks:**
- [ ] Warning banner is prominent
- [ ] Banner spans full width
- [ ] Icon is visible
- [ ] Text is readable
- [ ] Collapsible section works
- [ ] Badge is color-coded correctly

**Screenshot:** Take screenshot of consultation with authorization warning

---

### Test 2.2: Consultation After Authorization
**Steps:**
1. Login as desk office staff
2. Authorize the consultation (from Scenario 2.1)
3. Login back as doctor
4. View the same consultation detail page

**Expected UI Elements:**
- ✅ **No Warning Banner** (should be gone)
- ✅ **Authorization Status Badge** changed to:
  - Green badge: "Authorized"
  - Shows authorization details:
    - Authorization Code
    - Service Type
    - Expiry Date

**Visual Checks:**
- [ ] Warning banner is completely removed
- [ ] Badge changed from yellow to green
- [ ] Authorization details are displayed
- [ ] Code is formatted correctly
- [ ] Expiry date is readable

**Screenshot:** Take screenshot of authorized consultation

---

## Scenario 3: Prescription UI

### Test 3.1: Create Prescription Form
**Steps:**
1. Login as: `test_general_doctor` / `test123`
2. Navigate to: `http://localhost:8000/pharmacy/prescriptions/create/`
3. Examine the form

**Expected UI Elements:**
- ✅ Standard prescription form fields
- ✅ **Authorization Code Input Field**:
  - Label: "Authorization Code (if required)"
  - Text input field
  - Placeholder: "Enter authorization code (e.g., AUTH-20250930-ABC123)"
  - Help text: "Enter the authorization code if this prescription requires NHIA authorization"

**Visual Checks:**
- [ ] Field is clearly labeled
- [ ] Placeholder text is visible
- [ ] Help text is informative
- [ ] Field is optional (can be left blank)

**Screenshot:** Take screenshot of prescription form with authorization field

---

### Test 3.2: Prescription Detail with Authorization Required
**Steps:**
1. Create a prescription for "Test NHIA Patient Two" (from authorized consultation)
2. Don't enter authorization code
3. Save prescription
4. View prescription detail page

**Expected UI Elements:**
- ✅ **Warning Banner** at top:
  - Similar to consultation warning
  - Specific to prescriptions
- ✅ **Authorization Status Badge**:
  - Yellow: "Authorization Required"

**Visual Checks:**
- [ ] Warning is prescription-specific
- [ ] Badge is in correct location
- [ ] Message is clear

**Screenshot:** Take screenshot of prescription requiring authorization

---

### Test 3.3: Prescription Detail After Authorization
**Steps:**
1. Edit the prescription and add the authorization code (from Scenario 2.2)
2. Save prescription
3. View prescription detail page

**Expected UI Elements:**
- ✅ **No Warning Banner**
- ✅ **Authorization Status Badge**:
  - Green: "Authorized"
  - Shows code details

**Visual Checks:**
- [ ] Warning removed
- [ ] Badge is green
- [ ] Code details visible

**Screenshot:** Take screenshot of authorized prescription

---

## Scenario 4: Laboratory Test Request UI

### Test 4.1: Test Request Form
**Steps:**
1. Navigate to: `http://localhost:8000/laboratory/test-requests/create/`
2. Examine the form

**Expected UI Elements:**
- ✅ Standard test request form fields
- ✅ **Authorization Code Input Field** (same as prescription)

**Visual Checks:**
- [ ] Field is present
- [ ] Styling is consistent
- [ ] Help text is clear

**Screenshot:** Take screenshot of test request form

---

### Test 4.2: Test Request Detail with Authorization
**Steps:**
1. Create test request for NHIA patient from authorized consultation
2. View test request detail page

**Expected UI Elements:**
- ✅ **Warning Banner** (if no code entered)
- ✅ **Authorization Status Badge**

**Visual Checks:**
- [ ] Warning is test-specific
- [ ] Badge displays correctly
- [ ] Layout is consistent

**Screenshot:** Take screenshot of test request detail

---

## Scenario 5: Radiology Order UI

### Test 5.1: Radiology Order Form
**Steps:**
1. Navigate to: `http://localhost:8000/radiology/orders/create/`
2. Examine the form

**Expected UI Elements:**
- ✅ Standard radiology order form fields
- ✅ **Authorization Code Input Field** (same as others)

**Visual Checks:**
- [ ] Field is present
- [ ] Styling is consistent
- [ ] Help text is clear

**Screenshot:** Take screenshot of radiology order form

---

### Test 5.2: Radiology Order Detail with Authorization
**Steps:**
1. Create radiology order for NHIA patient from authorized consultation
2. View order detail page

**Expected UI Elements:**
- ✅ **Warning Banner** (if no code entered)
- ✅ **Authorization Status Badge**

**Visual Checks:**
- [ ] Warning is radiology-specific
- [ ] Badge displays correctly
- [ ] Layout is consistent

**Screenshot:** Take screenshot of radiology order detail

---

## Responsive Design Testing

### Test 6.1: Mobile View (< 768px)
**Steps:**
1. Resize browser to 375px width (iPhone size)
2. Test each page:
   - Dashboard
   - Consultation detail
   - Prescription detail
   - Lab test detail
   - Radiology order detail

**Expected Behavior:**
- ✅ Tables become scrollable or stack
- ✅ Cards stack vertically
- ✅ Buttons remain accessible
- ✅ Text remains readable
- ✅ No horizontal scrolling (except tables)

**Visual Checks:**
- [ ] Layout adapts properly
- [ ] No overlapping elements
- [ ] Touch targets are large enough
- [ ] Navigation is accessible

---

### Test 6.2: Tablet View (768px - 1024px)
**Steps:**
1. Resize browser to 768px width (iPad size)
2. Test each page

**Expected Behavior:**
- ✅ Cards may be 2 per row
- ✅ Tables are fully visible
- ✅ Forms are well-spaced

**Visual Checks:**
- [ ] Layout is balanced
- [ ] Elements are properly spaced
- [ ] No wasted space

---

## Accessibility Testing

### Test 7.1: Keyboard Navigation
**Steps:**
1. Use Tab key to navigate through dashboard
2. Use Enter to activate buttons
3. Use arrow keys in dropdowns

**Expected Behavior:**
- ✅ All interactive elements are reachable
- ✅ Focus indicators are visible
- ✅ Tab order is logical
- ✅ Buttons can be activated with Enter/Space

**Visual Checks:**
- [ ] Focus outline is visible
- [ ] Focus order makes sense
- [ ] No keyboard traps

---

### Test 7.2: Screen Reader (Optional)
**Steps:**
1. Enable screen reader (NVDA, JAWS, or VoiceOver)
2. Navigate through pages

**Expected Behavior:**
- ✅ All content is announced
- ✅ Form labels are read
- ✅ Button purposes are clear
- ✅ Status messages are announced

---

## UI Testing Checklist Summary

### Dashboard
- [ ] Statistics cards display correctly
- [ ] Tables are functional (sort, search, paginate)
- [ ] Action buttons work
- [ ] Responsive on all screen sizes

### Warning Banners
- [ ] Appear when authorization required
- [ ] Disappear when authorized
- [ ] Correct messaging for each service type
- [ ] Collapsible sections work

### Status Badges
- [ ] Color-coded correctly (yellow/green/red)
- [ ] Show correct status
- [ ] Display authorization details when authorized
- [ ] Positioned consistently

### Authorization Code Input
- [ ] Present on all service forms
- [ ] Validates correctly
- [ ] Shows helpful error messages
- [ ] Optional when not required

### Forms
- [ ] All fields are accessible
- [ ] Validation works
- [ ] Success/error messages display
- [ ] Buttons are styled correctly

### Responsive Design
- [ ] Mobile view works
- [ ] Tablet view works
- [ ] Desktop view works
- [ ] No layout issues

### Accessibility
- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Screen reader compatible
- [ ] Color contrast sufficient

---

## Bug Reporting Template

If you find any UI issues, report them using this template:

```
**Page:** [e.g., Prescription Detail]
**Issue:** [Brief description]
**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected:** [What should happen]
**Actual:** [What actually happens]
**Screenshot:** [Attach screenshot]
**Browser:** [Chrome/Firefox/Safari/Edge]
**Screen Size:** [Desktop/Tablet/Mobile]
**Priority:** [High/Medium/Low]
```

---

## Testing Completion

Once all tests are complete:
- [ ] All UI elements display correctly
- [ ] All interactions work as expected
- [ ] Responsive design works on all devices
- [ ] Accessibility requirements met
- [ ] No critical bugs found
- [ ] Screenshots documented
- [ ] Ready for user acceptance testing

---

**Testing Guide Version:** 1.0
**Last Updated:** 2025-09-30
**Status:** Ready for Testing

