import logging
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    MedicationCategory, Medication, Supplier, Purchase,
    PurchaseItem, Prescription, PrescriptionItem, DispensingLog, Dispensary, MedicationInventory
)
from patients.models import Patient
from django.contrib.auth import get_user_model
from accounts.models import CustomUser
from billing.models import Payment, Invoice
User = get_user_model()

class MedicationCategoryForm(forms.ModelForm):
    """Form for creating and editing medication categories"""

    class Meta:
        model = MedicationCategory
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class MedicationForm(forms.ModelForm):
    """Form for creating and editing medications"""

    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()})
    )

    class Meta:
        model = Medication
        fields = [
            'name', 'generic_name', 'category', 'description', 'dosage_form',
            'strength', 'manufacturer', 'price',
            'expiry_date', 'side_effects', 'precautions', 'storage_instructions',
            'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'side_effects': forms.Textarea(attrs={'rows': 3}),
            'precautions': forms.Textarea(attrs={'rows': 3}),
        }

class SupplierForm(forms.ModelForm):
    """Form for creating and editing suppliers"""

    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'email', 'phone_number', 'address',
            'city', 'state', 'country', 'is_active'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class PurchaseForm(forms.ModelForm):
    """Form for creating and editing purchases"""

    purchase_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Purchase
        fields = [
            'supplier', 'purchase_date', 'invoice_number', 'total_amount',
            'payment_status', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
        }

class PurchaseItemForm(forms.ModelForm):
    """Form for creating and editing purchase items"""

    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()})
    )

    class Meta:
        model = PurchaseItem
        fields = [
            'medication', 'quantity', 'unit_price', 'batch_number', 'expiry_date'
        ]

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        if quantity and unit_price:
            cleaned_data['total_price'] = quantity * unit_price

        return cleaned_data

class PrescriptionForm(forms.ModelForm):
    """Form for creating and editing prescriptions"""

    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Patient"
    )

    doctor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, roles__name='doctor').distinct(),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Doctor"
    )

    prescription_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        patient_id = None
        if request:
            patient_id = request.GET.get('patient')
        if not patient_id:
            patient_id = self.initial.get('patient')
        if patient_id:
            self.fields['patient'].initial = patient_id
            # Keep patient field visible but pre-selected for user convenience
        # All users can select any doctor now
        # Ensure all patients are available for selection
        self.fields['patient'].queryset = Patient.objects.all()

    class Meta:
        model = Prescription
        fields = [
            'patient', 'doctor', 'prescription_date', 'diagnosis', 'notes', 'prescription_type'
        ]
        widgets = {
            'diagnosis': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'prescription_type': forms.Select(attrs={'class': 'form-select'}),
        }

