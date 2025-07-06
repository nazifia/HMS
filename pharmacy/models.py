from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from patients.models import Patient
from django.conf import settings

class MedicationCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Medication Categories"

class Medication(models.Model):
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, blank=True, null=True)
    category = models.ForeignKey(MedicationCategory, on_delete=models.SET_NULL, null=True, related_name='medications')
    description = models.TextField(blank=True, null=True)
    dosage_form = models.CharField(max_length=50)  # e.g., tablet, capsule, syrup
    strength = models.CharField(max_length=50)  # e.g., 500mg, 250ml
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    reorder_level = models.IntegerField(default=10)
    expiry_date = models.DateField(blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    precautions = models.TextField(blank=True, null=True)
    storage_instructions = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.strength})"

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['name']

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]
        ordering = ['name']

class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchases')
    purchase_date = models.DateField()
    invoice_number = models.CharField(max_length=50, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ), default='pending')
    notes = models.TextField(blank=True, null=True)
    dispensary = models.ForeignKey('Dispensary', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases') # New field
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='draft', db_index=True)
    current_approver = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='pending_purchase_approvals')
    approval_notes = models.TextField(blank=True, null=True)
    approval_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Purchase #{self.invoice_number} - {self.supplier.name}"

class PurchaseApproval(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')], default='pending')
    comments = models.TextField(blank=True, null=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    step_order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['step_order', 'created_at']
        unique_together = ('purchase', 'approver', 'step_order')

    def __str__(self):
        return f"{self.purchase.invoice_number} - Step {self.step_order} - {self.approver.get_full_name()} ({self.status})"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField()

    def __str__(self):
        return f"{self.medication.name} - {self.quantity} units"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price

        if not self.pk:  # If this is a new item (not an update)
            if self.purchase.dispensary:
                inventory, created = MedicationInventory.objects.get_or_create(
                    medication=self.medication,
                    dispensary=self.purchase.dispensary,
                    defaults={'stock_quantity': 0} # Initialize if new
                )
                inventory.stock_quantity += self.quantity
                inventory.last_restock_date = timezone.now()
                inventory.save()
            else:
                # Handle cases where a purchase might not be linked to a specific dispensary yet
                # For now, we can log a warning or raise an error, depending on desired behavior
                # For this implementation, we'll assume dispensary is always set for purchases that affect inventory
                pass # Or raise an exception: raise ValueError("Purchase must have a dispensary to update inventory.")

        super().save(*args, **kwargs)

class Prescription(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('dispensed', 'Dispensed'),
        ('partially_dispensed', 'Partially Dispensed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('waived', 'Waived'), # For cases where payment is not required
    )

    PRESCRIPTION_TYPE_CHOICES = (
        ('inpatient', 'In-Patient (MAR/eMAR)'),
        ('outpatient', 'Out-Patient (Take-Home)'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_prescriptions')
    prescription_date = models.DateField(default=timezone.now)
    diagnosis = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid') # New field
    prescription_type = models.CharField(
        max_length=20,
        choices=PRESCRIPTION_TYPE_CHOICES,
        default='outpatient',
        help_text='Is this an in-patient (MAR/eMAR) or out-patient (take-home) prescription?'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='prescription_invoice')

    def __str__(self):
        return f"Prescription for {self.patient.get_full_name()} - {self.prescription_date}"

    def get_total_prescribed_price(self): # Renamed for clarity
        """Calculate the total price of all originally prescribed medications in this prescription"""
        total = 0
        for item in self.items.all():
            total += item.medication.price * item.quantity # item.quantity is prescribed quantity
        return total

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)  # e.g., 1 tablet
    frequency = models.CharField(max_length=100)  # e.g., twice daily
    duration = models.CharField(max_length=100)  # e.g., 7 days
    instructions = models.TextField(blank=True, null=True)  # e.g., take after meals
    quantity = models.IntegerField() # Original prescribed quantity
    
    quantity_dispensed_so_far = models.IntegerField(default=0) # Total quantity dispensed for this item

    is_dispensed = models.BooleanField(default=False) # True if fully dispensed (quantity_dispensed_so_far >= quantity)
    
    # These now reflect the LAST dispense action on this item
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='last_dispensed_items')
    dispensed_date = models.DateTimeField(blank=True, null=True) # Last dispensed date

    def __str__(self):
        return f"{self.medication.name} ({self.quantity}) for {self.prescription.patient.get_full_name()}"

    def get_medication_price(self):
        return self.medication.price

    @property
    def remaining_quantity_to_dispense(self):
        return self.quantity - self.quantity_dispensed_so_far

class DispensingLog(models.Model):
    """Logs each individual act of dispensing a medication item."""
    prescription_item = models.ForeignKey(PrescriptionItem, on_delete=models.CASCADE, related_name='dispensing_logs')
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='dispensing_actions')
    dispensed_quantity = models.IntegerField()
    dispensed_date = models.DateTimeField(default=timezone.now)
    unit_price_at_dispense = models.DecimalField(max_digits=10, decimal_places=2)
    total_price_for_this_log = models.DecimalField(max_digits=10, decimal_places=2) # Calculated: dispensed_quantity * unit_price_at_dispense
    dispensary = models.ForeignKey('Dispensary', on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensing_logs')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispensed {self.dispensed_quantity} of {self.prescription_item.medication.name} on {self.dispensed_date.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.pk: # On creation
            self.total_price_for_this_log = self.dispensed_quantity * self.unit_price_at_dispense
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-dispensed_date']
        verbose_name = "Dispensing Log Entry"
        verbose_name_plural = "Dispensing Log Entries"


class Dispensary(models.Model):
    """Represents a pharmacy dispensary location or unit."""
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_dispensaries')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Dispensaries"
        ordering = ['name']

class MedicationInventory(models.Model):
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='inventories')
    dispensary = models.ForeignKey(Dispensary, on_delete=models.CASCADE, related_name='medications')
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    last_restock_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.medication.name} at {self.dispensary.name}"

    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

    def is_expired(self):
        if self.medication.expiry_date:
            return timezone.now().date() >= self.medication.expiry_date
        return False

    class Meta:
        verbose_name_plural = "Medication Inventories"
        unique_together = ['medication', 'dispensary']
