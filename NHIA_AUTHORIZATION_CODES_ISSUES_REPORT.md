# NHIA Authorization Codes Page - Issues Report

**Page URL:** `/desk-office/authorization-codes/`  
**Template:** `templates/desk_office/authorization_code_list.html`  
**View:** `desk_office/authorization_dashboard_views.py::authorization_code_list`  
**Testing Date:** 2025-10-26

---

## 🔴 CRITICAL ISSUES

### 1. **Missing POST Handler for Generate Authorization Code**
**Severity:** CRITICAL  
**Location:** `desk_office/views.py::generate_authorization_code` (line 9)  
**Issue:** The template's JavaScript (line 512) sends a POST request to `{% url "desk_office:generate_authorization_code" %}` expecting a JSON response, but the view at `desk_office/views.py::generate_authorization_code` doesn't handle this type of POST request. It only handles POST requests with 'search_patients' or 'generate_code' in the POST data.

**Expected Behavior:** When clicking "Generate Code" button in the modal, the system should create an authorization code and return JSON response.

**Actual Behavior:** The POST request fails or returns unexpected response format.

**Impact:** Users cannot generate authorization codes from the modal on the authorization codes list page.

**Fix Required:** Add a new view or modify existing view to handle AJAX POST requests for code generation.

---

### 2. **Incorrect Parameter Name in Filter**
**Severity:** CRITICAL  
**Location:** `desk_office/authorization_dashboard_views.py::authorization_code_list` (line 445)  
**Issue:** The view checks for `request.GET.get('patient')` but the template form field is named `patient_search` (line 161).

**Expected Behavior:** Patient search filter should work when user enters patient name/ID and clicks "Apply Filters".

**Actual Behavior:** Patient search filter doesn't work because parameter names don't match.

**Impact:** Users cannot filter authorization codes by patient name or ID.

**Fix Required:** Change line 445 from `patient_search = request.GET.get('patient')` to `patient_search = request.GET.get('patient_search')`.

---

### 3. **Wrong HTTP Method for Cancel Authorization Code**
**Severity:** CRITICAL  
**Location:** `templates/desk_office/authorization_code_list.html` (line 299)  
**Issue:** The cancel button uses a GET request (anchor tag with href), but the view `cancel_authorization_code` expects POST method (line 156 in views.py).

**Expected Behavior:** Clicking cancel should cancel the authorization code.

**Actual Behavior:** Cancel action doesn't work because of HTTP method mismatch.

**Impact:** Users cannot cancel active authorization codes.

**Fix Required:** Change the cancel button to use a form with POST method or add JavaScript to submit via POST.

---

### 4. **Incorrect Authorization Code Detail URL**
**Severity:** CRITICAL  
**Location:** `templates/desk_office/authorization_code_list.html` (line 554) & `desk_office/views.py` (line 171)  
**Issue:** The JavaScript fetches `/desk-office/authorization-code-detail/${codeId}/` but the view expects `code_id` to be the actual code string, not the database ID. The template passes `data-code-id="{{ code.id }}"` (line 294) which is the database ID, not the code string.

**Expected Behavior:** Clicking "View Details" should show authorization code details.

**Actual Behavior:** Detail modal shows error because it's looking up by ID instead of code string.

**Impact:** Users cannot view authorization code details.

**Fix Required:** Either change the view to accept database ID or change the template to pass the code string.

---

## 🟡 MAJOR ISSUES

### 5. **Missing Export Functionality**
**Severity:** MAJOR  
**Location:** `templates/desk_office/authorization_code_list.html` (line 599)  
**Issue:** The export button adds `?export=csv` to the URL, but there's no handling for this parameter in the view.

**Expected Behavior:** Clicking export should download a CSV file of authorization codes.

**Actual Behavior:** Export button just reloads the page with export parameter but doesn't export anything.

**Impact:** Users cannot export authorization codes data.

**Fix Required:** Add export handling in the view to generate and return CSV file.

---

### 6. **Missing HTMX Library**
**Severity:** MAJOR  
**Location:** `templates/desk_office/authorization_code_list.html` (line 376)  
**Issue:** The template uses HTMX attributes (`hx-get`, `hx-target`, etc.) but doesn't include the HTMX library in the page.

