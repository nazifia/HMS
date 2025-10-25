# Department Dashboard Testing Checklist

## 🧪 Testing Instructions

This checklist will help you verify that all department dashboards are working correctly.

---

## Pre-Testing Setup

### 1. Create Test Users for Each Department

You'll need to create users assigned to different departments to test access control:

```sql
-- Example: Create a test user for Laboratory department
-- Do this through Django admin or create users manually
```

**Required Test Users:**
- Laboratory staff user
- Radiology staff user  
- Dental staff user
- Theatre staff user
- Ophthalmic staff user
- ENT staff user
- Oncology staff user
- SCBU staff user
- ANC staff user
- Labor staff user
- ICU staff user
- Family Planning staff user
- Gynae Emergency staff user
- Superuser (for testing unrestricted access)

### 2. Create Test Referrals

Create at least 2-3 referrals for each department with different authorization statuses:
- ✅ Authorized referral
- ⚪ Not required referral
- 🟡 Pending authorization referral
- 🔴 Required authorization referral

---

## Testing Checklist

### For Each Department Dashboard:

#### 1. Laboratory Dashboard (`/laboratory/dashboard/`)

**Access Control:**
- [ ] Laboratory staff can access the dashboard
- [ ] Non-laboratory staff get "Access denied" error
- [ ] Superuser can access the dashboard
- [ ] Unauthenticated users are redirected to login

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] Statistics cards show correct counts:
  - [ ] Total records
  - [ ] Records today
  - [ ] Records this week
  - [ ] Records this month
  - [ ] Pending referrals count
  - [ ] Pending authorizations count
- [ ] Laboratory-specific metrics display (pending tests, in progress, completed today, urgent tests)
- [ ] Pending referrals section displays correctly
- [ ] Authorization status badges are color-coded correctly
- [ ] Recent records table shows latest 10 records
- [ ] Quick Actions panel has all links

**Functionality:**
- [ ] "New Test Request" button works
- [ ] "View All Records" link works
- [ ] "View Referrals" link works
- [ ] "Authorization Dashboard" link appears when needed
- [ ] Referral detail links work
- [ ] Accept/Reject buttons appear for authorized referrals only

**Navigation:**
- [ ] Sidebar "Laboratory" section has dashboard link
- [ ] Dashboard link is highlighted when active
- [ ] All navigation links work correctly

---

#### 2. Radiology Dashboard (`/radiology/`)

**Access Control:**
- [ ] Radiology staff can access the dashboard
- [ ] Non-radiology staff cannot access (if access control added)
- [ ] Superuser can access the dashboard

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] Statistics cards display correctly
- [ ] Pending referrals section appears
- [ ] Authorization status badges work
- [ ] Recent imaging orders display

**Functionality:**
- [ ] All quick action links work
- [ ] Referral integration works correctly

---

#### 3. Dental Dashboard (`/dental/dashboard/`)

**Access Control:**
- [ ] Dental staff can access the dashboard
- [ ] Non-dental staff get "Access denied" error
- [ ] Superuser can access the dashboard

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All statistics cards display correctly
- [ ] Pending referrals section works
- [ ] Recent dental records display

**Functionality:**
- [ ] "New Dental Record" button works
- [ ] All navigation links work
- [ ] Dental sidebar has dashboard link

---

#### 4. Theatre Dashboard (`/theatre/`)

**Access Control:**
- [ ] Theatre staff can access
- [ ] Access control works correctly

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] Surgery statistics display
- [ ] Theatre availability shows
- [ ] Equipment statistics display
- [ ] **NEW:** Pending referrals section appears
- [ ] **NEW:** Authorization status badges work

**Functionality:**
- [ ] All existing theatre features still work
- [ ] Referral integration doesn't break existing functionality

---

#### 5. Ophthalmic Dashboard (`/ophthalmic/dashboard/`)

**Access Control:**
- [ ] Ophthalmic staff can access
- [ ] Non-ophthalmic staff get error
- [ ] Superuser can access

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] Statistics cards display
- [ ] Pending referrals section works
- [ ] Recent records display

**Functionality:**
- [ ] All links work correctly
- [ ] Accept/Reject functionality accessible

---

#### 6. ENT Dashboard (`/ent/dashboard/`)

**Access Control:**
- [ ] ENT staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 7. Oncology Dashboard (`/oncology/dashboard/`)

**Access Control:**
- [ ] Oncology staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 8. SCBU Dashboard (`/scbu/dashboard/`)

**Access Control:**
- [ ] SCBU staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 9. ANC Dashboard (`/anc/dashboard/`)

**Access Control:**
- [ ] ANC staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 10. Labor Dashboard (`/labor/dashboard/`)

**Access Control:**
- [ ] Labor staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 11. ICU Dashboard (`/icu/dashboard/`)

**Access Control:**
- [ ] ICU staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 12. Family Planning Dashboard (`/family_planning/dashboard/`)

