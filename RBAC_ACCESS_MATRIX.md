# HMS Role-Based Access Control (RBAC) Matrix

## Overview
This document defines the comprehensive access control matrix for all 9 roles in the Hospital Management System.

## Role Definitions

### 1. **Administrator (admin)**
**Full System Access** - Manages entire hospital operations
- ✅ All Modules
- ✅ User Management
- ✅ System Configuration
- ✅ Financial Management
- ✅ Reports & Analytics

### 2. **Doctor (doctor)**
**Medical Care Provider** - Primary patient care and treatment
- ✅ Patient Management (View, Edit)
- ✅ Consultations (Full Access)
- ✅ Medical Records (View, Create, Edit)
- ✅ Prescriptions (Create, Edit)
- ✅ Lab Requests (Create, View)
- ✅ Radiology Requests (Create, View)
- ✅ Inpatient Management (View, Edit)
- ✅ Appointments (View, Create)
- ✅ Referrals (Create, View)
- ✅ Medical Specialty Modules (Dental, ENT, ANC, etc.)
- ✅ Theatre/Surgery (Schedule, View)
- ❌ Billing (View only, no create/edit)
- ❌ User Management
- ❌ Pharmacy Dispensing

### 3. **Nurse (nurse)**
**Patient Care Support** - Vital signs, patient monitoring, assist doctors
- ✅ Patient Management (View, Edit)
- ✅ Vitals Management (Full Access)
- ✅ Medical Records (View, Create, Edit)
- ✅ Consultations (View)
- ✅ Prescriptions (View only)
- ✅ Inpatient Management (Full Access)
- ✅ Appointments (View)
- ✅ Referrals (Create for doctor review)
- ✅ Medical Specialty Modules (Assist in procedures)
- ✅ Theatre/Surgery (Assist)
- ❌ Lab/Radiology (View results only, no requests)
- ❌ Billing
- ❌ Pharmacy Dispensing
- ❌ User Management

### 4. **Receptionist (receptionist)**
**Front Desk Operations** - Patient registration, appointments, basic billing
- ✅ Patient Registration (Full Access)
- ✅ Appointments (Full Access)
- ✅ Waiting List Management
- ✅ Basic Patient Info (View, Edit demographics)
- ✅ Billing (View, Create invoices)
- ✅ Wallet Management (Top-up, view balance)
- ✅ NHIA Registration
- ❌ Medical Records (Limited view)
- ❌ Prescriptions
- ❌ Lab/Radiology Results
- ❌ Consultations (Create waiting list only)
- ❌ User Management

### 5. **Pharmacist (pharmacist)**
**Medication Management** - Dispensing, inventory, stock control
- ✅ Pharmacy Module (Full Access)
  - Inventory Management
  - Stock Control
  - Dispensing
  - Transfers
  - Medical Packs
  - Procurement
- ✅ Prescriptions (View, Dispense)
- ✅ Patient Info (View basic info)
- ✅ Pharmacy Reports
- ❌ Medical Records
- ❌ Consultations
- ❌ Billing (except pharmacy sales)
- ❌ User Management

### 6. **Lab Technician (lab_technician)**
**Laboratory Services** - Test processing, result entry
- ✅ Laboratory Module (Full Access)
  - Test Requests (View, Process)
  - Results Entry
  - Sample Management
  - Equipment Management
- ✅ Patient Info (View basic info)
- ✅ Lab Reports & Statistics
- ❌ Medical Records
- ❌ Prescriptions
- ❌ Consultations
- ❌ Billing
- ❌ User Management

### 7. **Accountant (accountant)**
**Financial Management** - Billing, payments, financial reports
- ✅ Billing Module (Full Access)
  - Invoice Management
  - Payment Processing
  - Services Management
- ✅ Wallet Management (Full Access)
- ✅ Financial Reports (All)
  - Revenue Dashboard
  - Revenue Trends
  - Department Reports
  - Transaction History
- ✅ Patient Info (View for billing purposes)
- ❌ Medical Records
- ❌ Prescriptions
- ❌ Lab/Radiology Results
- ❌ User Management (except viewing)

### 8. **Health Record Officer (health_record_officer)**
**Medical Records Management** - Documentation, record-keeping
- ✅ Patient Management (Full Access)
- ✅ Medical Records (View, Create, Edit, Archive)
- ✅ Vitals Management (View, Edit)
- ✅ Patient Registration (Full)
- ✅ Record Reports
- ❌ Prescriptions (View only)
- ❌ Lab Results (View only)
- ❌ Billing
- ❌ Pharmacy
- ❌ User Management

### 9. **Radiology Staff (radiology_staff)**
**Imaging Services** - X-ray, ultrasound, imaging procedures
- ✅ Radiology Module (Full Access)
  - Imaging Requests (View, Process)
  - Results Entry
  - Report Management
- ✅ Patient Info (View basic info)
- ✅ Radiology Reports & Statistics
- ❌ Medical Records (except related to imaging)
- ❌ Prescriptions
- ❌ Consultations
- ❌ Billing
- ❌ User Management

---

## Module Access Summary Table

