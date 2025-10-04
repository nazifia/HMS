from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone
from django.conf import settings
import random
import logging
from decimal import Decimal


class Patient(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    )

    MARITAL_STATUS_CHOICES = (
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    )

    PATIENT_TYPE_CHOICES = (
        ('regular', 'Regular'),
        ('nhia', 'NHIA'),
        ('private', 'Private Pay'),
        ('insurance', 'Private Insurance'),
        ('corporate', 'Corporate'),
        ('staff', 'Staff'),
        ('dependant', 'Dependant'),
        ('emergency', 'Emergency'),
    )

    # Basic Information
    first_name = models.CharField(max_length=100)
    patient_type = models.CharField(max_length=15, choices=PATIENT_TYPE_CHOICES, default='regular')
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)

    # Contact Information
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')

    # Medical Information
    registration_date = models.DateTimeField(default=timezone.now)
    patient_id = models.CharField(max_length=20, unique=True)  # Custom patient ID
    allergies = models.TextField(blank=True, null=True)
    chronic_diseases = models.TextField(blank=True, null=True)
    current_medications = models.TextField(blank=True, null=True)
    primary_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_patients', help_text='Primary doctor responsible for this patient')

    # Insurance Information
    insurance_provider = models.CharField(max_length=100, blank=True, null=True)
    insurance_policy_number = models.CharField(max_length=50, blank=True, null=True)
    insurance_expiry_date = models.DateField(blank=True, null=True)

    # Additional Information
    occupation = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # Consolidated profile image field (removed duplicate profile_picture)
    photo = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    id_document = models.FileField(upload_to='id_documents/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate patient ID if not exists
        if not self.patient_id:
            self.patient_id = self._generate_patient_id()

        # Validate required fields
        self.clean()

        super().save(*args, **kwargs)

    def _generate_patient_id(self):
        """Generate a unique patient ID based on patient type"""
        max_attempts = 100  # Prevent infinite loops
        attempts = 0

        while attempts < max_attempts:
            if self.patient_type == 'nhia':
                # NHIA patient ID: 10 digits, starting with 4
                new_id = '4' + ''.join([str(random.randint(0, 9)) for _ in range(9)])
            else:
                # Regular patient ID: 10 digits, starting with 0
                new_id = '0' + ''.join([str(random.randint(0, 9)) for _ in range(9)])

            if not Patient.objects.filter(patient_id=new_id).exists():
                return new_id

            attempts += 1

        # If we can't generate a unique ID after max_attempts, raise an error
        raise ValueError(f"Unable to generate unique patient ID after {max_attempts} attempts")

    def clean(self):
        """Validate model data"""
        from django.core.exceptions import ValidationError

        # Validate date of birth is not in the future
        if self.date_of_birth and self.date_of_birth > timezone.now().date():
            raise ValidationError("Date of birth cannot be in the future")

        # Validate age is reasonable (not over 150 years)
        if self.date_of_birth:
            age = self.get_age()
            if age > 150:
                raise ValidationError("Patient age cannot exceed 150 years")
            if age < 0:
                raise ValidationError("Patient age cannot be negative")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_age(self):
        today = timezone.now().date()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def age(self):
        """Property to easily access patient's age"""
        return self.get_age()

    def get_profile_image(self):
        """
        Get the profile image for the patient.
        Returns the image field object or None if no image is available.
        """
        return self.photo if self.photo else None

    def get_profile_image_url(self):
        """
        Get the URL of the profile image.
        Returns the image URL or None if no image is available.
        """
        return self.photo.url if self.photo else None

    def has_profile_image(self):
        """
        Check if the patient has a profile image available.
        Returns True if photo is available.
        """
        return bool(self.photo)

    def get_patient_type_display(self):
        return dict(self.PATIENT_TYPE_CHOICES).get(self.patient_type, self.patient_type)

    def is_nhia_patient(self):
        """
        Check if patient is an active NHIA patient.
        Returns True if patient has active NHIA information, False otherwise.
        """
        try:
            return (hasattr(self, 'nhia_info') and
                    self.nhia_info is not None and
                    self.nhia_info.is_active)
        except Exception:
            return False

    class Meta:
        db_table = 'patients_patient'
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['-created_at', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['patient_id'], name='idx_patient_id'),
            models.Index(fields=['phone_number'], name='idx_patient_phone'),
            models.Index(fields=['email'], name='idx_patient_email'),
            models.Index(fields=['patient_type'], name='idx_patient_type'),
            models.Index(fields=['is_active'], name='idx_patient_active'),
            models.Index(fields=['created_at'], name='idx_patient_created'),
        ]