class PrescriptionItemForm(forms.ModelForm):
    """Form for creating and editing prescription items"""

    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Medication"
    )

    class Meta:
        model = PrescriptionItem
        fields = [
            'medication', 'dosage', 'frequency', 'duration', 'instructions', 'quantity'
        ]
        widgets = {
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        # Removed stock check here as it will be handled during dispensing
        # medication = self.cleaned_data.get('medication')
        # if quantity and medication:
        #     if quantity > medication.stock_quantity:
        #         raise forms.ValidationError(f"Not enough stock. Available: {medication.stock_quantity}")
        return quantity

import logging

import logging

class DispenseItemForm(forms.Form):
    """Form for a single item in the dispensing process."""
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    dispense_this_item = forms.BooleanField(required=False, label="Dispense")
    quantity_to_dispense = forms.IntegerField(min_value=0, required=False, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width: 70px;'}))
    dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        required=False,
        empty_label="Select Dispensary",
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )
    stock_quantity_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'}))

    def __init__(self, *args, **kwargs):
        self.prescription_item = kwargs.pop('prescription_item', None)
        self.selected_dispensary = kwargs.pop('selected_dispensary', None)
        super(DispenseItemForm, self).__init__(*args, **kwargs)

        if self.prescription_item:
            logging.debug(f"DispenseItemForm __init__: Initializing for item ID {self.prescription_item.id}")
            logging.debug(f"  Medication: {self.prescription_item.medication.name}")
            logging.debug(f"  Remaining Qty: {self.prescription_item.remaining_quantity_to_dispense}")
            logging.debug(f"  Is Dispensed: {self.prescription_item.is_dispensed}")
            self.fields['item_id'].initial = self.prescription_item.id
            remaining_qty = self.prescription_item.remaining_quantity_to_dispense
            
            is_fully_dispensed = self.prescription_item.is_dispensed # Based on new logic (qty_dispensed_so_far >= quantity)
            
            # Get available stock from MedicationInventory for the selected dispensary
            available_stock = 0
            if self.selected_dispensary:
                try:
                    med_inventory = MedicationInventory.objects.get(
                        medication=self.prescription_item.medication,
                        dispensary=self.selected_dispensary
                    )
                    available_stock = med_inventory.stock_quantity
                    logging.debug(f"  Available stock at selected dispensary ({self.selected_dispensary.name}): {available_stock}")
                except MedicationInventory.DoesNotExist:
                    available_stock = 0 # No inventory for this medication at this dispensary
                    logging.debug(f"  No inventory found for {self.prescription_item.medication.name} at {self.selected_dispensary.name}")

            # Store available stock as instance variable for template access
            self.available_stock = available_stock
            
            can_be_dispensed = remaining_qty > 0 and available_stock > 0 and not is_fully_dispensed
            logging.debug(f"  Can be dispensed: {can_be_dispensed}")

            if not can_be_dispensed:
                self.fields['dispense_this_item'].widget.attrs['disabled'] = True
                self.fields['quantity_to_dispense'].widget.attrs['disabled'] = True
                self.fields['quantity_to_dispense'].initial = 0
                if is_fully_dispensed:
                    self.fields['dispense_this_item'].label = "Fully Dispensed"
                elif available_stock == 0:
                     self.fields['dispense_this_item'].label = "Out of Stock"
            else:
                # Default to remaining quantity, capped by current stock
                initial_qty_to_dispense = min(remaining_qty, available_stock)
                self.fields['quantity_to_dispense'].initial = initial_qty_to_dispense
                self.fields['quantity_to_dispense'].widget.attrs['max'] = min(remaining_qty, available_stock)
                self.fields['quantity_to_dispense'].widget.attrs['min'] = 0 # Allow 0 if user unchecks

            # Set initial value for dispensary field if selected_dispensary is provided
            if self.selected_dispensary:
                self.fields['dispensary'].initial = self.selected_dispensary
                self.fields['dispensary'].widget = forms.HiddenInput()
                self.fields['dispensary'].required = True # Make it required if pre-selected
            
            # Set the stock quantity display field
            if self.selected_dispensary:
                self.fields['stock_quantity_display'].initial = f"{available_stock} in stock"
            else:
                self.fields['stock_quantity_display'].initial = "Select a dispensary"

        else:
            logging.debug("DispenseItemForm __init__: prescription_item is None")

    @property
    def p_item(self):
        """Expose the prescription_item to the template."""
        logging.debug(f"Accessing p_item property. Item ID: {self.prescription_item.id if self.prescription_item else 'None'}")
        return self.prescription_item

    @property
    def stock_available(self):
        """Expose the available stock to the template."""
        return getattr(self, 'available_stock', 0)

    def clean(self):
        cleaned_data = super().clean()
        dispense_this_item = cleaned_data.get('dispense_this_item')
        quantity_to_dispense = cleaned_data.get('quantity_to_dispense')
        dispensary = cleaned_data.get('dispensary') # Get dispensary from cleaned_data


        logging.debug(f"DispenseItemForm clean: Item ID {self.prescription_item.id if self.prescription_item else 'None'}")
        logging.debug(f"  dispense_this_item: {dispense_this_item}, quantity_to_dispense: {quantity_to_dispense}, dispensary: {dispensary}")

        if not self.prescription_item:
            self.add_error(None, "Form not initialized with a prescription item.")
            logging.error("DispenseItemForm clean: Form not initialized with a prescription item.")
            return cleaned_data

        remaining_qty = self.prescription_item.remaining_quantity_to_dispense
        is_fully_dispensed = self.prescription_item.is_dispensed

        # Get available stock from MedicationInventory for the selected dispensary
        available_stock = 0
        if dispensary: # Use the cleaned_data dispensary here
            try:
                med_inventory = MedicationInventory.objects.get(
                    medication=self.prescription_item.medication,
                    dispensary=dispensary
                )
                available_stock = med_inventory.stock_quantity
            except MedicationInventory.DoesNotExist:
                available_stock = 0
        logging.debug(f"  Remaining Qty: {remaining_qty}, Is Fully Dispensed: {is_fully_dispensed}, Available Stock: {available_stock}")
        print(f"DEBUG: DispenseItemForm clean - Item ID: {self.prescription_item.id if self.prescription_item else 'None'}")
        print(f"DEBUG:   Remaining Qty: {remaining_qty}")
        print(f"DEBUG:   Is Fully Dispensed: {is_fully_dispensed}")
        print(f"DEBUG:   Available Stock: {available_stock}")

        can_be_dispensed = remaining_qty > 0 and available_stock > 0 and not is_fully_dispensed

        if dispense_this_item and not can_be_dispensed:
            error_message = ""
            if is_fully_dispensed:
                error_message = "This item is already fully dispensed."
            elif remaining_qty <= 0:
                error_message = "No remaining quantity to dispense for this item."
            elif available_stock <= 0:
                error_message = "This item is out of stock at the selected dispensary."
            
            if error_message:
                raise forms.ValidationError(error_message)

        if dispense_this_item:
            if not dispensary:
                self.add_error('dispensary', 'Please select a dispensary for this item.')
                logging.warning(f"  Validation Error: Dispensary not selected for item {self.prescription_item.id}.")
            if quantity_to_dispense is None or quantity_to_dispense <= 0:
                self.add_error('quantity_to_dispense', 'Quantity must be greater than 0 if selected for dispensing.')
                logging.warning(f"  Validation Error: Invalid quantity for item {self.prescription_item.id}.")
            elif quantity_to_dispense > remaining_qty:
                self.add_error('quantity_to_dispense', f'Cannot dispense more than remaining ({remaining_qty}).')
                logging.warning(f"  Validation Error: Quantity ({quantity_to_dispense}) > remaining ({remaining_qty}) for item {self.prescription_item.id}.")
            elif quantity_to_dispense > available_stock:
                self.add_error('quantity_to_dispense', f'Not enough stock at selected dispensary. Available: {available_stock}.')
                logging.warning(f"  Validation Error: Quantity ({quantity_to_dispense}) > available stock ({available_stock}) for item {self.prescription_item.id}.")
        
        return cleaned_data
        
        

from django.forms.formsets import BaseFormSet

class BaseDispenseItemFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.prescription_items_qs = kwargs.pop('prescription_items_qs', None)
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if self.prescription_items_qs and index < len(self.prescription_items_qs):
            form.prescription_item = self.prescription_items_qs[index]
            # Re-initialize the form with the prescription_item and selected_dispensary
            if hasattr(self, 'form_kwargs') and self.form_kwargs:
                selected_dispensary = self.form_kwargs.get('selected_dispensary')
                form.__init__(
                    data=form.data if form.is_bound else None,
                    files=form.files if form.is_bound else None,
                    initial=form.initial,
                    prefix=form.prefix,
                    prescription_item=form.prescription_item,
                    selected_dispensary=selected_dispensary
                )
        else:
            # Handle the case where prescription_items_qs is not provided
            # This might indicate an error or a different use case for the formset
            form.prescription_item = None # Or raise an error, depending on desired behavior

    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        selected_items_count = 0
        for form in self.forms:
            if form.cleaned_data.get('dispense_this_item') and form.cleaned_data.get('quantity_to_dispense', 0) > 0:
                selected_items_count += 1
        
        if selected_items_count == 0:
            raise forms.ValidationError("You must select at least one item and specify a quantity greater than 0 to dispense.")

class MedicationSearchForm(forms.Form):
    """Form for searching medications"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by name, generic name, or category'})
    )

    category = forms.ModelChoiceField(
        queryset=MedicationCategory.objects.all(),
        required=False,
        empty_label="All Categories"
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        required=False
    )

class PrescriptionSearchForm(forms.Form):
    """Enhanced form for searching prescriptions with comprehensive filters"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by patient name, ID, or phone number',
            'class': 'form-control'
        }),
        label='Patient Search'
    )

    patient_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter patient ID/number',
            'class': 'form-control'
        }),
        label='Patient Number'
    )

    medication_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by medication name',
            'class': 'form-control'
        }),
        label='Medication Name'
    )

    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('dispensed', 'Dispensed'),
            ('partially_dispensed', 'Partially Dispensed'),
            ('cancelled', 'Cancelled'),
            ('on_hold', 'On Hold'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Status'
    )

    payment_status = forms.ChoiceField(
        choices=[('', 'All Payment Statuses')] + [
            ('unpaid', 'Unpaid'),
            ('paid', 'Paid'),
            ('waived', 'Waived'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Payment Status'
    )

    doctor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, roles__name='doctor').distinct(),
        required=False,
        empty_label="All Doctors",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Doctor'
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='From Date'
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='To Date'
    )


