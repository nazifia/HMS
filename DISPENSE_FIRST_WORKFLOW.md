# Dispense-First Workflow Implementation

## Overview
Modified the prescription dispensing workflow so that pharmacists can dispense medications FIRST, then the system creates an invoice based on actual dispensed quantities, and finally the patient makes payment.

## New Workflow

### Previous Workflow (Removed)
1. Doctor creates prescription
2. Pharmacist generates invoice (with availability check)
3. Patient pays
4. Pharmacist dispenses

### New Workflow (Current)
1. **Doctor creates prescription** → No invoice created
2. **Pharmacist goes to dispense page** → `http://127.0.0.1:8000/pharmacy/prescriptions/{id}/dispense/`
3. **Pharmacist selects dispensary** → Chooses which dispensary to dispense from
4. **Pharmacist inputs quantities** → Adjusts quantities based on availability and patient needs
5. **System checks availability** → Real-time stock checking
6. **Pharmacist dispenses medications** → Inventory is updated, dispensing logs created
7. **System creates invoice** → Based on ACTUAL dispensed quantities (not prescribed quantities)
8. **System redirects to payment page** → Patient can now pay for what they're getting
9. **Patient makes payment** → Payment processed
10. **Receipt generated** → Professional printable receipt

## Key Benefits

### 1. **Flexibility**
- Pharmacist can adjust quantities based on actual stock availability
- No need to pre-generate invoice before knowing what's available
- Can dispense partial quantities if full prescription isn't available

### 2. **Accuracy**
- Invoice reflects ACTUAL dispensed quantities, not prescribed quantities
- Patient pays for what they actually receive
- No discrepancies between invoice and dispensed items

### 3. **Efficiency**
- Single workflow - dispense and invoice in one step
- No need for separate "Generate Invoice" step
- Faster patient service

### 4. **NHIA Support**
- Automatically applies 10% patient payment for NHIA patients
- 90% NHIA coverage calculated automatically
- Proper pricing breakdown displayed

## Technical Changes

### 1. Modified `pharmacy/views.py` - `dispense_prescription` View

**Location**: Lines 2099-2158

**Changes**:
- Added invoice creation after successful dispensing
- Calculate total based on dispensing logs (actual dispensed quantities)
- Apply NHIA discount if applicable (10% patient, 90% NHIA)
- Create pharmacy_billing.Invoice using `create_pharmacy_invoice` utility
- Redirect to payment page instead of prescription detail

**Code Added**:
```python
# Create invoice based on dispensed quantities
from pharmacy_billing.models import Invoice as PharmacyInvoice
from pharmacy_billing.utils import create_pharmacy_invoice

# Check if invoice already exists
try:
    pharmacy_invoice = PharmacyInvoice.objects.get(prescription=prescription)
    messages.info(request, 'Invoice already exists for this prescription.')
except PharmacyInvoice.DoesNotExist:
    # Calculate total based on dispensed quantities
    dispensed_total = Decimal('0.00')
    for log in DispensingLog.objects.filter(prescription_item__prescription=prescription):
        dispensed_total += log.total_price_for_this_log
    
    # Apply NHIA discount if applicable
    if prescription.patient.is_nhia_patient():
        # Patient pays 10%, NHIA covers 90%
        patient_payable = dispensed_total * Decimal('0.10')
    else:
        # Patient pays 100%
        patient_payable = dispensed_total
    
    # Create invoice
    pharmacy_invoice = create_pharmacy_invoice(request, prescription, patient_payable)
    
    if pharmacy_invoice:
        messages.success(request, f'Invoice created successfully. Total: ₦{patient_payable:.2f}')
    else:
        messages.error(request, 'Failed to create invoice. Please contact billing.')

# Redirect to payment page
return redirect('pharmacy:prescription_payment', prescription_id=prescription.id)
```

### 2. Modified `pharmacy/templates/pharmacy/dispense_prescription.html`

**Changes**:

#### A. Removed Payment Verification Requirement (Line 200)
**Old**:
```html
<form id="dispense-form" method="post" {% if not prescription.is_payment_verified %}style="pointer-events: none; opacity: 0.6;"{% endif %}>
```

