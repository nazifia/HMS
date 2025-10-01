# Wallet System: Negative Balance for All Patients

## Overview
This document summarizes the changes made to allow wallet negative balance for **ALL patients** (both NHIA and regular patients).

**Date:** 2025-09-30
**Status:** ✅ Complete

---

## Business Logic Change

### Previous Behavior
- ✅ **Regular Patients:** Wallet deducted automatically (negative balance allowed)
- ❌ **NHIA Patients:** Completely exempt from admission fees and daily charges

### New Behavior
- ✅ **Regular Patients:** Wallet deducted automatically (negative balance allowed)
- ✅ **NHIA Patients:** Wallet deducted automatically (negative balance allowed)

**Key Change:** NHIA patients are **NO LONGER EXEMPT** from admission fees and daily charges. All patients will have their wallets deducted, allowing negative balance if insufficient funds.

---

## Changes Implemented

### 1. ✅ Admission Fee Deduction (Signal)
**File:** `inpatient/signals.py`
**Lines:** 13-17

**Before:**
```python
# Check if patient is NHIA - NHIA patients are exempt from admission fees
if instance.patient.is_nhia_patient():
    logger.info(f'Patient {instance.patient.get_full_name()} is NHIA - no admission fee charged.')
    return

admission_cost = instance.get_total_cost()
```

**After:**
```python
# All patients (NHIA and regular) will have admission fees deducted from wallet
# Wallet can go negative if insufficient balance
admission_cost = instance.get_total_cost()
```

**Impact:**
- ✅ NHIA patients now charged admission fees
- ✅ Wallet can go negative for NHIA patients
- ✅ Invoice created for NHIA patients
- ✅ Payment record created for NHIA patients

---

### 2. ✅ Daily Admission Charges (Management Command)
**File:** `inpatient/management/commands/daily_admission_charges.py`
**Lines:** 180-187

**Before:**
```python
def process_admission_charge(self, admission, charge_date, dry_run=False):
    """
    Process daily charge for a single admission.
    Returns the charge amount if successful, None if skipped.
    """
    # Check if patient is NHIA - NHIA patients are exempt from admission fees
    try:
        is_nhia_patient = (hasattr(admission.patient, 'nhia_info') and
                         admission.patient.nhia_info and
                         admission.patient.nhia_info.is_active)
    except:
        is_nhia_patient = False

    if is_nhia_patient:
        logger.info(f'Patient {admission.patient.get_full_name()} is NHIA - no daily charges applied.')
        return None

    # Check if admission was active on the charge date
```

**After:**
```python
def process_admission_charge(self, admission, charge_date, dry_run=False):
    """
    Process daily charge for a single admission.
    Returns the charge amount if successful, None if skipped.
    All patients (NHIA and regular) will have daily charges deducted.
    Wallet can go negative if insufficient balance.
    """
    # Check if admission was active on the charge date
```

**Impact:**
- ✅ NHIA patients now charged daily admission fees
- ✅ Wallet can go negative for NHIA patients
- ✅ Daily charges applied to all active admissions

---

### 3. ✅ Outstanding Balance Recovery (Management Command)
**File:** `inpatient/management/commands/daily_admission_charges.py`
**Lines:** 269-275

**Before:**
```python
def process_outstanding_balance(self, admission, charge_date, recovery_strategy='balance_aware', ...):
    """
    Process outstanding balance recovery for an admission using wallet-balance-aware strategies.
    Returns the amount recovered.
    """
    # Check if patient is NHIA - NHIA patients are exempt
    try:
        is_nhia_patient = (hasattr(admission.patient, 'nhia_info') and
                         admission.patient.nhia_info and
                         admission.patient.nhia_info.is_active)
    except:
        is_nhia_patient = False

    if is_nhia_patient:
        return Decimal('0.00')

    # Calculate outstanding balance
```

**After:**
```python
def process_outstanding_balance(self, admission, charge_date, recovery_strategy='balance_aware', ...):
    """
    Process outstanding balance recovery for an admission using wallet-balance-aware strategies.
    Returns the amount recovered.
    All patients (NHIA and regular) will have outstanding balances recovered.
    """
    # Calculate outstanding balance
```