class DispensedItemsSearchForm(forms.Form):
    """Form for searching dispensed items with advanced filters"""

    medication_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Type first few letters of medication name...',
            'class': 'form-control',
            'autocomplete': 'off'
        }),
        help_text='Search by medication name (supports partial matching)'
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text='Start date for dispensing period'
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text='End date for dispensing period'
    )

    patient_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Patient name...',
            'class': 'form-control'
        }),
        help_text='Search by patient name'
    )

    dispensed_by = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        required=False,
        empty_label="All Staff",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter by staff member who dispensed'
    )

    category = forms.ModelChoiceField(
        queryset=MedicationCategory.objects.all().order_by('name'),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter by medication category'
    )

    min_quantity = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min quantity'
        }),
        help_text='Minimum dispensed quantity'
    )

    max_quantity = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max quantity'
        }),
        help_text='Maximum dispensed quantity'
    )

    prescription_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Prescription.PRESCRIPTION_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter by prescription type'
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        min_quantity = cleaned_data.get('min_quantity')
        max_quantity = cleaned_data.get('max_quantity')

        # Validate date range
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date.")

        # Validate quantity range
        if min_quantity and max_quantity and min_quantity > max_quantity:
            raise forms.ValidationError("Minimum quantity cannot be greater than maximum quantity.")

        return cleaned_data


