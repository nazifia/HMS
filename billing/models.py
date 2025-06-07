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
            self.status = 'paid' # Consider 0 amount invoices as paid unless draft/cancelled

        super().save(*args, **kwargs)

        # If the invoice is marked as paid and is linked to a prescription, update the prescription's payment_status
        if self.status == 'paid' and self.prescription:
            try:
                prescription = Prescription.objects.get(id=self.prescription.id)
                if prescription.payment_status != 'paid':
                    prescription.payment_status = 'paid'
                    prescription.save(update_fields=['payment_status'])
            except Prescription.DoesNotExist:
                # Handle the case where the prescription might have been deleted
                pass # Or log an error

        # Update related service statuses if applicable

    def _generate_invoice_number(self):
        """
        Generate a unique invoice number in the format INVYYYYMMDDXXXX
        where XXXX is a zero-padded sequence for the day.
        """
        from django.utils import timezone
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        prefix = 'INV'
        # Count existing invoices for today
        count = Invoice.objects.filter(invoice_date=today).count() + 1
        return f"{prefix}{date_str}{str(count).zfill(4)}"

    class Meta:
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['patient']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice_date']),
        ]
        ordering = ['-invoice_date']

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    description = models.CharField(max_length=200, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.service.name} - {self.quantity} x ₦{self.unit_price}"

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
        is_new = self.pk is None
        payment_processed_in_transaction = False

        if is_new and self.payment_method == 'wallet':
            with transaction.atomic():
                # Save the Payment record first to get an ID for linking
                # This call to super().save() is for the Payment model itself.
                super().save(*args, **kwargs)
                # At this point, self.pk is populated if the save was successful.

                try:
                    # Ensure PatientWallet model is imported if not already at top level
                    # from patients.models import PatientWallet # Already imported at top
                    patient_wallet = PatientWallet.objects.get(patient=self.invoice.patient)
                    
                    # Perform the debit operation
                    patient_wallet.debit(
                        amount=self.amount,
                        description=f"Payment for Invoice #{self.invoice.invoice_number} via Wallet",
                        transaction_type="payment",
                        user=self.received_by,
                        invoice=self.invoice, # Pass the invoice instance
                        payment_instance=self  # Pass the payment instance (self)
                    )

                    # Update invoice's amount_paid and status
                    # It's crucial to fetch the invoice again or ensure its state is fresh
                    # if other operations might have modified it, though here it should be fine.
                    invoice_to_update = self.invoice 
                    invoice_to_update.amount_paid += self.amount
                    # The Invoice.save() method should handle updating its own status based on amount_paid
                    invoice_to_update.save(update_fields=['amount_paid', 'status'])
                    
                    payment_processed_in_transaction = True

                except PatientWallet.DoesNotExist as e:
                    # This error implies the patient does not have a wallet.
                    # The transaction will roll back the Payment save.
                    raise ValueError(f"Patient wallet not found for {self.invoice.patient.get_full_name()}. Payment cancelled.") from e
                except ValueError as e:
                    # This catches validation errors from patient_wallet.debit (e.g., debit amount <= 0)
                    # or other ValueErrors. The transaction will roll back the Payment save.
                    raise e # Re-raise to signal failure and ensure rollback
                # Any other unexpected error will also cause a rollback.
        else:
            # Standard save for non-wallet payments or for updates to existing payments.
            super().save(*args, **kwargs)
            # If it's a new non-wallet payment, update the invoice.
            if is_new: # and self.payment_method != 'wallet' (already covered by outer else)
                invoice_to_update = self.invoice
                invoice_to_update.amount_paid += self.amount
                invoice_to_update.save(update_fields=['amount_paid', 'status'])
            elif not is_new: # Existing payment is being updated
                # Handling updates to existing payment amounts and their effect on invoice.amount_paid
                # requires careful logic to correctly adjust the invoice's total paid amount.
                # This typically involves: 
                # 1. Getting the original amount of the payment before this save.
                # 2. Calculating the difference between the new amount and the original amount.
                # 3. Adjusting invoice.amount_paid by this difference.
                # This is a simplified placeholder and might need a more robust implementation, 
                # possibly by recalculating the sum of all payments for the invoice.
                # For now, if only other fields of an existing payment are updated (not amount), 
                # this block might not need to do much to invoice.amount_paid.
                # If 'amount' is in update_fields, then recalculation is essential.
                # Let's assume for now that if an existing payment's amount is changed, 
                # a more comprehensive invoice update mechanism is needed or handled by a signal/service.
                # A simple approach for amount updates (if kwargs indicate amount changed):
                # We'd need the original amount. Django doesn't easily provide this in save().
                # A common pattern is to override __init__ to store original values or use signals.
                # For now, this part is a placeholder for more complex update logic.
                pass

        # If a wallet payment was processed, the invoice update is already handled within the transaction.
        # The conditional invoice update for new non-wallet payments is handled in the 'else' block.
        # No further invoice update should be needed here if logic above is correct.
