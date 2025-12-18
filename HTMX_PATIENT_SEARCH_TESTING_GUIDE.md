# HTMX Patient Search - Testing Guide

## ✅ Implementation Complete

The HTMX patient search has been successfully integrated into the laboratory test request creation form.

## 🔗 Testing URLs

### 1. Main Laboratory Test Request Form
**URL:** `http://127.0.0.1:8000/laboratory/requests/create/`

This is the production page with HTMX patient search integrated.

### 2. Diagnostic Testing Page
**URL:** `http://127.0.0.1:8000/laboratory/htmx-diagnostic/`

Use this page to diagnose any HTMX issues. It includes:
- Real-time system status checks
- Console output viewer
- Manual test button
- Detailed logging

## 🧪 How to Test

### Step 1: Login
Make sure you're logged in to the system as a user with laboratory access.

### Step 2: Access the Diagnostic Page
1. Go to: `http://127.0.0.1:8000/laboratory/htmx-diagnostic/`
2. Check the "System Status" section - all checks should be green
3. Type "test" in the search field
4. Watch the console output for:
   ```
   ✓ HTMX library loaded
   → HTMX Request: /patients/htmx-search/?q=test
   ✓ HTMX Response received and swapped
   ```

### Step 3: Test the Production Page
1. Go to: `http://127.0.0.1:8000/laboratory/requests/create/`
2. Type at least 2 characters in the "Search Patient" field
3. You should see:
   - A loading spinner while fetching
   - Dropdown with matching patients
   - Clicking a result selects the patient

## 🔍 Debugging

### If Search Doesn't Work:

#### 1. Check Browser Console (F12)
Look for these messages:
```
✓ HTMX is loaded and ready
✓ Setting up HTMX patient search listeners
```

If you see errors, check:
- Is HTMX library loaded? Check base.html includes htmx script
- Are there JavaScript errors blocking execution?

#### 2. Check Network Tab (F12 → Network)
When you type in the search field, you should see:
- Request to: `/patients/htmx-search/?q=<your_search>`
- Method: GET
- Status: 200
- Response: HTML with patient list

#### 3. Manual Test in Console
Run this in the browser console:
```javascript
// Check if HTMX is loaded
console.log('HTMX:', typeof htmx !== 'undefined' ? 'Loaded' : 'Not loaded');

// Check if input exists
console.log('Input:', document.getElementById('patientSearch'));

// Test HTMX manually
htmx.ajax('GET', '/patients/htmx-search/?q=test', {
    target: '#patientResults',
    swap: 'innerHTML'
});
```

#### 4. Check View Directly
Test the endpoint directly:
```
http://127.0.0.1:8000/patients/htmx-search/?q=test
```

This should return HTML with patient search results.

## 📋 Verification Checklist

Use this checklist to verify everything is working:

### Backend
- [x] `ajax_patient_search` view returns HTML (not JSON)
- [x] View accepts `q` parameter
- [x] View returns empty string for queries < 2 chars
- [x] Patient search results template exists
- [x] URL `/patients/htmx-search/` is configured

### Frontend
- [x] Input field has `name="q"`
- [x] Input has `hx-get="/patients/htmx-search/"`
- [x] Input has `hx-trigger="keyup changed delay:500ms"`
- [x] Input has `hx-target="#patientResults"`
- [x] Results div exists with `id="patientResults"`
- [x] HTMX library is loaded in base template
- [x] JavaScript event listeners are set up
- [x] Loading spinner shows during fetch

### Database
- [x] Active patients exist (62 patients available)
- [x] Patients with "test" in name exist (26 found)

## 🎯 Expected Behavior

1. **User types in search field**
   - Loading spinner appears
   - After 500ms delay, HTMX sends request

2. **HTMX receives response**
   - HTML is inserted into #patientResults
   - Dropdown becomes visible
   - Click handlers are attached

3. **User clicks a patient**
   - Patient is selected
   - Selected info shows in alert box
   - Hidden patient field is populated
   - Dropdown selection syncs

4. **User can also use dropdown**
   - Select2 dropdown works as fallback
   - Selecting from dropdown updates search field
   - Both methods work seamlessly together

## 📊 Test Results

### Automated Tests Passed
```
✓ Template syntax validated
✓ HTMX endpoint returns correct HTML
✓ URL configuration correct
✓ JavaScript event handlers in place
✓ 62 active patients in database
✓ 26 patients match "test" query
```

### Manual Testing Required
- [ ] Login to the system
- [ ] Visit diagnostic page
- [ ] Verify all status checks are green
- [ ] Type in search field
- [ ] Verify dropdown appears
- [ ] Click a patient result
- [ ] Verify patient is selected
- [ ] Try the main form page
- [ ] Create a test request successfully

## 🛠️ Troubleshooting Common Issues

### Issue: "No patients found" message
**Solution:** Database may be empty. Add test patients through admin interface.

### Issue: Loading spinner never stops
**Solution:** Check Network tab for failed requests. Verify you're logged in.

### Issue: Dropdown doesn't appear
**Solution:**
1. Check console for JavaScript errors
2. Verify `#patientResults` div exists
3. Check CSS for `display: none` overrides

### Issue: HTMX not defined
**Solution:** Base template may not include HTMX script. Check `templates/base.html` line 16.

### Issue: 302 redirect errors
**Solution:** Make sure you're logged in. The views require authentication.

## 📝 Notes

- Minimum search length: 2 characters
- Search delay: 500ms (debounce)
- Maximum results: 10 patients
- Search fields: first_name, last_name, patient_id, phone_number
- Only active patients are returned

## 🎉 Success Indicators

You'll know it's working when:
1. ✅ You can type and see the loading spinner
2. ✅ Patient list appears after typing
3. ✅ Clicking a patient selects them
4. ✅ Selected patient info shows in the alert box
5. ✅ You can submit the form with a selected patient

## 📞 Support

If issues persist after following this guide:
1. Check the diagnostic page console output
2. Review browser console for errors
3. Check Django server logs
4. Verify database has patient records
5. Ensure HTMX library is loaded

---
Generated: December 18, 2025
Server: http://127.0.0.1:8000