**New**:
```html
<form id="dispense-form" method="post">
```

**Reason**: Form is no longer disabled when payment is not verified, allowing pharmacist to dispense first.

#### B. Updated Payment Alert (Lines 236-240)
**Old**:
```html
{% if not prescription.is_payment_verified %}
<div class="alert alert-warning" role="alert">
    <h5 class="alert-heading"><i class="fas fa-exclamation-triangle"></i> Payment Required</h5>
    <p>This prescription cannot be dispensed until payment is completed.</p>
    ...
</div>
{% endif %}
```

**New**:
```html
<div class="alert alert-info" role="alert">
    <h5 class="alert-heading"><i class="fas fa-info-circle"></i> Dispensing Workflow</h5>
    <p class="mb-0">Select medications and quantities to dispense. An invoice will be created based on dispensed quantities, then patient can proceed to payment.</p>
</div>
```

**Reason**: Informs pharmacist of the new workflow instead of blocking dispensing.

## How It Works

### Step-by-Step Process

#### 1. Pharmacist Opens Dispense Page
- URL: `/pharmacy/prescriptions/{id}/dispense/`
- Page shows all prescription items
- No payment required to access

#### 2. Pharmacist Selects Dispensary
- Dropdown shows all active dispensaries
- Selection updates stock availability display
- AJAX call checks inventory in real-time

#### 3. Pharmacist Inputs Quantities
- Each medication has quantity input field
- Pre-filled with prescribed quantity
- Pharmacist can adjust based on:
  - Stock availability
  - Patient needs
  - Partial dispensing requirements

#### 4. Pharmacist Submits Form
- System validates quantities against stock
- Creates dispensing logs for each item
- Updates inventory (deducts stock)
- Updates prescription item quantities

#### 5. System Creates Invoice
- Calculates total from dispensing logs
- Applies NHIA discount if applicable:
  - NHIA patient: Patient pays 10%, NHIA covers 90%
  - Regular patient: Patient pays 100%
- Creates `pharmacy_billing.Invoice` record
- Links invoice to prescription

#### 6. Redirect to Payment
- Automatically redirects to payment page
- Shows invoice details
- Patient can pay using various methods:
  - Cash
  - Card
  - Bank Transfer
  - Wallet

#### 7. Payment Processing
- Payment recorded in system
- Invoice marked as paid
- Receipt generated
- Can be printed

## Invoice Calculation Examples

### Example 1: Regular Patient (Non-NHIA)
**Dispensed Items**:
- Paracetamol 500mg x 20 tablets @ ₦50 = ₦1,000
- Amoxicillin 250mg x 15 capsules @ ₦100 = ₦1,500

**Calculation**:
- Total dispensed: ₦2,500
- Patient pays: ₦2,500 (100%)
- NHIA covers: ₦0

**Invoice Amount**: ₦2,500

### Example 2: NHIA Patient
**Dispensed Items**:
- Paracetamol 500mg x 20 tablets @ ₦50 = ₦1,000
- Amoxicillin 250mg x 15 capsules @ ₦100 = ₦1,500

**Calculation**:
- Total dispensed: ₦2,500
- Patient pays: ₦250 (10%)
- NHIA covers: ₦2,250 (90%)

**Invoice Amount**: ₦250

### Example 3: Partial Dispensing
**Prescribed**:
- Paracetamol 500mg x 30 tablets @ ₦50 = ₦1,500

**Actually Dispensed** (only 20 available):
- Paracetamol 500mg x 20 tablets @ ₦50 = ₦1,000

**Calculation** (NHIA Patient):
- Total dispensed: ₦1,000
- Patient pays: ₦100 (10%)
- NHIA covers: ₦900 (90%)

**Invoice Amount**: ₦100

**Note**: Patient only pays for 20 tablets, not the prescribed 30.

## Advantages Over Previous System

### 1. **No Pre-Payment Barrier**
- **Old**: Patient had to pay before pharmacist could dispense
- **New**: Pharmacist dispenses first, then patient pays for what they receive

### 2. **Accurate Billing**
- **Old**: Invoice based on prescribed quantities (might not match dispensed)
- **New**: Invoice based on actual dispensed quantities (always accurate)

