# Wallet Net Impact Implementation Summary

## Overview
This implementation adds functionality to calculate and apply the net impact of outstanding charges on a patient's wallet balance. The system now properly updates the wallet balance based on all outstanding charges from admissions and invoices, and creates appropriate transaction records.

## Changes Made

### 1. Model Changes

#### patients/models.py
- Modified `get_total_wallet_impact_with_admissions` method to:
  - Accept an `update_balance` parameter (default: False)
  - Update the wallet balance when `update_balance=True`
  - Create an 'adjustment' transaction record with proper `balance_after` field
  - Added better error handling and logging

#### inpatient/models.py
- Modified `get_total_wallet_impact` method to:
  - Accept an `update_balance` parameter (default: False)
  - Update the wallet balance when `update_balance=True`
  - Create an 'adjustment' transaction record with proper `balance_after` field
  - Added better error handling and logging

### 2. Template Implementation

#### templates/patients/wallet_net_impact.html
- Created a comprehensive template for analyzing and applying net impact to patient wallets
- Displays current wallet balance, outstanding charges, and projected balance
- Shows detailed breakdown of active admissions and outstanding invoices
- Includes a modal for confirming the application of net impact calculation

#### templates/inpatient/admission_net_impact.html
- Created a template specifically for analyzing admission net impact
- Displays admission details, costs, and wallet impact
- Includes a modal for confirming the application of net impact calculation

#### templates/patients/wallet_dashboard.html
- Added a "Net Impact" button to navigate to the net impact analysis page

#### templates/inpatient/admission_detail.html
- Added an "Analyze Net Impact" button to navigate to the admission net impact analysis page

### 3. View Implementation

#### patients/views.py
- Added `wallet_net_impact` view to display net impact analysis for a patient
- Added `apply_wallet_net_impact` view to apply net impact calculation and update wallet balance
- Both views handle all outstanding charges from admissions and invoices

#### inpatient/views.py
- Added `admission_net_impact` view to display net impact analysis for a specific admission
- Added `apply_admission_net_impact` view to apply admission net impact calculation and update wallet balance

### 4. URL Configuration

#### patients/urls.py
- Added URL patterns for wallet net impact views:
  - `wallet/net-impact/` for analysis view
  - `wallet/apply-net-impact/` for applying the calculation

#### inpatient/urls.py
- Added URL patterns for admission net impact views:
  - `admissions/<int:pk>/net-impact/` for analysis view
  - `admissions/<int:pk>/apply-net-impact/` for applying the calculation

## How It Works

1. **Net Impact Calculation**: The system calculates the net impact by subtracting all outstanding charges from the current wallet balance.
   - `Net Impact = Current Wallet Balance - Total Outstanding Charges`

2. **Balance Update**: When applying the net impact:
   - If net impact is positive, the wallet balance is set to that amount
   - If net impact is negative, the wallet balance is set to 0 (indicating debt)

3. **Transaction Record**: An 'adjustment' transaction is created to record the balance change, including:
   - Transaction type: 'adjustment'
   - Amount: The difference between the old and new balance
   - Balance after: The new wallet balance
   - Description: Details about the net impact calculation

## Testing

A test script (`test_net_impact_wallet_update.py`) was created to verify the functionality:
- Tests that net impact calculations return correct values
- Tests that wallet balances are properly updated when requested
- Tests that transaction records are created when balances change
- Tests that balances remain unchanged when update_balance=False

## Usage

### For Patient Wallet Net Impact:
1. Navigate to a patient's wallet dashboard
2. Click the "Net Impact" button
3. Review the analysis of current balance, outstanding charges, and projected balance
4. Click "Apply Net Impact to Wallet" to update the balance and create a transaction record

### For Admission Net Impact:
1. Navigate to an admission detail page
2. Click the "Analyze Net Impact" button
3. Review the analysis of admission costs and wallet impact
4. Click "Apply Net Impact to Wallet" to update the balance and create a transaction record

## Benefits

1. **Financial Transparency**: Clear visibility into how outstanding charges affect wallet balances
2. **Proper Balance Management**: Ensures wallet balances accurately reflect all outstanding charges
3. **Transaction History**: Creates proper transaction records for all balance adjustments
4. **Flexible Application**: Allows users to analyze impact before applying changes
5. **Comprehensive Coverage**: Handles both admission charges and invoice charges

## Future Enhancements

1. **Batch Processing**: Add functionality to apply net impact calculations for multiple patients at once
2. **Scheduled Updates**: Implement scheduled tasks to automatically update wallet balances
3. **Reporting**: Create reports for wallet balance adjustments and outstanding charges
4. **Notifications**: Add notifications when wallet balances reach certain thresholds