# Wallet System Review and Required Changes

## Overview
This document provides a comprehensive review of the HMS wallet system and identifies necessary changes based on system requirements.

**Date:** 2025-09-30
**Status:** 🔍 Under Review

---

## Current Implementation Status

### ✅ What's Working

#### 1. **Automatic Admission Fee Deduction**
- **Location:** `inpatient/signals.py` (lines 11-122)
- **Status:** ✅ Implemented and working
- **Features:**
  - Automatically deducts admission fees from patient wallet
  - Creates invoice and marks as paid
  - Creates payment record
  - Allows negative balance
  - Prevents double deduction

#### 2. **NHIA Patient Exemption**
- **Location:** `inpatient/signals.py` (lines 15-27)
- **Status:** ✅ Implemented and working
- **Logic:**
  ```python
  is_nhia_patient = (hasattr(instance.patient, 'nhia_info') and
                     instance.patient.nhia_info and
                     instance.patient.nhia_info.is_active)
  
  if is_nhia_patient:
      logger.info(f'Patient {instance.patient.get_full_name()} is NHIA - no admission fee charged.')
      return
  ```

#### 3. **Wallet Models**
- **PatientWallet:** ✅ Complete with balance tracking
- **WalletTransaction:** ✅ Complete with audit trail
- **Methods:** ✅ credit(), debit(), transfer_to(), settle_outstanding_balance()

#### 4. **Daily Admission Charges**
- **Location:** `inpatient/management/commands/daily_admission_charges.py`
- **Status:** ✅ Implemented and working
- **Features:**
  - Automatic daily charge deduction
  - NHIA exemption
  - Duplicate prevention
  - Links to admission

---

## 🔍 Issues Identified

### Issue 1: Missing Admission Parameter in Signal
**Severity:** ⚠️ Medium
**Location:** `inpatient/signals.py` line 93-99

**Problem:**
The wallet debit call in the admission signal doesn't pass the `admission` parameter, which means the transaction won't be linked to the admission.

**Current Code:**
```python
wallet.debit(
    amount=admission_cost,
    description=f'Admission fee for {instance.patient.get_full_name()} - {instance.bed.ward.name if instance.bed else "General"}',
    transaction_type='admission_fee',
    user=instance.created_by,
    invoice=invoice
    # ❌ Missing: admission=instance
)
```

**Impact:**
- Wallet transactions for admission fees are not linked to admissions
- Harder to track admission-specific charges
- `Admission.get_actual_charges_from_wallet()` may not work correctly

**Fix Required:** Add `admission=instance` parameter

---

### Issue 2: Inconsistent NHIA Check Logic
**Severity:** ⚠️ Medium
**Location:** Multiple files

**Problem:**
Different parts of the codebase use different methods to check if a patient is NHIA:

**Method 1 (inpatient/signals.py):**
```python
is_nhia_patient = (hasattr(instance.patient, 'nhia_info') and
                   instance.patient.nhia_info and
                   instance.patient.nhia_info.is_active)
```

**Method 2 (billing/views.py):**
```python
is_nhia_patient = hasattr(admission.patient, 'nhia_info') and admission.patient.nhia_info.is_active
```

**Method 3 (patients/models.py - should exist):**
```python
# Should have a method like:
def is_nhia_patient(self):
    return hasattr(self, 'nhia_info') and self.nhia_info and self.nhia_info.is_active
```

**Impact:**
- Code duplication
- Potential inconsistencies
- Harder to maintain

**Fix Required:** Create a centralized `is_nhia_patient()` method on Patient model

---

### Issue 3: Duplicate Deduction Prevention Logic
**Severity:** ⚠️ Low
**Location:** `inpatient/signals.py` lines 36-45

**Problem:**
The duplicate prevention check uses string matching which is fragile:

**Current Code:**
```python
existing_admission_fee = WalletTransaction.objects.filter(
    wallet__patient=instance.patient,
    transaction_type='admission_fee',
    description__icontains=f'Admission fee for {instance.patient.get_full_name()}'
).exists()
```

