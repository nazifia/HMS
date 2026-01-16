# Complete Pharmacist-Dispensary Assignment UI System

This document covers the complete user interface for managing pharmacist-dispensary assignments in the HMS Pharmacy module.

## Quick Start

### Run Demo Setup
```bash
python assignment_ui_demo.py
```

### Access UI
```bash
# Start server
python manage.py runserver

# Navigate to
http://localhost:8000/pharmacy/assignments/
```

## Interface Overview

The system provides two main UI surfaces:

### 1. Assignment Management Interface
**URL**: `/pharmacy/assignments/`

#### Features
- **Add New Assignment Form** (Left Column)
  - Select pharmacist from dropdown
  - Select dispensary from dropdown
  - Set start date (defaults to today)
  - Add notes (optional)
  - Toggle active status

- **Current Assignments Table** (Right Column)
  - Filter by status (Active/All)
  - Shows pharmacist name and contact
  - Dispensary location
  - Start/End dates
  - Status badges (Active/Inactive)
  - Action buttons (Edit, End, Delete)

- **Quick Statistics Cards**
  - Total pharmacists assigned
  - Active assignments
  - Dispensaries with pharmacists

#### Action Buttons

| Button | Icon | Purpose | Result |
|--------|------|---------|--------|
| **Edit** | ✎ | Edit Assignment | Opens edit form with current data |
| **End** | 🚫 | End Assignment | Sets end_date=today, marks as inactive |
| **Delete** | 🗑️ | Permanently Remove | Deletes assignment from database |

### 2. Assignment Reports & Analytics
**URL**: `/pharmacy/assignments/reports/`

#### Dashboard Views

**A. Distribution by Dispensary**
- Table showing assignment counts per dispensary
- Active vs Total counts
- Utilization percentage

**B. Top Pharmacists**
- Pharmacists with highest assignment counts
- Assignment history summary
- Current status indicator

**C. Recent Activity (Last 30 Days)**
- New assignments created
- Assignments that ended
- Activity timeline

**D. Key Metrics**
- Total assignments
- Active assignments
- Expired recently
- Utilization rate

## User Roles & Access

### Superusers / Admins
- **Full Access**: Can view, create, edit, end, delete any assignment
- **Navigation**: Access via sidebar → Dispensaries → Pharmacist Assignments
- **Permission**: Automatically have full access

### Pharmacists with Assignment
- **Limited Access**: Can view but not manage assignments
- **Data Access**: Only see data for assigned dispensary
- **Session**: Auto-selects dispensary on login
- **Change**: Can change dispensary via Select page

### Pharmacists without assigned dispensary
- **Prompt Required**: Must select dispensary before accessing pharmacy features
- **UI Flow**: Redirected to `/pharmacy/select-dispensary/`

## Complete UI Flow Examples

### Example 1: Admin Creates New Assignment
1. Login as admin user
2. Navigate to: **Sidebar → Dispensaries → Pharmacist Assignments**
3. In "Add New Assignment" form:
   - Select **Pharmacist:** Jane Smith (pharma_jane)
   - Select **Dispensary:** Main Pharmacy
   - **Start Date:** 2025-01-16 (auto-filled)
   - **Notes:** "Afternoon shift coverage"
   - Check **"Assignment is active"**
4. Click **"Create Assignment"**
5. Success message appears
6. New assignment appears in table with Active badge

### Example 2: End an Assignment
1. Find active assignment in the table
2. Click **🚫 End** button
3. System confirms: "Assignment ended: Jane Smith no longer assigned to Main Pharmacy"
4. Assignment moves to inactive (still visible in list)
5. Status changes from Active → Inactive
6. End date is set to today

### Example 3: View Assignment Reports
1. Navigate to: **Sidebar → Dispensaries → Assignment Reports**
2. View Distribution Table:
   - See which dispensary has most assignments
   - Check utilization percentages
3. View Top Pharmacists:
   - See who has been assigned most frequently
4. Check Recent Activity:
   - See what changed in last 30 days
5. Review Key Metrics:
   - Total: 3 assignments
   - Active: 2 assignments
   - Utilization: 66.7%

