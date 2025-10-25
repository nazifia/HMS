# Department Dashboard Deployment Checklist

## 📋 Pre-Deployment Tasks

### 1. Database Setup ✅

**Create Missing Departments in Django Admin:**

The following departments need to be created in the database:

- [ ] Dental Department
- [ ] Theatre Department  
- [ ] Ophthalmic Department
- [ ] ENT Department
- [ ] Oncology Department
- [ ] SCBU Department
- [ ] ANC Department
- [ ] Labor Department
- [ ] ICU Department
- [ ] Family Planning Department
- [ ] Gynae Emergency Department

**How to Create:**
1. Login to Django Admin: `/admin/`
2. Navigate to: `Accounts > Departments`
3. Click "Add Department"
4. Enter department name exactly as listed above
5. Save

**Note:** Laboratory and Radiology departments already exist.

---

### 2. User Assignment ✅

**Assign Users to Departments:**

For each department, ensure staff members are assigned:

1. Login to Django Admin
2. Navigate to: `Accounts > Custom User Profiles`
3. Edit each user profile
4. Select appropriate department from dropdown
5. Save

**Example Assignments:**
- Lab technicians → Laboratory Department
- Radiologists → Radiology Department
- Dentists → Dental Department
- Surgeons → Theatre Department
- Etc.

---

### 3. Code Verification ✅

**Run Verification Script:**

```bash
python verify_dashboards.py
```

**Expected Results:**
- ✅ URL Configuration: PASSED
- ✅ Template Existence: PASSED
- ✅ View Functions: PASSED
- ⚠️ Department Database: WARNINGS (until departments created)

---

### 4. System Checks ✅

**Run Django System Check:**

```bash
python manage.py check
```

**Expected Output:**
```
System check identified no issues (0 silenced).
```

**Check for Migrations:**

```bash
python manage.py makemigrations --dry-run
```

**Expected Output:**
```
No changes detected
```

---

## 🧪 Testing Phase

### 1. Local Testing

**Start Development Server:**

```bash
python manage.py runserver
```

**Test Each Dashboard:**

Use the `TESTING_CHECKLIST.md` for comprehensive testing.

**Quick Test URLs:**
- Laboratory: http://127.0.0.1:8000/laboratory/dashboard/
- Radiology: http://127.0.0.1:8000/radiology/
- Dental: http://127.0.0.1:8000/dental/dashboard/
- Theatre: http://127.0.0.1:8000/theatre/
- Ophthalmic: http://127.0.0.1:8000/ophthalmic/dashboard/
- ENT: http://127.0.0.1:8000/ent/dashboard/
- Oncology: http://127.0.0.1:8000/oncology/dashboard/
- SCBU: http://127.0.0.1:8000/scbu/dashboard/
- ANC: http://127.0.0.1:8000/anc/dashboard/
- Labor: http://127.0.0.1:8000/labor/dashboard/
- ICU: http://127.0.0.1:8000/icu/dashboard/
- Family Planning: http://127.0.0.1:8000/family-planning/dashboard/
- Gynae Emergency: http://127.0.0.1:8000/gynae-emergency/dashboard/

---

### 2. Access Control Testing

**Test with Different User Roles:**

- [ ] Test with superuser (should access all dashboards)
- [ ] Test with laboratory staff (should only access laboratory)
- [ ] Test with dental staff (should only access dental)
- [ ] Test with unassigned user (should get error message)
- [ ] Test with user from wrong department (should get access denied)

---

### 3. Referral Workflow Testing

**Create Test Referrals:**

- [ ] Create NHIA patient referral (requires authorization)
- [ ] Create non-NHIA patient referral (no authorization)
- [ ] Verify referrals appear on correct department dashboards
- [ ] Test authorization workflow
- [ ] Test accept/reject functionality
- [ ] Verify notifications are sent

---

### 4. Performance Testing

**Check Query Performance:**

- [ ] Enable Django Debug Toolbar
- [ ] Check number of database queries per dashboard
- [ ] Verify no N+1 query issues
- [ ] Test with large datasets (100+ records, 50+ referrals)
- [ ] Measure page load times

**Expected Performance:**
- Dashboard load time: < 2 seconds
- Database queries: < 20 per page
- No duplicate queries

---

### 5. Browser Compatibility Testing

**Test on Multiple Browsers:**

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)
- [ ] Safari (if available)

**Check:**
- [ ] Layout renders correctly
- [ ] Icons display properly
- [ ] Buttons work
- [ ] Navigation functions
- [ ] No console errors

---

### 6. Mobile Responsiveness Testing

**Test on Different Screen Sizes:**

- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

**Verify:**
- [ ] Statistics cards stack properly
- [ ] Tables are scrollable
- [ ] Buttons are accessible
- [ ] Navigation works
- [ ] No horizontal scrolling

---

## 🚀 Deployment Steps

### 1. Backup Current System

**Before Deployment:**

