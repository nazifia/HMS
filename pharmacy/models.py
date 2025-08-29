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

# Inventory Models
class Dispensary(models.Model):
    """Model representing a pharmacy dispensary location"""
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

class BulkStore(models.Model):
    """Model representing the central bulk storage facility"""
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(help_text="Maximum storage capacity in units")
    temperature_controlled = models.BooleanField(default=False)
    humidity_controlled = models.BooleanField(default=False)
    security_level = models.CharField(max_length=20, choices=[
        ('basic', 'Basic'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], default='basic')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class ActiveStore(models.Model):
    """Model representing the active storage area within a dispensary"""
    dispensary = models.OneToOneField(Dispensary, on_delete=models.CASCADE, related_name='active_store')
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField(help_text="Maximum storage capacity in units")
    temperature_controlled = models.BooleanField(default=False)
    humidity_controlled = models.BooleanField(default=False)
    security_level = models.CharField(max_length=20, choices=[
        ('basic', 'Basic'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], default='basic')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class MedicationInventory(models.Model):
    """Legacy model for tracking medication inventory in dispensaries (maintained for backward compatibility)"""
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

class BulkStoreInventory(models.Model):
    """Model for tracking medication inventory in the bulk store"""
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='bulk_inventories')
    bulk_store = models.ForeignKey(BulkStore, on_delete=models.CASCADE, related_name='inventories')
    batch_number = models.CharField(max_length=50)
    stock_quantity = models.IntegerField(default=0)
    expiry_date = models.DateField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.medication.name} - Batch {self.batch_number}"

    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    def is_low_stock(self):
        return self.stock_quantity <= self.medication.reorder_level

class ActiveStoreInventory(models.Model):
    """Model for tracking medication inventory in active stores"""
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='active_inventories')
    active_store = models.ForeignKey(ActiveStore, on_delete=models.CASCADE, related_name='inventories')
    batch_number = models.CharField(max_length=50)
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10, help_text="Minimum stock level before reorder is needed")
    expiry_date = models.DateField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_restock_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.medication.name} in {self.active_store.name}"

    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

class MedicationTransfer(models.Model):
    """Model to track transfers of medications from bulk store to active store"""
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
        """Execute the transfer by moving stock from bulk store to active store"""
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
            bulk_inventory.save()

            # Add to active store inventory
            active_inventory, created = ActiveStoreInventory.objects.get_or_create(
                medication=self.medication,
                active_store=self.to_active_store,
                batch_number=self.batch_number,
                defaults={
                    'stock_quantity': 0,
                    'expiry_date': self.expiry_date or bulk_inventory.expiry_date,
                    'unit_cost': self.unit_cost or bulk_inventory.unit_cost
                }
            )

            if created:
                active_inventory.stock_quantity = self.quantity
            else:
                active_inventory.stock_quantity += self.quantity
            
            active_inventory.save()

            # Update transfer status
            self.status = 'completed'
            self.transferred_by = user
            self.transferred_at = timezone.now()
            self.save()

class DispensingLog(models.Model):
    """Model to track when medications are dispensed to patients"""
    prescription_item = models.ForeignKey('PrescriptionItem', on_delete=models.CASCADE, related_name='dispensing_logs')
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='dispensing_actions')
    dispensed_quantity = models.IntegerField()
    dispensed_date = models.DateTimeField(default=timezone.now)
    unit_price_at_dispense = models.DecimalField(max_digits=10, decimal_places=2)
    total_price_for_this_log = models.DecimalField(max_digits=10, decimal_places=2)
    dispensary = models.ForeignKey('Dispensary', on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensing_logs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispensed {self.dispensed_quantity} of {self.prescription_item.medication.name} on {self.dispensed_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-dispensed_date']
        verbose_name = "Dispensing Log"
        verbose_name_plural = "Dispensing Logs"

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
                elif self.invoice.status == 'unpaid':
                    return {
                        'status': 'unpaid',
                        'message': 'Payment pending',
                        'css_class': 'danger',
                        'icon': 'exclamation-circle'
                    }
                elif self.invoice.status == 'waived':
                    return {
                        'status': 'waived',
                        'message': 'Payment waived',
                        'css_class': 'info',
                        'icon': 'info-circle'
                    }
            return {
                'status': 'unpaid',
                'message': 'Payment required',
                'css_class': 'danger',
                'icon': 'exclamation-circle'
            }

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100, blank=True, null=True, help_text="Dosage instructions (e.g., 500mg, 10ml)")
    frequency = models.CharField(max_length=100, blank=True, null=True, help_text="How often to take (e.g., twice daily, once daily)")
    duration = models.CharField(max_length=100, blank=True, null=True, help_text="How long to take (e.g., 7 days, 2 weeks)")
    instructions = models.TextField(blank=True, null=True, help_text="Special instructions for taking the medication")
    quantity = models.IntegerField()
    is_dispensed = models.BooleanField(default=False)
    dispensed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.medication.name} - {self.quantity} units"

    @property
    def remaining_quantity_to_dispense(self):
        """Calculate how many units still need to be dispensed"""
        if self.is_dispensed:
            return 0
        # Sum up all dispensing logs for this item
        total_dispensed = self.dispensing_logs.aggregate(
            total=models.Sum('dispensed_quantity')
        )['total'] or 0
        return max(0, self.quantity - total_dispensed)

