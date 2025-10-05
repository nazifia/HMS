# Prescription Invoice and Payment Receipt Implementation

## Overview
This document describes the comprehensive implementation of prescription invoice generation and payment receipt system across the HMS application.

## Key Features Implemented

### 1. Pharmacist-Controlled Invoice Generation
**Problem Solved:** Previously, invoices were automatically created when prescriptions were created, leading to patients being charged for medications that might not be available in the dispensary.

**Solution:**
- Modified `core/prescription_utils.py` to make invoice creation optional
- Added `auto_create_invoice` parameter (default: False) to `create_prescription_from_module()`
- Created new view `pharmacist_generate_invoice()` that:
  - Checks medication availability across all dispensaries
  - Shows real-time stock levels for each medication
  - Allows pharmacist to select a dispensary
  - Generates invoice ONLY for medications available in the selected dispensary
  - Calculates correct amounts based on NHIA status (10% for NHIA, 100% for regular patients)

**Files Modified:**
- `core/prescription_utils.py` - Made invoice creation optional
- `pharmacy/views.py` - Added `pharmacist_generate_invoice()` view
- `pharmacy/urls.py` - Added route for pharmacist invoice generation
- `pharmacy/templates/pharmacy/pharmacist_generate_invoice.html` - New template
- `pharmacy/templates/pharmacy/prescription_detail.html` - Updated to show "Generate Invoice" button

### 2. Universal Payment Receipt System
**Problem Solved:** No standardized, printable payment receipts across different services.

**Solution:**
- Created comprehensive, printable payment receipt template
- Implemented receipt generation for all payment types:
  - Pharmacy/Medication payments
  - Laboratory test payments
  - Consultation payments
  - Admission payments

**Features:**
- Professional layout with hospital branding
- Complete patient information
- Detailed service/item breakdown
- Payment method and transaction details
- Amount summary with subtotal, tax, discount, and balance
- Signature sections for patient and authorized personnel
- Official stamp area
- Print-optimized CSS
- Computer-generated receipt disclaimer

**Files Created:**
- `templates/payments/payment_receipt.html` - Universal receipt template

**Files Modified:**
- `pharmacy/views.py` - Added receipt generation views:
  - `pharmacy_payment_receipt()`
  - `laboratory_payment_receipt()`
  - `consultation_payment_receipt()`
  - `admission_payment_receipt()`
- `pharmacy/urls.py` - Added receipt URL routes
- `pharmacy/templates/pharmacy/prescription_payment.html` - Added payment history with receipt buttons
- `templates/laboratory/payment_history.html` - Added receipt buttons

### 3. Interactive Inventory-Based Invoice Generation
**How It Works:**
1. Doctor creates prescription (no invoice created automatically)
2. Prescription appears in pharmacist's queue
3. Pharmacist clicks "Generate Invoice (Pharmacist)" button
4. Pharmacist selects a dispensary from dropdown
5. System displays all prescribed medications with:
   - Prescribed quantity (pre-filled)
   - Editable quantity input field
   - Real-time availability status
   - Item total calculation
6. Pharmacist can adjust quantities as needed (cannot exceed prescribed amount)
7. Pharmacist clicks "Check Availability for All Medications"
8. System performs real-time AJAX check against selected dispensary inventory
9. System displays:
   - Available medications (green highlight)
   - Unavailable medications (red highlight)
   - Stock levels for each medication
   - Total summary with available/unavailable counts
   - Calculated invoice amount (with NHIA discount if applicable)
10. Pharmacist reviews and clicks "Generate Invoice"
11. System generates invoice for available medications only
12. Patient is charged only for available medications at specified quantities

**Benefits:**
- Prevents charging for unavailable medications
- Improves patient satisfaction
- Reduces billing disputes
- Ensures accurate inventory management
- Supports NHIA pricing (10% patient payment)

### 4. Payment Receipt Integration
**Pharmacy Payments:**
- Receipt accessible from payment history
- Shows all prescribed medications with quantities and prices
- Includes NHIA discount information if applicable
- Receipt number format: PH-{payment_id}

**Laboratory Payments:**
- Receipt shows all tests performed
- Individual test prices listed
- Receipt number format: LAB-{payment_id}

**Consultation Payments:**
- Shows consultation details
- Doctor information included
- Receipt number format: CONS-{payment_id}