**Access Control:**
- [ ] Family Planning staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

#### 13. Gynae Emergency Dashboard (`/gynae_emergency/dashboard/`)

**Access Control:**
- [ ] Gynae Emergency staff can access
- [ ] Access control enforced

**Dashboard Display:**
- [ ] Page loads without errors
- [ ] All sections display correctly

**Functionality:**
- [ ] All features work

---

## Cross-Department Testing

### Referral Workflow Testing

**Scenario 1: NHIA Patient Referral (Requires Authorization)**

1. [ ] Doctor refers NHIA patient to Laboratory
2. [ ] Referral appears on Laboratory dashboard with "Required" badge (red)
3. [ ] Laboratory staff cannot accept/reject (blocked)
4. [ ] NHIA desk authorizes the referral
5. [ ] Referral badge changes to "Authorized" (green)
6. [ ] Laboratory staff can now accept/reject
7. [ ] Laboratory staff accepts referral
8. [ ] Referring doctor receives notification
9. [ ] Referral disappears from pending list

**Scenario 2: Non-NHIA Patient Referral (No Authorization Required)**

1. [ ] Doctor refers non-NHIA patient to Dental
2. [ ] Referral appears on Dental dashboard with "Not Required" badge (gray)
3. [ ] Dental staff can immediately accept/reject
4. [ ] Dental staff rejects with reason
5. [ ] Referring doctor receives rejection notification
6. [ ] Referral status changes to "cancelled"

**Scenario 3: Cross-Department Referral Chain**

1. [ ] Patient referred from Consultation to Radiology
2. [ ] Radiology dashboard shows referral
3. [ ] Radiology accepts and completes imaging
4. [ ] Radiology refers to Oncology
5. [ ] Oncology dashboard shows referral
6. [ ] Full referral chain is tracked

---

## Navigation Testing

### Main Sidebar

- [ ] "Laboratory" section has dashboard link
- [ ] "Medical Modules" section has all department dashboard links
- [ ] All dashboard links work correctly
- [ ] Active dashboard is highlighted
- [ ] Icons display correctly for each department

### Department-Specific Sidebars

- [ ] Dental sidebar has dashboard link
- [ ] Dashboard link is first in the list
- [ ] Active state works correctly

---

## Mobile Responsiveness Testing

Test on different screen sizes:

- [ ] Desktop (1920x1080)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

**Check:**
- [ ] Statistics cards stack properly
- [ ] Tables are responsive
- [ ] Navigation works on mobile
- [ ] Buttons are accessible
- [ ] No horizontal scrolling

---

## Performance Testing

- [ ] Dashboard loads in < 2 seconds
- [ ] No N+1 query issues (check Django Debug Toolbar)
- [ ] Referral queries are optimized with select_related/prefetch_related
- [ ] Statistics calculations are efficient

---

## Error Handling Testing

**Test Error Scenarios:**

- [ ] User not assigned to any department
  - Expected: Error message + redirect to main dashboard
- [ ] User assigned to wrong department
  - Expected: "Access denied" message
- [ ] No referrals exist
  - Expected: "No pending referrals" message displays
- [ ] No recent records exist
  - Expected: "No recent records" message displays
- [ ] Invalid department name in decorator
  - Expected: Proper error handling

---

## Regression Testing

**Verify No Breaking Changes:**

- [ ] Existing record creation still works
- [ ] Existing record listing still works
- [ ] Existing record detail views still work
- [ ] Existing record editing still works
- [ ] Existing record deletion still works
- [ ] Pharmacy integration still works
- [ ] Billing integration still works
- [ ] Patient search still works
- [ ] Doctor assignment still works

---

## Browser Compatibility Testing

Test on:

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)
- [ ] Safari (if available)

---

## Final Verification

- [ ] All 13 department dashboards are accessible
- [ ] All dashboards display correct data
- [ ] All navigation links work
- [ ] Access control is enforced
- [ ] Referral integration works
- [ ] Authorization workflow works
- [ ] No console errors
- [ ] No Python errors
- [ ] No database errors
- [ ] System check passes: `python manage.py check`

---

## Sign-Off

**Tested By:** ___________________  
**Date:** ___________________  
**Status:** [ ] PASS [ ] FAIL  
**Notes:**

---

## Quick Test Commands

```bash
# Run system check
python manage.py check

# Run tests (if you have automated tests)
python manage.py test

# Check for migrations
python manage.py makemigrations --dry-run

# Start development server
python manage.py runserver
```

---

## Known Issues / Notes

(Document any issues found during testing here)

---

## Next Steps After Testing

1. Fix any issues found
2. Deploy to staging environment
3. Conduct user acceptance testing (UAT)
4. Train department staff on new dashboards
5. Deploy to production
6. Monitor for issues
7. Gather user feedback
8. Plan enhancements based on feedback