class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_histories')
    diagnosis = models.CharField(max_length=200)
    treatment = models.TextField()
    date = models.DateField()
    doctor_name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.diagnosis} ({self.date})"

    class Meta:
        verbose_name_plural = "Medical Histories"
        ordering = ['-date']

class Vitals(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    date_time = models.DateTimeField(default=timezone.now)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in Celsius
    blood_pressure_systolic = models.IntegerField(blank=True, null=True)  # in mmHg
    blood_pressure_diastolic = models.IntegerField(blank=True, null=True)  # in mmHg
    pulse_rate = models.IntegerField(blank=True, null=True)  # in bpm
    respiratory_rate = models.IntegerField(blank=True, null=True)  # in breaths per minute
    oxygen_saturation = models.IntegerField(blank=True, null=True)  # in percentage
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in cm
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in kg
    bmi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.date_time.strftime('%Y-%m-%d %H:%M')}"

    def calculate_bmi(self):
        if self.height and self.weight and self.height > 0:
            height_in_meters = self.height / 100
            bmi = self.weight / (height_in_meters ** 2)
            return round(bmi, 2)
        return None

    def save(self, *args, **kwargs):
        self.bmi = self.calculate_bmi()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Vitals"
        ordering = ['-date_time']

    @classmethod
    def safe_filter(cls, **kwargs):
        """
        Safely filter vitals, handling InvalidOperation errors from decimal fields
        Returns a list of valid vitals, skipping any with invalid decimal data
        """
        logger = logging.getLogger(__name__)
        try:
            # Try normal query first
            return list(cls.objects.filter(**kwargs))
        except Exception as e:
            logger.warning(f"Database error when querying vitals: {e}")

            # Fallback: get IDs first, then filter individually
            try:
                from django.db import connection

                # Build WHERE clause from kwargs
                where_conditions = []
                params = []
                for key, value in kwargs.items():
                    if key.endswith('__order_by'):
                        continue
                    where_conditions.append(f"{key.replace('__', '_')} = %s")
                    params.append(value)

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SELECT id FROM patients_vitals WHERE {where_clause} ORDER BY date_time DESC",
                        params
                    )
                    vital_ids = [row[0] for row in cursor.fetchall()]

                # Get each vital individually, skipping invalid ones
                valid_vitals = []
                for vital_id in vital_ids:
                    try:
                        vital = cls.objects.get(id=vital_id)
                        # Test decimal field access
                        _ = vital.temperature
                        _ = vital.height
                        _ = vital.weight
                        _ = vital.bmi
                        valid_vitals.append(vital)
                    except Exception:
                        logger.warning(f"Skipping vital record {vital_id} due to invalid decimal data")
                        continue

                return valid_vitals
            except Exception as inner_e:
                logger.error(f"Failed to retrieve vitals with fallback method: {inner_e}")
                return []