### Example 4: Pharmacist Adding Dispensary Selection
1. Login as pharmacist without assignment:
   ```
   Username: pharma_jane
   Password: pharma123
   ```
2. System prompts: "Select Your Pharmacy Dispensary"
3. Select **Main Pharmacy** (or any available)
4. Click **"Set Dispensary"**
5. Redirected to pharmacy dashboard
6. Top bar now shows: "Main Pharmacy 🔄"

## Editing Existing Assignments

### Access Edit Form
1. Go to assignment management page
2. Click **Edit** (pencil icon) next to any assignment
3. Form loads with current data

### Editable Fields
- **Start Date**: When assignment began
- **End Date**: When assignment should end (leave empty for ongoing)
- **Notes**: Update assignment description
- **Is Active**: Toggle active/inactive status

### Validation Rules
- End date must be equal or after start date
- Start date cannot be in the future
- End date can be cleared for ongoing assignments

## Website Navigation Structure

### Sidebar Hierarchy
```
Pharmacy (click to expand)
├── Prescriptions
├── Dispensed Items Tracker
├── Prescription Carts
├── Enhanced Transfers
├── Inventory
├── Stock Alerts
├── All Medical Packs
├── Create New Pack
├── Pack Orders
├── Order Medical Pack
├── Inter-Dispensary Transfers
├── Create Transfer
├── Transfer Statistics
├── Procurement Dashboard
├── Purchase Management
├── Bulk Store
├── Select Dispatch              ← For Pharmacists
├── Expiring Medications
├── Low Stock Report
├── Manage Dispensaries
├── Pharmacist Assignments       ← New UI! Click here
└── Assignment Reports           ← New UI! Click here
```

### Welcome/Notification System
**Top Bar Display**
```
[Current Dispensary: Main Pharmacy] 🔄 (for pharmacists)
```

Changes to:
```
[No Dispensary Selected] 🔄 (if no selection)
```

### Manual Navigation Options
1. **Direct URL**: `http://localhost:8000/pharmacy/assignments/`
2. **Sidebar**: Pharmacist Assignments
3. **Reports Link**: Assignment Reports

## Function Details

### Add New Assignment Form

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Pharmacist | Dropdown | Yes | Must have pharmacist role |
| Dispensary | Dropdown | Yes | Only active dispensaries shown |
| Start Date | Date | Yes | Defaults to today |
| Notes | Text | No | Can be empty |
| Active | Checkbox | No | Default checked |

### Reaction Messages
- **Success**: "Successfully assigned [Name] to [Dispensary]"
- **Error**: "Please fill in all required fields"
- **Warning**: "[Name] already has active assignment to [Dispensary]"

### Data Captured
Each assignment stores:
- `pharmacist`: CustomUser reference
- `dispensary`: Dispensary reference
- `start_date`: Date
- `end_date`: Date (optional)
- `is_active`: Boolean
- `notes`: Text
- Timestamps (created, updated)

## Permission Assignment

### Via Django Admin
```
1. Login → Go to /admin/auth/user/
2. Click your admin user
3. Scroll to "User permissions"
4. Find "pharmacy | pharmacist dispensary assignment" → "manage_pharmacists"
5. Add to selected permissions
6. Save
```

### Via User Management UI
```
1. Login
2. Go to /accounts/superuser/user-permissions/
3. Find user by username
4. Add "pharmacy.manage_pharmacists" to permissions
5. Save changes
```

## Testing Checklist

### Admin Functions
- [ ] Create new assignment
- [ ] End existing assignment
- [ ] Delete assignment
- [ ] Edit assignment (change dates/notes)
- [ ] Filter assignments (Active only)
- [ ] Generate assignment reports

### Pharmacist Functions
- [ ] Pharmacy dashboard with single assignment
- [ ] Pharmacy dashboard with multiple assignments
- [ ] Pharmacy dashboard with no assignment (redirect)
- [ ] Change dispensary during session
- [ ] Logout clears current dispensary

### Cross-Functionality
- [ ] Pharmacy operations respect subdivision
- [ ] Inventory shows correct current dispensary
- [ ] Carts filter by current dispensary
- [ ] Reports include current dispensary data
- [ ] Admin sees all vs pharmacist sees assigned

