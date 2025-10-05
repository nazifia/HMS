# Testing Guide: Prescription Invoice and Payment Receipt System

## Pre-Testing Setup

### 1. Database Preparation
Ensure you have:
- At least 2 active dispensaries with active stores
- Several medications in inventory
- Test patients (both NHIA and non-NHIA)
- Test doctor accounts
- Test pharmacist accounts

### 2. Test Data Requirements
```python
# Run this in Django shell to verify setup
from pharmacy.models import Dispensary, Medication, ActiveStoreInventory
from patients.models import Patient

# Check dispensaries
dispensaries = Dispensary.objects.filter(is_active=True)
print(f"Active Dispensaries: {dispensaries.count()}")

# Check medications
medications = Medication.objects.filter(is_active=True)
print(f"Active Medications: {medications.count()}")

# Check inventory
inventory = ActiveStoreInventory.objects.all()
print(f"Inventory Items: {inventory.count()}")

# Check patients
nhia_patients = Patient.objects.filter(nhia_info__is_active=True)
regular_patients = Patient.objects.exclude(nhia_info__is_active=True)
print(f"NHIA Patients: {nhia_patients.count()}")
print(f"Regular Patients: {regular_patients.count()}")
```

## Test Cases

### Test Case 1: Basic Prescription Creation (No Auto-Invoice)
**Objective:** Verify that prescriptions are created without automatic invoice generation

**Steps:**
1. Log in as a doctor
2. Navigate to Pharmacy → Create Prescription
3. Select a patient
4. Add 2-3 medications
5. Save prescription

**Expected Results:**
- ✅ Prescription created successfully
- ✅ No invoice created automatically
- ✅ Prescription status shows "Pending"
- ✅ Payment status shows "Unpaid"
- ✅ "Generate Invoice (Pharmacist)" button visible

**Verification:**
```python
from pharmacy.models import Prescription
from billing.models import Invoice

prescription = Prescription.objects.latest('id')
print(f"Prescription ID: {prescription.id}")
print(f"Has invoice: {hasattr(prescription, 'invoice') and prescription.invoice is not None}")
# Should print: Has invoice: False
```

### Test Case 2: Pharmacist Invoice Generation - All Items Available
**Objective:** Generate invoice when all medications are available

**Setup:**
- Ensure all prescribed medications have sufficient stock in at least one dispensary

**Steps:**
1. Log in as pharmacist
2. Open the prescription from Test Case 1
3. Click "Generate Invoice (Pharmacist)"
4. Review availability check page
5. Verify all medications show "Sufficient" status
6. Select a dispensary with all items available
7. Click "Generate Invoice"

**Expected Results:**
- ✅ Availability page shows all medications with stock levels
- ✅ At least one dispensary shows "Sufficient" for all items
- ✅ Invoice generated successfully
- ✅ Success message shows all items included
- ✅ Invoice amount calculated correctly
- ✅ NHIA discount applied if patient is NHIA

**Verification:**
```python
from pharmacy_billing.models import Invoice as PharmacyInvoice

prescription = Prescription.objects.latest('id')
invoice = PharmacyInvoice.objects.get(prescription=prescription)
print(f"Invoice ID: {invoice.id}")
print(f"Invoice Amount: ₦{invoice.total_amount}")
print(f"Items in prescription: {prescription.items.count()}")
```

### Test Case 3: Pharmacist Invoice Generation - Partial Availability
**Objective:** Generate invoice when some medications are unavailable

**Setup:**
- Create prescription with 3 medications
- Ensure only 2 medications have stock

**Steps:**
1. Create prescription with 3 medications
2. Log in as pharmacist
3. Click "Generate Invoice (Pharmacist)"
4. Review availability - should show 2 available, 1 unavailable
5. Select dispensary
6. Generate invoice

**Expected Results:**
- ✅ Availability page shows mixed status
- ✅ Invoice generated for available items only
- ✅ Success message indicates excluded items
- ✅ Invoice amount reflects only available medications

### Test Case 4: NHIA Patient Invoice Generation
**Objective:** Verify NHIA discount calculation

**Setup:**
- Use NHIA patient
- Medications total value: ₦10,000

**Steps:**
1. Create prescription for NHIA patient
2. Generate invoice as pharmacist
3. Verify invoice amount

**Expected Results:**
- ✅ NHIA badge visible on prescription detail
- ✅ Invoice amount = 10% of total (₦1,000)
- ✅ Availability page shows NHIA status
- ✅ Success message mentions NHIA discount

**Verification:**
```python
prescription = Prescription.objects.latest('id')
total_cost = prescription.get_total_prescribed_price()
patient_pays = prescription.get_patient_payable_amount()
print(f"Total Cost: ₦{total_cost}")
print(f"Patient Pays (10%): ₦{patient_pays}")
print(f"NHIA Covers (90%): ₦{total_cost - patient_pays}")
```

### Test Case 5: Payment Processing and Receipt Generation
**Objective:** Process payment and generate receipt

**Steps:**
1. Open prescription with generated invoice
2. Click "Billing Office Payment"
3. Enter payment details:
   - Amount: Full invoice amount
   - Method: Cash
   - Transaction ID: TEST-001
4. Submit payment
5. Go to payment history
6. Click "Receipt" button

**Expected Results:**
- ✅ Payment recorded successfully
- ✅ Invoice status updated to "Paid"
- ✅ Receipt button appears in payment history
- ✅ Receipt opens in new tab
- ✅ Receipt contains all required information:
  - Hospital details
  - Patient information
  - Service details
  - Payment information
  - Amount breakdown
  - Signature sections