**Impact:**
- ✅ NHIA patients now have outstanding balances recovered
- ✅ All recovery strategies apply to NHIA patients
- ✅ Consistent behavior for all patients

---

### 4. ✅ Daily Charge Processing (Tasks)
**File:** `inpatient/tasks.py`
**Lines:** 148-154

**Before:**
```python
def process_admission_charge_internal(admission, charge_date):
    """
    Internal function to process daily charge for a single admission.
    This mirrors the logic from the management command but returns structured data.
    """
    # Check if patient is NHIA - NHIA patients are exempt from admission fees
    if admission.patient.is_nhia_patient():
        return {'success': True, 'amount': None, 'reason': 'NHIA patient - exempt from charges'}
```

**After:**
```python
def process_admission_charge_internal(admission, charge_date):
    """
    Internal function to process daily charge for a single admission.
    This mirrors the logic from the management command but returns structured data.
    All patients (NHIA and regular) will have daily charges deducted.
    Wallet can go negative if insufficient balance.
    """
```

**Impact:**
- ✅ NHIA patients charged in internal task processing
- ✅ Consistent with management command behavior
- ✅ Automated daily charge processing for all patients

---

## Files Modified

| # | File | Lines Changed | Description |
|---|------|---------------|-------------|
| 1 | `inpatient/signals.py` | 13-17 | Removed NHIA exemption from admission fee deduction |
| 2 | `inpatient/management/commands/daily_admission_charges.py` | 180-187 | Removed NHIA exemption from daily charges |
| 3 | `inpatient/management/commands/daily_admission_charges.py` | 269-275 | Removed NHIA exemption from outstanding balance recovery |
| 4 | `inpatient/tasks.py` | 148-154 | Removed NHIA exemption from internal charge processing |

**Total Files Modified:** 3
**Total Changes:** 4

---

## What This Means

### For NHIA Patients
**Before:**
- ❌ No admission fees charged
- ❌ No daily charges applied
- ❌ No outstanding balance recovery
- ❌ No invoices created
- ❌ No wallet deductions

**After:**
- ✅ Admission fees charged on admission
- ✅ Daily charges applied automatically
- ✅ Outstanding balances recovered
- ✅ Invoices created and marked as paid
- ✅ Wallet deducted (can go negative)

### For Regular Patients
**No Change:**
- ✅ Admission fees charged on admission (same as before)
- ✅ Daily charges applied automatically (same as before)
- ✅ Outstanding balances recovered (same as before)
- ✅ Invoices created and marked as paid (same as before)
- ✅ Wallet deducted (can go negative) (same as before)

---

## Wallet Behavior

### Negative Balance Allowed
Both NHIA and regular patients can now have negative wallet balances:

**Example Scenario:**
1. Patient has ₦0 in wallet
2. Admission fee is ₦5,000
3. Wallet is debited ₦5,000
4. **New wallet balance: -₦5,000** ✅ Allowed

### Automatic Deduction Flow

#### On Admission:
1. Patient admitted to ward
2. System calculates admission cost
3. System creates invoice
4. System debits wallet (even if balance is ₦0)
5. Wallet goes negative if insufficient funds
6. Invoice marked as paid
7. Payment record created

#### Daily Charges (12:00 AM):
1. Cron job runs `daily_admission_charges` command
2. System finds all active admissions
3. For each admission:
   - Calculate daily charge
   - Debit wallet (even if balance is negative)
   - Wallet balance decreases further
   - Transaction recorded

#### Outstanding Balance Recovery:
1. Run command with `--recover-outstanding` flag
2. System calculates outstanding balance
3. Apply recovery strategy (balance_aware, gradual, etc.)
4. Debit wallet based on strategy
5. Transaction recorded

---

## Testing Checklist