```bash
# Backup database
python manage.py dumpdata > backup_before_dashboard_deployment.json

# Backup static files
cp -r static static_backup

# Backup templates
cp -r templates templates_backup
```

---

### 2. Deploy to Staging

**Steps:**

1. [ ] Push code to staging branch
2. [ ] Deploy to staging server
3. [ ] Run migrations (if any)
4. [ ] Collect static files
5. [ ] Create departments in staging database
6. [ ] Assign test users to departments
7. [ ] Run verification script
8. [ ] Perform UAT (User Acceptance Testing)

**Commands:**

```bash
# On staging server
git pull origin staging
python manage.py migrate
python manage.py collectstatic --noinput
python verify_dashboards.py
```

---

### 3. User Acceptance Testing (UAT)

**Invite Department Staff to Test:**

- [ ] Laboratory staff test laboratory dashboard
- [ ] Radiology staff test radiology dashboard
- [ ] Dental staff test dental dashboard
- [ ] Theatre staff test theatre dashboard
- [ ] Other departments test their dashboards

**Gather Feedback:**
- [ ] Usability feedback
- [ ] Feature requests
- [ ] Bug reports
- [ ] Performance issues

---

### 4. Fix Issues

**Address Feedback:**

- [ ] Fix critical bugs
- [ ] Improve UI/UX based on feedback
- [ ] Optimize performance if needed
- [ ] Update documentation

---

### 5. Deploy to Production

**Final Deployment:**

1. [ ] Merge to main/production branch
2. [ ] Schedule deployment window
3. [ ] Notify users of deployment
4. [ ] Deploy to production server
5. [ ] Run migrations
6. [ ] Collect static files
7. [ ] Create departments in production database
8. [ ] Assign users to departments
9. [ ] Run verification script
10. [ ] Smoke test all dashboards

**Commands:**

```bash
# On production server
git pull origin main
python manage.py migrate
python manage.py collectstatic --noinput
python verify_dashboards.py
python manage.py check
```

---

## 📚 Post-Deployment Tasks

### 1. User Training

**Conduct Training Sessions:**

- [ ] Schedule training for each department
- [ ] Demonstrate dashboard features
- [ ] Explain referral workflow
- [ ] Show authorization process
- [ ] Answer questions

**Training Materials:**
- Use `QUICK_REFERENCE_GUIDE.md`
- Create video tutorials (optional)
- Provide hands-on practice

---

### 2. Documentation

**Update System Documentation:**

- [ ] Add dashboard URLs to user manual
- [ ] Document referral workflow
- [ ] Update admin guide with department setup
- [ ] Create troubleshooting guide

---

### 3. Monitoring

**Monitor System Performance:**

- [ ] Check error logs daily (first week)
- [ ] Monitor page load times
- [ ] Track user adoption
- [ ] Gather user feedback

**Metrics to Track:**
- Dashboard page views
- Referral acceptance rate
- Average response time
- Error rate

---

### 4. Support

**Provide User Support:**

- [ ] Set up support channel (email/phone/chat)
- [ ] Respond to user questions
- [ ] Document common issues
- [ ] Create FAQ based on questions

---

## ✅ Sign-Off

### Pre-Deployment Sign-Off

- [ ] All code reviewed and approved
- [ ] All tests passed
- [ ] Database setup complete
- [ ] User assignments complete
- [ ] Staging deployment successful
- [ ] UAT completed and approved

**Approved By:** ___________________  
**Date:** ___________________

---

### Production Deployment Sign-Off

- [ ] Production deployment successful
- [ ] All dashboards accessible
- [ ] No critical errors
- [ ] User training completed
- [ ] Documentation updated
- [ ] Monitoring in place

**Deployed By:** ___________________  
**Date:** ___________________  
**Status:** [ ] SUCCESS [ ] ROLLBACK REQUIRED

---

## 🔄 Rollback Plan

**If Issues Occur:**

1. **Immediate Actions:**
   ```bash
   # Restore from backup
   git checkout previous_stable_version
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

2. **Notify Users:**
   - Send notification about rollback
   - Explain issue and timeline for fix

3. **Fix and Redeploy:**
   - Fix issues in development
   - Test thoroughly
   - Redeploy when ready

---

## 📞 Emergency Contacts

**Technical Issues:**
- IT Support: ___________________
- Database Admin: ___________________
- System Admin: ___________________

**Business Issues:**
- Project Manager: ___________________
- Department Heads: ___________________

---

## 📊 Success Criteria

**Deployment is Successful When:**

- ✅ All 13 dashboards are accessible
- ✅ Access control works correctly
- ✅ Referral workflow functions properly
- ✅ No critical errors in logs
- ✅ Page load times < 2 seconds
- ✅ Users can perform daily tasks
- ✅ No data loss or corruption
- ✅ All existing features still work

---

**Last Updated:** 2025-10-24  
**Version:** 1.0  
**Status:** Ready for Deployment