### 3. **Better Stock Management**
- **Old**: Invoice created before checking availability
- **New**: Invoice created after confirming availability and dispensing

### 4. **Flexible Partial Dispensing**
- **Old**: Difficult to handle partial dispensing with pre-created invoice
- **New**: Easy to dispense partial quantities, invoice reflects actual amounts

### 5. **Improved Patient Experience**
- **Old**: Patient pays upfront, might not get full prescription
- **New**: Patient pays for exactly what they receive

## Integration with Existing Systems

### Compatible With:
- ✅ NHIA authorization workflow
- ✅ Inventory management (ActiveStoreInventory & MedicationInventory)
- ✅ Dispensing logs
- ✅ Payment processing
- ✅ Receipt generation
- ✅ Audit logging

### Does Not Affect:
- ✅ Prescription creation
- ✅ Doctor workflow
- ✅ Patient records
- ✅ Other billing modules (consultations, lab, admissions)

## Testing Guide

### Test Case 1: Regular Patient Full Dispensing
1. Create prescription for regular patient
2. Go to dispense page
3. Select dispensary
4. Dispense all items with full quantities
5. Verify invoice created with 100% patient payment
6. Complete payment
7. Verify receipt generated

### Test Case 2: NHIA Patient Full Dispensing
1. Create prescription for NHIA patient
2. Go to dispense page
3. Select dispensary
4. Dispense all items with full quantities
5. Verify invoice created with 10% patient payment
6. Complete payment
7. Verify receipt shows NHIA breakdown

### Test Case 3: Partial Dispensing
1. Create prescription
2. Go to dispense page
3. Select dispensary
4. Dispense only some items or partial quantities
5. Verify invoice reflects only dispensed items
6. Complete payment
7. Verify prescription status is "partially_dispensed"

### Test Case 4: Multiple Dispensing Sessions
1. Create prescription
2. Dispense some items (invoice created)
3. Patient pays
4. Later, dispense remaining items
5. Verify existing invoice is used (not duplicate)
6. Verify total is updated

## Troubleshooting

### Issue: Invoice Not Created
**Symptoms**: Dispensing succeeds but no invoice created

**Possible Causes**:
1. `create_pharmacy_invoice` utility failed
2. Service "Medication Dispensing" not configured
3. Database error

**Solution**:
- Check error messages
- Verify "Medication Dispensing" service exists in billing module
- Check logs for detailed error

### Issue: Wrong Invoice Amount
**Symptoms**: Invoice amount doesn't match dispensed quantities

**Possible Causes**:
1. Dispensing logs not created properly
2. NHIA discount not applied correctly
3. Medication prices incorrect

**Solution**:
- Verify dispensing logs exist for all dispensed items
- Check patient NHIA status
- Verify medication prices in database

### Issue: Duplicate Invoice Error
**Symptoms**: Error about invoice already existing

**Possible Causes**:
1. Invoice already created in previous dispensing session
2. Multiple simultaneous dispense attempts

**Solution**:
- System handles this gracefully - uses existing invoice
- No action needed, this is expected behavior

## Future Enhancements

1. **Batch Dispensing**
   - Dispense multiple prescriptions at once
   - Create consolidated invoice

2. **Inventory Reservation**
   - Reserve stock when prescription created
   - Prevent overselling

3. **Automated Stock Alerts**
   - Alert pharmacist when stock low
   - Suggest alternative medications

4. **Dispensing Analytics**
   - Track dispensing patterns
   - Identify frequently dispensed medications
   - Optimize inventory levels

## Related Files

- `pharmacy/views.py` - Dispense view with invoice creation
- `pharmacy/templates/pharmacy/dispense_prescription.html` - Dispense template
- `pharmacy_billing/utils.py` - Invoice creation utility
- `pharmacy_billing/models.py` - Pharmacy invoice model
- `pharmacy/models.py` - Prescription and dispensing models

## Conclusion

The new dispense-first workflow provides a more practical and accurate approach to prescription dispensing and billing. Pharmacists can now dispense medications based on actual availability, and patients pay for exactly what they receive. This improves accuracy, flexibility, and patient satisfaction.

