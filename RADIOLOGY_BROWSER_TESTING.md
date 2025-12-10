# Radiology Dashboard - Browser Testing Guide

## Pre-Testing Setup

### 1. Ensure Development Server is Running
```bash
python manage.py runserver
```

### 2. Create Test Data (if needed)
```bash
python manage.py shell
```

```python
from patients.models import Patient
from radiology.models import RadiologyCategory, RadiologyTest, RadiologyOrder
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Get or create a test patient
patient, created = Patient.objects.get_or_create(
    patient_number='TEST001',
    defaults={
        'first_name': 'Test',
        'last_name': 'Patient',
        'date_of_birth': '1990-01-01',
        'gender': 'M'
    }
)

# Get or create test category
category, created = RadiologyCategory.objects.get_or_create(
    name='X-Ray',
    defaults={'description': 'X-Ray imaging tests'}
)

# Get or create test
test, created = RadiologyTest.objects.get_or_create(
    name='Chest X-Ray',
    category=category,
    defaults={
        'price': 5000.00,
        'duration_minutes': 30,
        'is_active': True
    }
)

# Get admin or create test user
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

# Create today's order
order_today = RadiologyOrder.objects.create(
    patient=patient,
    test=test,
    referring_doctor=user,
    order_date=timezone.now(),
    status='pending',
    priority='normal'
)

# Create past order
from datetime import timedelta
order_past = RadiologyOrder.objects.create(
    patient=patient,
    test=test,
    referring_doctor=user,
    order_date=timezone.now() - timedelta(days=2),
    status='completed',
    priority='normal'
)

print(f"Created today's order: {order_today.id}")
print(f"Created past order: {order_past.id}")
```

---

## Test Scenarios

### Test 1: New Radiology Order Button (CRITICAL FIX)

**URL**: http://127.0.0.1:8000/radiology/

#### Test 1a: With Existing Patients
**Steps**:
1. Navigate to radiology dashboard
2. Locate "New Radiology Order" button in top-right
3. Click the button

**Expected Result**:
- ✅ Button should work and redirect to order form
- ✅ URL should be `/radiology/order/` (not `/radiology/order/<patient_id>/`)
- ✅ Should show order form with patient selection dropdown

**FAIL If**:
- ❌ Button links to `#` (hash/dead link)
- ❌ 404 error
- ❌ Button doesn't work

---

#### Test 1b: Without Any Patients
**Steps**:
1. Delete all radiology orders (via admin or shell)
2. Navigate to radiology dashboard
3. Click "New Radiology Order" button

**Expected Result**:
- ✅ Button should still work
- ✅ Should redirect to order form
- ✅ No JavaScript errors

**FAIL If**:
- ❌ Button links to `#`
- ❌ Console error about missing patient
- ❌ Button doesn't work

---

### Test 2: Today Badge Display (CRITICAL FIX)

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Create a radiology order with today's date (see setup above)
2. Navigate to radiology dashboard
3. Scroll to "Recent Radiology Orders" table
4. Find today's order

**Expected Result**:
- ✅ Row with today's order should have light blue background (`table-info` class)
- ✅ Order date cell should show blue "Today" badge
- ✅ Past orders should NOT have "Today" badge
- ✅ Past orders should NOT have blue background

**FAIL If**:
- ❌ "Today" badge appears on past orders
- ❌ "Today" badge missing from today's orders
- ❌ Blue background missing from today's orders

---

### Test 3: Status Filter Functionality

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Navigate to radiology dashboard
2. Click the three-dot menu icon (⋮) in "Recent Radiology Orders" card header
3. Select "Pending" from dropdown
4. Note URL changes to `?status=pending`
5. Verify only pending orders are shown

**Expected Result**:
- ✅ Only pending orders displayed
- ✅ Table updates correctly
- ✅ Filter indicator visible

**FAIL If**:
- ❌ All orders still shown
- ❌ Wrong orders filtered
- ❌ JavaScript errors

---

### Test 4: Patient Filter Functionality

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Navigate to radiology dashboard
2. Note a patient ID from the orders table (e.g., "1" or "TEST001")
3. Enter patient ID in "Filter by Patient ID" search box
4. Click "Filter" button

**Expected Result**:
- ✅ Only orders for that patient are shown
- ✅ URL updates with `?patient_id=<id>`
- ✅ Search box retains entered value

**FAIL If**:
- ❌ All orders still shown
- ❌ No filtering occurs
- ❌ Search box clears

---

### Test 5: Combined Filters (UX FIX)

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Navigate to radiology dashboard
2. Apply status filter: Click dropdown → Select "Pending"
3. Note URL is `?status=pending`
4. Now use patient filter: Enter patient ID → Click "Filter"

**Expected Result**:
- ✅ Both filters should be active
- ✅ URL should be `?status=pending&patient_id=<id>`
- ✅ Only pending orders for that patient shown
- ✅ Status filter NOT lost when applying patient filter

**FAIL If**:
- ❌ Status filter cleared when patient filter applied
- ❌ URL only has `?patient_id=<id>` (missing status)
- ❌ Shows all statuses instead of just pending

