# Dashboard Template Fixes Needed

## Issues Found During Playwright Testing

### Date: 2025-10-25

---

## 🚨 **CRITICAL ISSUE: Dashboard URLs Not Being Registered**

**Affected Departments:** Dental, Laboratory, and likely ALL 13 departments
**Severity:** CRITICAL - Dashboard URLs are completely inaccessible

### **Problem Description:**

When navigating to `/dental/dashboard/` or `/laboratory/dashboard/`, Django returns a 404 error. The 404 debug page shows that Django is loading the URL patterns from these apps, BUT the `dashboard/` pattern is being SKIPPED.

**Evidence:**
- `dental/urls.py` line 8 defines: `path('dashboard/', views.dental_dashboard, name='dashboard')`
- `laboratory/urls.py` line 9 defines: `path('dashboard/', views.laboratory_dashboard, name='dashboard')`
- Both functions exist and are importable (verified with Python shell)
- But Django's URL resolver does NOT include these patterns in the loaded URL list

**Django's Loaded URL Patterns (from 404 page):**

**Dental URLs:**
- ❌ `dental/dashboard/` - **MISSING!**
- ✅ `dental/` [name='dental_records'] - Line 11 in urls.py
- ✅ `dental/create/` [name='create_dental_record'] - Line 12 in urls.py
- ✅ All other dental URLs are loaded correctly

**Laboratory URLs:**
- ❌ `laboratory/dashboard/` - **MISSING!**
- ✅ `laboratory/tests/` [name='tests'] - Line 12 in urls.py
- ✅ `laboratory/tests/add/` [name='add_test'] - Line 13 in urls.py
- ✅ All other laboratory URLs are loaded correctly

**Pattern:** The FIRST URL pattern (dashboard) in both apps is being skipped, but all subsequent patterns are loaded.

---

## 1. **Radiology Dashboard - Chart Data Not Rendering**

**Issue:** JavaScript error "Unexpected token ','" in Chart.js initialization
**Root Cause:** The `daily_trend`, `status_distribution`, and `modality` data are not being passed to the template correctly
**Location:** `templates/radiology/index.html` and `radiology/views.py`

**Problem Details:**
- The RadiologyOrder model uses `order_date` field instead of `created_at`
- The `build_enhanced_dashboard_context()` function defaults to using `created_at` field
- This causes the query to fail and return empty data
- Empty data results in JavaScript like `labels: ,` which causes syntax errors

**Fix Applied:**
- Modified `radiology/views.py` to manually call chart data functions with correct date field
- Changed from using `build_enhanced_dashboard_context()` to `build_department_dashboard_context()`
- Added manual calls to:
  - `get_daily_trend_data(RadiologyOrder, days=7, date_field='order_date')`
  - `get_status_distribution(RadiologyOrder, status_field='status')`
  - `calculate_completion_rate(RadiologyOrder, status_field='status', completed_status='completed')`
  - `get_urgent_items(RadiologyOrder, priority_field='priority')`
  - `get_active_staff(user_department)`

**Status:** ✅ Fixed in code, needs server restart to test

---

## 2. **Laboratory Dashboard - URL Not Found (404)**

**Issue:** `/laboratory/dashboard/` returns 404 error
**Root Cause:** URL pattern exists in `laboratory/urls.py` line 9 but is being SKIPPED by Django's URL loader
**Location:** `laboratory/urls.py` line 9, `hms/urls.py` line 38

**Problem Details:**
- The URL pattern `path('dashboard/', views.laboratory_dashboard, name='dashboard')` is defined at line 9
- The `laboratory_dashboard` function exists in `laboratory/views.py` and is importable
- But the URL is not accessible - returns 404
- Django's URL resolver shows laboratory URLs starting from line 12 (tests/), skipping line 9 (dashboard/)

**Status:** ⚠️ CRITICAL - Needs immediate investigation

---

## 3. **Dental Dashboard - URL Not Found (404)**

