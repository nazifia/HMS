from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db import transaction # Added for atomic transactions
from patients.models import Patient, PatientWallet
from appointments.models import Appointment
from laboratory.models import TestRequest
from pharmacy.models import Prescription
from radiology.models import RadiologyOrder

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Service Categories"

class Service(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, related_name='services')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ₦{self.price}"

    def get_price_with_tax(self):
        tax_amount = (self.price * self.tax_percentage) / 100
        return self.price + tax_amount

class Invoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('insurance', 'Insurance'),
        ('wallet', 'Wallet'),
        ('other', 'Other'),
    )

    SOURCE_APP_CHOICES = (
        ('laboratory', 'Laboratory'),
        ('radiology', 'Radiology'),
        ('pharmacy', 'Pharmacy'),
        ('appointment', 'Appointment'),
        ('theatre', 'Theatre'),
        ('billing', 'Billing/General'), # For invoices created directly
        ('other', 'Other'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True)
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    test_request = models.OneToOneField(TestRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_record')
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    admission = models.ForeignKey('inpatient.Admission', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    source_app = models.CharField(
        max_length=20,
        choices=SOURCE_APP_CHOICES,
        default='billing', # Default to 'billing' for general invoices
        null=True,
        blank=True
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.patient.get_full_name()}"

    def get_balance(self):
        return self.total_amount - self.amount_paid

    def is_paid(self):
        return self.amount_paid >= self.total_amount

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()

        # Calculate totals before saving if items exist or subtotal is provided
        if self.id or hasattr(self, 'subtotal'): # Ensure subtotal exists if we are to calculate total
            self.total_amount = (self.subtotal or 0) + (self.tax_amount or 0) - (self.discount_amount or 0)

        # Update status based on amount_paid and total_amount
        if self.total_amount > 0:
            if self.amount_paid >= self.total_amount:
                self.status = 'paid'
            elif self.amount_paid > 0 and self.amount_paid < self.total_amount:
                self.status = 'partially_paid'
            elif self.amount_paid == 0 and self.status not in ['draft', 'cancelled']:
                 self.status = 'pending' # Or back to pending if payment was reversed for e.g.
        elif self.total_amount == 0 and self.status not in ['draft', 'cancelled']:
            # Only auto-mark zero amount invoices as paid if explicitly marked for auto-payment
            # This prevents accidental auto-payment of invoices with calculation errors
            if hasattr(self, '_auto_pay_zero_amount') and self._auto_pay_zero_amount:
                self.status = 'paid'
            else:
                self.status = 'pending'  # Keep zero amount invoices as pending by default

        super().save(*args, **kwargs)

        # If the invoice is marked as paid and is linked to a prescription, update the prescription's payment_status
        # Only update if this is a legitimate payment (not automatic zero-amount)
        if self.status == 'paid' and self.prescription:
            try:
                prescription = Prescription.objects.get(id=self.prescription.id)
                # Only auto-update prescription payment status if:
                # 1. There was actual payment processing (manual payment), OR
                # 2. The total amount is greater than 0 (indicating legitimate payment), OR
                # 3. This is explicitly marked as an auto-pay zero amount invoice
                should_update = (
                    hasattr(self, '_manual_payment_processed') or
                    self.total_amount > 0 or
                    (hasattr(self, '_auto_pay_zero_amount') and self._auto_pay_zero_amount)
                )

                if prescription.payment_status != 'paid' and should_update:
                    prescription.payment_status = 'paid'
                    prescription.save(update_fields=['payment_status'])
            except Prescription.DoesNotExist:
                # Handle the case where the prescription might have been deleted
                pass # Or log an error

        # If the invoice is marked as paid and is linked to an admission, update the admission's amount_paid
        if self.admission:
            try:
                admission = self.admission
                # Only update if the invoice is paid or partially paid
                if self.status in ['paid', 'partially_paid']:
                    admission.amount_paid = self.amount_paid
                    admission.save(update_fields=['amount_paid'])
            except Exception as e:
                # Log the error if the admission object cannot be found or updated
                print(f"Error updating admission amount_paid for invoice {self.invoice_number}: {e}")

        # Update related service statuses if applicable

    def _generate_invoice_number(self):
        """
        Generate a unique invoice number in the format INVYYYYMMDDXXXX
        where XXXX is a zero-padded sequence for the day.
        Uses a retry mechanism to handle race conditions.
        """
        from django.utils import timezone
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        prefix = 'INV'

        # Try to generate a unique invoice number with retry logic
        max_attempts = 100
        for attempt in range(max_attempts):
            # Count existing invoices for today and add attempt number
            count = Invoice.objects.filter(invoice_date=today).count() + 1 + attempt
            invoice_number = f"{prefix}{date_str}{str(count).zfill(4)}"

            # Check if this invoice number already exists
            if not Invoice.objects.filter(invoice_number=invoice_number).exists():
                return invoice_number

        # If we couldn't generate a unique number after max_attempts, use timestamp
        import time
        timestamp = str(int(time.time() * 1000))[-4:]  # Last 4 digits of millisecond timestamp
        return f"{prefix}{date_str}{timestamp}"

    class Meta:
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['patient']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice_date']),
            models.Index(fields=['status', 'invoice_date']),
            models.Index(fields=['patient', 'status']),
        ]
        ordering = ['-invoice_date']

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=200, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        if self.service:
            return f"{self.service.name} - {self.quantity} x ₦{self.unit_price}"
        return f"{self.description or 'Item'} - {self.quantity} x ₦{self.unit_price}"

    def save(self, *args, **kwargs):
        # Calculate tax amount
        self.tax_amount = (self.unit_price * self.quantity * self.tax_percentage) / 100

        # Calculate discount amount
        self.discount_amount = (self.unit_price * self.quantity * self.discount_percentage) / 100

        # Calculate total amount
        self.total_amount = (self.unit_price * self.quantity) + self.tax_amount - self.discount_amount

        super().save(*args, **kwargs)

class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=Invoice.PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of ₦{self.amount} for Invoice #{self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        """
        Simple save method. Wallet and invoice operations are handled by signals
        to ensure consistent behavior for create, update, and delete operations.
        """
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['payment_date'], name='idx_payment_date'),
            models.Index(fields=['invoice'], name='idx_payment_invoice'),
            models.Index(fields=['payment_method'], name='idx_payment_method'),
            models.Index(fields=['created_at'], name='idx_payment_created'),
        ]
        ordering = ['-payment_date', '-created_at']
