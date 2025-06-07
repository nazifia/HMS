from django.db import models
from django.utils import timezone
from django.conf import settings


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

    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)

    # Contact Information
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15)
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
        # Generate a unique patient ID if not provided
        if not self.patient_id:
            year = timezone.now().year
            month = timezone.now().month
            # Only use numbers for patient ID: YYYYMMNNNN
            prefix = f"{year}{month:02d}"
            last_patient = Patient.objects.filter(patient_id__startswith=prefix).order_by('-patient_id').first()

            if last_patient:
                try:
                    last_number = int(last_patient.patient_id[len(prefix):])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = 1
            else:
                new_number = 1

            self.patient_id = f"{prefix}{new_number:04d}"

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

    def credit(self, amount, description="Credit", transaction_type="credit", user=None):
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
            created_by=user
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