**Admission Payments:**
- Shows ward information
- Admission fee details
- Receipt number format: ADM-{payment_id}

## Technical Implementation

### Database Changes
No database migrations required. All changes are logic-based.

### URL Routes Added
```python
# Pharmacy URLs
path('prescriptions/<int:prescription_id>/generate-invoice/', views.pharmacist_generate_invoice, name='pharmacist_generate_invoice'),
path('payments/<int:payment_id>/receipt/', views.pharmacy_payment_receipt, name='pharmacy_payment_receipt'),
path('payments/laboratory/<int:payment_id>/receipt/', views.laboratory_payment_receipt, name='laboratory_payment_receipt'),
path('payments/consultation/<int:payment_id>/receipt/', views.consultation_payment_receipt, name='consultation_payment_receipt'),
path('payments/admission/<int:payment_id>/receipt/', views.admission_payment_receipt, name='admission_payment_receipt'),
```

### Views Added
1. `pharmacist_generate_invoice(request, prescription_id)` - Main invoice generation view
2. `pharmacy_payment_receipt(request, payment_id)` - Pharmacy receipt generation
3. `laboratory_payment_receipt(request, payment_id)` - Laboratory receipt generation
4. `consultation_payment_receipt(request, payment_id)` - Consultation receipt generation
5. `admission_payment_receipt(request, payment_id)` - Admission receipt generation

### Templates Created/Modified
**Created:**
- `pharmacy/templates/pharmacy/pharmacist_generate_invoice.html`
- `templates/payments/payment_receipt.html`

**Modified:**
- `pharmacy/templates/pharmacy/prescription_detail.html`
- `pharmacy/templates/pharmacy/prescription_payment.html`
- `templates/laboratory/payment_history.html`

## User Workflow

### Prescription to Payment Flow
1. **Doctor Creates Prescription**
   - Selects patient
   - Adds medications
   - Saves prescription
   - No invoice created yet

2. **Pharmacist Reviews and Generates Invoice**
   - Opens prescription detail
   - Clicks "Generate Invoice (Pharmacist)"
   - Reviews medication availability across dispensaries
   - Selects appropriate dispensary
   - System generates invoice for available items only

3. **Payment Processing**
   - Billing office or patient processes payment
   - Payment can be from wallet or direct billing
   - Payment is recorded with all details

4. **Receipt Generation**
   - After payment, receipt button appears in payment history
   - Click "Receipt" button to view/print
   - Receipt opens in new tab, ready to print
   - Professional format with all necessary information

## NHIA Integration
- System automatically detects NHIA patients
- Calculates 10% patient payment for NHIA patients
- Shows clear breakdown of patient vs NHIA portions
- Receipts indicate NHIA status and discount

## Inventory Management Integration
- Checks both ActiveStoreInventory (new system) and MedicationInventory (legacy)
- Real-time stock level display
- Prevents overselling
- Supports multiple dispensaries
- Batch number tracking

## Error Handling
- Validates dispensary selection
- Checks for existing invoices
- Handles missing inventory gracefully
- Provides clear error messages
- Logs all actions for audit trail

## Security Features
- Login required for all views
- Permission checks for sensitive operations
- Audit logging for invoice generation
- Transaction atomicity for payment processing

## Printing Features
- Print-optimized CSS
- Automatic page breaks
- Professional layout
- Hospital branding
- Signature sections
- Official stamp area
- Print button (hidden when printing)

## Future Enhancements
1. Email receipt to patient
2. SMS notification with receipt link
3. Bulk receipt printing
4. Receipt customization per department
5. Multi-language support
6. QR code for receipt verification
7. Digital signature integration

## Testing Checklist
- [ ] Create prescription without auto-invoice
- [ ] Generate invoice with available medications
- [ ] Generate invoice with partially available medications
- [ ] Test NHIA patient invoice generation
- [ ] Test regular patient invoice generation
- [ ] Process payment and generate receipt
- [ ] Print receipt from browser
- [ ] Test all payment types (pharmacy, lab, consultation, admission)
- [ ] Verify inventory deduction after dispensing
- [ ] Test with multiple dispensaries

## Maintenance Notes
- Receipt template is universal and can be used for any payment type
- Hospital information can be configured in settings
- Receipt numbering follows module-specific format
- All receipts use the same base template for consistency

## Support
For issues or questions, contact the development team.