**Issues:**
- Relies on description text matching
- Won't work if description format changes
- Doesn't check for specific admission

**Better Approach:**
```python
existing_admission_fee = WalletTransaction.objects.filter(
    wallet__patient=instance.patient,
    transaction_type='admission_fee',
    admission=instance  # Direct FK check
).exists()
```

**Fix Required:** Use admission FK for duplicate detection

---

### Issue 4: Missing Error Handling in Wallet Operations
**Severity:** ⚠️ Medium
**Location:** Various wallet operation views

**Problem:**
Some wallet operations don't have proper error handling for edge cases:
- What if wallet.debit() raises an exception?
- What if balance calculation fails?
- What if transaction creation fails?

**Example (inpatient/signals.py):**
```python
try:
    # ... admission fee deduction
except Exception as e:
    logger.error(f'Error processing admission invoice and wallet deduction for admission {instance.id}: {str(e)}')
    # Don't raise the exception to avoid breaking the admission creation process
```

**Issue:** Silently swallowing exceptions could hide critical errors

**Fix Required:** Better error handling and user notification

---

### Issue 5: No Wallet Balance Validation Before Admission
**Severity:** ℹ️ Low (by design - negative balance allowed)
**Location:** Admission creation flow

**Current Behavior:**
- Admission is created regardless of wallet balance
- Wallet can go negative
- No warning to user about negative balance

**Question:** Should we:
1. Keep current behavior (allow negative balance)?
2. Warn user if balance will go negative?
3. Require minimum balance for admission?

**Recommendation:** Add a warning message when wallet will go negative

---

### Issue 6: Missing Wallet Transaction Types
**Severity:** ℹ️ Low
**Location:** `patients/models.py` - WalletTransaction model

**Current Transaction Types:**
Based on codebase search, we have:
- `admission_fee`
- `daily_admission_charge`
- `admission_payment`
- `pharmacy_payment`
- `credit`
- `debit`
- `transfer_in`
- `transfer_out`

**Missing/Unclear:**
- Are all transaction types defined in TRANSACTION_TYPES choices?
- Is there a complete list?

**Fix Required:** Verify and document all transaction types

---

## 🔧 Required Changes

### Change 1: Add Admission Parameter to Signal
**Priority:** High
**File:** `inpatient/signals.py`
**Lines:** 93-99

**Change:**
```python
# Add admission parameter
wallet.debit(
    amount=admission_cost,
    description=f'Admission fee for {instance.patient.get_full_name()} - {instance.bed.ward.name if instance.bed else "General"}',
    transaction_type='admission_fee',
    user=instance.created_by,
    invoice=invoice,
    admission=instance  # ✅ ADD THIS
)
```

---

### Change 2: Add is_nhia_patient() Method to Patient Model
**Priority:** Medium
**File:** `patients/models.py`
**Location:** Patient model

**Add Method:**
```python
def is_nhia_patient(self):
    """Check if patient is an active NHIA patient"""
    try:
        return (hasattr(self, 'nhia_info') and 
                self.nhia_info is not None and 
                self.nhia_info.is_active)
    except:
        return False
```

**Then Update All NHIA Checks:**
```python
# Before:
is_nhia_patient = (hasattr(instance.patient, 'nhia_info') and
                   instance.patient.nhia_info and
                   instance.patient.nhia_info.is_active)

# After:
is_nhia_patient = instance.patient.is_nhia_patient()
```

---

### Change 3: Improve Duplicate Detection
**Priority:** Medium
**File:** `inpatient/signals.py`
**Lines:** 36-45

**Change:**
```python
# Before:
existing_admission_fee = WalletTransaction.objects.filter(
    wallet__patient=instance.patient,
    transaction_type='admission_fee',
    description__icontains=f'Admission fee for {instance.patient.get_full_name()}'
).exists()

# After:
existing_admission_fee = WalletTransaction.objects.filter(
    wallet__patient=instance.patient,
    transaction_type='admission_fee',
    admission=instance  # Use FK relationship
).exists()
```

