# Department Dashboard Quick Reference Guide

## 📋 Overview

This guide provides quick access to all department dashboards and their URLs for testing and daily use.

---

## 🔗 Dashboard URLs

### **All 13 Department Dashboards:**

| Department | URL | Access Required |
|------------|-----|-----------------|
| **Laboratory** | `/laboratory/dashboard/` | Laboratory staff |
| **Radiology** | `/radiology/` | Radiology staff |
| **Dental** | `/dental/dashboard/` | Dental staff |
| **Theatre** | `/theatre/` | Theatre staff |
| **Ophthalmic** | `/ophthalmic/dashboard/` | Ophthalmic staff |
| **ENT** | `/ent/dashboard/` | ENT staff |
| **Oncology** | `/oncology/dashboard/` | Oncology staff |
| **SCBU** | `/scbu/dashboard/` | SCBU staff |
| **ANC** | `/anc/dashboard/` | ANC staff |
| **Labor** | `/labor/dashboard/` | Labor staff |
| **ICU** | `/icu/dashboard/` | ICU staff |
| **Family Planning** | `/family_planning/dashboard/` | Family Planning staff |
| **Gynae Emergency** | `/gynae_emergency/dashboard/` | Gynae Emergency staff |

**Note:** Superusers can access all dashboards regardless of department assignment.

---

## 🎯 Dashboard Features

### **Every Dashboard Includes:**

#### 1. **Statistics Cards** 📊
- Total Records
- Records Today
- Records This Week
- Records This Month
- Pending Referrals
- Pending Authorizations

#### 2. **Pending Referrals Section** 🔄
- List of all pending referrals to the department
- Color-coded authorization status badges:
  - 🟢 **Green (Authorized)** - Ready to accept/reject
  - ⚪ **Gray (Not Required)** - Ready to accept/reject
  - 🟡 **Yellow (Pending)** - Waiting for authorization
  - 🔴 **Red (Required)** - Needs authorization
- Patient information (name, ID, age, gender)
- Referring doctor information
- Referral reason
- Quick action buttons (Accept/Reject for authorized referrals)

#### 3. **Quick Actions Panel** ⚡
- Create New Record
- View All Records
- View Referrals
- Authorization Dashboard (when applicable)

#### 4. **Recent Activity** 📋
- Table showing latest 10 records
- Patient details
- Assigned doctor
- Timestamp
- Quick view links

---

## 🔐 Access Control

### **How It Works:**

1. **Department Assignment Required**
   - Users must be assigned to a department in their profile
   - Access is restricted to assigned department only
   - Clear error messages for unauthorized access

2. **Superuser Access**
   - Superusers can access all department dashboards
   - No department assignment required for superusers

3. **Error Messages:**
   - "You must be logged in to access this page."
   - "You must be assigned to a department to access this page."
   - "Access denied. This page is for [Department] staff only."

---

## 🧭 Navigation

### **Main Sidebar:**

**Laboratory Section:**
```
Laboratory
├── Dashboard
├── Tests
└── Test Requests
```

**Medical Modules Section:**
```
Medical Modules
├── Department Dashboards
│   ├── Dental
│   ├── Ophthalmic
│   ├── ENT
│   ├── Oncology
│   ├── SCBU
│   ├── ANC
│   ├── Labor
│   ├── ICU
│   ├── Family Planning
│   └── Gynae Emergency
└── Record Lists
    ├── ENT Records
    ├── Ophthalmic Records
    ├── Oncology Records
    ├── SCBU Records
    ├── ANC Records
    ├── Labor Records
    ├── ICU Records
    ├── Family Planning Records
    ├── Gynae Emergency Records
    └── Dental Records
```

**Theatre Section:**
```
Theatre
├── Dashboard
├── Surgeries
├── Surgery Types
└── Equipment
```

**Radiology Section:**
```
Radiology (Dashboard)
```

---

## 🔄 Referral Workflow

### **Complete Workflow:**

1. **Doctor Creates Referral**
   - From consultation or department
   - Selects destination department
   - Provides referral reason

2. **Authorization Check (NHIA Patients Only)**
   - System checks if patient is NHIA
   - If yes, authorization required
   - Referral appears on NHIA desk dashboard

3. **NHIA Desk Authorizes (If Required)**
   - Reviews referral
   - Generates authorization code
   - Authorizes referral

4. **Referral Appears on Department Dashboard**
   - Shows in "Pending Referrals" section
   - Authorization status badge displayed
   - Patient and referring doctor info shown

5. **Department Staff Takes Action**
   - **If Authorized/Not Required:**
     - Can accept or reject immediately
   - **If Pending/Required Authorization:**
     - Cannot take action (blocked)
     - Must wait for authorization