class Pack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    medications = models.ManyToManyField(Medication, through='PackItem')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PackItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('medication', 'Medication'),
        ('supply', 'Medical Supply'),
        ('equipment', 'Equipment'),
    ]
    
    CRITICALITY_CHOICES = [
        ('critical', 'Critical'),
        ('important', 'Important'),
        ('optional', 'Optional'),
    ]

    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='medication')
    usage_instructions = models.TextField(blank=True, null=True, help_text="Instructions for using this item")
    is_critical = models.BooleanField(default=False, help_text="Critical items cannot be substituted")
    is_optional = models.BooleanField(default=False, help_text="Optional items can be omitted if unavailable")
    order = models.IntegerField(default=0, help_text="Order of usage in procedure (0 for no specific order)")

    def __str__(self):
        return f"{self.pack.name} - {self.medication.name} - {self.quantity} units"

    def clean(self):
        # Item cannot be both critical and optional
        if self.is_critical and self.is_optional:
            raise ValidationError('Item cannot be both critical and optional.')

class DispensaryTransfer(models.Model):
    """Model to track transfers of medications from active store to dispensary"""
    TRANSFER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='dispensary_transfers')
    from_active_store = models.ForeignKey('ActiveStore', on_delete=models.CASCADE, related_name='outgoing_dispensary_transfers')
    to_dispensary = models.ForeignKey('Dispensary', on_delete=models.CASCADE, related_name='incoming_dispensary_transfers')
    quantity = models.IntegerField()
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='requested_dispensary_transfers')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_dispensary_transfers')
    transferred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='executed_dispensary_transfers')
    notes = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dispensary Transfer {self.quantity} {self.medication.name} from {self.from_active_store.dispensary.name} to {self.to_dispensary.name}"

    def can_approve(self):
        """Check if transfer can be approved"""
        return self.status == 'pending'

    def can_execute(self):
        """Check if transfer can be executed"""
        return self.status in ['pending', 'in_transit'] and self.approved_by is not None

    def execute_transfer(self, user):
        """Execute the transfer by moving stock from active store to dispensary"""
        if not self.can_execute():
            raise ValueError("Transfer cannot be executed in current status")

        with transaction.atomic():
            # Import models here to avoid circular imports
            from .models import ActiveStoreInventory, MedicationInventory
            
            # Find active store inventory
            active_inventory = ActiveStoreInventory.objects.filter(
                medication=self.medication,
                active_store=self.from_active_store,
                batch_number=self.batch_number,
                stock_quantity__gte=self.quantity
            ).first()

            if not active_inventory:
                raise ValueError("Insufficient stock in active store")

            # Reduce active store inventory
            active_inventory.stock_quantity -= self.quantity
            active_inventory.save()

            # Add to dispensary inventory (legacy model for backward compatibility)
            dispensary_inventory, created = MedicationInventory.objects.get_or_create(
                medication=self.medication,
                dispensary=self.to_dispensary,
                defaults={
                    'stock_quantity': 0,
                    'reorder_level': 10
                }
            )

            dispensary_inventory.stock_quantity += self.quantity
            dispensary_inventory.last_restock_date = timezone.now()
            dispensary_inventory.save()

            # Update transfer status
            self.status = 'completed'
            self.transferred_by = user
            self.transferred_at = timezone.now()
            self.save()

class PackOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='pack_orders')
    pack = models.ForeignKey(Pack, on_delete=models.CASCADE)
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordered_pack_orders')
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_pack_orders')
    processed_at = models.DateTimeField(null=True, blank=True)
    order_notes = models.TextField(blank=True, null=True, help_text="Additional notes about this pack order")
    scheduled_date = models.DateTimeField(null=True, blank=True, help_text="When the pack is needed")

    def __str__(self):
        return f"Pack Order #{self.id} - {self.pack.name}"

    def can_be_processed(self):
        return self.status == 'pending'

    def process_order(self, user):
        """Process the pack order and create prescription"""
        if not self.can_be_processed():
            raise ValueError("Pack order cannot be processed in current status")
        
        # Check if all medications in the pack are available in the active store
        # If not, attempt to transfer from bulk store to active store
        missing_medications = []
        for pack_item in self.pack.items.all():
            # Check if medication is available in sufficient quantity in active stores
            available_stock = ActiveStoreInventory.objects.filter(
                medication=pack_item.medication
            ).aggregate(total=models.Sum('stock_quantity'))['total'] or 0
            
            if available_stock < pack_item.quantity:
                missing_medications.append({
                    'medication': pack_item.medication,
                    'required': pack_item.quantity,
                    'available': available_stock,
                    'shortage': pack_item.quantity - available_stock
                })
        
        # If there are missing medications, try to transfer from bulk store
        if missing_medications:
            # Import models here to avoid circular imports
            from .models import Dispensary, ActiveStore, BulkStore, BulkStoreInventory, MedicationTransfer
            try:
                # Try to get user's associated dispensary
                if hasattr(user, 'profile') and hasattr(user.profile, 'dispensary'):
                    dispensary = user.profile.dispensary
                else:
                    # Use default dispensary
                    dispensary = Dispensary.objects.filter(is_active=True).first()
                
                if dispensary:
                    active_store = getattr(dispensary, 'active_store', None)
                    if not active_store:
                        # Create active store if it doesn't exist
                        active_store = ActiveStore.objects.create(
                            dispensary=dispensary,
                            name=f"Active Store - {dispensary.name}",
                            capacity=1000
                        )
                    
                    # Get bulk store (use main bulk store)
                    bulk_store = BulkStore.objects.filter(is_active=True).first()
                    
                    if bulk_store:
                        # For each missing medication, create a transfer request
                        for missing in missing_medications:
                            medication = missing['medication']
                            shortage = missing['shortage']
                            
                            # Check if bulk store has this medication
                            bulk_inventory = BulkStoreInventory.objects.filter(
                                medication=medication,
                                bulk_store=bulk_store,
                                stock_quantity__gte=shortage
                            ).first()
                            
                            if bulk_inventory:
                                # Create transfer request
                                transfer = MedicationTransfer.objects.create(
                                    medication=medication,
                                    from_bulk_store=bulk_store,
                                    to_active_store=active_store,
                                    quantity=shortage,
                                    batch_number=bulk_inventory.batch_number,
                                    expiry_date=bulk_inventory.expiry_date,
                                    unit_cost=bulk_inventory.unit_cost,
                                    status='pending',
                                    requested_by=user
                                )
                                
                                # Approve and execute transfer immediately
                                transfer.approved_by = user
                                transfer.approved_at = timezone.now()
                                transfer.status = 'in_transit'
                                transfer.save()
                                
                                try:
                                    transfer.execute_transfer(user)
                                except Exception as e:
                                    # Log the error but continue processing
                                    pass  # In a real implementation, you might want to log this
            except Exception as e:
                # Continue with processing even if transfers fail
                pass  # In a real implementation, you might want to log this
        
        # Now, ensure that medications are moved from active store to the respective dispensary
        # This is for cases where we want to ensure the dispensary has the required medications
        try:
            # Try to get user's associated dispensary
            if hasattr(user, 'profile') and hasattr(user.profile, 'dispensary'):
                dispensary = user.profile.dispensary
            else:
                # Use default dispensary
                dispensary = Dispensary.objects.filter(is_active=True).first()
            
            if dispensary:
                active_store = getattr(dispensary, 'active_store', None)
                if active_store:
                    # For each medication in the pack, ensure it's available in the dispensary
                    for pack_item in self.pack.items.all():
                        medication = pack_item.medication
                        required_quantity = pack_item.quantity
                        
                        # Check if medication is available in the active store
                        active_inventory = ActiveStoreInventory.objects.filter(
                            medication=medication,
                            active_store=active_store,
                            stock_quantity__gte=required_quantity
                        ).first()
                        
                        if not active_inventory:
                            # If not available in active store, check if it's in legacy inventory
                            try:
                                legacy_inventory = MedicationInventory.objects.get(
                                    medication=medication,
                                    dispensary=dispensary,
                                    stock_quantity__gte=required_quantity
                                )
                                # If found in legacy inventory, we'll use that for dispensing
                                # No transfer needed in this case
                                pass
                            except MedicationInventory.DoesNotExist:
                                # Medication not available in either inventory
                                # This will be handled during prescription dispensing
                                pass
                        else:
                            # Medication is available in active store
                            # Check if it's also available in the dispensary (legacy inventory)
                            # If not, create a transfer from active store to dispensary
                            try:
                                dispensary_inventory = MedicationInventory.objects.get(
                                    medication=medication,
                                    dispensary=dispensary
                                )
                                # If dispensary already has this medication, check if quantity is sufficient
                                if dispensary_inventory.stock_quantity < required_quantity:
                                    # Need to transfer more from active store to dispensary
                                    shortage = required_quantity - dispensary_inventory.stock_quantity
                                    
                                    # Create dispensary transfer request
                                    from .models import DispensaryTransfer
                                    dispensary_transfer = DispensaryTransfer.objects.create(
                                        medication=medication,
                                        from_active_store=active_store,
                                        to_dispensary=dispensary,
                                        quantity=shortage,
                                        batch_number=active_inventory.batch_number,
                                        expiry_date=active_inventory.expiry_date,
                                        unit_cost=active_inventory.unit_cost,
                                        status='pending',
                                        requested_by=user
                                    )
                                    
                                    # Approve and execute transfer immediately
                                    dispensary_transfer.approved_by = user
                                    dispensary_transfer.approved_at = timezone.now()
                                    dispensary_transfer.status = 'in_transit'
                                    dispensary_transfer.save()
                                    
                                    try:
                                        dispensary_transfer.execute_transfer(user)
                                    except Exception as e:
                                        # Log the error but continue processing
                                        pass  # In a real implementation, you might want to log this
                            except MedicationInventory.DoesNotExist:
                                # Dispensary doesn't have this medication at all
                                # Create a transfer from active store to dispensary
                                from .models import DispensaryTransfer
                                dispensary_transfer = DispensaryTransfer.objects.create(
                                    medication=medication,
                                    from_active_store=active_store,
                                    to_dispensary=dispensary,
                                    quantity=required_quantity,
                                    batch_number=active_inventory.batch_number,
                                    expiry_date=active_inventory.expiry_date,
                                    unit_cost=active_inventory.unit_cost,
                                    status='pending',
                                    requested_by=user
                                )
                                
                                # Approve and execute transfer immediately
                                dispensary_transfer.approved_by = user
                                dispensary_transfer.approved_at = timezone.now()
                                dispensary_transfer.status = 'in_transit'
                                dispensary_transfer.save()
                                
                                try:
                                    dispensary_transfer.execute_transfer(user)
                                except Exception as e:
                                    # Log the error but continue processing
                                    pass  # In a real implementation, you might want to log this
        except Exception as e:
            # Continue processing even if this check fails
            pass
        
        # Create prescription from pack items
        prescription = self.create_prescription()
        
        self.status = 'ready'
        self.processed_by = user
        self.processed_at = timezone.now()
        self.save()
        
        return prescription

    def create_prescription(self):
        """Create a prescription from pack items"""
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.ordered_by,
            prescription_date=timezone.now(),
            status='approved',
            payment_status='unpaid',
            prescription_type='outpatient',
            notes=f"Created from Pack Order #{self.id}"
        )
        
        for pack_item in self.pack.items.all():
            PrescriptionItem.objects.create(
                prescription=prescription,
                medication=pack_item.medication,
                quantity=pack_item.quantity
            )
        
        return prescription

