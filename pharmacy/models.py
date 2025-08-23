from django.db import models, transaction
from django.utils import timezone
from accounts.models import CustomUser
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

    def calculate_total_amount(self):
        """Calculate total amount from all purchase items"""
        from django.db.models import Sum, F
        total = self.items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        return total

    def update_total_amount(self):
        """Update the total_amount field based on current items"""
        self.total_amount = self.calculate_total_amount()
        self.save(update_fields=['total_amount'])

    def get_items_count(self):
        """Get total number of different items in this purchase"""
        return self.items.count()

    def get_total_quantity(self):
        """Get total quantity of all items in this purchase"""
        from django.db.models import Sum
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    def can_be_approved(self):
        """Check if purchase can be approved"""
        return (
            self.approval_status == 'pending' and
            self.items.exists() and
            self.total_amount > 0
        )

    def can_be_paid(self):
        """Check if purchase can be paid"""
        return (
            self.approval_status == 'approved' and
            self.payment_status in ['pending', 'partial']
        )

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
        # Always calculate total price
        self.total_price = self.quantity * self.unit_price

        if not self.pk:  # If this is a new item (not an update)
            # Add to bulk store instead of directly to dispensary
            self._add_to_bulk_store()

            # Also maintain legacy dispensary inventory for backward compatibility
            if self.purchase.dispensary:
                inventory, created = MedicationInventory.objects.get_or_create(
                    medication=self.medication,
                    dispensary=self.purchase.dispensary,
                    defaults={'stock_quantity': 0} # Initialize if new
                )
                inventory.stock_quantity += self.quantity
                inventory.last_restock_date = timezone.now()
                inventory.save()

        super().save(*args, **kwargs)

        # Update purchase total amount after saving the item
        self.purchase.update_total_amount()

    def delete(self, *args, **kwargs):
        purchase = self.purchase
        super().delete(*args, **kwargs)
        # Update purchase total amount after deleting the item
        purchase.update_total_amount()

    def _add_to_bulk_store(self):
        """Add procured medication to bulk store"""
        # Get or create a default bulk store
        bulk_store, created = BulkStore.objects.get_or_create(
            name='Main Bulk Store',
            defaults={
                'location': 'Central Storage Area',
                'description': 'Main bulk storage for all procured medications',
                'capacity': 50000,
                'temperature_controlled': True,
                'humidity_controlled': True,
                'security_level': 'high',
                'is_active': True
            }
        )

        # Add to bulk store inventory
        bulk_inventory, created = BulkStoreInventory.objects.get_or_create(
            medication=self.medication,
            bulk_store=bulk_store,
            batch_number=self.batch_number or f"BATCH-{timezone.now().strftime('%Y%m%d')}-{self.pk or 'NEW'}",
            defaults={
                'stock_quantity': 0,
                'expiry_date': self.expiry_date,
                'unit_cost': self.unit_price,
                'supplier': self.purchase.supplier,
                'purchase_date': self.purchase.purchase_date
            }
        )

        if not created:
            # Update existing inventory
            bulk_inventory.stock_quantity += self.quantity
            bulk_inventory.save()
        else:
            # Set initial quantity for new inventory
            bulk_inventory.stock_quantity = self.quantity
            bulk_inventory.save()

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

    def get_patient_payable_amount(self):
        """Calculate the amount patient needs to pay based on their type"""
        from decimal import Decimal
        total_price = Decimal(str(self.get_total_prescribed_price()))

        # NHIA patients pay 10%, others pay 100%
        if self.patient.patient_type == 'nhia':
            return total_price * Decimal('0.10')
        else:
            return total_price

    def get_pricing_breakdown(self):
        """Get detailed pricing breakdown for the prescription"""
        from decimal import Decimal
        total_price = Decimal(str(self.get_total_prescribed_price()))
        is_nhia = self.patient.patient_type == 'nhia'

        if is_nhia:
            patient_portion = total_price * Decimal('0.10')
            nhia_portion = total_price * Decimal('0.90')
        else:
            patient_portion = total_price
            nhia_portion = Decimal('0.00')

        return {
            'total_medication_cost': total_price,
            'patient_portion': patient_portion,
            'nhia_portion': nhia_portion,
            'is_nhia_patient': is_nhia,
            'discount_percentage': 90 if is_nhia else 0
        }

    def is_payment_verified(self):
        """Check if the prescription payment has been verified and completed"""
        # Check payment_status field first
        if self.payment_status == 'paid':
            return True
        elif self.payment_status == 'waived':
            return True
        elif self.payment_status == 'unpaid':
            # Double-check with invoice if it exists
            if self.invoice:
                return self.invoice.status == 'paid'
            return False
        return False

    def can_be_dispensed(self):
        """Check if prescription can be dispensed based on payment and other conditions"""
        # Check if prescription is in a dispensable state
        if self.status in ['cancelled', 'dispensed']:
            return False, f'Cannot dispense prescription with status: {self.get_status_display()}'

        # Check payment verification
        if not self.is_payment_verified():
            return False, 'Payment must be completed before dispensing medications'

        # Check if there are items to dispense
        pending_items = self.items.filter(is_dispensed=False)
        if not pending_items.exists():
            return False, 'All items in this prescription have been dispensed'

        return True, 'Prescription is ready for dispensing'

    def get_payment_status_display_info(self):
        """Get detailed payment status information for display"""
        if self.payment_status == 'paid':
            return {
                'status': 'paid',
                'message': 'Payment completed',
                'css_class': 'success',
                'icon': 'check-circle'
            }
        elif self.payment_status == 'waived':
            return {
                'status': 'waived',
                'message': 'Payment waived',
                'css_class': 'info',
                'icon': 'info-circle'
            }
        else:
            # Check invoice status if available
            if self.invoice:
                if self.invoice.status == 'paid':
                    return {
                        'status': 'paid',
                        'message': 'Payment completed via invoice',
                        'css_class': 'success',
                        'icon': 'check-circle'
                    }
                else:
                    return {
                        'status': 'unpaid',
                        'message': f'Payment pending - Invoice #{self.invoice.id}',
                        'css_class': 'warning',
                        'icon': 'exclamation-triangle'
                    }
            else:
                return {
                    'status': 'unpaid',
                    'message': 'Payment required',
                    'css_class': 'danger',
                    'icon': 'exclamation-circle'
                }

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

    @property
    def remaining_quantity(self):
        """Alias for remaining_quantity_to_dispense for cleaner template access"""
        return self.remaining_quantity_to_dispense

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


