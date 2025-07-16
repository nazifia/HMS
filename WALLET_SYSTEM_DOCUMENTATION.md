# Patient Wallet System - Complete Implementation

## Overview
The Patient Wallet System is a comprehensive financial management feature for the HMS (Hospital Management System) that allows patients to maintain a digital wallet for hospital transactions. This system provides full functionality for managing patient financial transactions with complete audit trails.

## Features Implemented

### 1. Core Wallet Functionality
- **Patient Wallet Model**: Each patient can have a digital wallet with balance tracking
- **Transaction History**: Complete audit trail of all wallet transactions
- **Multiple Transaction Types**: Support for credits, debits, deposits, withdrawals, payments, refunds, transfers, and adjustments
- **Real-time Balance Updates**: Automatic balance calculation with transaction recording
- **Security**: All transactions are logged with user attribution and timestamps

### 2. Transaction Types
- **Credit/Deposit**: Add funds to wallet
- **Debit/Payment**: Remove funds for payments
- **Withdrawal**: Cash out funds from wallet
- **Transfer**: Move funds between patient wallets
- **Refund**: Process refunds to patient wallet
- **Adjustment**: Administrative balance corrections

### 3. User Interface Components

#### Wallet Dashboard (`/patients/<id>/wallet/`)
- Current balance display
- Transaction statistics (total credits, debits, monthly activity)
- Recent transaction history
- Quick action buttons
- Patient information summary

#### Transaction Management
- **Add Funds** (`/patients/<id>/wallet/add-funds/`): Deposit money with payment method selection
- **Withdraw Funds** (`/patients/<id>/wallet/withdraw/`): Cash out with withdrawal method options
- **Transfer Funds** (`/patients/<id>/wallet/transfer/`): Transfer between patient wallets
- **Process Refund** (`/patients/<id>/wallet/refund/`): Issue refunds with reason tracking
- **Make Adjustment** (`/patients/<id>/wallet/adjustment/`): Administrative balance corrections

#### Transaction History (`/patients/<id>/wallet/transactions/`)
- Comprehensive transaction listing with pagination
- Advanced search and filtering options
- Export capabilities
- Transaction status tracking

### 4. Integration with Billing System
- **Automatic Wallet Payments**: When payment method is 'wallet', automatically debit patient wallet
- **Invoice Integration**: Link wallet transactions to specific invoices
- **Payment Tracking**: Complete integration with existing payment system

## Technical Implementation

### Models

#### PatientWallet
```python
class PatientWallet(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
```

