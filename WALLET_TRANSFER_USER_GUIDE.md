# Wallet Fund Transfer - User Guide

## Overview

The Wallet Fund Transfer feature allows hospital staff to securely transfer funds between patient wallets within the HMS system. This feature provides a complete audit trail and ensures all transfers are processed atomically with proper validation.

## Accessing Wallet Transfers

### Navigation Path
1. Go to **Patients** → **Patient List**
2. Select a patient to view their details
3. Click **Wallet Dashboard** 
4. Click **Transfer Funds** button

### Direct URL Access
- URL Pattern: `/patients/<patient_id>/wallet/transfer/`
- Example: `/patients/123/wallet/transfer/`

## How to Perform a Transfer

### Step 1: Access Transfer Form
- Navigate to the patient's wallet dashboard
- Click the **"Transfer Funds"** button
- You'll see the transfer form with sender information displayed

### Step 2: Select Recipient
- Use the **"Transfer To Patient"** dropdown
- Select the patient who will receive the funds
- The system automatically excludes:
  - The current patient (prevents self-transfers)
  - Inactive patients
  - Patients with inactive wallets

### Step 3: Enter Transfer Amount
- Enter the amount to transfer in the **"Amount to Transfer"** field
- The system shows your available balance
- Real-time validation provides immediate feedback:
  - ✅ Green: Sufficient balance
  - ⚠️ Orange: Amount exceeds balance (still allowed)
  - ❌ Red: Invalid amount

### Step 4: Add Description (Optional)
- Provide a reason for the transfer
- This helps with record keeping and audit trails
- Examples: "Payment for services", "Family support", "Billing correction"

### Step 5: Review Transfer Summary
- The system automatically shows a transfer preview
- Verify all details:
  - Sender and recipient names
  - Transfer amount
  - Your balance after transfer
  - Description

### Step 6: Confirm Transfer
- Click **"Transfer Funds"** to process
- The system processes the transfer atomically
- You'll see a success message with:
  - Transfer amount
  - New balance
  - Transaction reference number

## Transfer Validation Rules

### Automatic Validations
- **Positive Amount**: Transfer amount must be greater than zero
- **Valid Recipient**: Cannot transfer to the same patient
- **Active Wallets**: Both sender and recipient wallets must be active
- **Active Patients**: Can only transfer to active patients

### Balance Handling
- The system allows transfers even if they exceed the current balance
- Wallets can have negative balances
- Warning messages are shown for transfers exceeding balance
- This flexibility accommodates various hospital billing scenarios

## Transfer Features

### Real-Time Validation
- **Live Balance Calculation**: See your balance after transfer as you type
- **Recipient Validation**: Immediate feedback on recipient selection
- **Amount Validation**: Real-time validation of transfer amounts
- **Form State Management**: Transfer button enables/disables based on form validity

### Transfer Preview
- **Summary Display**: Complete transfer summary before confirmation
- **Balance Impact**: Shows sender's balance before and after transfer
- **Recipient Information**: Clear display of who will receive the funds
- **Description Preview**: Shows the transfer description that will be recorded

### Security Features
- **User Authentication**: All transfers require valid user login
- **Audit Logging**: Complete audit trail for all transfer operations
- **Transaction Linking**: Sender and recipient transactions are properly linked
- **Reference Numbers**: Unique reference numbers for each transaction

## Understanding Transfer Records

### Transaction Types
- **Transfer Out**: Appears in sender's transaction history
- **Transfer In**: Appears in recipient's transaction history
- Both transactions are linked and reference each other

### Transaction Information
Each transfer creates two transaction records:

**Sender Transaction:**
- Type: "Transfer Out"
- Amount: Debit amount
- Description: "Transfer to [Recipient Name] - [Your Description]"
- Reference: Unique transaction reference number

**Recipient Transaction:**
- Type: "Transfer In" 
- Amount: Credit amount
- Description: "Transfer from [Sender Name] - [Your Description]"
- Reference: Unique transaction reference number

### Viewing Transfer History
- Go to **Wallet Dashboard** → **View Transactions**
- Filter by transaction type: "Transfer In" or "Transfer Out"
- Search by description or reference number
- Export transaction history for reporting

## Error Handling

### Common Error Messages

**"Cannot transfer funds to the same patient"**
- You selected the same patient as sender and recipient
- Solution: Select a different recipient patient

**"Cannot transfer to an inactive patient"**
- The selected recipient patient is not active
- Solution: Contact administrator to activate the patient

**"Recipient's wallet is not active"**
- The recipient's wallet has been deactivated
- Solution: Contact administrator to activate the recipient's wallet

**"Transfer amount must be greater than zero"**
- You entered zero or negative amount
- Solution: Enter a positive transfer amount

**"Please select a recipient patient"**
- No recipient was selected
- Solution: Choose a recipient from the dropdown

### System Error Recovery
- If a transfer fails, the system automatically rolls back any partial changes
- No partial transfers are possible - transfers are atomic
- Error messages provide clear guidance on how to resolve issues
- Contact system administrator for persistent errors

## Best Practices

### Before Transferring
1. **Verify Recipient**: Double-check you're transferring to the correct patient
2. **Confirm Amount**: Ensure the transfer amount is correct
3. **Add Description**: Always provide a clear reason for the transfer
4. **Check Balance**: Review the impact on sender's wallet balance

### After Transferring
1. **Save Reference**: Note the transaction reference number for records
2. **Verify Completion**: Check both sender and recipient transaction histories
3. **Update Records**: Update any external records or documentation
4. **Inform Parties**: Notify relevant parties about the transfer if needed

### Record Keeping
- Always include meaningful descriptions for transfers
- Keep transaction reference numbers for audit purposes
- Regularly review transfer history for accuracy
- Report any discrepancies immediately

## Troubleshooting

### Transfer Button Disabled
**Possible Causes:**
- No recipient selected
- Invalid transfer amount
- Form validation errors

**Solutions:**
- Select a valid recipient patient
- Enter a positive transfer amount
- Check for and resolve any form validation errors

### Transfer Not Appearing
**Possible Causes:**
- Transfer failed due to system error
- Looking in wrong patient's wallet
- Transaction history not refreshed

**Solutions:**
- Check for error messages after transfer attempt
- Verify you're looking at the correct patient's wallet
- Refresh the transaction history page
- Contact administrator if transfer is missing

### Balance Discrepancies
**Possible Causes:**
- Multiple concurrent transfers
- System synchronization issues
- Calculation errors

**Solutions:**
- Refresh wallet dashboard to get latest balance
- Review complete transaction history
- Contact administrator for balance reconciliation

## Support and Contact

### For Technical Issues
- Contact: System Administrator
- Include: Patient IDs, transfer amounts, error messages, timestamps

### For Training
- Request wallet transfer training from your supervisor
- Practice with test patients in training environment
- Review this guide regularly for updates

### For Audit Inquiries
- All transfers are logged with complete audit trails
- Transaction references can be used for tracking
- Contact administrator for detailed audit reports

## System Requirements

### User Permissions
- Must be logged in as authorized hospital staff
- Requires wallet management permissions
- Patient access permissions for both sender and recipient

### Browser Requirements
- Modern web browser with JavaScript enabled
- Stable internet connection for real-time validation
- Cookies enabled for session management

---

**Last Updated:** [Current Date]  
**Version:** 1.0  
**System:** HMS Wallet Transfer Module