# Wallet Settlement Feature - User Guide

## Overview

The Wallet Settlement feature allows hospital administrators to settle outstanding negative balances in patient wallets by converting them to zero. This is particularly useful when a patient has a negative balance (owing money to the hospital) and you want to clear that debt administratively.

## How It Works

When a patient's wallet has a negative balance, the settlement feature will:

1. Create a credit transaction to offset the negative balance
2. Create a debit transaction to record the settlement
3. Set the wallet balance to zero
4. Maintain a complete audit trail of all transactions

## Accessing the Settlement Feature

### From Wallet Dashboard

1. Navigate to **Patients** → Select a patient
2. Click on **Wallet Dashboard**
3. If the patient has a negative balance, you will see:
   - An alert banner showing the outstanding amount
   - A "Settle Outstanding Balance" button in the Quick Actions section
   - A "Settle Balance" button in the main action buttons (only visible when balance is negative)

### Direct URL Access

- URL Pattern: `/patients/<patient_id>/wallet/settlement/`
- Example: `/patients/123/wallet/settlement/`

## Settlement Process

### Step 1: Review Settlement Details

When you click the settlement button, you'll see:
- Current negative balance amount
- Settlement amount (equal to the absolute value of the negative balance)
- Explanation of what the settlement will do

### Step 2: Confirm Settlement

- Review the settlement details carefully
- Click "Confirm Settlement" to proceed
- Or click "Cancel" to return to the wallet dashboard

### Step 3: Settlement Completion

- The system will process the settlement
- The wallet balance will be set to zero
- Two transactions will be created in the wallet history:
  - A credit adjustment for the offset amount
  - A debit adjustment for the settlement
- A success message will be displayed

## Transaction Records

The settlement process creates two specific transactions:

1. **Credit Adjustment**: 
   - Type: Adjustment
   - Description: "Outstanding balance settlement - Positive balance offset"
   - Amount: Equal to the absolute value of the negative balance

2. **Debit Adjustment**: 
   - Type: Adjustment
   - Description: "Outstanding balance settlement - Outstanding balance settled"
   - Amount: Equal to the absolute value of the negative balance

## Important Notes

- Settlement can only be performed on wallets with negative balances
- The settlement amount is automatically calculated as the absolute value of the negative balance
- Once settled, the wallet balance will be zero
- All settlements are logged and auditable
- Settlement is an administrative action that should be used carefully
- Regular users should not have access to this feature - only administrators

## Error Handling

The system includes proper error handling:
- Prevents settlement of positive or zero balances
- Provides clear error messages for invalid operations
- Maintains data integrity through database transactions
- Logs any errors that occur during the settlement process

## Best Practices

1. **Review Before Settlement**: Always review the patient's transaction history before settling
2. **Document Reason**: Add notes in the patient's medical record explaining why the settlement was necessary
3. **Verify Authorization**: Ensure you have proper authorization before performing settlements
4. **Check for Errors**: Verify that the negative balance was not caused by a system error before settling