class MedicalPack(models.Model):
    """Model representing a predefined pack of medications and supplies for specific medical procedures"""
    PACK_TYPE_CHOICES = [
        ('surgery', 'Surgery'),
        ('labor', 'Labor/Delivery'),
        ('emergency', 'Emergency'),
        ('routine', 'Routine Care'),
    ]
    
    SURGERY_TYPE_CHOICES = [
        ('appendectomy', 'Appendectomy'),
        ('cholecystectomy', 'Cholecystectomy'),
        ('hernia_repair', 'Hernia Repair'),
        ('cesarean_section', 'Cesarean Section'),
        ('tonsillectomy', 'Tonsillectomy'),
    ]
    
    LABOR_TYPE_CHOICES = [
        ('normal_delivery', 'Normal Delivery'),
        ('assisted_delivery', 'Assisted Delivery'),
        ('cesarean_section', 'Cesarean Section'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    pack_type = models.CharField(max_length=20, choices=PACK_TYPE_CHOICES)
    surgery_type = models.CharField(max_length=50, choices=SURGERY_TYPE_CHOICES, blank=True, null=True)
    labor_type = models.CharField(max_length=50, choices=LABOR_TYPE_CHOICES, blank=True, null=True)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='medium')
    requires_approval = models.BooleanField(default=False, help_text="Check if this pack requires approval before processing")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Medical Pack"
        verbose_name_plural = "Medical Packs"

    def get_item_count(self):
        """Get the total number of items in this pack"""
        return self.items.count()

    def get_total_value(self):
        """Calculate the total value of all items in the pack"""
        total = 0
        for item in self.items.all():
            total += item.medication.price * item.quantity
        return total