| Module | Admin | Doctor | Nurse | Receptionist | Pharmacist | Lab Tech | Accountant | HRO | Radiology |
|--------|-------|--------|-------|--------------|------------|----------|------------|-----|-----------|
| **Dashboard** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Patients** | Full | View/Edit | View/Edit | Full | View | View | View | Full | View |
| **Consultations** | ✅ | Full | View | Waiting List | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Doctors** | Full | Own Profile | ❌ | View List | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Inpatient** | Full | Full | Full | ❌ | ❌ | ❌ | ❌ | View | ❌ |
| **Appointments** | Full | View/Create | View | Full | ❌ | ❌ | ❌ | View | ❌ |
| **Consulting Rooms** | Full | Full | View | Full | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Pharmacy** | Full | View | View | ❌ | Full | ❌ | Reports | ❌ | ❌ |
| **Dispensaries** | Full | ❌ | ❌ | ❌ | Full | ❌ | ❌ | ❌ | ❌ |
| **Laboratory** | Full | Request/View | View | ❌ | ❌ | Full | Reports | ❌ | ❌ |
| **Radiology** | Full | Request/View | View | ❌ | ❌ | ❌ | Reports | ❌ | Full |
| **Medical Specialties** | Full | Full | Assist | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Theatre** | Full | Full | Assist | ❌ | Medical Packs | ❌ | ❌ | ❌ | ❌ |
| **Desk Office (NHIA)** | Full | ❌ | ❌ | View | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Billing** | Full | View | ❌ | Create/View | ❌ | ❌ | Full | ❌ | ❌ |
| **Wallet** | Full | ❌ | ❌ | Top-up | ❌ | ❌ | Full | ❌ | ❌ |
| **Core Features** | Full | ❌ | ❌ | ❌ | ❌ | ❌ | Revenue | ❌ | ❌ |
| **User Management** | Full | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **HR** | Full | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Financial Reports** | Full | ❌ | ❌ | ❌ | Pharmacy | Lab | Full | ❌ | Radiology |
| **Departments** | Full | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Permission-to-Module Mapping

### Navigation Menu Access

**Dashboard** - `view_dashboard`
- All authenticated users

**Access Control** - `manage_roles`, `view_user_management`
- Admin only

**Consultations** - `view_consultations`, `create_consultation`, `view_patients`
- Doctor (Full), Nurse (View), Receptionist (Waiting List)

**Patients** - `view_patients`, `create_patient`
- Doctor, Nurse, Receptionist, Admin, HRO

**Doctors** - `view_doctors`, `manage_doctors`
- Admin (Manage), All (View List)

**Inpatient** - `manage_admission`, `view_inpatient_records`
- Doctor, Nurse, Admin

**Appointments** - `view_appointments`, `create_appointment`
- Doctor, Receptionist, Admin, HRO

**Consulting Rooms** - `view_consulting_rooms`, `view_waiting_list`
- Doctor, Receptionist, Admin

**Pharmacy** - `manage_inventory`, `dispense_medication`, `view_prescriptions`
- Pharmacist (Full), Admin (Full), Doctor (View)

**Dispensaries** - `manage_dispensary`, `transfer_medication`
- Pharmacist, Admin

**Laboratory** - `create_test_request`, `view_tests`, `enter_results`
- Lab Technician (Full), Doctor (Request), Admin (Full)

**Radiology** - `create_radiology_request`, `view_radiology`
- Radiology Staff (Full), Doctor (Request), Admin (Full)

**Medical Specialties** (Dental, ENT, ANC, etc.)
- Doctor, Nurse, Admin

**Theatre** - Surgery management
- Doctor, Nurse (Assist), Admin

**Desk Office** - NHIA Authorization
- Admin, Receptionist (View)

**Billing** - `view_invoices`, `create_invoice`, `process_payments`
- Accountant (Full), Receptionist (Create), Admin (Full)

**Wallet** - `manage_wallet`
- Accountant (Full), Receptionist (Top-up), Admin (Full)

**Core Features** - Admin tools, revenue, transactions
- Admin (Full), Accountant (Revenue)

**User Management** - `view_user_management`, `manage_roles`
- Admin only

**HR** - Staff management
- Admin only

**Financial Reports** - `view_financial_reports`, `view_reports`
- Admin (All), Accountant (All), Pharmacist (Pharmacy), Lab Tech (Lab), Radiology Staff (Radiology)

**Departments** - `manage_departments`
- Admin only

---

## Quick Access Links (Topbar)

### Bed Dashboard
- **Access**: Nurse, Doctor, Admin
- **Permission**: `manage_admission` OR `view_inpatient_records`

### Dispensing Report
- **Access**: Pharmacist, Admin
- **Permission**: `manage_inventory` OR `dispense_medication`

### Revenue Statistics
- **Access**: Accountant, Admin
- **Permission**: Role-based (accountant, admin)

### User Management
- **Access**: Admin only
- **Permission**: Role-based (admin)

### Notifications
- **Access**: All authenticated users
- **Permission**: Authenticated

---

## Implementation Notes

1. **Superusers**: Bypass all restrictions (full access)
2. **Permission Hierarchy**: Uses template filters from `core_tags.py`
3. **Backwards Compatibility**: All existing functionalities preserved
4. **Standard Healthcare Roles**: Based on industry standards
5. **Customizable**: Permissions can be modified via role management interface

---

**Last Updated**: 2025-01-14
**Version**: 1.0
**Maintained By**: HMS Development Team
