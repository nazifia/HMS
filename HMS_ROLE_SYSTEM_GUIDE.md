# HMS Role-Based Access Control System

## Overview

The Hospital Management System (HMS) now includes a comprehensive role-based access control system that allows administrators to assign specific roles to users, controlling their access to different parts of the application.

## Available Roles

The system includes the following predefined roles based on typical hospital operations:

### 1. **Admin** 
- **Description**: System Administrator - Full access to all HMS modules and user management
- **Access**: Complete system access, user management, role management
- **Users**: 2 (superuser, admin)

### 2. **Doctor**
- **Description**: Medical Doctor - Access to patient care, consultations, prescriptions, and medical records
- **Permissions**: 13 permissions including patient management, consultations, prescriptions, lab requests
- **Users**: 1 (Dr. John Smith - Cardiology)

### 3. **Nurse**
- **Description**: Registered Nurse - Patient care, vitals monitoring, and inpatient management
- **Permissions**: 5 permissions including patient care, vitals, inpatient management
- **Users**: 1 (Jane Doe - Emergency)

### 4. **Receptionist**
- **Description**: Front Desk Receptionist - Patient registration, appointment scheduling, and basic billing
- **Permissions**: 19 permissions including patient registration, appointments, waiting list, basic billing
- **Users**: 1 (Mary Johnson - Front Desk)

### 5. **Pharmacist**
- **Description**: Licensed Pharmacist - Medication management, prescription dispensing, and inventory control
- **Permissions**: 8 permissions including pharmacy inventory, prescriptions, dispensing
- **Users**: 1 (Bob Wilson - Pharmacy)

### 6. **Lab Technician**
- **Description**: Laboratory Technician - Lab test management, sample processing, and result entry
- **Permissions**: 11 permissions including lab tests, test requests, results, sample management
- **Users**: 1 (Alice Brown - Laboratory)

### 7. **Radiology Staff**
- **Description**: Radiology Technician - Imaging services, radiology requests, and report management
- **Permissions**: 3 permissions for radiology services
- **Users**: 0

### 8. **Accountant**
- **Description**: Hospital Accountant - Financial management, billing oversight, and payment processing
- **Permissions**: 17 permissions including billing, payments, financial reports
- **Users**: 1 (David Lee - Finance)

### 9. **Health Record Officer**
- **Description**: Health Records Officer - Medical records management, patient data, and information systems
- **Permissions**: 9 permissions including patient management, medical records, health information
- **Users**: 0

## How to Use the Role System

### 1. **Accessing Role Management**
- Navigate to **User Management** → **Role System Demo** in the sidebar
- Or go directly to `/accounts/role-demo/`

### 2. **Assigning Roles to Users**
1. Go to **User Management** → **All Users**
2. Find the user you want to assign roles to
3. Click the **Manage Privileges** button (🔧 icon)
4. Select the appropriate roles for that user
5. Click **Update Privileges** to save

### 3. **Managing Roles**
1. Go to **User Management** → **Manage Roles**
2. View existing roles or create new ones
3. Edit role permissions as needed
4. Set up role hierarchies if required

### 4. **Bulk Role Assignment**
1. In the **User Dashboard**, select multiple users using checkboxes
2. Choose **Assign Role** from the bulk actions dropdown
3. Select the role to assign
4. Click **Apply** to assign the role to all selected users

## Key Features

### **Role Hierarchy Support**
- Roles can inherit permissions from parent roles
- Flexible permission inheritance system

### **Permission Management**
- Each role has specific permissions
- Permissions control access to different parts of the application
- Fine-grained control over user capabilities

### **Audit Logging**
- All role assignments and changes are logged
- Track who made changes and when
- View audit logs for security and compliance

### **User-Friendly Interface**
- Visual role cards showing permissions and user counts
- Easy-to-use role assignment interface
- Quick actions for common tasks

## Security Features

### **Superuser Access**
- Superusers have unrestricted access to all parts of the HMS application
- Superuser status bypasses role-based restrictions

### **Admin Independence**
- Django admin interface is completely independent from application roles
- Only staff users can access Django admin functionality

### **Role Validation**
- Prevents circular role hierarchies
- Validates role assignments before saving
- Ensures data integrity

## Management Commands

### **Populate Roles**
```bash
python manage.py populate_roles
```
Creates all predefined HMS roles with appropriate permissions.

### **Create Demo Users**
```bash
python manage.py demo_users --assign-existing
```
Creates demo users for each role and assigns roles to existing users.

## Current System Status

- **Total Roles**: 9
- **Total Users**: 8
- **Users with Roles**: 8
- **Users without Roles**: 0
- **Permissions in Use**: 85+ permissions across all roles

## Quick Access Links

When logged in as an admin, you can access:

- **Role System Demo**: `/accounts/role-demo/`
- **User Management**: `/accounts/user-dashboard/`
- **Role Management**: `/accounts/roles/`
- **Create New Role**: `/accounts/roles/create/`
- **Permission Management**: `/accounts/permissions/`
- **Audit Logs**: `/accounts/audit-logs/`

## Best Practices

1. **Assign Minimum Required Roles**: Only assign roles that users actually need
2. **Regular Audits**: Periodically review user roles and permissions
3. **Use Role Hierarchies**: Set up parent-child relationships for related roles
4. **Monitor Changes**: Regularly check audit logs for unauthorized changes
5. **Test Permissions**: Verify that users can access what they need and nothing more

## Support

For questions or issues with the role system, check the audit logs or contact the system administrator.

---

*This role system provides a secure, flexible, and user-friendly way to manage access control in the HMS application.*