class ActiveStore(models.Model):
    """Represents the active storage area for a dispensary where medications are stored for immediate dispensing."""
    dispensary = models.OneToOneField(Dispensary, on_delete=models.CASCADE, related_name='active_store')
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(default=1000, help_text="Maximum number of medication units this store can hold")
    temperature_controlled = models.BooleanField(default=False)
    humidity_controlled = models.BooleanField(default=False)
    security_level = models.CharField(max_length=20, choices=[
        ('basic', 'Basic'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('maximum', 'Maximum')
    ], default='basic')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Active Store - {self.dispensary.name}"

    def get_current_stock_count(self):
        """Get total number of medication units currently in this store"""
        return self.medication_stocks.aggregate(
            total=models.Sum('stock_quantity')
        )['total'] or 0

    def get_available_capacity(self):
        """Get remaining capacity in this store"""
        return self.capacity - self.get_current_stock_count()

    def is_at_capacity(self):
        """Check if store is at or over capacity"""
        return self.get_current_stock_count() >= self.capacity

    class Meta:
        verbose_name = "Active Store"
        verbose_name_plural = "Active Stores"
        ordering = ['dispensary__name']


class BulkStore(models.Model):
    """Represents the bulk storage area where procured medications are initially stored before distribution to dispensaries."""
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(default=10000, help_text="Maximum number of medication units this bulk store can hold")
    temperature_controlled = models.BooleanField(default=True)
    humidity_controlled = models.BooleanField(default=True)
    security_level = models.CharField(max_length=20, choices=[
        ('basic', 'Basic'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('maximum', 'Maximum')
    ], default='high')
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_bulk_stores')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_current_stock_count(self):
        """Get total number of medication units currently in this bulk store"""
        return self.medication_stocks.aggregate(
            total=models.Sum('stock_quantity')
        )['total'] or 0

    def get_available_capacity(self):
        """Get remaining capacity in this bulk store"""
        return self.capacity - self.get_current_stock_count()

    def is_at_capacity(self):
        """Check if store is at or over capacity"""
        return self.get_current_stock_count() >= self.capacity

    class Meta:
        verbose_name = "Bulk Store"
        verbose_name_plural = "Bulk Stores"
        ordering = ['name']

class MedicationInventory(models.Model):
    """Legacy model for medication inventory - kept for backward compatibility"""
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


class ActiveStoreInventory(models.Model):
    """Inventory for medications in active stores (dispensary storage areas)"""
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='active_store_inventories')
    active_store = models.ForeignKey(ActiveStore, on_delete=models.CASCADE, related_name='medication_stocks')
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_restock_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.medication.name} in {self.active_store.dispensary.name} Active Store"

    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date <= timezone.now().date()
        return False

    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    class Meta:
        unique_together = ['medication', 'active_store', 'batch_number']
        verbose_name = "Active Store Inventory"
        verbose_name_plural = "Active Store Inventories"
        ordering = ['active_store__dispensary__name', 'medication__name']


