# NHIA Authorization Surgery Fee Update

## Summary

Updated the surgery fee logic so that NHIA patients use authorization codes to cover surgery fees (no fee charged to patient), while regular patients continue to pay the full surgery fee.

---

## Changes Made

### **Previous Logic:**
- **NHIA Patients:** Paid 10% of surgery fee
- **Regular Patients:** Paid 100% of surgery fee

### **New Logic:**
- **NHIA Patients:** Pay ₦0.00 for surgery (covered by authorization code)
- **Regular Patients:** Pay 100% of surgery fee

---

## Implementation Details

### **File Modified:** `theatre/views.py`

**Updated Code (lines 296-359):**

```python
# Get surgery fee from surgery type
surgery_fee = Decimal(str(self.object.surgery_type.fee))

# NHIA patients use authorization code (no fee charged to patient)
# Regular patients pay full surgery fee
if self.object.patient.patient_type == 'nhia':
    # NHIA patients: Surgery covered by authorization, no fee charged
    patient_payable_fee = Decimal('0.00')
    invoice_description = f"Theatre Procedure: {self.object.surgery_type.name} (NHIA Covered)"
else:
    # Regular patients: Pay full surgery fee
    patient_payable_fee = surgery_fee
    invoice_description = f"Theatre Procedure: {self.object.surgery_type.name}"
```

---

## Medical Pack Costs

**Important:** Medical pack costs remain unchanged:
- **NHIA Patients:** Still pay 10% of pack costs
- **Regular Patients:** Pay 100% of pack costs

**Rationale:** Medical packs are consumables that may not be fully covered by NHIA authorization. The 10% co-payment ensures patients contribute to consumable costs.

---

## Complete Billing Examples

### **Example 1: Regular Patient - Appendectomy**

**Surgery Details:**
- Surgery Type: Appendectomy
- Surgery Fee: ₦80,000.00
- Medical Pack: Appendectomy Surgery Pack (₦3,957.00)

**Invoice Breakdown:**
- Surgery Fee: ₦80,000.00
- Medical Pack: ₦3,957.00
- **Total: ₦83,957.00**

---

### **Example 2: NHIA Patient - Appendectomy (With Authorization)**

**Surgery Details:**
- Surgery Type: Appendectomy
- Surgery Fee: ₦80,000.00 (covered by NHIA)
- Medical Pack: Appendectomy Surgery Pack (₦3,957.00)
- Authorization Code: Provided

**Invoice Breakdown:**
- Surgery Fee: ₦0.00 (NHIA Covered)
- Medical Pack: ₦395.70 (10% of ₦3,957.00)
- **Total: ₦395.70**
- **Status: Paid** (via authorization code)

---

### **Example 3: NHIA Patient - Appendectomy (Without Authorization)**

**Surgery Details:**
- Surgery Type: Appendectomy
- Surgery Fee: ₦80,000.00 (should be covered by NHIA)
- Medical Pack: Appendectomy Surgery Pack (₦3,957.00)
- Authorization Code: Not provided yet

**Invoice Breakdown:**
- Surgery Fee: ₦0.00 (NHIA Covered - pending authorization)
- Medical Pack: ₦395.70 (10% of ₦3,957.00)
- **Total: ₦395.70**
- **Status: Pending** (awaiting authorization code)

---

### **Example 4: NHIA Patient - Cesarean Section (With Authorization)**

**Surgery Details:**
- Surgery Type: Cesarean Section
- Surgery Fee: ₦120,000.00 (covered by NHIA)
- Medical Pack: Cesarean Section Surgery Pack (₦6,449.00)
- Authorization Code: Provided

**Invoice Breakdown:**
- Surgery Fee: ₦0.00 (NHIA Covered)
- Medical Pack: ₦644.90 (10% of ₦6,449.00)
- **Total: ₦644.90**
- **Status: Paid** (via authorization code)

---

## Authorization Code Workflow