## Error Handling & Edge Cases

### Scenario: Pharmacist with No Assignment
- **Action**: Try to access `/pharmacy/`
- **Result**: Redirected to `/pharmacy/select-dispensary/`
- **Message**: "You have not been assigned to any dispensary yet."

### Scenario: Pharmacist with Multiple Assignments
- **Action**: Login
- **Result**: Show dispensary selection page
- **Feature**: Both options shown as clickable

### Scenario: Trying to Access Another Dispensary
- **Action**: Direct URL to `/pharmacy/dispensaries/2/` (not assigned)
- **Result**: Access denied, redirect to dashboard
- **Message**: "You don't have permission to access 'Dispensary 2'..."

### Scenario: Deleted Assignment During Session
- **Action**: Admin ends pharmacist's assignment simultaneously
- **Result**: Pharmacist still has session until logout
- **Message**: Normal operations continue until session refresh

### Scenario: Pharmacist Hidden by Filter
- **Action**: User not in "available_pharmacists" queryset
- **Available Filters**: 
  - Active role only
  - Profile exists
  - Not already assigned (prevents duplicates)

## Clean Up Process

### Remove Demo Data
```bash
# Remove test assignments
from pharmacy.models import PharmacistDispensaryAssignment
PharmacistDispensaryAssignment.objects.filter(
    pharmacist__username__contains='test_'
).delete()

# Remove demo users
from accounts.models import CustomUser
CustomUser.objects.filter(username__contains='pharma_').delete()

# Remove demo dispensary
from pharmacy.models import Dispensary
Dispensary.objects.filter(location__contains='Test ').delete()
```

### Graceful Cleanup
1. **End all assignments**: Set end_date to today, make inactive
2. **Re-assign pharmacists**: Update assignments if needed
3. **Delete users**: Use Django admin if cleanup needed
4. **Backup**: Export assignment data before cleanup

## Performance Impact

### Database Queries
- **List View**: 2-3 optimized queries (assignees + assignments + stats)
- **Single Assignment**: 1 query (pk lookup)
- **Reports**: 3-4 queries (analytics)

### Caching
- Session storage for current dispensary (constant time)
- No additional caching beyond Django defaults

### Bulk Operations
- **Export**: Uses streaming response for large datasets
- **Report prep**: Materialized views not required (small datasets)

## Delegate/Re-assign Pattern

### Reassignment Note
If a pharmacist needs to change primary dispensary:
1. **End current assignment** (set end_date, inactive)
2. **Create new assignment** at new dispensary
3. **Retain history** (old assignments preserved for audit)

## Audit Trail
All actions are recorded in:
- Core AuditLog models
- Includes: action type, user, timestamp, assignment IDs
- Available via Admin → Audit Logs

## Local Development Setup

### Known Issues & Solutions

**Issue**: Permission error accessing assignments
**Solution**: Run `python manage.py create_custom_permissions`

**Issue**: No pharmacists available in dropdown
**Solution**: Verify user has `profile.role == 'pharmacist'`

**Issue**: Dispensary already exists
**Solution**: Use existing dispenser or run `setup_test_pharmacist.py`

### Testing in Interactive Mode
Open two browser windows:
1. Admin: Create/ manage assignments
2. Pharmacist: Verify real-time filtering

## Feature Extensions (Future)

### Planned Enhancements
- [ ] Send email notification on new assignment
- [ ] Daily email reminders for today's shifts
- [ ] Export assignments to CSV/JSON
- [ ] Bulk upload assignments from Excel
- [ ] Drag-and-drop calendar view
- [ ] Assignment approval workflow
- [ ] Approver field (manager must approve)

### Database Cleanup
- Create management command: `assign_pharmacist_to_dispensary --cleanup`
- Move ended assignments to archive table
- Purge deleted assignments after retention period

## Conclusion

The pharmacist-dispensary assignment UI provides:
1. **Complete management interface** for admin users
2. **Analytics and reporting** for assignment distribution
3. **Session-based access control** for pharmacist users
4. **Full integration** with existing pharmacy workflows
5. **Audit trail** for compliance and tracking

The system ensures pharmacists only access data for their assigned dispensary while providing administrators with full control over assignment management.
