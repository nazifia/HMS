# Wallet Fund Transfer - Technical Documentation

## Architecture Overview

The Wallet Fund Transfer system is built on top of the existing HMS wallet infrastructure, providing secure, atomic transfers between patient wallets with comprehensive audit trails.

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Transfer Form  │───▶│  Transfer View  │───▶│ Transfer Model  │
│   (Frontend)    │    │   (Controller)  │    │   (Backend)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Validation    │    │  Error Handling │    │ Audit Logging   │
│   (Real-time)   │    │   (Rollback)    │    │  (Tracking)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Database Schema

### Enhanced PatientWallet Model

```python
class PatientWallet(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Enhanced Methods
    def transfer_to(self, recipient_wallet, amount, description, user):
        """Atomic transfer with transaction linking"""
    
    def get_total_transfers_in(self):
        """Get total received via transfers"""
    
    def get_total_transfers_out(self):
        """Get total sent via transfers"""
```

### WalletTransaction Model

```python
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        # ... other types
    )
    
    wallet = models.ForeignKey(PatientWallet, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_number = models.CharField(max_length=50, unique=True)
    
    # Transfer Linking Fields
    transfer_to_wallet = models.ForeignKey(PatientWallet, related_name='incoming_transfers')
    transfer_from_wallet = models.ForeignKey(PatientWallet, related_name='outgoing_transfers')
    
    created_by = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
```

## API Endpoints

### Transfer Endpoint
- **URL**: `/patients/<int:patient_id>/wallet/transfer/`
- **Methods**: `GET`, `POST`
- **Authentication**: Required (login_required decorator)
- **Permissions**: Wallet management permissions

#### GET Request
Returns transfer form with:
- Sender wallet information
- Available recipient patients (filtered)
- Form validation rules

#### POST Request
Processes transfer with:
- Form validation
- Atomic transaction processing
- Audit logging
- Success/error response

### Request/Response Examples

**POST Request:**
```json
{
    "recipient_patient": "456",
    "amount": "100.00",
    "description": "Payment for services"
}
```

**Success Response:**
```json
{
    "status": "success",
    "message": "Successfully transferred ₦100.00 to John Doe",
    "transaction_reference": "TXN20240116123456ABCD1234",
    "new_balance": "450.00"
}
```

**Error Response:**
```json
{
    "status": "error",
    "message": "Cannot transfer to inactive patient",
    "errors": {
        "recipient_patient": ["Cannot transfer to an inactive patient"]
    }
}
```

## Transfer Processing Flow

### 1. Form Validation
```python
def clean_recipient_patient(self):
    recipient = self.cleaned_data.get('recipient_patient')
    
    if not recipient:
        raise ValidationError("Please select a recipient patient.")
    
    if not recipient.is_active:
        raise ValidationError("Cannot transfer to an inactive patient.")
    
    if self.wallet and recipient.id == self.wallet.patient.id:
        raise ValidationError("Cannot transfer to the same patient.")
    
    return recipient
```

### 2. Atomic Transfer Processing
```python
@transaction.atomic
def transfer_to(self, recipient_wallet, amount, description, user):
    # Validate transfer
    if amount <= 0:
        raise ValueError("Transfer amount must be positive.")
    
    if recipient_wallet == self:
        raise ValueError("Cannot transfer to the same wallet.")
    
    # Process transfer
    self.debit(amount, f'Transfer to {recipient_wallet.patient.get_full_name()}', 'transfer_out', user)
    recipient_wallet.credit(amount, f'Transfer from {self.patient.get_full_name()}', 'transfer_in', user)
    
    # Link transactions
    sender_txn = self.transactions.filter(transaction_type='transfer_out').latest('created_at')
    recipient_txn = recipient_wallet.transactions.filter(transaction_type='transfer_in').latest('created_at')
    
    sender_txn.transfer_to_wallet = recipient_wallet
    recipient_txn.transfer_from_wallet = self
    
    sender_txn.save()
    recipient_txn.save()
    
    return sender_txn, recipient_txn
```

### 3. Error Handling
```python
try:
    sender_transaction, recipient_transaction = wallet.transfer_to(
        recipient_wallet=recipient_wallet,
        amount=amount,
        description=description,
        user=request.user
    )
    # Success handling
except ValueError as e:
    # Validation errors
    messages.error(request, f'Transfer failed: {str(e)}')
except Exception as e:
    # System errors
    messages.error(request, 'An unexpected error occurred')
    logger.error(f"Transfer error: {str(e)}", exc_info=True)
```

## Frontend Implementation

### Real-Time Validation JavaScript

```javascript
function updateTransferSummary() {
    const amount = parseFloat(amountInput.value) || 0;
    const recipientOption = recipientSelect.options[recipientSelect.selectedIndex];
    const recipientName = recipientOption.text;
    const description = descriptionInput.value || '-';
    
    if (amount > 0 && recipientSelect.value) {
        // Show transfer summary
        transferSummary.style.display = 'block';
        
        // Update summary values
        document.getElementById('balance-after').textContent = `₦${(availableBalance - amount).toFixed(2)}`;
        document.getElementById('recipient-name').textContent = recipientName;
        document.getElementById('transfer-amount').textContent = `₦${amount.toFixed(2)}`;
        document.getElementById('transfer-description').textContent = description;
        
        // Update button state
        if (amount > availableBalance) {
            transferBtn.className = 'btn btn-warning';
            transferBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Transfer (Exceeds Balance)';
        } else {
            transferBtn.className = 'btn btn-info';
            transferBtn.innerHTML = '<i class="fas fa-exchange-alt"></i> Transfer Funds';
        }
        transferBtn.disabled = false;
    } else {
        transferSummary.style.display = 'none';
        transferBtn.disabled = true;
    }
}
```