- ✅ Receipt is printable (Ctrl+P works)

### Test Case 6: Partial Payment and Multiple Receipts
**Objective:** Test partial payments and multiple receipts

**Steps:**
1. Create prescription with invoice amount ₦5,000
2. Make first payment of ₦3,000
3. Generate receipt for first payment
4. Make second payment of ₦2,000
5. Generate receipt for second payment

**Expected Results:**
- ✅ First receipt shows ₦3,000 paid, ₦2,000 balance
- ✅ Second receipt shows ₦2,000 paid, ₦0 balance
- ✅ Both receipts available in payment history
- ✅ Each receipt has unique receipt number

### Test Case 7: Laboratory Payment Receipt
**Objective:** Test receipt generation for laboratory payments

**Steps:**
1. Create test request for non-NHIA patient
2. Process payment
3. Generate receipt

**Expected Results:**
- ✅ Receipt shows laboratory service type
- ✅ Receipt number format: LAB-{payment_id}
- ✅ Test details included
- ✅ Receipt printable

### Test Case 8: Consultation Payment Receipt
**Objective:** Test receipt generation for consultation payments

**Steps:**
1. Create consultation
2. Process payment
3. Generate receipt

**Expected Results:**
- ✅ Receipt shows consultation service type
- ✅ Receipt number format: CONS-{payment_id}
- ✅ Doctor information included
- ✅ Receipt printable

### Test Case 9: Admission Payment Receipt
**Objective:** Test receipt generation for admission payments

**Steps:**
1. Create admission for non-NHIA patient
2. Process payment
3. Generate receipt

**Expected Results:**
- ✅ Receipt shows admission service type
- ✅ Receipt number format: ADM-{payment_id}
- ✅ Ward information included
- ✅ Receipt printable

### Test Case 10: Wallet Payment with Receipt
**Objective:** Test wallet payment and receipt generation

**Steps:**
1. Ensure patient has sufficient wallet balance
2. Process payment from wallet
3. Generate receipt

**Expected Results:**
- ✅ Payment method shows "Wallet"
- ✅ Wallet balance deducted
- ✅ Receipt generated correctly
- ✅ Receipt shows wallet payment method

## Browser Testing

Test in multiple browsers:
- ✅ Chrome
- ✅ Firefox
- ✅ Edge
- ✅ Safari (if available)

## Print Testing

Test printing:
1. Open receipt
2. Click Print button
3. Verify print preview shows:
   - ✅ Proper formatting
   - ✅ No cut-off content
   - ✅ Print button hidden
   - ✅ Signature sections visible
   - ✅ Hospital branding visible

## Mobile Testing

Test on mobile devices:
- ✅ Receipt displays correctly
- ✅ All information readable
- ✅ Print option available

## Performance Testing

Test with:
- ✅ Large prescription (10+ medications)
- ✅ Multiple dispensaries (5+)
- ✅ Large inventory (1000+ items)
- ✅ Multiple payments (10+)

## Error Handling Testing

### Test Error Scenarios:
1. **No Dispensary Selected**
   - Try to generate invoice without selecting dispensary
   - Expected: Error message displayed

2. **All Medications Unavailable**
   - Try to generate invoice when no medications available
   - Expected: Error message, invoice not created

3. **Invoice Already Exists**
   - Try to generate invoice twice
   - Expected: Warning message, redirect to existing invoice

4. **Invalid Payment Amount**
   - Try to pay more than invoice amount
   - Expected: Validation error

5. **Negative Payment Amount**
   - Try to enter negative amount
   - Expected: Validation error

## Regression Testing

Verify existing functionalities still work:
- ✅ Prescription creation
- ✅ Medication dispensing
- ✅ Inventory management
- ✅ Stock transfers
- ✅ Purchase orders
- ✅ Patient wallet operations
- ✅ NHIA authorization workflow

## Security Testing

Test access controls:
- ✅ Only authorized users can generate invoices
- ✅ Only authorized users can process payments
- ✅ Receipts accessible only to authorized users
- ✅ Audit logs created for all actions

## Reporting Issues

If you find issues, report with:
1. Test case number
2. Steps to reproduce
3. Expected result
4. Actual result
5. Screenshots (if applicable)
6. Browser/device information
7. Error messages (if any)

## Success Criteria

All test cases should pass with:
- ✅ No errors or exceptions
- ✅ Correct calculations
- ✅ Proper data display
- ✅ Functional printing
- ✅ Audit trail created
- ✅ Existing features working

## Post-Testing

After successful testing:
1. Document any issues found
2. Verify fixes for reported issues
3. Conduct user acceptance testing
4. Train staff on new features
5. Monitor system in production
6. Collect user feedback

## Automated Testing (Optional)

Create automated tests:
```python
# tests/test_prescription_invoice.py
from django.test import TestCase
from pharmacy.models import Prescription
from pharmacy.views import pharmacist_generate_invoice

class PrescriptionInvoiceTestCase(TestCase):
    def test_no_auto_invoice_creation(self):
        # Test that invoice is not created automatically
        pass
    
    def test_pharmacist_invoice_generation(self):
        # Test pharmacist invoice generation
        pass
    
    def test_nhia_discount_calculation(self):
        # Test NHIA discount
        pass
```

## Conclusion

Complete all test cases before deploying to production. Document results and any issues found.