class DispensaryForm(forms.ModelForm):
    """Form for creating and editing dispensaries"""

    class Meta:
        model = Dispensary
        fields = ['name', 'location', 'description', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter dispensary name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'manager': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter manager choices to only show staff users
        self.fields['manager'].queryset = CustomUser.objects.filter(is_active=True)
        self.fields['manager'].empty_label = "Select Manager (Optional)"

class PrescriptionPaymentForm(forms.ModelForm):
    """Form for processing payments for prescriptions with dual payment method support"""

    PAYMENT_SOURCE_CHOICES = [
        ('direct', 'Direct Payment'),
        ('patient_wallet', 'Patient Wallet'),
    ]

    payment_source = forms.ChoiceField(
        choices=PAYMENT_SOURCE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='direct',
        help_text="Choose payment method"
    )

    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter payment amount',
                'step': '0.01',
                'min': '0.01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any payment notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Extract custom parameters
        self.invoice = kwargs.pop('invoice', None)
        self.prescription = kwargs.pop('prescription', None)
        self.patient_wallet = kwargs.pop('patient_wallet', None)

        super().__init__(*args, **kwargs)

        # Set payment method choices
        from billing.models import Invoice
        self.fields['payment_method'].choices = Invoice.PAYMENT_METHOD_CHOICES

        # Update payment source field if wallet is available
        if self.patient_wallet:
            wallet_balance = self.patient_wallet.balance
            self.fields['payment_source'].help_text = f'Wallet Balance: ₦{wallet_balance:.2f}'

        # Set initial amount if invoice is provided
        if self.invoice:
            remaining_amount = self.invoice.get_balance()
            self.fields['amount'].initial = remaining_amount

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        payment_source = cleaned_data.get('payment_source')
        payment_method = cleaned_data.get('payment_method')

        if not amount:
            raise ValidationError("Payment amount is required.")

        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")

        # Validate against invoice balance
        if self.invoice:
            remaining_balance = self.invoice.get_balance()
            if amount > remaining_balance:
                raise ValidationError(
                    f"Payment amount (₦{amount:.2f}) cannot exceed the remaining balance (₦{remaining_balance:.2f})."
                )

        # Validate payment method for wallet payments
        if payment_source == 'patient_wallet' and payment_method != 'wallet':
            cleaned_data['payment_method'] = 'wallet'

        # Allow wallet payments even with insufficient balance (negative balance allowed)
        # Wallet balance validation removed to support negative balances

        return cleaned_data

class MedicationInventoryForm(forms.ModelForm):
    """Form for managing medication inventory in dispensaries"""

    class Meta:
        model = MedicationInventory
        fields = ['medication', 'dispensary', 'stock_quantity', 'reorder_level']
        widgets = {
            'medication': forms.Select(attrs={'class': 'form-control'}),
            'dispensary': forms.Select(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
        }