class PatientWallet(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.patient.get_full_name()} (₦{self.balance})"

    def credit(self, amount, description="Credit", transaction_type="credit", user=None, invoice=None, payment_instance=None, admission=None):
        """Credit amount to wallet and create transaction record"""
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")

        self.balance += amount
        self.save(update_fields=['balance', 'last_updated'])

        # Create transaction record
        transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            created_by=user,
            invoice=invoice,
            payment=payment_instance,
            admission=admission
        )
        
        # Check if this credit settles an outstanding negative balance
        # This would be the case when balance goes from negative to positive or zero
        if self.balance >= 0 and (self.balance - amount) < 0:
            # The balance just crossed from negative to positive/zero
            # We could automatically settle here, but for now we'll just add a notification
            # In a real implementation, you might want to add a setting to control this behavior
            
            # For now, we'll just make sure the transaction is properly recorded
            pass

        return transaction

    def debit(self, amount, description="Debit", transaction_type="debit", user=None, invoice=None, payment_instance=None, admission=None):
        """Debit amount from wallet and create transaction record"""
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")
        # Allow balance to go negative
        # if amount > self.balance:
        #     raise ValueError("Insufficient wallet balance.")

        original_balance = self.balance
        self.balance -= amount
        self.save(update_fields=['balance', 'last_updated'])

        # Create transaction record
        transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            created_by=user,
            invoice=invoice,
            payment=payment_instance,
            admission=admission
        )
        
        # Check if this debit creates a negative balance
        # This would be the case when balance goes from positive to negative
        if self.balance < 0 and original_balance >= 0:
            # The balance just crossed from positive to negative
            # We could send a notification here
            pass

        return transaction

    def settle_outstanding_balance(self, description="Balance settlement", user=None):
        """
        Settle outstanding balance by paying from current wallet balance regardless of status.
        This function will pay outstanding amounts from the current wallet balance,
        whether the wallet is positive or negative.
        
        Returns a dictionary with settlement details.
        """
        # Store original balance for reporting
        original_balance = self.balance
        
        # If wallet has positive balance, we can use it to pay outstanding amounts
        if self.balance > 0:
            # Get all outstanding invoices for this patient
            from billing.models import Invoice
            outstanding_invoices = Invoice.objects.filter(
                patient=self.patient,
                status__in=['pending', 'partially_paid']
            ).order_by('created_at')
            
            total_outstanding = sum(invoice.get_balance() for invoice in outstanding_invoices)
            
            if total_outstanding <= 0:
                return {
                    'settled': False,
                    'message': 'No outstanding invoices to settle',
                    'original_balance': original_balance,
                    'new_balance': self.balance,
                    'amount_settled': 0
                }
            
            # Calculate how much we can pay from current wallet balance
            amount_to_pay = min(self.balance, total_outstanding)
            
            if amount_to_pay <= 0:
                return {
                    'settled': False,
                    'message': 'Insufficient wallet balance to pay outstanding amounts',
                    'original_balance': original_balance,
                    'new_balance': self.balance,
                    'amount_settled': 0
                }
            
            # Pay outstanding invoices using wallet balance
            remaining_to_pay = amount_to_pay
            invoices_paid = []
            
            for invoice in outstanding_invoices:
                if remaining_to_pay <= 0:
                    break
                    
                invoice_balance = invoice.get_balance()
                if invoice_balance <= 0:
                    continue
                
                # Calculate payment amount for this invoice
                payment_amount = min(remaining_to_pay, invoice_balance)
                
                # Create payment record
                from billing.models import Payment
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=payment_amount,
                    payment_method='wallet',
                    payment_date=timezone.now().date(),
                    received_by=user,
                    notes=f'Wallet payment for outstanding balance - {description}'
                )
                
                # Update invoice
                invoice.amount_paid += payment_amount
                if invoice.amount_paid >= invoice.total_amount:
                    invoice.status = 'paid'
                elif invoice.amount_paid > 0:
                    invoice.status = 'partially_paid'
                invoice.save()
                
                invoices_paid.append({
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'amount_paid': payment_amount
                })
                
                remaining_to_pay -= payment_amount
            
            # Deduct the total amount paid from wallet
            self.balance -= amount_to_pay
            self.save(update_fields=['balance', 'last_updated'])
            
            # Create wallet transaction for the payment
            WalletTransaction.objects.create(
                wallet=self,
                transaction_type='payment',
                amount=amount_to_pay,
                balance_after=self.balance,
                description=f"{description} - Paid outstanding invoices",
                created_by=user
            )
            
            return {
                'settled': True,
                'message': f'Successfully paid ₦{amount_to_pay} from wallet balance to settle outstanding invoices',
                'original_balance': original_balance,
                'new_balance': self.balance,
                'amount_settled': amount_to_pay,
                'invoices_paid': invoices_paid
            }
        
        # If wallet has negative balance, we can still attempt to settle by adding funds
        elif self.balance < 0:
            # Get all outstanding invoices for this patient
            from billing.models import Invoice
            outstanding_invoices = Invoice.objects.filter(
                patient=self.patient,
                status__in=['pending', 'partially_paid']
            ).order_by('created_at')
            
            total_outstanding = sum(invoice.get_balance() for invoice in outstanding_invoices)
            
            if total_outstanding <= 0:
                return {
                    'settled': False,
                    'message': 'No outstanding invoices to settle',
                    'original_balance': original_balance,
                    'new_balance': self.balance,
                    'amount_settled': 0
                }
            
            # For negative balance, we'll create a settlement that shows the outstanding amount
            # but doesn't actually change the wallet balance (since it's already negative)
            amount_outstanding = abs(self.balance)
            
            return {
                'settled': False,
                'message': f'Wallet has negative balance of ₦{amount_outstanding}. Outstanding invoices total ₦{total_outstanding}. Please add funds to wallet first.',
                'original_balance': original_balance,
                'new_balance': self.balance,
                'amount_settled': 0,
                'outstanding_invoices': [
                    {
                        'invoice_id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'balance': invoice.get_balance()
                    } for invoice in outstanding_invoices
                ]
            }
        
        # If wallet balance is exactly zero
        else:
            return {
                'settled': False,
                'message': 'Wallet balance is zero. No funds available to pay outstanding amounts.',
                'original_balance': original_balance,
                'new_balance': self.balance,
                'amount_settled': 0
            }

    def get_transaction_history(self, limit=None):
        """Get wallet transaction history"""
        transactions = self.transactions.all().order_by('-created_at')
        if limit:
            transactions = transactions[:limit]
        return transactions

    def get_total_credits(self):
        """Get total amount credited to wallet"""
        return self.transactions.filter(
            transaction_type__in=['credit', 'deposit', 'refund']
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_total_debits(self):
        """Get total amount debited from wallet"""
        return self.transactions.filter(
            transaction_type__in=['debit', 'payment', 'withdrawal']
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_transaction_statistics(self):
        """Get comprehensive transaction statistics"""
        from django.db.models import Sum, Count

        # Credit transactions
        credit_types = [
            'credit', 'deposit', 'refund', 'transfer_in', 'adjustment',
            'insurance_claim', 'bonus', 'cashback', 'reversal'
        ]

        # Debit transactions
        debit_types = [
            'debit', 'withdrawal', 'payment', 'transfer_out', 'admission_fee',
            'daily_admission_charge', 'lab_test_payment', 'pharmacy_payment',
            'consultation_fee', 'procedure_fee', 'penalty_fee', 'discount_applied'
        ]

        stats = {}

        # Overall statistics
        stats['total_credits'] = self.transactions.filter(
            transaction_type__in=credit_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        stats['total_debits'] = self.transactions.filter(
            transaction_type__in=debit_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        # Category-wise statistics
        stats['by_category'] = {}

        # Medical Services
        medical_types = ['consultation_fee', 'procedure_fee', 'lab_test_payment', 'pharmacy_payment']
        stats['by_category']['medical_services'] = self.transactions.filter(
            transaction_type__in=medical_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        # Hospital Services
        hospital_types = ['admission_fee', 'daily_admission_charge']
        stats['by_category']['hospital_services'] = self.transactions.filter(
            transaction_type__in=hospital_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        # Transfers
        transfer_types = ['transfer_in', 'transfer_out']
        stats['by_category']['transfers'] = self.transactions.filter(
            transaction_type__in=transfer_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        # Deposits & Withdrawals
        deposit_types = ['deposit', 'withdrawal']
        stats['by_category']['deposits_withdrawals'] = self.transactions.filter(
            transaction_type__in=deposit_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        # Refunds & Adjustments
        adjustment_types = ['refund', 'adjustment', 'reversal']
        stats['by_category']['adjustments'] = self.transactions.filter(
            transaction_type__in=adjustment_types
        ).aggregate(total=Sum('amount'), count=Count('id'))

        return stats

    def transfer_to(self, recipient_wallet, amount, description="Transfer", user=None):
        """Transfer funds to another wallet atomically"""
        if amount <= 0:
            raise ValueError("Transfer amount must be positive.")
        
        if recipient_wallet == self:
            raise ValueError("Cannot transfer to the same wallet.")
        
        if not recipient_wallet.is_active:
            raise ValueError("Recipient wallet is not active.")
        
        from django.db import transaction
        
        with transaction.atomic():
            # Debit from sender
            self.debit(
                amount=amount,
                description=f'Transfer to {recipient_wallet.patient.get_full_name()} - {description}',
                transaction_type='transfer_out',
                user=user
            )
            
            # Credit to recipient
            recipient_wallet.credit(
                amount=amount,
                description=f'Transfer from {self.patient.get_full_name()} - {description}',
                transaction_type='transfer_in',
                user=user
            )
            
            # Link the transactions
            sender_transaction = self.transactions.filter(
                transaction_type='transfer_out',
                amount=amount
            ).latest('created_at')
            
            recipient_transaction = recipient_wallet.transactions.filter(
                transaction_type='transfer_in',
                amount=amount
            ).latest('created_at')
            
            # Update transfer relationships
            sender_transaction.transfer_to_wallet = recipient_wallet
            sender_transaction.save(update_fields=['transfer_to_wallet'])
            
            recipient_transaction.transfer_from_wallet = self
            recipient_transaction.save(update_fields=['transfer_from_wallet'])
            
            return sender_transaction, recipient_transaction

    def get_transfer_history(self, limit=None):
        """Get transfer-specific transaction history"""
        transfers = self.transactions.filter(
            transaction_type__in=['transfer_in', 'transfer_out']
        ).order_by('-created_at')
        
        if limit:
            transfers = transfers[:limit]
        return transfers

    def get_total_transfers_in(self):
        """Get total amount received via transfers"""
        return self.transactions.filter(
            transaction_type='transfer_in'
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_total_transfers_out(self):
        """Get total amount sent via transfers"""
        return self.transactions.filter(
            transaction_type='transfer_out'
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    def get_admission_spend(self, admission):
        """Get total amount spent on a specific admission"""
        # Use direct FK relationship if available
        direct_spend = self.transactions.filter(
            admission=admission,
            transaction_type__in=['admission_fee', 'daily_admission_charge']
        ).aggregate(total=Sum('amount'))['total']
        
        if direct_spend is not None:
            return direct_spend        # Fallback to date-range method
        admission_date = admission.admission_date.date()
        end_date = admission.discharge_date.date() if admission.discharge_date else timezone.now().date()
        
        return self.transactions.filter(
            transaction_type__in=['admission_fee', 'daily_admission_charge'],
            created_at__date__range=[admission_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    def get_total_wallet_impact_with_admissions(self):
        """Get total wallet impact including all outstanding costs (admissions + invoices)"""
        try:
            from inpatient.models import Admission
            from billing.models import Invoice
            current_balance = self.balance
            
            # Get all active admissions for this patient
            active_admissions = Admission.objects.filter(
                patient=self.patient,
                status='admitted'
            )
            
            # Calculate outstanding admission costs
            admission_outstanding = sum(
                admission.get_outstanding_admission_cost()
                for admission in active_admissions
            )
            
            # Get all outstanding invoices for this patient
            outstanding_invoices = Invoice.objects.filter(
                patient=self.patient,
                status__in=['pending', 'partially_paid']
            )
            
            # Calculate outstanding invoice amounts
            invoice_outstanding = sum(
                invoice.get_balance() for invoice in outstanding_invoices
            )
            
            # Total outstanding amount (admissions + invoices)
            total_outstanding = admission_outstanding + invoice_outstanding

            # Apply wallet balance to total outstanding
            if current_balance >= total_outstanding:
                wallet_after = current_balance - total_outstanding
                outstanding_after = 0
            else:
                wallet_after = Decimal('0.00')
                outstanding_after = total_outstanding - current_balance

            # Return net impact: positive = wallet remaining, negative = amount still owed
            return wallet_after - outstanding_after
        except:
            return self.balance

    class Meta:
        verbose_name = "Patient Wallet"
        verbose_name_plural = "Patient Wallets"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Adjustment'),
        ('admission_fee', 'Admission Fee'),
        ('daily_admission_charge', 'Daily Admission Charge'),
        ('outstanding_admission_recovery', 'Outstanding Admission Recovery'),
        ('lab_test_payment', 'Lab Test Payment'),
        ('pharmacy_payment', 'Pharmacy Payment'),
        ('consultation_fee', 'Consultation Fee'),
        ('procedure_fee', 'Procedure Fee'),
        ('insurance_claim', 'Insurance Claim'),
        ('discount_applied', 'Discount Applied'),
        ('penalty_fee', 'Penalty Fee'),
        ('reversal', 'Transaction Reversal'),
        ('bonus', 'Bonus Credit'),
        ('cashback', 'Cashback'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    wallet = models.ForeignKey(PatientWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_number = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    # Related objects
    invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.ForeignKey('billing.Payment', on_delete=models.SET_NULL, null=True, blank=True)
    admission = models.ForeignKey('inpatient.Admission', on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions')

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional fields for transfers
    transfer_to_wallet = models.ForeignKey(PatientWallet, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transfers')
    transfer_from_wallet = models.ForeignKey(PatientWallet, on_delete=models.SET_NULL, null=True, blank=True, related_name='outgoing_transfers')

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self._generate_reference_number()
        super().save(*args, **kwargs)

    def _generate_reference_number(self):
        """Generate unique reference number for transaction"""
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"TXN{timestamp}{unique_id}"

    def is_credit_transaction(self):
        """Check if this transaction increases the wallet balance"""
        credit_types = [
            'credit', 'deposit', 'refund', 'transfer_in', 'adjustment',
            'insurance_claim', 'bonus', 'cashback', 'reversal'
        ]
        return self.transaction_type in credit_types

    def is_debit_transaction(self):
        """Check if this transaction decreases the wallet balance"""
        return not self.is_credit_transaction()

    def get_transaction_category(self):
        """Get the category of transaction for better organization"""
        categories = {
            'credit': 'Manual Credit',
            'debit': 'Manual Debit',
            'deposit': 'Deposit',
            'withdrawal': 'Withdrawal',
            'payment': 'General Payment',
            'refund': 'Refund',
            'transfer_in': 'Transfer Received',
            'transfer_out': 'Transfer Sent',
            'adjustment': 'Balance Adjustment',
            'admission_fee': 'Hospital Services',
            'daily_admission_charge': 'Hospital Services',
            'lab_test_payment': 'Laboratory Services',
            'pharmacy_payment': 'Pharmacy Services',
            'consultation_fee': 'Medical Services',
            'procedure_fee': 'Medical Services',
            'insurance_claim': 'Insurance',
            'discount_applied': 'Discounts',
            'penalty_fee': 'Penalties',
            'reversal': 'Reversals',
            'bonus': 'Bonuses',
            'cashback': 'Cashback',
        }
        return categories.get(self.transaction_type, 'Other')

    def get_icon_class(self):
        """Get appropriate icon class for transaction type"""
        icons = {
            'credit': 'fas fa-plus-circle text-success',
            'debit': 'fas fa-minus-circle text-danger',
            'deposit': 'fas fa-piggy-bank text-success',
            'withdrawal': 'fas fa-money-bill-wave text-warning',
            'payment': 'fas fa-credit-card text-danger',
            'refund': 'fas fa-undo text-success',
            'transfer_in': 'fas fa-arrow-down text-success',
            'transfer_out': 'fas fa-arrow-up text-danger',
            'adjustment': 'fas fa-balance-scale text-info',
            'admission_fee': 'fas fa-hospital text-danger',
            'daily_admission_charge': 'fas fa-bed text-danger',
            'lab_test_payment': 'fas fa-flask text-danger',
            'pharmacy_payment': 'fas fa-pills text-danger',
            'consultation_fee': 'fas fa-user-md text-danger',
            'procedure_fee': 'fas fa-procedures text-danger',
            'insurance_claim': 'fas fa-shield-alt text-success',
            'discount_applied': 'fas fa-percentage text-success',
            'penalty_fee': 'fas fa-exclamation-triangle text-danger',
            'reversal': 'fas fa-undo-alt text-info',
            'bonus': 'fas fa-gift text-success',
            'cashback': 'fas fa-coins text-success',
        }
        return icons.get(self.transaction_type, 'fas fa-exchange-alt text-secondary')

    def __str__(self):
        return f"{self.transaction_type.title()} - ₦{self.amount} - {self.wallet.patient.get_full_name()}"

    class Meta:
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"
        ordering = ['-created_at']


class NHIAPatientManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(patient_type='nhia')

class NHIAPatient(Patient):
    objects = NHIAPatientManager()

    class Meta:
        proxy = True
        verbose_name = 'NHIA Patient'
        verbose_name_plural = 'NHIA Patients'

    def save(self, *args, **kwargs):
        self.patient_type = 'nhia'
        super().save(*args, **kwargs)