### Form Enhancement Features

1. **Real-time Balance Calculation**
   - Updates as user types amount
   - Shows balance after transfer
   - Provides visual feedback

2. **Recipient Validation**
   - Filters out invalid recipients
   - Shows patient names with IDs
   - Prevents self-selection

3. **Transfer Preview**
   - Shows complete transfer summary
   - Updates dynamically
   - Confirms all details before submission

## Security Implementation

### Authentication & Authorization
```python
@login_required
def wallet_transfer(request, patient_id):
    # User must be authenticated
    # Additional permission checks can be added here
```

### Input Validation
- Server-side validation for all inputs
- Client-side validation for user experience
- SQL injection prevention through ORM
- XSS prevention through template escaping

### Audit Trail
```python
log_audit_action(
    request.user, 
    'wallet_transfer', 
    wallet, 
    f"Transferred ₦{amount:,.2f} from {patient.get_full_name()} "
    f"to {recipient_patient.get_full_name()}. "
    f"Transaction refs: {sender_transaction.reference_number}"
)
```

## Performance Considerations

### Database Optimization
- Indexed foreign keys for fast lookups
- Efficient queries with select_related/prefetch_related
- Transaction batching for atomic operations

### Caching Strategy
- Patient data caching for recipient selection
- Wallet balance caching (with invalidation)
- Form option caching for better UX

### Query Optimization
```python
# Efficient recipient query
recipients = Patient.objects.filter(
    is_active=True
).exclude(
    id=wallet.patient.id
).select_related('wallet').order_by('first_name', 'last_name')
```

## Testing Strategy

### Unit Tests
```python
class WalletTransferTestCase(TestCase):
    def test_successful_transfer(self):
        # Test successful transfer between wallets
        
    def test_insufficient_balance_warning(self):
        # Test transfer with insufficient balance (allowed)
        
    def test_self_transfer_prevention(self):
        # Test prevention of self-transfers
        
    def test_inactive_recipient_validation(self):
        # Test validation of inactive recipients
```

### Integration Tests
```python
class WalletTransferIntegrationTestCase(TestCase):
    def test_transfer_form_submission(self):
        # Test complete form submission workflow
        
    def test_transaction_linking(self):
        # Test proper transaction relationship creation
        
    def test_audit_logging(self):
        # Test audit trail generation
```

### Performance Tests
- Load testing with concurrent transfers
- Database performance under high transaction volume
- Memory usage monitoring during transfers

## Deployment Considerations

### Database Migrations
```python
# Migration for transfer relationship fields
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='wallettransaction',
            name='transfer_to_wallet',
            field=models.ForeignKey(...)
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='transfer_from_wallet',
            field=models.ForeignKey(...)
        ),
    ]
```

### Configuration Settings
```python
# settings.py
WALLET_TRANSFER_SETTINGS = {
    'MAX_TRANSFER_AMOUNT': Decimal('10000.00'),
    'ALLOW_NEGATIVE_BALANCE': True,
    'REQUIRE_TRANSFER_DESCRIPTION': False,
    'AUDIT_TRANSFER_OPERATIONS': True,
}
```

### Monitoring & Logging
- Transfer operation logging
- Error rate monitoring
- Performance metrics tracking
- Audit trail integrity checks

## Troubleshooting Guide

### Common Issues

**Transfer Button Not Enabling**
- Check JavaScript console for errors
- Verify form validation logic
- Ensure all required fields are filled

**Transaction Not Linking**
- Check database transaction isolation
- Verify foreign key relationships
- Review atomic transaction implementation

**Balance Discrepancies**
- Check for concurrent modification issues
- Verify decimal precision settings
- Review transaction ordering

### Debug Tools
```python
# Debug transfer processing
import logging
logger = logging.getLogger('wallet_transfer')

def debug_transfer(sender_wallet, recipient_wallet, amount):
    logger.debug(f"Transfer: {sender_wallet.patient} -> {recipient_wallet.patient}, Amount: {amount}")
    logger.debug(f"Sender balance before: {sender_wallet.balance}")
    logger.debug(f"Recipient balance before: {recipient_wallet.balance}")
```

## Future Enhancements

### Planned Features
1. **Transfer Limits**: Daily/monthly transfer limits
2. **Approval Workflow**: Multi-step approval for large transfers
3. **Batch Transfers**: Transfer to multiple recipients
4. **Scheduled Transfers**: Recurring transfer scheduling
5. **Mobile API**: REST API for mobile applications

### Performance Improvements
1. **Async Processing**: Background transfer processing
2. **Caching Layer**: Redis caching for better performance
3. **Database Sharding**: Horizontal scaling for high volume

### Security Enhancements
1. **Two-Factor Authentication**: Additional security for transfers
2. **Transfer Encryption**: End-to-end encryption for sensitive data
3. **Fraud Detection**: Automated suspicious activity detection

---

**Last Updated:** [Current Date]  
**Version:** 1.0  
**Maintainer:** HMS Development Team