#### WalletTransaction
```python
class WalletTransaction(models.Model):
    wallet = models.ForeignKey(PatientWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Key Methods

#### Wallet Operations
- `wallet.credit(amount, description="Credit", transaction_type="credit", user=None, invoice=None, payment_instance=None)`: Add funds with transaction logging
- `wallet.debit(amount, description="Debit", transaction_type="debit", user=None, invoice=None, payment_instance=None)`: Remove funds with validation
- `wallet.get_transaction_history(limit)`: Retrieve transaction history
- `wallet.get_total_credits()`: Calculate total credits
- `wallet.get_total_debits()`: Calculate total debits

### Forms
- **AddFundsForm**: Enhanced with payment method and description
- **WalletWithdrawalForm**: Withdrawal with method selection and balance validation
- **WalletTransferForm**: Transfer between patients with recipient selection
- **WalletRefundForm**: Refund processing with reason tracking
- **WalletAdjustmentForm**: Administrative adjustments with type selection
- **WalletTransactionSearchForm**: Advanced search and filtering

### Views
- **wallet_dashboard**: Comprehensive wallet overview
- **wallet_transactions**: Transaction history with search/filter
- **add_funds_to_wallet**: Enhanced fund addition
- **wallet_withdrawal**: Secure fund withdrawal
- **wallet_transfer**: Inter-patient transfers
- **wallet_refund**: Refund processing
- **wallet_adjustment**: Administrative adjustments

## Security Features

### 1. Transaction Validation
- Balance validation before debits
- User authentication for all operations
- Transaction amount validation
- Duplicate transaction prevention

### 2. Audit Trail
- Complete transaction logging
- User attribution for all changes
- Timestamp tracking
- Reference number generation
- Status tracking

### 3. Access Control
- Login required for all wallet operations
- User-specific transaction attribution
- Administrative controls for adjustments

## Usage Instructions

### For Staff/Administrators

#### Adding Funds to Patient Wallet
1. Navigate to patient details page
2. Click "Wallet Dashboard" or "Add Funds"
3. Enter amount and select payment method
4. Add optional description
5. Submit to process transaction

#### Processing Withdrawals
1. Go to patient wallet dashboard
2. Click "Withdraw Funds"
3. Enter amount (validated against balance)
4. Select withdrawal method
5. Add description and submit

#### Making Transfers
1. Access wallet dashboard
2. Click "Transfer Funds"
3. Select recipient patient
4. Enter amount and description
5. Review summary and confirm

#### Processing Refunds
1. Navigate to wallet dashboard
2. Click "Process Refund"
3. Enter refund amount and reason
4. Optionally link to invoice
5. Submit to credit patient wallet

#### Administrative Adjustments
1. Access wallet dashboard
2. Click "Make Adjustment"
3. Select credit or debit adjustment
4. Enter amount and detailed reason
5. Review and confirm adjustment

### For Patients (Future Enhancement)
- View wallet balance and transaction history
- Request withdrawals (subject to approval)
- Receive notifications for transactions

## Integration Points

### 1. Billing System
- Automatic wallet debits for 'wallet' payment method
- Invoice linking for transaction tracking
- Payment method integration

### 2. Patient Management
- Wallet creation on patient registration
- Wallet status in patient details
- Quick access from patient profile

### 3. Reporting System
- Transaction reports by date range
- Patient wallet summaries
- Financial reconciliation reports

## Database Changes
- Added `PatientWallet` model with balance tracking
- Added `WalletTransaction` model for complete audit trail
- Enhanced `Payment` model integration
- Migration: `patients/migrations/0005_patientwallet_wallettransaction.py`

## URL Structure
```
/patients/<id>/wallet/                 # Wallet Dashboard
/patients/<id>/wallet/add-funds/       # Add Funds
/patients/<id>/wallet/transactions/    # Transaction History
/patients/<id>/wallet/withdraw/        # Withdraw Funds
/patients/<id>/wallet/transfer/        # Transfer Funds
/patients/<id>/wallet/refund/          # Process Refund
/patients/<id>/wallet/adjustment/      # Make Adjustment
```

## Templates Created
- `wallet_dashboard.html`: Main wallet interface
- `wallet_transactions.html`: Transaction history with search
- `wallet_withdrawal.html`: Withdrawal form
- `wallet_transfer.html`: Transfer form with validation
- `wallet_refund.html`: Refund processing form
- `wallet_adjustment.html`: Administrative adjustment form
- Enhanced `add_funds_form.html`: Improved fund addition
- Updated `patient_detail.html`: Wallet integration

## Admin Interface
- **PatientWallet Admin**: Manage patient wallets
- **WalletTransaction Admin**: View and manage transactions
- Read-only fields for security
- Search and filter capabilities

## Future Enhancements
1. **Mobile App Integration**: API endpoints for mobile wallet access
2. **Payment Gateway Integration**: Direct online payments to wallet
3. **Automated Notifications**: SMS/Email alerts for transactions
4. **Wallet Limits**: Daily/monthly transaction limits
5. **Multi-currency Support**: Support for different currencies
6. **Wallet Analytics**: Advanced reporting and analytics
7. **Patient Self-Service**: Allow patients to manage their own wallets

## Testing Recommendations
1. Test all transaction types with various amounts
2. Verify balance calculations and validations
3. Test search and filter functionality
4. Verify audit trail completeness
5. Test integration with billing system
6. Validate security and access controls

## Maintenance Notes
- Regular backup of wallet transaction data
- Monitor for unusual transaction patterns
- Periodic reconciliation of wallet balances
- Review and update transaction limits as needed
- Monitor system performance with large transaction volumes

This implementation provides a complete, secure, and user-friendly patient wallet system that integrates seamlessly with the existing HMS infrastructure.