### ✅ Test 1: NHIA Patient Admission
- [ ] Create admission for NHIA patient with ₦0 wallet balance
- [ ] Verify wallet is debited (goes negative)
- [ ] Verify invoice is created
- [ ] Verify invoice is marked as paid
- [ ] Verify payment record is created
- [ ] Check wallet transaction has admission link

### ✅ Test 2: NHIA Patient Daily Charges
- [ ] Create active admission for NHIA patient
- [ ] Run `python manage.py daily_admission_charges`
- [ ] Verify daily charge is deducted from wallet
- [ ] Verify wallet can go negative
- [ ] Check logs for charge confirmation

### ✅ Test 3: NHIA Patient Outstanding Balance
- [ ] Create admission with outstanding balance for NHIA patient
- [ ] Run `python manage.py daily_admission_charges --recover-outstanding`
- [ ] Verify outstanding balance is recovered
- [ ] Verify wallet is debited
- [ ] Check transaction records

### ✅ Test 4: Regular Patient (No Change)
- [ ] Create admission for regular patient
- [ ] Verify behavior is same as before
- [ ] Verify wallet deduction works
- [ ] Verify daily charges work
- [ ] Verify outstanding recovery works

### ✅ Test 5: Negative Balance Scenarios
- [ ] Test admission with ₦0 balance → goes negative
- [ ] Test admission with ₦1,000 balance, ₦5,000 fee → goes to -₦4,000
- [ ] Test daily charge on already negative balance → goes more negative
- [ ] Verify all transactions are recorded correctly

---

## Important Notes

### 1. **No Balance Validation**
- System does NOT check wallet balance before deduction
- Admissions proceed regardless of wallet balance
- Wallet can go infinitely negative (no limit)

### 2. **Automatic Deduction**
- All deductions are automatic
- No user confirmation required
- Happens in background via signals and cron jobs

### 3. **Invoice Behavior**
- Invoice created for all patients
- Invoice marked as "paid" via wallet deduction
- Payment record created with method="wallet"

### 4. **NHIA Authorization System**
- This change is **separate** from NHIA authorization system
- NHIA patients still need authorization for services outside NHIA units
- Wallet deduction is independent of authorization status

---

## Migration Notes

### No Database Migration Required
- No model changes
- No field additions/removals
- Only business logic changes

### Deployment Steps
1. Deploy code changes
2. Test with sample NHIA patient
3. Monitor logs for any errors
4. Verify wallet transactions are recorded correctly

### Rollback Plan
If needed to rollback:
1. Restore previous version of files
2. NHIA patients will be exempt again
3. No data cleanup required (transactions remain in database)

---

## Recommendations

### 1. **Add Negative Balance Warnings**
Consider adding UI warnings when wallet goes negative:
```python
if wallet.balance < 0:
    messages.warning(
        request,
        f'Patient wallet balance is negative: ₦{wallet.balance:.2f}. '
        f'Please advise patient to top up their wallet.'
    )
```

### 2. **Add Wallet Balance Alerts**
Consider sending notifications when:
- Wallet goes negative
- Wallet balance is below certain threshold
- Outstanding balance exceeds certain amount

### 3. **Add Wallet Top-Up Reminders**
Consider automated reminders for patients with negative balances

### 4. **Add Wallet Balance Dashboard**
Consider creating a dashboard showing:
- Patients with negative balances
- Total outstanding amounts
- Wallet balance trends

---

## Summary

### What Changed
✅ Removed NHIA exemption from admission fees
✅ Removed NHIA exemption from daily charges
✅ Removed NHIA exemption from outstanding balance recovery
✅ All patients now treated equally for wallet deductions

### Impact
- **NHIA Patients:** Now charged for admissions and daily charges
- **Regular Patients:** No change in behavior
- **Wallet System:** Consistent behavior for all patients
- **Negative Balance:** Allowed for all patients

### Benefits
- ✅ Consistent wallet behavior across all patient types
- ✅ Simplified business logic
- ✅ Better financial tracking
- ✅ Complete audit trail for all patients

### Status
**All changes implemented and ready for testing!**

---

**Document Version:** 1.0
**Last Updated:** 2025-09-30
**Status:** Complete