class BulkStoreInventory(models.Model):
    """Inventory for medications in bulk stores (central storage areas)"""
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='bulk_store_inventories')
    bulk_store = models.ForeignKey(BulkStore, on_delete=models.CASCADE, related_name='medication_stocks')
    stock_quantity = models.IntegerField(default=0)
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    purchase_date = models.DateField(auto_now_add=True)
    last_transfer_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.medication.name} in {self.bulk_store.name}"

    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date <= timezone.now().date()
        return False

    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    def can_transfer(self, quantity):
        """Check if specified quantity can be transferred from this bulk inventory"""
        return self.stock_quantity >= quantity and not self.is_expired()

    class Meta:
        unique_together = ['medication', 'bulk_store', 'batch_number']
        verbose_name = "Bulk Store Inventory"
        verbose_name_plural = "Bulk Store Inventories"
        ordering = ['bulk_store__name', 'medication__name']


class MedicationTransfer(models.Model):
    """Model to track transfers of medications between bulk stores and active stores"""
    TRANSFER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='transfers')
    from_bulk_store = models.ForeignKey(BulkStore, on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_active_store = models.ForeignKey(ActiveStore, on_delete=models.CASCADE, related_name='incoming_transfers')
    quantity = models.IntegerField()
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='requested_transfers')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transfers')
    transferred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='executed_transfers')
    notes = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transfer {self.quantity} {self.medication.name} from {self.from_bulk_store.name} to {self.to_active_store.dispensary.name}"

    def can_approve(self):
        """Check if transfer can be approved"""
        return self.status == 'pending'

    def can_execute(self):
        """Check if transfer can be executed"""
        return self.status in ['pending', 'in_transit'] and self.approved_by is not None

    def execute_transfer(self, user):
        """Execute the transfer by moving stock from bulk to active store"""
        if not self.can_execute():
            raise ValueError("Transfer cannot be executed in current status")

        with transaction.atomic():
            # Find bulk store inventory
            bulk_inventory = BulkStoreInventory.objects.filter(
                medication=self.medication,
                bulk_store=self.from_bulk_store,
                batch_number=self.batch_number,
                stock_quantity__gte=self.quantity
            ).first()

            if not bulk_inventory:
                raise ValueError("Insufficient stock in bulk store")

            # Reduce bulk store inventory
            bulk_inventory.stock_quantity -= self.quantity
            bulk_inventory.last_transfer_date = timezone.now()
            bulk_inventory.save()

            # Add to active store inventory
            active_inventory, created = ActiveStoreInventory.objects.get_or_create(
                medication=self.medication,
                active_store=self.to_active_store,
                batch_number=self.batch_number,
                defaults={
                    'stock_quantity': 0,
                    'expiry_date': self.expiry_date,
                    'unit_cost': self.unit_cost,
                    'reorder_level': 10
                }
            )

            active_inventory.stock_quantity += self.quantity
            active_inventory.last_restock_date = timezone.now()
            active_inventory.save()

            # Update transfer status
            self.status = 'completed'
            self.transferred_by = user
            self.transferred_at = timezone.now()
            self.save()

    class Meta:
        verbose_name = "Medication Transfer"
        verbose_name_plural = "Medication Transfers"
        ordering = ['-requested_at']