### **For NHIA Patients:**

1. **Surgery Creation:**
   - User creates surgery for NHIA patient
   - System sets surgery fee to ₦0.00
   - Invoice created with status "pending"

2. **Authorization Code Entry:**
   - User enters NHIA authorization code
   - System validates authorization code
   - Invoice status changed to "paid"
   - Authorization code marked as used

3. **Medical Pack Orders:**
   - User orders medical packs
   - System calculates 10% of pack cost
   - Pack cost added to invoice

4. **Final Payment:**
   - Patient pays only for medical pack costs (10%)
   - Surgery fee covered by NHIA authorization

---

## Invoice Status Logic

### **NHIA Patients:**

| Authorization Code | Surgery Fee | Invoice Status | Patient Pays |
|-------------------|-------------|----------------|--------------|
| Provided | ₦0.00 | Paid | Pack costs only (10%) |
| Not Provided | ₦0.00 | Pending | Pack costs only (10%) |

### **Regular Patients:**

| Payment Status | Surgery Fee | Invoice Status | Patient Pays |
|---------------|-------------|----------------|--------------|
| Paid | Full amount | Paid | Surgery fee + Pack costs (100%) |
| Not Paid | Full amount | Pending | Surgery fee + Pack costs (100%) |

---

## Benefits of New Logic

✅ **NHIA Compliance:** Surgery fees fully covered by authorization  
✅ **Clear Separation:** Surgery fees vs. consumable costs  
✅ **Transparent Billing:** Patients see exactly what they pay  
✅ **Authorization Tracking:** Full audit trail of NHIA coverage  
✅ **Flexible Pack Costs:** 10% co-payment for consumables  
✅ **Regular Patient Unchanged:** No impact on non-NHIA patients  

---

## Key Differences

### **Surgery Fee:**
- **Before:** NHIA patients paid 10% of surgery fee
- **After:** NHIA patients pay ₦0.00 (covered by authorization)

### **Medical Pack Costs:**
- **Before:** NHIA patients paid 10% of pack costs
- **After:** NHIA patients still pay 10% of pack costs (unchanged)

---

## Testing Checklist

- [ ] Create surgery for NHIA patient with authorization code
  - Verify surgery fee = ₦0.00
  - Verify invoice status = "paid"
  - Verify authorization code marked as used

- [ ] Create surgery for NHIA patient without authorization code
  - Verify surgery fee = ₦0.00
  - Verify invoice status = "pending"

- [ ] Order medical pack for NHIA patient surgery
  - Verify pack cost = 10% of total pack value
  - Verify pack cost added to invoice

- [ ] Create surgery for regular patient
  - Verify surgery fee = full amount
  - Verify invoice status = "pending"

- [ ] Order medical pack for regular patient surgery
  - Verify pack cost = 100% of total pack value
  - Verify pack cost added to invoice

---

## Files Modified

1. **theatre/views.py** - Updated surgery invoice creation logic (lines 296-359)

---

## Files Created

1. **NHIA_AUTHORIZATION_SURGERY_FEE_UPDATE.md** - This documentation

---

## Migration Required

**No migration required** - This is a logic change only, no database schema changes.

---

## Next Steps

1. ✅ Surgery fee logic updated for NHIA patients
2. ✅ Authorization code workflow maintained
3. ✅ Medical pack costs unchanged (10% for NHIA)
4. ✅ Regular patient logic unchanged

### **Optional Enhancements:**

- Add authorization code validation before surgery
- Send alerts when authorization code is missing
- Generate reports on NHIA-covered surgeries
- Track authorization code usage statistics
- Add authorization code expiry checks

---

🎉 **NHIA authorization surgery fee logic is now active!**

**Summary:**
- NHIA patients: ₦0.00 surgery fee (authorization covers it)
- Regular patients: Full surgery fee (unchanged)
- Medical packs: 10% for NHIA, 100% for regular (unchanged)