**Expected Behavior:** Patient search in the modal should work with HTMX.

**Actual Behavior:** HTMX attributes are ignored if library is not loaded.

**Impact:** Patient search in generate code modal may not work.

**Fix Required:** Add HTMX library to base template or this template's extra_js block.

---

### 7. **Missing Hidden Input for Selected Patient**
**Severity:** MAJOR  
**Location:** `templates/desk_office/authorization_code_list.html` (line 484)  
**Issue:** The JavaScript looks for `#modalPatientResults input[type="radio"]:checked` but the patient search results don't include radio buttons for selection.

**Expected Behavior:** Users should be able to select a patient from search results.

**Actual Behavior:** No way to select a patient, form submission fails.

**Impact:** Cannot generate authorization codes because patient selection doesn't work.

**Fix Required:** Add patient selection UI (radio buttons or clickable cards) in the patient search results.

---

## 🟢 MINOR ISSUES

### 8. **Inconsistent Date Filter Field Names**
**Severity:** MINOR  
**Location:** `desk_office/authorization_dashboard_views.py` (lines 488-490)  
**Issue:** The context passes `date_from` and `date_to` but these aren't used in the template to preserve filter values.

**Expected Behavior:** After applying filters, the date fields should retain their values.

**Actual Behavior:** Date fields are preserved (template uses `request.GET.date_from`), so this is actually working correctly.

**Impact:** None - this is working as expected.

**Fix Required:** None.

---

### 9. **Missing Loading State for Generate Code Button**
**Severity:** MINOR  
**Location:** `templates/desk_office/authorization_code_list.html` (line 439)  
**Issue:** The "Generate Code" button doesn't show a loading state while the request is being processed.

**Expected Behavior:** Button should show loading spinner while processing.

**Actual Behavior:** Button remains clickable and shows no feedback.

**Impact:** Users might click multiple times, creating duplicate requests.

**Fix Required:** Add loading state (disable button and show spinner) during form submission.

---

### 10. **No Validation for Manual Code Input**
**Severity:** MINOR  
**Location:** `templates/desk_office/authorization_code_list.html` (line 421)  
**Issue:** Manual code input has maxlength but no pattern validation or uniqueness check before submission.

**Expected Behavior:** Should validate manual code format and check for duplicates.

**Actual Behavior:** Only validates on server side after submission.

**Impact:** Poor user experience - errors only shown after submission.

**Fix Required:** Add client-side validation and AJAX uniqueness check.

---

## 📊 SUMMARY

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 Critical | 4 | Missing POST handler, Wrong parameter name, Wrong HTTP method, Incorrect URL |
| 🟡 Major | 3 | Missing export, Missing HTMX, Missing patient selection UI |
| 🟢 Minor | 3 | Loading states, Validation |
| **Total** | **10** | |

---

## 🎯 PRIORITY FIX ORDER

1. **Fix patient search parameter name** (Issue #2) - Quick fix, enables filtering
2. **Add POST handler for code generation** (Issue #1) - Critical for main functionality
3. **Fix cancel authorization code HTTP method** (Issue #3) - Critical for code management
4. **Fix authorization code detail lookup** (Issue #4) - Critical for viewing details
5. **Add patient selection UI** (Issue #7) - Required for code generation
6. **Add HTMX library** (Issue #6) - Required for patient search
7. **Add export functionality** (Issue #5) - Nice to have feature
8. **Add loading states** (Issue #9) - UX improvement
9. **Add validation** (Issue #10) - UX improvement

---

## 🔧 ADDITIONAL OBSERVATIONS

### Positive Aspects:
- ✅ Good UI/UX design with statistics cards
- ✅ Proper pagination implementation
- ✅ Good use of Bootstrap 5 components
- ✅ Responsive design considerations
- ✅ Print functionality implemented
- ✅ Good error handling in JavaScript

### Recommendations:
1. Add comprehensive error logging
2. Add user permission checks for sensitive operations
3. Consider adding bulk operations (bulk cancel, bulk export)
4. Add audit trail for code generation and cancellation
5. Consider adding code expiry notifications
6. Add search by code string functionality