---

### Change 4: Add Negative Balance Warning
**Priority:** Low
**File:** `inpatient/views.py` or admission creation view
**Location:** After admission creation

**Add Warning:**
```python
# After wallet deduction
if wallet.balance < 0:
    messages.warning(
        request,
        f'Patient wallet balance is now negative: ₦{wallet.balance:.2f}. '
        f'Please advise patient to top up their wallet.'
    )
```

---

### Change 5: Improve Error Handling
**Priority:** Medium
**File:** `inpatient/signals.py`
**Lines:** 120-122

**Change:**
```python
# Before:
except Exception as e:
    logger.error(f'Error processing admission invoice and wallet deduction for admission {instance.id}: {str(e)}')
    # Don't raise the exception to avoid breaking the admission creation process

# After:
except ValueError as e:
    # Validation errors - log but don't break admission
    logger.warning(f'Validation error in wallet deduction for admission {instance.id}: {str(e)}')
except Exception as e:
    # Unexpected errors - log with full traceback
    logger.error(f'Unexpected error processing admission invoice and wallet deduction for admission {instance.id}: {str(e)}', exc_info=True)
    # Consider notifying admins for critical errors
```

---

## 📊 Testing Checklist

### Test 1: NHIA Patient Admission
- [ ] Create admission for NHIA patient
- [ ] Verify NO wallet deduction
- [ ] Verify NO invoice created
- [ ] Check logs for NHIA exemption message

### Test 2: Regular Patient Admission
- [ ] Create admission for regular patient
- [ ] Verify wallet deduction occurs
- [ ] Verify invoice created and marked paid
- [ ] Verify payment record created
- [ ] Check wallet transaction has admission link

### Test 3: Negative Balance
- [ ] Create admission for patient with zero balance
- [ ] Verify wallet goes negative
- [ ] Verify warning message displayed (after fix)
- [ ] Verify admission still created

### Test 4: Duplicate Prevention
- [ ] Try to create duplicate admission fee transaction
- [ ] Verify duplicate is prevented
- [ ] Check logs for skip message

### Test 5: Daily Charges
- [ ] Run daily_admission_charges command
- [ ] Verify NHIA patients skipped
- [ ] Verify regular patients charged
- [ ] Verify transactions linked to admissions

---

## 📝 Summary of Required Changes

| # | Change | Priority | File | Status |
|---|--------|----------|------|--------|
| 1 | Add admission parameter to wallet.debit() | High | inpatient/signals.py | ⏳ Pending |
| 2 | Add is_nhia_patient() method | Medium | patients/models.py | ⏳ Pending |
| 3 | Update all NHIA checks to use new method | Medium | Multiple files | ⏳ Pending |
| 4 | Improve duplicate detection | Medium | inpatient/signals.py | ⏳ Pending |
| 5 | Add negative balance warning | Low | inpatient/views.py | ⏳ Pending |
| 6 | Improve error handling | Medium | inpatient/signals.py | ⏳ Pending |

---

## 🎯 Recommendations

### Immediate Actions (High Priority)
1. ✅ Add `admission=instance` parameter to wallet debit in signal
2. ✅ Test admission fee deduction with NHIA and regular patients
3. ✅ Verify wallet transactions are properly linked to admissions

### Short-term Actions (Medium Priority)
1. Add `is_nhia_patient()` method to Patient model
2. Refactor all NHIA checks to use centralized method
3. Improve duplicate detection using FK relationship
4. Enhance error handling with better logging

### Long-term Actions (Low Priority)
1. Add negative balance warnings
2. Create comprehensive wallet system documentation
3. Add wallet balance validation options
4. Implement wallet balance alerts/notifications

---

**Document Version:** 1.0
**Last Updated:** 2025-09-30
**Status:** Ready for Implementation

