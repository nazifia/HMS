from django.db import models, transaction
from django.core.exceptions import ValidationError
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
    payment_date = models.DateTimeField(null=True, blank=True)
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
    submitted_for_approval_at = models.DateTimeField(null=True, blank=True)

    PRIORITY_LEVEL_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]
    priority_level = models.CharField(max_length=20, choices=PRIORITY_LEVEL_CHOICES, default='normal')
    expected_delivery_date = models.DateField(null=True, blank=True)

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

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('can_approve_purchases', 'Can approve purchase orders'),
            ('can_process_payments', 'Can process purchase payments'),
        ]

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


class PurchasePayment(models.Model):
    """Payment records for purchase orders"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('credit_card', 'Credit Card'),
        ('mobile_money', 'Mobile Money'),
        ('other', 'Other'),
    ]

    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_payments_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of ₦{self.amount} for Purchase #{self.purchase.invoice_number}"

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
        ('delivered', 'Delivered'),
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
    delivered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivered_transfers')
    delivered_at = models.DateTimeField(null=True, blank=True)
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

    def can_deliver(self):
        """Check if transfer can be marked as delivered"""
        return self.status == 'completed'

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

    AUTHORIZATION_STATUS_CHOICES = (
        ('not_required', 'Not Required'),
        ('required', 'Required'),
        ('pending', 'Pending Authorization'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_prescriptions')
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

    # NHIA Authorization fields
    requires_authorization = models.BooleanField(
        default=False,
        help_text="True if this NHIA patient prescription from non-NHIA consultation requires desk office authorization"
    )
    authorization_status = models.CharField(
        max_length=20,
        choices=AUTHORIZATION_STATUS_CHOICES,
        default='not_required',
        help_text="Status of authorization for this prescription"
    )
    authorization_code = models.ForeignKey(
        'nhia.AuthorizationCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions',
        help_text="Authorization code from desk office for NHIA patient prescription"
    )
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions',
        help_text="Link to the consultation this prescription was created from"
    )

    def __str__(self):
        return f"Prescription for {self.patient.get_full_name()} - {self.prescription_date}"

    def is_nhia_patient(self):
        """Check if the patient is an NHIA patient"""
        return hasattr(self.patient, 'nhia_info') and self.patient.nhia_info is not None

    def is_from_pack_order(self):
        """Check if this prescription was created from a pack order"""
        return self.notes and "Created from Pack Order #" in self.notes

    def get_pack_order(self):
        """Get the pack order that created this prescription"""
        if not self.is_from_pack_order():
            return None
        try:
            # Extract pack order ID from notes
            import re
            match = re.search(r'Created from Pack Order #(\d+)', self.notes)
            if match:
                pack_order_id = int(match.group(1))
                return PackOrder.objects.get(id=pack_order_id)
        except (PackOrder.DoesNotExist, ValueError):
            pass
        return None

    def is_from_surgery_pack(self):
        """Check if this prescription was created from a surgery pack order"""
        pack_order = self.get_pack_order()
        return pack_order and pack_order.surgery is not None

    def check_authorization_requirement(self):
        """
        Check if this prescription requires authorization.
        NHIA patients with prescriptions from non-NHIA units require authorization.

        Authorization is required if:
        1. Patient is NHIA patient, AND
        2. Either:
           a. Prescription is linked to a consultation that requires authorization, OR
           b. Prescription is created by a doctor NOT in NHIA department
        """
        if self.is_nhia_patient():
            # Check if linked to a consultation that requires authorization
            if self.consultation and self.consultation.requires_authorization:
                self.requires_authorization = True
                if not self.authorization_code:
                    self.authorization_status = 'required'
                return True

            # Check if prescribing doctor is from non-NHIA department
            if self.doctor:
                # Check if doctor is in NHIA department
                if hasattr(self.doctor, 'profile') and self.doctor.profile:
                    doctor_profile = self.doctor.profile
                    if doctor_profile.department:
                        # If doctor is NOT in NHIA department, authorization required
                        if doctor_profile.department.name.upper() != 'NHIA':
                            self.requires_authorization = True
                            if not self.authorization_code:
                                self.authorization_status = 'required'
                            return True

        self.requires_authorization = False
        self.authorization_status = 'not_required'
        return False

    def save(self, *args, **kwargs):
        """Override save to auto-check authorization requirement"""
        # Auto-check authorization requirement on save
        self.check_authorization_requirement()
        super().save(*args, **kwargs)

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
        """Check if prescription can be dispensed based on authorization and other conditions"""
        # Check if prescription is in a dispensable state
        if self.status in ['cancelled', 'dispensed']:
            return False, f'Cannot dispense prescription with status: {self.get_status_display()}'

        # Check authorization requirement for NHIA patients from non-NHIA consultations
        if self.requires_authorization:
            if not self.authorization_code:
                return False, 'Desk office authorization required for NHIA patient from non-NHIA unit. Please obtain authorization code before dispensing.'
            elif not self.authorization_code.is_valid():
                return False, f'Authorization code is {self.authorization_code.status}. Please obtain a valid authorization code.'

        # Payment verification removed - invoice will be created after dispensing based on actual quantities

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

    def get_dispensing_status(self):
        """Get the dispensing status of the prescription"""
        items = self.items.all()
        if not items.exists():
            return 'no_items'
        
        fully_dispensed_count = items.filter(is_dispensed=True).count()
        partially_dispensed_count = items.filter(
            is_dispensed=False, 
            quantity_dispensed_so_far__gt=0
        ).count()
        total_items = items.count()
        
        if fully_dispensed_count == total_items:
            return 'fully_dispensed'
        elif fully_dispensed_count > 0 or partially_dispensed_count > 0:
            return 'partially_dispensed'
        else:
            return 'not_dispensed'
    
    def get_dispensing_status_display(self):
        """Get human-readable dispensing status"""
        status = self.get_dispensing_status()
        status_map = {
            'fully_dispensed': 'Fully Dispensed',
            'partially_dispensed': 'Partially Dispensed',
            'not_dispensed': 'Not Dispensed',
            'no_items': 'No Items'
        }
        return status_map.get(status, 'Unknown')
    
    def get_dispensing_status_info(self):
        """Get detailed dispensing status information for display"""
        status = self.get_dispensing_status()
        
        if status == 'fully_dispensed':
            return {
                'status': 'fully_dispensed',
                'message': 'Fully Dispensed',
                'css_class': 'success',
                'icon': 'check-circle',
                'badge_color': 'success'
            }
        elif status == 'partially_dispensed':
            return {
                'status': 'partially_dispensed',
                'message': 'Partially Dispensed',
                'css_class': 'warning',
                'icon': 'clock',
                'badge_color': 'warning'
            }
        elif status == 'not_dispensed':
            return {
                'status': 'not_dispensed',
                'message': 'Not Dispensed',
                'css_class': 'secondary',
                'icon': 'hourglass-start',
                'badge_color': 'secondary'
            }
        else:
            return {
                'status': 'no_items',
                'message': 'No Items',
                'css_class': 'light',
                'icon': 'question-circle',
                'badge_color': 'light'
            }
    
    def get_dispensing_progress(self):
        """Get dispensing progress information"""
        items = self.items.all()
        if not items.exists():
            return {
                'total_items': 0,
                'fully_dispensed': 0,
                'partially_dispensed': 0,
                'not_dispensed': 0,
                'progress_percentage': 0
            }
        
        fully_dispensed = items.filter(is_dispensed=True).count()
        partially_dispensed = items.filter(
            is_dispensed=False,
            quantity_dispensed_so_far__gt=0
        ).count()
        not_dispensed = items.filter(
            is_dispensed=False,
            quantity_dispensed_so_far=0
        ).count()
        
        total_items = items.count()
        progress_percentage = (fully_dispensed / total_items * 100) if total_items > 0 else 0
        
        return {
            'total_items': total_items,
            'fully_dispensed': fully_dispensed,
            'partially_dispensed': partially_dispensed,
            'not_dispensed': not_dispensed,
            'progress_percentage': round(progress_percentage, 1)
        }
    
    def is_fully_dispensed(self):
        """Check if all items in the prescription are fully dispensed"""
        return self.get_dispensing_status() == 'fully_dispensed'
    
    def is_partially_dispensed(self):
        """Check if prescription has some items dispensed but not all"""
        return self.get_dispensing_status() == 'partially_dispensed'

    class Meta:
        indexes = [
            models.Index(fields=['patient'], name='idx_presc_patient'),
            models.Index(fields=['doctor'], name='idx_presc_doctor'),
            models.Index(fields=['status'], name='idx_presc_status'),
            models.Index(fields=['prescription_date'], name='idx_presc_date'),
            models.Index(fields=['payment_status'], name='idx_presc_payment'),
            models.Index(fields=['authorization_status'], name='idx_presc_auth'),
            models.Index(fields=['created_at'], name='idx_presc_created'),
        ]
        ordering = ['-prescription_date', '-created_at']

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100, blank=True, null=True, help_text="Dosage instructions (e.g., 500mg, 10ml)")
    frequency = models.CharField(max_length=100, blank=True, null=True, help_text="How often to take (e.g., twice daily, once daily)")
    duration = models.CharField(max_length=100, blank=True, null=True, help_text="How long to take (e.g., 7 days, 2 weeks)")
    instructions = models.TextField(blank=True, null=True, help_text="Special instructions for taking the medication")
    quantity = models.IntegerField(default=1, help_text="Quantity to dispense (managed at cart level)")
    quantity_dispensed_so_far = models.IntegerField(default=0)  # Added back to fix IntegrityError
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
        ('delivered', 'Delivered'),
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

            # If quantity reaches zero, handle according to business logic
            if active_inventory.stock_quantity == 0:
                # Option 1: Keep record with zero stock for audit trail
                active_inventory.save()
                # Log that item is now out of stock
                print(f"Item {self.medication.name} is now out of stock in {self.from_active_store.name}")

                # Option 2: Remove the record entirely (uncomment if preferred)
                # active_inventory.delete()
                # print(f"Removed {self.medication.name} from {self.from_active_store.name} (quantity reached zero)")
            else:
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

            # Create audit log for the transfer
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=user,
                    action="DISPENSARY_TRANSFER_EXECUTED",
                    details=f"Transferred {self.quantity} units of {self.medication.name} from {self.from_active_store.name} to {self.to_dispensary.name}"
                )
            except ImportError:
                # AuditLog not available, skip logging
                pass

    @classmethod
    def create_transfer(cls, medication, from_active_store, to_dispensary, quantity, requested_by, **kwargs):
        """Create a new dispensary transfer with validation"""
        from datetime import date

        # Check if sufficient stock exists
        active_inventory = ActiveStoreInventory.objects.filter(
            medication=medication,
            active_store=from_active_store,
            stock_quantity__gte=quantity
        ).first()

        if not active_inventory:
            raise ValueError(f"Insufficient stock in {from_active_store.name}. Required: {quantity}")

        # Check if medication is expired
        if active_inventory.expiry_date and active_inventory.expiry_date < date.today():
            raise ValueError(f"Cannot transfer expired medication. Batch {active_inventory.batch_number} expired on {active_inventory.expiry_date}")

        # Create the transfer
        transfer = cls.objects.create(
            medication=medication,
            from_active_store=from_active_store,
            to_dispensary=to_dispensary,
            quantity=quantity,
            requested_by=requested_by,
            batch_number=kwargs.get('batch_number', active_inventory.batch_number),
            expiry_date=kwargs.get('expiry_date', active_inventory.expiry_date),
            unit_cost=kwargs.get('unit_cost', active_inventory.unit_cost),
            notes=kwargs.get('notes', ''),
            status='pending'
        )

        return transfer

class PackOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='pack_orders')
    pack = models.ForeignKey('MedicalPack', on_delete=models.CASCADE)
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordered_pack_orders')
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_pack_orders')
    processed_at = models.DateTimeField(null=True, blank=True)
    order_notes = models.TextField(blank=True, null=True, help_text="Additional notes about this pack order")
    scheduled_date = models.DateTimeField(null=True, blank=True, help_text="When the pack is needed")
    surgery = models.ForeignKey('theatre.Surgery', on_delete=models.CASCADE, null=True, blank=True, related_name='pack_orders')
    labor_record = models.ForeignKey('labor.LaborRecord', on_delete=models.CASCADE, null=True, blank=True, related_name='pack_orders')

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

    # This method is now defined below after the MedicalPackItem model

    def get_total_value(self):
        """Calculate the total value of all items in the pack"""
        from decimal import Decimal
        total = Decimal('0.00')
        try:
            for item in self.items.all():
                total += Decimal(str(item.medication.price)) * item.quantity
        except AttributeError:
            # Fallback if no items relationship exists
            total = Decimal('0.00')
        return total

    def get_total_cost(self):
        """Calculate the total cost of all items in the pack (alias for get_total_value)"""
        return self.get_total_value()

    def get_item_count(self):
        """Get the total number of items in this pack"""
        try:
            return self.items.count()
        except AttributeError:
            return 0


class MedicalPackItem(models.Model):
    """Model representing items in a medical pack"""
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

    pack = models.ForeignKey(MedicalPack, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='medication')
    usage_instructions = models.TextField(blank=True, null=True, help_text="Instructions for using this item")
    is_critical = models.BooleanField(default=False, help_text="Critical items cannot be substituted")
    is_optional = models.BooleanField(default=False, help_text="Optional items can be omitted if unavailable")
    order = models.IntegerField(default=0, help_text="Order of usage in procedure (0 for no specific order)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['pack', 'medication']
        ordering = ['order', 'medication__name']
        verbose_name = 'Medical Pack Item'
        verbose_name_plural = 'Medical Pack Items'

    def __str__(self):
        return f"{self.pack.name} - {self.medication.name} - {self.quantity} units"

    def get_total_cost(self):
        """Calculate total cost for this item"""
        return self.medication.price * self.quantity

    def clean(self):
        from django.core.exceptions import ValidationError
        # Item cannot be both critical and optional
        if self.is_critical and self.is_optional:
            raise ValidationError('Item cannot be both critical and optional.')


class InterDispensaryTransfer(models.Model):
    """Model to track transfers of medications between dispensaries"""
    TRANSFER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='inter_dispensary_transfers')
    from_dispensary = models.ForeignKey('Dispensary', on_delete=models.CASCADE, related_name='outgoing_inter_transfers')
    to_dispensary = models.ForeignKey('Dispensary', on_delete=models.CASCADE, related_name='incoming_inter_transfers')
    quantity = models.IntegerField()
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='requested_inter_transfers')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_inter_transfers')
    transferred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='executed_inter_transfers')
    rejection_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inter-Dispensary Transfer'
        verbose_name_plural = 'Inter-Dispensary Transfers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['from_dispensary', 'status']),
            models.Index(fields=['to_dispensary', 'status']),
            models.Index(fields=['medication', 'status']),
        ]

    def __str__(self):
        return f"Inter-Dispensary Transfer: {self.quantity} {self.medication.name} from {self.from_dispensary.name} to {self.to_dispensary.name}"

    def can_approve(self):
        """Check if transfer can be approved"""
        return self.status == 'pending'

    def can_reject(self):
        """Check if transfer can be rejected"""
        return self.status == 'pending'

    def can_execute(self):
        """Check if transfer can be executed"""
        return self.status in ['pending', 'in_transit'] and self.approved_by is not None

    def is_self_transfer(self):
        """Check if this is a self-transfer (same dispensary)"""
        return self.from_dispensary == self.to_dispensary

    def check_availability(self):
        """Check if sufficient stock exists in source dispensary"""
        if self.is_self_transfer():
            return False, "Cannot transfer to same dispensary"
        
        # Check if medication inventory exists and has sufficient quantity
        inventory = MedicationInventory.objects.filter(
            medication=self.medication,
            dispensary=self.from_dispensary,
            stock_quantity__gte=self.quantity
        ).first()
        
        if not inventory:
            return False, f"Insufficient stock. Available: 0, Required: {self.quantity}"
        
        if inventory.stock_quantity < self.quantity:
            return False, f"Insufficient stock. Available: {inventory.stock_quantity}, Required: {self.quantity}"
        
        return True, "Transfer can be executed"

    def approve_transfer(self, approving_user):
        """Approve the transfer"""
        if not self.can_approve():
            raise ValueError("Transfer cannot be approved in current status")
        
        if self.is_self_transfer():
            raise ValueError("Cannot approve self-transfer")
        
        # Check availability
        can_transfer, message = self.check_availability()
        if not can_transfer:
            raise ValueError(message)
        
        self.status = 'in_transit'
        self.approved_by = approving_user
        self.approved_at = timezone.now()
        self.save()

    def reject_transfer(self, rejecting_user, reason=None):
        """Reject the transfer"""
        if not self.can_reject():
            raise ValueError("Transfer cannot be rejected in current status")
        
        self.status = 'rejected'
        self.approved_by = rejecting_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason or "Transfer rejected"
        self.save()

    def execute_transfer(self, executing_user):
        """Execute the transfer by moving stock from source to destination dispensary"""
        if not self.can_execute():
            raise ValueError("Transfer cannot be executed in current status")
        
        if self.is_self_transfer():
            raise ValueError("Cannot execute self-transfer")
        
        with transaction.atomic():
            # Check availability again
            can_transfer, message = self.check_availability()
            if not can_transfer:
                raise ValueError(message)
            
            # Find source inventory
            source_inventory = MedicationInventory.objects.get(
                medication=self.medication,
                dispensary=self.from_dispensary
            )
            
            # Find or create destination inventory
            dest_inventory, created = MedicationInventory.objects.get_or_create(
                medication=self.medication,
                dispensary=self.to_dispensary,
                defaults={
                    'stock_quantity': 0,
                    'reorder_level': self.medication.reorder_level
                }
            )
            
            # Update quantities
            source_inventory.stock_quantity -= self.quantity
            source_inventory.save()
            
            dest_inventory.stock_quantity += self.quantity
            dest_inventory.save()
            
            # Update transfer status
            self.status = 'completed'
            self.transferred_by = executing_user
            self.transferred_at = timezone.now()
            self.save()
            
            # Create audit log
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=executing_user,
                    action="INTER_DISPENSARY_TRANSFER_EXECUTED",
                    details=f"Transferred {self.quantity} units of {self.medication.name} from {self.from_dispensary.name} to {self.to_dispensary.name}"
                )
            except ImportError:
                # AuditLog not available, skip logging
                pass

    @classmethod
    def create_transfer(cls, medication, from_dispensary, to_dispensary, quantity, requested_by, **kwargs):
        """Create a new inter-dispensary transfer with validation"""
        if from_dispensary == to_dispensary:
            raise ValueError("Cannot transfer to same dispensary")
        
        # Check if sufficient stock exists
        can_transfer, message = cls.check_transfer_feasibility(medication, from_dispensary, quantity)
        if not can_transfer:
            raise ValueError(message)
        
        # Create the transfer
        transfer = cls.objects.create(
            medication=medication,
            from_dispensary=from_dispensary,
            to_dispensary=to_dispensary,
            quantity=quantity,
            requested_by=requested_by,
            **kwargs
        )
        
        return transfer

    @staticmethod
    def check_transfer_feasibility(medication, from_dispensary, quantity):
        """Check if a transfer is feasible"""
        inventory = MedicationInventory.objects.filter(
            medication=medication,
            dispensary=from_dispensary
        ).first()
        
        if not inventory:
            return False, f"No inventory found for {medication.name} in {from_dispensary.name}"
        
        if inventory.stock_quantity < quantity:
            return False, f"Insufficient stock. Available: {inventory.stock_quantity}, Required: {quantity}"
        
        return True, "Transfer is feasible"