**Issue:** `/dental/dashboard/` returns 404 error
**Root Cause:** URL pattern exists in `dental/urls.py` line 8 but is being SKIPPED by Django's URL loader
**Location:** `dental/urls.py` line 8, `hms/urls.py` line 50

**Problem Details:**
- The URL pattern `path('dashboard/', views.dental_dashboard, name='dashboard')` is defined at line 8
- The `dental_dashboard` function exists in `dental/views.py` and is importable
- But the URL is not accessible - returns 404
- Django's URL resolver shows dental URLs starting from line 11 (empty path), skipping line 8 (dashboard/)

**Status:** ⚠️ CRITICAL - Needs immediate investigation

---

## 3. **Similar Issues Expected in Other Departments**

Based on the radiology issue, the following departments likely have the same problem with date fields:

### Departments Using Non-Standard Date Fields:

1. **Laboratory** - Uses `created_at` (should work) ✅
2. **Radiology** - Uses `order_date` (fixed) ✅
3. **Dental** - Need to check model
4. **Theatre** - Uses `scheduled_date` for surgeries ⚠️
5. **ICU** - Need to check model
6. **ANC** - Need to check model
7. **Labor** - Need to check model
8. **SCBU** - Need to check model
9. **Ophthalmic** - Need to check model
10. **ENT** - Need to check model
11. **Oncology** - Need to check model
12. **Family Planning** - Need to check model
13. **Gynae Emergency** - Need to check model

**Action Required:**
- Check each department's model to identify the date field used
- Update each view to pass the correct `date_field` parameter to `get_daily_trend_data()`
- Or update models to include a `created_at` field if missing

---

## 4. **Chart.js Integration Issues**

**Common Pattern Found:**
When chart data is empty or undefined, the template renders:
```javascript
labels: ,
data: ,
```

This causes JavaScript syntax errors.

**Solution:**
Ensure all chart data variables have default values in the view:
```python
context.update({
    'daily_trend': get_daily_trend_data(...) or {'labels': '[]', 'data': '[]'},
    'status_distribution': get_status_distribution(...) or {'labels': '[]', 'data': '[]', 'colors': '[]'},
})
```

---

## 5. **Testing Checklist**

### For Each Department Dashboard:

- [ ] **Laboratory** (`/laboratory/dashboard/`)
  - [ ] Fix 404 error
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Radiology** (`/radiology/`)
  - [x] Fix date field issue
  - [ ] Verify charts render after restart
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Dental** (`/dental/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Theatre** (`/theatre/dashboard/`)
  - [ ] Check date field (likely `scheduled_date`)
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **ICU** (`/icu/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **ANC** (`/anc/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Labor** (`/labor/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **SCBU** (`/scbu/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Ophthalmic** (`/ophthalmic/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **ENT** (`/ent/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Oncology** (`/oncology/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Family Planning** (`/family-planning/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

- [ ] **Gynae Emergency** (`/gynae-emergency/dashboard/`)
  - [ ] Check date field
  - [ ] Verify charts render
  - [ ] Check console for JavaScript errors
  - [ ] Take screenshot

---

## 6. **Next Steps**

1. ✅ Fix radiology date field issue (DONE)
2. ⏳ Investigate laboratory 404 error (IN PROGRESS)
3. ⏳ Check all department models for date fields
4. ⏳ Update all views with correct date fields
5. ⏳ Test all 13 dashboards with Playwright
6. ⏳ Take screenshots of working dashboards
7. ⏳ Document any additional issues found
8. ⏳ Create final testing report

---

## 7. **Files Modified**

- ✅ `radiology/views.py` - Fixed date field issue

---

## 8. **Files Needing Modification**

- ⏳ Other department views (pending investigation)
- ⏳ Possibly `core/department_dashboard_utils.py` to handle missing date fields gracefully

---

**Last Updated:** 2025-10-25  
**Status:** In Progress - 1 of 13 dashboards tested, 1 issue found and fixed