class MedicalPack(models.Model):
    """Model representing a predefined pack of medications and consumables for specific medical procedures"""
    PACK_TYPE_CHOICES = [
        ('surgery', 'Surgery Pack'),
        ('labor', 'Labor/Delivery Pack'),
        ('emergency', 'Emergency Pack'),
        ('general', 'General Medical Pack'),
    ]
    
    SURGERY_TYPE_CHOICES = [
        ('appendectomy', 'Appendectomy'),
        ('cholecystectomy', 'Cholecystectomy'),
        ('hernia_repair', 'Hernia Repair'),
        ('cesarean_section', 'Cesarean Section'),
        ('tonsillectomy', 'Tonsillectomy'),
        ('orthopedic_surgery', 'Orthopedic Surgery'),
        ('cardiac_surgery', 'Cardiac Surgery'),
        ('neurosurgery', 'Neurosurgery'),
        ('general_surgery', 'General Surgery'),
        ('plastic_surgery', 'Plastic Surgery'),
    ]
    
    LABOR_TYPE_CHOICES = [
        ('normal_delivery', 'Normal Delivery'),
        ('assisted_delivery', 'Assisted Delivery'),
        ('cesarean_delivery', 'Cesarean Delivery'),
        ('labor_induction', 'Labor Induction'),
        ('episiotomy', 'Episiotomy'),
        ('emergency_delivery', 'Emergency Delivery'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    pack_type = models.CharField(max_length=20, choices=PACK_TYPE_CHOICES)
    surgery_type = models.CharField(max_length=50, choices=SURGERY_TYPE_CHOICES, blank=True, null=True)
    labor_type = models.CharField(max_length=50, choices=LABOR_TYPE_CHOICES, blank=True, null=True)
    
    # Risk level and complexity
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ], default='medium')
    
    # Pricing
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Status and availability
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_pack_type_display()}"
    
    def get_total_cost(self):
        """Calculate total cost from pack items"""
        total = 0
        for item in self.items.all():
            total += item.medication.price * item.quantity
        return total
    
    def update_total_cost(self):
        """Update the total cost field"""
        self.total_cost = self.get_total_cost()
        self.save(update_fields=['total_cost'])
    
    def get_items_count(self):
        """Get number of different medications in this pack"""
        return self.items.count()
    
    def get_total_quantity(self):
        """Get total quantity of all items in this pack"""
        from django.db.models import Sum
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    def can_be_ordered(self):
        """Check if pack can be ordered (all medications available)"""
        for item in self.items.all():
            # Check if medication is available in sufficient quantity
            available_stock = MedicationInventory.objects.filter(
                medication=item.medication
            ).aggregate(total=models.Sum('stock_quantity'))['total'] or 0
            
            if available_stock < item.quantity:
                return False, f"Insufficient stock for {item.medication.name}"
        
        return True, "Pack can be ordered"
    
    class Meta:
        verbose_name = "Medical Pack"
        verbose_name_plural = "Medical Packs"
        ordering = ['pack_type', 'name']
        indexes = [
            models.Index(fields=['pack_type']),
            models.Index(fields=['surgery_type']),
            models.Index(fields=['labor_type']),
            models.Index(fields=['is_active']),
        ]


