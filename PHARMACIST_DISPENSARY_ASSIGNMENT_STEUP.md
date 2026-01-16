# Pharmacist-to-Dispensary Assignment Guide

This guide explains how to set up pharmacist-to-dispensary assignments in the HMS Pharmacy module.

## Overview

The new pharmacist-dispensary assignment system allows administrators to:
- Assign specific pharmacists to specific pharmacy dispensary locations
- Enforce access control: Pharmacists can only access their assigned dispensary
- Multiple pharmacists can be assigned to the same dispensary
- Same pharmacist can be assigned to different dispensaries

## Features

### 1. Multi-Dispensary Support
- Pharmacists can be assigned to multiple dispensaries
- Pharmacists select their working dispensary on login
- Easy switching between dispensaries via the pharmacy interface

### 2. Access Control
- Pharmacists can only see data from their assigned dispensary
- Admins retain full access to all dispensary data
- Session-based selection persists across requests

### 3. Pharmacy Operations Filtering
- Pharmacy dashboard shows statistics only for the selected dispensary
- Prescription carts are filtered by dispensary
- Inventory and reporting reflect the selected location
- Transfer management is restricted to assigned dispensaries

## Setup Instructions

### Step 1: Access Admin Panel
1. Login as an administrator
2. Navigate to `/admin/` or `/pharmacy/dispensaries/`

### Step 2: Create Dispensaries (if not already present)
- Go to Admin → Pharmacy → Dispensaries
- You should already have dispensaries configured in your system

### Step 3: Assign Pharmacists to Dispensaries

#### Option A: Using Django Admin
1. Navigate to Admin → Pharmacy → Pharmacist Dispensary Assignments
2. Click "Add Pharmacist Dispensary Assignment"
3. Select:
   - **Pharmacist**: Choose the user (must have pharmacist role)
   - **Dispensary**: Choose the dispensary location
   - **Start Date**: Assignment start date (defaults to today)
   - **Is Active**: Checked by default
   - **Notes**: Optional notes about the assignment
4. Save the assignment

#### Option B: Using Management Command
```bash
# List current assignments
python manage.py assign_pharmacist_to_dispensary --list

# Add new assignment
python manage.py assign_pharmacist_to_dispensary --pharmacist [username_or_phone] --dispensary [dispensary_name]

# Add assignment with specific start date
python manage.py assign_pharmacist_to_dispensary --pharmacist [username] --dispensary [dispensary_name] --start-date 2024-01-01

# Remove assignment (end current assignment)
python manage.py assign_pharmacist_to_dispensary --pharmacist [username] --dispensary [dispensary_name] --remove

# Clear all assignments for a pharmacist (use carefully)
python manage.py assign_pharmacist_to_dispensary --pharmacist [username] --clear-all
```

### Step 4: Verify Pharmacists Have Correct Roles
1. Ensure the user has the `pharmacist` role assigned
2. This can be done via Admin → Users or User Management interface

## User Experience

### When Pharmacist Logs In

1. **Single Assignment**: Automatically selects the dispensary and shows welcome message
2. **Multiple Assignments**: Shows dispensary selection page
3. **No Assignments**: Shows error message and redirects to main dashboard

### During Session

- **Top Bar**: Shows current dispensary name with change icon
- **Sidebar**: Pharmacy menu shows "Select/Change Dispatch" option
- **Dashboard**: Shows statistics for the current dispensary only
- **Carts**: Only shows carts for the selected dispensary
- **Inventory**: Shows items available in the selected dispensary

### Changing Dispensary During Session

1. Click "Select/Change Dispatch" in the sidebar
2. Choose a different dispensary from the list
3. Click "Set Dispensary"
4. All subsequent operations will use the new dispensary

### Logout

- Dispensary selection is cleared on logout
- Next login will prompt for dispensary selection again
- Existing session data remains valid

## Access Rules

### Administrative Access
- **Superusers**: Full access to all dispensary data (no restrictions)
- **Site Admins**: See all dispensaries, limited operations based on role

### Pharmacist Access
- **Without Assignment**: Cannot access specific pharmacy sections
- **Single Assignment**: Automatically assigned to that dispensary
- **Multiple Assignments**: Must select a dispensary before accessing pharmacy features

### Special Cases

#### Select Dispensary Page Access
- **Access Allowed**: All pharmacists can access `/pharmacy/select-dispensary/`
- **Purpose**: Required to choose a dispensary when multiple are assigned
- **Redirect**: If only one assignment, automatically redirects to dashboard

#### Admin-Only Features
The following pages are restricted to admins only:
- Add/Edit/Delete dispensaries
- Manage all pharmacist assignments
- View all data across dispensaries

## Troubleshooting

### Issue: Pharmacist Cannot Access Pharmacy
**Solution**: 
1. Check if pharmacist has 'pharmacist' role
2. Verify assignment exists in PharmacistDispensaryAssignment table
3. Ensure assignment is marked as active
4. Check if end_date is set (assignment would be inactive)

### Issue: Cannot See Specific Dispensary
**Solution**:
- Verify the dispensary exists and is marked as active
- Check if pharmacist has assignment to that specific dispensary
- Contact admin to create assignment

### Issue: All Data Shows Despite Assignment
**Solution**:
- This likely means user has superuser/admin status
- Regular pharmacists should only see assigned dispensary data
- Check user roles in admin panel

## Database Schema

### New Model: PharmacistDispensaryAssignment
```python
Fields:
- pharmacist: ForeignKey to CustomUser
- dispensary: ForeignKey to Dispensary
- start_date: DateField (when assignment started)
- end_date: DateField (null when assignment is active)
- is_active: BooleanField (auto-set based on end_date)
- notes: TextField (optional)
- created_at: DateTimeField
- updated_at: DateTimeField
```

### Extended Model: Dispensary
Added many-to-many relationship with CustomUser:
```python
pharmacists: ManyToManyField to CustomUser through PharmacistDispensaryAssignment
```

## Session Variables

The system uses these session keys:
- `selected_dispensary_id`: ID of the current dispensary (for pharmacists)
- `selected_dispensary_name`: Name of the current dispensary (for display)
- `selected_dispensary_id` is cleared on logout and login

## Backup/Restore Considerations

When backing up the database:
- PharmacistDispensaryAssignment rows will be preserved
- Current session selections are stored in session tables (cleared on logout)
- No additional manual steps required for assignment data

## Migration from Older Version

This is a new feature with no migration steps required from previous versions. Pharmacy functionality continues to work as before for users without assignments.