**BEFORE FIX**: Status filter would be lost
**AFTER FIX**: Both filters work together

---

### Test 6: Placeholder Buttons (UX FIX)

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Navigate to radiology dashboard
2. Locate "Enhanced Radiology Features" card
3. Examine the three buttons:
   - "Search Results"
   - "Report Templates"
   - "Quality Metrics"

**Expected Result**:
- ✅ "Search Results" button is blue/info colored and clickable
- ✅ "Report Templates" button is gray and disabled with "(Coming Soon)"
- ✅ "Quality Metrics" button is gray and disabled with "(Coming Soon)"
- ✅ Disabled buttons don't respond to clicks
- ✅ Cursor changes to "not-allowed" on disabled buttons

**FAIL If**:
- ❌ Placeholder buttons are clickable
- ❌ Placeholder buttons link to `#`
- ❌ No "Coming Soon" indicator
- ❌ Buttons appear fully functional

**BEFORE FIX**: Buttons looked functional but linked to `#`
**AFTER FIX**: Buttons clearly marked as coming soon

---

### Test 7: Statistics Cards

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Navigate to radiology dashboard
2. View the 4 statistics cards at the top:
   - Today's Orders
   - Urgent Orders
   - Avg Reporting Time
   - Pending Orders

**Expected Result**:
- ✅ All cards display numeric values (0 or actual counts)
- ✅ No template errors or {{ variable }} showing
- ✅ Cards are responsive on mobile

**FAIL If**:
- ❌ Raw template tags visible
- ❌ JavaScript errors
- ❌ Missing data

---

### Test 8: Patient Results Links

**URL**: http://127.0.0.1:8000/radiology/

**Steps**:
1. Navigate to radiology dashboard
2. Locate "Recent Patients with Radiology Orders" section
3. Find a patient row
4. Click "Results" button

**Expected Result**:
- ✅ Redirects to patient's radiology results page
- ✅ Shows all results for that patient
- ✅ Back navigation works

**FAIL If**:
- ❌ 404 error
- ❌ Wrong patient's results
- ❌ Empty results when orders exist

---

### Test 9: Responsive Design

**Steps**:
1. Open radiology dashboard
2. Resize browser window to mobile size (< 768px)
3. Check layout

**Expected Result**:
- ✅ Statistics cards stack vertically
- ✅ Table is horizontally scrollable
- ✅ Filters remain usable
- ✅ Sidebar collapses to hamburger menu

**FAIL If**:
- ❌ Layout breaks
- ❌ Horizontal scrolling on entire page
- ❌ Text overlaps

---

### Test 10: JavaScript Console Check

**Steps**:
1. Open radiology dashboard
2. Open browser DevTools (F12)
3. Go to Console tab
4. Refresh page

**Expected Result**:
- ✅ No red errors
- ✅ jQuery loaded
- ✅ DataTables initialized (if enabled)
- ✅ No 404s for missing resources

**FAIL If**:
- ❌ jQuery not defined error
- ❌ DataTables not defined error
- ❌ Template syntax errors
- ❌ Missing CSS/JS files

---

## Performance Testing

### Test 11: Large Dataset Performance

**Steps**:
1. Create 100+ radiology orders via shell
2. Navigate to dashboard
3. Apply filters

**Expected Result**:
- ✅ Page loads in < 3 seconds
- ✅ Filtering works efficiently
- ✅ No browser lag

**Verify**:
- Template-level filtering removed (our fix)
- Database-level filtering used in view

---

## Cross-Browser Testing

Test in:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari (if available)

Common issues to watch:
- Date formatting
- CSS compatibility
- JavaScript errors

---

## Sign-Off Checklist

After completing all tests above:

- [ ] All critical fixes verified
- [ ] No JavaScript console errors
- [ ] All filters work correctly
- [ ] Responsive design works
- [ ] No template rendering errors
- [ ] Performance is acceptable
- [ ] Documentation is complete

---

## Issue Reporting

If you find any issues during testing, report with:

1. **Test Number**: e.g., "Test 5: Combined Filters"
2. **Expected**: What should happen
3. **Actual**: What actually happened
4. **Browser**: Chrome 120, Firefox 121, etc.
5. **Screenshot**: If applicable
6. **Console Errors**: Any JavaScript errors

Example:
```
Test 5 FAILED
Expected: Status filter preserved when applying patient filter
Actual: Status filter was cleared
Browser: Chrome 120
URL: ?patient_id=1 (missing status parameter)
```

---

## Rollback Instructions

If critical issues are found and rollback is needed:

```bash
git checkout HEAD -- templates/radiology/index.html
git status
python manage.py runserver
```

Then report issues for fixing.

---

## Next Steps After Testing

Once all tests pass:
1. Commit changes with detailed message
2. Create pull request (if using feature branches)
3. Deploy to staging environment
4. Final UAT (User Acceptance Testing)
5. Deploy to production

---

**Testing Date**: _________________
**Tested By**: _________________
**Test Result**: PASS / FAIL
**Notes**: _________________