class PackItem(models.Model):
    """Model representing an item (medication/consumable) within a medical pack"""
    ITEM_TYPE_CHOICES = [
        ('medication', 'Medication'),
        ('consumable', 'Consumable'),
        ('equipment', 'Equipment'),
        ('supply', 'Medical Supply'),
    ]
    
    pack = models.ForeignKey(MedicalPack, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='medication')
    
    # Usage instructions
    usage_instructions = models.TextField(blank=True, null=True)
    is_critical = models.BooleanField(default=False, help_text="Critical item that cannot be substituted")
    is_optional = models.BooleanField(default=False, help_text="Optional item that can be omitted if not available")
    
    # Ordering within pack
    order = models.PositiveIntegerField(default=0, help_text="Order of usage in procedure")
    
    def __str__(self):
        return f"{self.medication.name} x{self.quantity} in {self.pack.name}"
    
    def get_total_cost(self):
        """Get total cost for this pack item"""
        return self.medication.price * self.quantity
    
    class Meta:
        verbose_name = "Pack Item"
        verbose_name_plural = "Pack Items"
        ordering = ['order', 'medication__name']
        unique_together = ['pack', 'medication']


class PackOrder(models.Model):
    """Model representing an order for a medical pack"""
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Collection'),
        ('dispensed', 'Dispensed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic information
    pack = models.ForeignKey(MedicalPack, on_delete=models.PROTECT)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='pack_orders')
    
    # Medical context
    surgery = models.ForeignKey('theatre.Surgery', on_delete=models.CASCADE, null=True, blank=True, related_name='pack_orders')
    labor_record = models.ForeignKey('labor.LaborRecord', on_delete=models.CASCADE, null=True, blank=True, related_name='pack_orders')
    
    # Ordering details
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ordered_packs')
    order_date = models.DateTimeField(auto_now_add=True)
    scheduled_date = models.DateTimeField(null=True, blank=True, help_text="When the pack is needed")
    
    # Status and processing
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_packs')
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_packs')
    
    # Timing
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes and instructions
    order_notes = models.TextField(blank=True, null=True)
    processing_notes = models.TextField(blank=True, null=True)
    
    # Linked prescription (when converted to individual items)
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='pack_orders')
    
    def __str__(self):
        return f"Pack Order: {self.pack.name} for {self.patient.get_full_name()}"
    
    def can_be_approved(self):
        """Check if pack order can be approved"""
        return self.status == 'pending'
    
    def can_be_processed(self):
        """Check if pack order can be processed"""
        return self.status in ['approved', 'pending'] and not self.processed_by
    
    def can_be_dispensed(self):
        """Check if pack order can be dispensed"""
        return self.status == 'ready' and not self.dispensed_by
    
    def create_prescription(self):
        """Convert pack order to individual prescription items"""
        from django.db import transaction
        
        if self.prescription:
            return self.prescription
        
        with transaction.atomic():
            # Create prescription
            prescription = Prescription.objects.create(
                patient=self.patient,
                doctor=self.ordered_by,
                prescription_date=timezone.now().date(),
                diagnosis=f"Pack order: {self.pack.name}",
                notes=f"Auto-generated from pack order #{self.id}",
                prescription_type='outpatient' if not self.surgery else 'inpatient'
            )
            
            # Create prescription items for each pack item
            for pack_item in self.pack.items.all():
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medication=pack_item.medication,
                    dosage='As per pack requirements',
                    frequency='As needed',
                    duration='Single use',
                    quantity=pack_item.quantity,
                    instructions=pack_item.usage_instructions or 'Use as directed for procedure'
                )
            
            # Link prescription to this pack order
            self.prescription = prescription
            self.save()
            
            return prescription
    
    def approve_order(self, user):
        """Approve the pack order"""
        if not self.can_be_approved():
            raise ValueError("Pack order cannot be approved in current status")
        
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.save()
    
    def process_order(self, user):
        """Process the pack order and create prescription"""
        if not self.can_be_processed():
            raise ValueError("Pack order cannot be processed in current status")
        
        # Create prescription from pack items
        prescription = self.create_prescription()
        
        self.status = 'ready'
        self.processed_by = user
        self.processed_at = timezone.now()
        self.save()
        
        return prescription
    
    def dispense_order(self, user):
        """Mark pack order as dispensed"""
        if not self.can_be_dispensed():
            raise ValueError("Pack order cannot be dispensed in current status")
        
        self.status = 'dispensed'
        self.dispensed_by = user
        self.dispensed_at = timezone.now()
        self.save()
    
    class Meta:
        verbose_name = "Pack Order"
        verbose_name_plural = "Pack Orders"
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
            models.Index(fields=['scheduled_date']),
        ]
