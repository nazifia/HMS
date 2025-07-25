from django.db import models
from django.utils import timezone
from django.conf import settings
import random


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
    )

    # Basic Information
    first_name = models.CharField(max_length=100)
    patient_type = models.CharField(max_length=10, choices=PATIENT_TYPE_CHOICES, default='regular')
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
    profile_picture = models.ImageField(upload_to='patients/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    id_document = models.FileField(upload_to='id_documents/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.patient_id:
            if self.patient_type == 'nhia':
                while True:
                    # NHIA patient ID: 10 digits, starting with 4
                    new_id = '4' + ''.join([str(random.randint(0, 9)) for _ in range(9)])
                    if not Patient.objects.filter(patient_id=new_id).exists():
                        self.patient_id = new_id
                        break
            else:
                # Regular patient ID: 10 digits, starting with 0
                while True:
                    new_id = '0' + ''.join([str(random.randint(0, 9)) for _ in range(9)])
                    if not Patient.objects.filter(patient_id=new_id).exists():
                        self.patient_id = new_id
                        break
        super().save(*args, **kwargs)

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
        Get the best available profile image for the patient.
        Prioritizes 'photo' field over 'profile_picture' field.
        Returns the image field object or None if no image is available.
        """
        if self.photo:
            return self.photo
        elif self.profile_picture:
            return self.profile_picture
        return None

    def get_profile_image_url(self):
        """
        Get the URL of the best available profile image.
        Returns the image URL or None if no image is available.
        """
        image = self.get_profile_image()
        return image.url if image else None

    def has_profile_image(self):
        """
        Check if the patient has any profile image available.
        Returns True if either photo or profile_picture is available.
        """
        return bool(self.photo or self.profile_picture)

    def get_patient_type_display(self):
        return dict(self.PATIENT_TYPE_CHOICES).get(self.patient_type, self.patient_type)

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


class PatientWallet(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.patient.get_full_name()} (₦{self.balance})"

    def credit(self, amount, description="Credit", transaction_type="credit", user=None, invoice=None, payment_instance=None):
        """Credit amount to wallet and create transaction record"""
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")

        self.balance += amount
        self.save(update_fields=['balance', 'last_updated'])

        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            created_by=user,
            invoice=invoice,
            payment=payment_instance
        )

    def debit(self, amount, description="Debit", transaction_type="debit", user=None, invoice=None, payment_instance=None):
        """Debit amount from wallet and create transaction record"""
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")
        # Allow balance to go negative
        # if amount > self.balance:
        #     raise ValueError("Insufficient wallet balance.")

        self.balance -= amount
        self.save(update_fields=['balance', 'last_updated'])

        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            created_by=user,
            invoice=invoice,
            payment=payment_instance
        )

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
        ).aggregate(total=models.Sum('amount'))['total'] or 0

    def get_total_debits(self):
        """Get total amount debited from wallet"""
        return self.transactions.filter(
            transaction_type__in=['debit', 'payment', 'withdrawal']
        ).aggregate(total=models.Sum('amount'))['total'] or 0

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
        ).aggregate(total=models.Sum('amount'))['total'] or 0

    def get_total_transfers_out(self):
        """Get total amount sent via transfers"""
        return self.transactions.filter(
            transaction_type='transfer_out'
        ).aggregate(total=models.Sum('amount'))['total'] or 0

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
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    wallet = models.ForeignKey(PatientWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_number = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    # Related objects
    invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.ForeignKey('billing.Payment', on_delete=models.SET_NULL, null=True, blank=True)

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