6. **Accept or Reject**
   - **Accept:** Referral status → "accepted"
   - **Reject:** Provide reason, status → "cancelled"
   - Referring doctor receives notification

7. **Complete Service**
   - Department provides service
   - Updates referral status to "completed"

---

## 🎨 Authorization Status Badges

### **Badge Colors and Meanings:**

| Badge | Color | Meaning | Can Act? |
|-------|-------|---------|----------|
| **Authorized** | Green | NHIA authorized | ✅ Yes |
| **Not Required** | Gray | Non-NHIA patient | ✅ Yes |
| **Pending** | Yellow | Awaiting authorization | ❌ No |
| **Required** | Red | Needs authorization | ❌ No |

---

## 🛠️ Common Tasks

### **For Department Staff:**

#### **View Pending Referrals:**
1. Navigate to department dashboard
2. Scroll to "Pending Referrals" section
3. Review list of referrals

#### **Accept a Referral:**
1. Find referral with green or gray badge
2. Click "Accept" button
3. Confirm action
4. Referral status changes to "accepted"

#### **Reject a Referral:**
1. Find referral with green or gray badge
2. Click "Reject" button
3. Enter rejection reason
4. Confirm action
5. Referring doctor receives notification

#### **View Referral Details:**
1. Click on patient name or "View Details" link
2. See full referral information
3. View patient history
4. See authorization details (if applicable)

#### **Create New Record:**
1. Click "New [Department] Record" button
2. Fill in patient information
3. Complete examination/service details
4. Save record

---

## 📊 Statistics Explained

### **What Each Metric Means:**

- **Total Records:** All-time count of department records
- **Records Today:** Records created today
- **Records This Week:** Records created this week (Monday-Sunday)
- **Records This Month:** Records created this month
- **Pending Referrals:** Referrals awaiting acceptance
- **Pending Authorizations:** NHIA referrals awaiting authorization

---

## 🚨 Troubleshooting

### **Common Issues:**

#### **"Access Denied" Error**
- **Cause:** Not assigned to the department
- **Solution:** Contact admin to assign you to correct department

#### **"No Pending Referrals" Message**
- **Cause:** No referrals sent to your department
- **Solution:** Normal - wait for referrals from doctors

#### **Cannot Accept/Reject Referral**
- **Cause:** Referral requires NHIA authorization
- **Solution:** Wait for NHIA desk to authorize

#### **Dashboard Not Loading**
- **Cause:** Network issue or server error
- **Solution:** Refresh page, check internet connection

---

## 📱 Mobile Access

All dashboards are mobile-responsive:
- Statistics cards stack vertically
- Tables scroll horizontally
- Buttons remain accessible
- Navigation adapts to screen size

---

## 🔍 Quick Testing Checklist

### **Before Going Live:**

- [ ] Test each department dashboard with correct user role
- [ ] Verify access control blocks unauthorized users
- [ ] Test referral workflow end-to-end
- [ ] Verify authorization badges display correctly
- [ ] Test accept/reject functionality
- [ ] Check mobile responsiveness
- [ ] Verify all navigation links work
- [ ] Test with different patient types (NHIA/Non-NHIA)

---

## 📞 Support

### **For Technical Issues:**
- Contact IT Support
- Check system logs
- Review error messages

### **For Training:**
- Refer to `TESTING_CHECKLIST.md` for detailed testing
- Refer to `IMPLEMENTATION_COMPLETE.md` for technical details

---

## 🎓 Training Tips

### **For New Users:**

1. **Start with Dashboard Tour**
   - Show statistics cards
   - Explain each metric
   - Demonstrate navigation

2. **Practice Referral Workflow**
   - Create test referral
   - Show how it appears on dashboard
   - Practice accept/reject

3. **Explain Authorization**
   - Show badge colors
   - Explain when authorization needed
   - Demonstrate blocked actions

4. **Show Quick Actions**
   - Create new record
   - View all records
   - Access referrals

---

## 📈 Best Practices

### **Daily Workflow:**

1. **Morning:**
   - Check dashboard for pending referrals
   - Review statistics
   - Accept urgent referrals

2. **Throughout Day:**
   - Monitor new referrals
   - Process as they arrive
   - Update record statuses

3. **End of Day:**
   - Review completed referrals
   - Check for pending authorizations
   - Plan for next day

---

## 🔗 Related Documentation

- **`IMPLEMENTATION_COMPLETE.md`** - Full technical documentation
- **`TESTING_CHECKLIST.md`** - Comprehensive testing guide
- **Django Admin** - User and department management

---

## 📝 Notes

- All dashboards use the same standardized layout
- Consistent navigation across all departments
- Real-time statistics (no caching)
- Optimized database queries for performance
- Full audit trail for all actions

---

**Last Updated:** 2025-10-24  
**Version:** 1.0  
**Status:** Production Ready

