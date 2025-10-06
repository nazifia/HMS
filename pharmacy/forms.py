import logging
import calendar
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    MedicationCategory, Medication, Supplier, Purchase,
    PurchaseItem, Prescription, PrescriptionItem, DispensingLog, Dispensary, MedicationInventory, ActiveStoreInventory,
    MedicalPack, PackItem, PackOrder
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
            'supplier', 'purchase_date', 'payment_status', 'notes'
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
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date()
    )

    # Authorization code input field
    authorization_code_input = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter authorization code (if required)'
        }),
        help_text="Required for NHIA patients from non-NHIA consultations"
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        preselected_patient = kwargs.pop('preselected_patient', None)
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Handle patient preselection from multiple sources
        patient_id = None
        patient_instance = None

        # Priority: preselected_patient > request.GET > initial data
        if preselected_patient:
            # Check if preselected_patient is already an integer (patient ID) or a Patient object
            if isinstance(preselected_patient, int):
                patient_id = preselected_patient
            else:
                patient_instance = preselected_patient
                patient_id = preselected_patient.id
        elif request:
            patient_id = request.GET.get('patient')

        if not patient_id and not patient_instance:
            patient_instance = self.initial.get('patient')
            if patient_instance:
                # Check if patient_instance is already an integer (patient ID) or a Patient object
                if isinstance(patient_instance, int):
                    patient_id = patient_instance
                else:
                    patient_id = patient_instance.id

        if patient_id and not patient_instance:
            try:
                patient_instance = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                patient_instance = None

        if patient_instance:
            self.fields['patient'].initial = patient_instance
            # Don't disable the field, just set it as readonly in the template
            self.fields['patient'].widget.attrs.update({
                'class': 'form-select',
                'style': 'pointer-events: none; background-color: #e9ecef;'
            })
            # Limit queryset to only the selected patient
            patient_id_for_filter = patient_instance.id if hasattr(patient_instance, 'id') else patient_instance
            self.fields['patient'].queryset = Patient.objects.filter(id=patient_id_for_filter)
            self.fields['patient'].empty_label = None
        else:
            # Ensure all patients are available for selection when not preselected
            self.fields['patient'].queryset = Patient.objects.filter(is_active=True)

        # Handle doctor field - set to current user and make read-only
        if current_user:
            self.fields['doctor'].initial = current_user
            self.fields['doctor'].widget.attrs.update({
                'class': 'form-select',
                'style': 'pointer-events: none; background-color: #e9ecef;'
            })
            # Limit queryset to only the current user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['doctor'].queryset = User.objects.filter(id=current_user.id)
            self.fields['doctor'].empty_label = None

    def clean_authorization_code_input(self):
        """Validate authorization code if provided"""
        code_str = self.cleaned_data.get('authorization_code_input', '').strip()
        if not code_str:
            return None

        from nhia.models import AuthorizationCode
        try:
            auth_code = AuthorizationCode.objects.get(code=code_str)
            if not auth_code.is_valid():
                raise forms.ValidationError(f"Authorization code is {auth_code.status}")
            return auth_code
        except AuthorizationCode.DoesNotExist:
            raise forms.ValidationError("Invalid authorization code")

    def clean(self):
        cleaned_data = super().clean()

        # Ensure required fields are present
        if not cleaned_data.get('patient'):
            raise forms.ValidationError("Patient is required.")
        
        if not cleaned_data.get('doctor'):
            raise forms.ValidationError("Doctor is required.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        auth_code = self.cleaned_data.get('authorization_code_input')
        if auth_code:
            instance.authorization_code = auth_code
            instance.authorization_status = 'authorized'
        if commit:
            instance.save()
        return instance

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
            'medication', 'dosage', 'frequency', 'duration', 'instructions'
        ]
        widgets = {
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'rows': 2}),
        }

import logging

import logging

class DispenseItemForm(forms.Form):
    """Form for a single item in the dispensing process."""
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    dispense_this_item = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    quantity_to_dispense = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm quantity-input',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        required=False,
        empty_label="Select Dispensary",
        widget=forms.Select(attrs={'class': 'form-control form-control-sm d-none'})  # Hidden since we have global selection
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

            # Get available stock from both inventory models for the selected dispensary
            available_stock = 0
            if self.selected_dispensary:
                try:
                    # First try MedicationInventory (legacy)
                    med_inventory = MedicationInventory.objects.get(
                        medication=self.prescription_item.medication,
                        dispensary=self.selected_dispensary
                    )
                    available_stock = med_inventory.stock_quantity
                    logging.debug(f"  Available stock at selected dispensary ({self.selected_dispensary.name}): {available_stock}")
                except MedicationInventory.DoesNotExist:
                    # If not found, try ActiveStoreInventory (new)
                    try:
                        active_store = getattr(self.selected_dispensary, 'active_store', None)
                        if active_store:
                            # Handle multiple inventory records by summing all available stock
                            inventories = ActiveStoreInventory.objects.filter(
                                medication=self.prescription_item.medication,
                                active_store=active_store
                            )
                            available_stock = sum(inv.stock_quantity for inv in inventories)
                            logging.debug(f"  Available stock at selected dispensary ({self.selected_dispensary.name}): {available_stock}")
                        else:
                            available_stock = 0
                            logging.debug(f"  No active store found for {self.selected_dispensary.name}")
                    except ActiveStoreInventory.DoesNotExist:
                        available_stock = 0 # No inventory for this medication at this dispensary
                        logging.debug(f"  No inventory found for {self.prescription_item.medication.name} at {self.selected_dispensary.name}")

            # Store available stock as instance variable for template access
            self.available_stock = available_stock

            can_be_dispensed = remaining_qty > 0 and not is_fully_dispensed
            logging.debug(f"  Can be dispensed: {can_be_dispensed}")

            # Disable checkbox and quantity input for already dispensed items
            if is_fully_dispensed:
                self.fields['dispense_this_item'].widget.attrs['disabled'] = True
                self.fields['dispense_this_item'].widget.attrs['title'] = 'Already fully dispensed'
                self.fields['dispense_this_item'].label = "Fully Dispensed"
                self.fields['dispense_this_item'].initial = False
                self.fields['quantity_to_dispense'].widget.attrs['disabled'] = True
                self.fields['quantity_to_dispense'].initial = 0
            elif not can_be_dispensed:
                # Disable if no remaining quantity
                if self.selected_dispensary and available_stock == 0:
                    self.fields['dispense_this_item'].widget.attrs['disabled'] = True
                    self.fields['dispense_this_item'].widget.attrs['title'] = 'Out of stock'
                    self.fields['dispense_this_item'].label = "Out of Stock"
                    self.fields['quantity_to_dispense'].widget.attrs['disabled'] = True
                    self.fields['quantity_to_dispense'].initial = 0
                elif not self.selected_dispensary:
                    # No dispensary selected yet, allow form submission
                    self.fields['dispense_this_item'].initial = False
                    self.fields['quantity_to_dispense'].initial = 0
            else:
                # Set initial quantity to remaining quantity, capped by available stock
                initial_qty_to_dispense = remaining_qty
                if self.selected_dispensary and available_stock > 0:
                    initial_qty_to_dispense = min(remaining_qty, available_stock)
                    # Don't auto-check the checkbox - let user decide what to dispense
                    # self.fields['dispense_this_item'].initial = True

                self.fields['quantity_to_dispense'].initial = initial_qty_to_dispense
                self.fields['quantity_to_dispense'].widget.attrs['max'] = min(remaining_qty, available_stock) if self.selected_dispensary else remaining_qty
                self.fields['quantity_to_dispense'].widget.attrs['min'] = 1

            # Set initial value for dispensary field if selected_dispensary is provided
            if self.selected_dispensary:
                self.fields['dispensary'].initial = self.selected_dispensary
                # Make it required if pre-selected
                self.fields['dispensary'].required = True
            
            # Set the stock quantity display field
            if self.selected_dispensary:
                if available_stock > 0:
                    self.fields['stock_quantity_display'].initial = f"{available_stock} in stock"
                else:
                    self.fields['stock_quantity_display'].initial = "Out of Stock"
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
        logging.debug(f"  selected_dispensary: {self.selected_dispensary}")

        if not self.prescription_item:
            self.add_error(None, "Form not initialized with a prescription item.")
            logging.error("DispenseItemForm clean: Form not initialized with a prescription item.")
            return cleaned_data

        remaining_qty = self.prescription_item.remaining_quantity_to_dispense
        is_fully_dispensed = self.prescription_item.is_dispensed

        # Get available stock from both inventory models for the selected dispensary
        # Use effective dispensary (form dispensary OR selected_dispensary)
        effective_dispensary_for_stock = dispensary or self.selected_dispensary
        available_stock = 0
        if effective_dispensary_for_stock:
            try:
                # First try MedicationInventory (legacy)
                med_inventory = MedicationInventory.objects.get(
                    medication=self.prescription_item.medication,
                    dispensary=effective_dispensary_for_stock
                )
                available_stock = med_inventory.stock_quantity
            except MedicationInventory.DoesNotExist:
                # If not found, try ActiveStoreInventory (new)
                try:
                    active_store = getattr(effective_dispensary_for_stock, 'active_store', None)
                    if active_store:
                        # Handle multiple inventory records by summing all available stock
                        inventories = ActiveStoreInventory.objects.filter(
                            medication=self.prescription_item.medication,
                            active_store=active_store
                        )
                        available_stock = sum(inv.stock_quantity for inv in inventories)
                    else:
                        available_stock = 0
                except Exception as e:
                    available_stock = 0
        else:
            # No dispensary selected yet; skip stock validation until dispensary provided
            available_stock = None
        logging.debug(f"  Remaining Qty: {remaining_qty}, Is Fully Dispensed: {is_fully_dispensed}, Available Stock: {available_stock}")
        print(f"DEBUG: DispenseItemForm clean - Item ID: {self.prescription_item.id if self.prescription_item else 'None'}")
        print(f"DEBUG:   Remaining Qty: {remaining_qty}")
        print(f"DEBUG:   Is Fully Dispensed: {is_fully_dispensed}")
        print(f"DEBUG:   Available Stock: {available_stock}")

        # Determine if we can dispense only when we have stock info
        can_be_dispensed = False
        if available_stock is None:
            # Can't determine stock until a dispensary is chosen; defer strict stock check
            can_be_dispensed = remaining_qty > 0 and not is_fully_dispensed
        else:
            can_be_dispensed = remaining_qty > 0 and available_stock > 0 and not is_fully_dispensed

        if dispense_this_item and not can_be_dispensed:
            error_message = ""
            if is_fully_dispensed:
                error_message = "This item is already fully dispensed."
            elif remaining_qty <= 0:
                error_message = "No remaining quantity to dispense for this item."
            elif available_stock is None:
                error_message = "Please select a dispensary to check stock for this item."
            elif available_stock <= 0:
                error_message = "This item is out of stock at the selected dispensary."

            if error_message:
                raise forms.ValidationError(error_message)

        if dispense_this_item:
            # Check if we have a dispensary from the form or from the selected_dispensary
            effective_dispensary = dispensary or self.selected_dispensary

            if not effective_dispensary:
                self.add_error('dispensary', 'Please select a dispensary for this item.')
                logging.warning(f"  Validation Error: Dispensary not selected for item {self.prescription_item.id}.")
            if quantity_to_dispense is None or quantity_to_dispense <= 0:
                self.add_error('quantity_to_dispense', 'Quantity must be greater than 0 if selected for dispensing.')
                logging.warning(f"  Validation Error: Invalid quantity for item {self.prescription_item.id}.")
            elif quantity_to_dispense > remaining_qty:
                self.add_error('quantity_to_dispense', f'Cannot dispense more than remaining ({remaining_qty}).')
                logging.warning(f"  Validation Error: Quantity ({quantity_to_dispense}) > remaining ({remaining_qty}) for item {self.prescription_item.id}.")
            elif available_stock is not None and quantity_to_dispense > available_stock:
                self.add_error('quantity_to_dispense', f'Not enough stock at selected dispensary. Available: {available_stock}.')
                logging.warning(f"  Validation Error: Quantity ({quantity_to_dispense}) > available stock ({available_stock}) for item {self.prescription_item.id}.")
        
        return cleaned_data
        
        

from django.forms.formsets import BaseFormSet

class BaseDispenseItemFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        # prescription_items_qs: queryset/list of PrescriptionItem objects to bind to each form
        self.prescription_items_qs = kwargs.pop('prescription_items_qs', None)
        # form_kwargs may include things like 'selected_dispensary' that individual forms need
        # Store with a different name to avoid conflicts with Django's BaseFormSet
        self.custom_form_kwargs = kwargs.pop('form_kwargs', None)
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if self.prescription_items_qs and index < len(self.prescription_items_qs):
            form.prescription_item = self.prescription_items_qs[index]
            # Set the selected_dispensary directly instead of re-initializing
            if hasattr(self, 'custom_form_kwargs') and self.custom_form_kwargs:
                selected_dispensary = self.custom_form_kwargs.get('selected_dispensary')
                form.selected_dispensary = selected_dispensary
                # Also update the initial value for the dispensary field if we have a selected dispensary
                if selected_dispensary and 'dispensary' in form.fields:
                    form.fields['dispensary'].initial = selected_dispensary
        else:
            # Handle the case where prescription_items_qs is not provided
            # This might indicate an error or a different use case for the formset
            form.prescription_item = None # Or raise an error, depending on desired behavior

    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
            
        # Check if any items were selected for dispensing
        any_selected = False
        for form in self.forms:
            # Check if form has cleaned_data attribute before accessing it
            if hasattr(form, 'cleaned_data') and form.cleaned_data and form.cleaned_data.get('dispense_this_item'):
                any_selected = True
                break
        
        # If items were selected but no dispensary was provided, add a formset-level error
        if any_selected:
            # Check if all forms have a dispensary selected
            all_have_dispensary = True
            global_selected_dispensary = self.custom_form_kwargs.get('selected_dispensary') if self.custom_form_kwargs else None

            for form in self.forms:
                # Check if form has cleaned_data attribute before accessing it
                if hasattr(form, 'cleaned_data') and form.cleaned_data and form.cleaned_data.get('dispense_this_item'):
                    dispensary = form.cleaned_data.get('dispensary')
                    # If form doesn't have dispensary but we have a global selected dispensary, use that
                    effective_dispensary = dispensary or global_selected_dispensary

                    if not effective_dispensary:
                        all_have_dispensary = False
                        break
                    else:
                        # Set the effective dispensary back to the form's cleaned_data
                        form.cleaned_data['dispensary'] = effective_dispensary

            if not all_have_dispensary:
                raise forms.ValidationError("Please select a dispensary for all items to be dispensed.")
        
        return


class MedicationSearchForm(forms.Form):
    """Form for searching medications"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name, generic name, or category',
            'class': 'form-control'
        }),
        label='Search'
    )

    category = forms.ModelChoiceField(
        queryset=MedicationCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Category'
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
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
    
    transaction_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter transaction ID (optional)'
        }),
        label='Transaction ID',
        help_text='Reference number for electronic payments'
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


        

class ActiveStoreInventoryForm(forms.ModelForm):
    """Form for managing ActiveStoreInventory (active store per dispensary)"""

    class Meta:
        model = ActiveStoreInventory
        fields = ['medication', 'active_store', 'stock_quantity', 'reorder_level', 'batch_number', 'expiry_date', 'unit_cost']
        widgets = {
            'medication': forms.Select(attrs={'class': 'form-control'}),
            'active_store': forms.Select(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class PharmacyDashboardSearchForm(forms.Form):
    """Comprehensive search form for pharmacy dashboard"""

    SEARCH_TYPE_CHOICES = [
        ('', 'All'),
        ('medications', 'Medications'),
        ('prescriptions', 'Prescriptions'),
        ('patients', 'Patients'),
        ('suppliers', 'Suppliers'),
    ]

    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search medications, prescriptions, patients, or suppliers...',
            'class': 'form-control',
            'id': 'global-search'
        }),
        label='Search'
    )

    search_type = forms.ChoiceField(
        choices=SEARCH_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Search In'
    )

    # Medication specific filters
    medication_category = forms.ModelChoiceField(
        queryset=MedicationCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Medication Category'
    )

    stock_status = forms.ChoiceField(
        choices=[
            ('', 'All Stock Levels'),
            ('in_stock', 'In Stock'),
            ('low_stock', 'Low Stock'),
            ('out_of_stock', 'Out of Stock'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Stock Status'
    )

    # Prescription specific filters
    prescription_status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('pending', 'Pending'),
            ('partially_dispensed', 'Partially Dispensed'),
            ('dispensed', 'Fully Dispensed'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Prescription Status'
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='From Date'
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='To Date'
    )


# ComprehensiveRevenueFilterForm removed - use MonthFilterHelper and simple view instead


# Medical Pack Forms
class MedicalPackForm(forms.ModelForm):
    """Form for creating and editing medical packs"""
    
    class Meta:
        model = MedicalPack
        fields = [
            'name', 'description', 'pack_type', 'surgery_type', 'labor_type',
            'risk_level', 'requires_approval', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'pack_type': forms.Select(attrs={'class': 'form-select', 'onchange': 'handlePackTypeChange()'}),
            'surgery_type': forms.Select(attrs={'class': 'form-select', 'id': 'surgery-type-select'}),
            'labor_type': forms.Select(attrs={'class': 'form-select', 'id': 'labor-type-select'}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'requires_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initially hide surgery_type and labor_type fields
        self.fields['surgery_type'].required = False
        self.fields['labor_type'].required = False
        
        # Add help text
        self.fields['requires_approval'].help_text = 'Check if this pack requires approval before processing'
        self.fields['pack_type'].help_text = 'Select the type of medical pack'
    
    def clean(self):
        cleaned_data = super().clean()
        pack_type = cleaned_data.get('pack_type')
        surgery_type = cleaned_data.get('surgery_type')
        labor_type = cleaned_data.get('labor_type')
        
        # Validate that appropriate type is selected based on pack type
        if pack_type == 'surgery' and not surgery_type:
            raise ValidationError('Surgery type is required for surgery packs.')
        elif pack_type == 'labor' and not labor_type:
            raise ValidationError('Labor type is required for labor packs.')
        
        # Clear inappropriate type fields
        if pack_type != 'surgery':
            cleaned_data['surgery_type'] = None
        if pack_type != 'labor':
            cleaned_data['labor_type'] = None
            
        return cleaned_data


class PackItemForm(forms.ModelForm):
    """Form for creating and editing pack items"""
    
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Medication/Consumable"
    )
    
    class Meta:
        model = PackItem
        fields = [
            'medication', 'quantity', 'item_type', 'usage_instructions',
            'is_critical', 'is_optional', 'order'
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'usage_instructions': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'is_critical': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_optional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['is_critical'].help_text = 'Critical items cannot be substituted'
        self.fields['is_optional'].help_text = 'Optional items can be omitted if unavailable'
        self.fields['order'].help_text = 'Order of usage in procedure (0 for no specific order)'
    
    def clean(self):
        cleaned_data = super().clean()
        is_critical = cleaned_data.get('is_critical')
        is_optional = cleaned_data.get('is_optional')
        
        # Item cannot be both critical and optional
        if is_critical and is_optional:
            raise ValidationError('Item cannot be both critical and optional.')
            
        return cleaned_data


class PackOrderForm(forms.ModelForm):
    """Form for creating pack orders"""
    
    pack = forms.ModelChoiceField(
        queryset=MedicalPack.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Medical Pack"
    )
    
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Patient"
    )
    
    scheduled_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        help_text='When the pack is needed (optional)'
    )
    
    class Meta:
        model = PackOrder
        fields = [
            'pack', 'patient', 'scheduled_date', 'order_notes'
        ]
        widgets = {
            'order_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Handle pre-selection of patient and related objects
        self.preselected_patient = kwargs.pop('preselected_patient', None)
        self.surgery = kwargs.pop('surgery', None)
        self.labor_record = kwargs.pop('labor_record', None)
        request = kwargs.pop('request', None)

        super().__init__(*args, **kwargs)

        # Handle patient pre-selection for surgery context
        if self.surgery and not self.preselected_patient:
            self.preselected_patient = self.surgery.patient

        # Handle patient pre-selection for labor context
        if self.labor_record and not self.preselected_patient:
            self.preselected_patient = self.labor_record.patient

        # Apply patient pre-selection if set
        if self.preselected_patient:
            self.fields['patient'].initial = self.preselected_patient
            self.fields['patient'].required = False  # Make it not required since we use patient_hidden
            self.fields['patient'].widget.attrs.update({
                'readonly': True,
                'disabled': True,
                'class': 'form-select',
                'style': 'background-color: #e9ecef; cursor: not-allowed;'
            })
            self.fields['patient'].queryset = Patient.objects.filter(id=self.preselected_patient.id)

            # Add hidden field for patient
            self.fields['patient_hidden'] = forms.ModelChoiceField(
                queryset=Patient.objects.filter(id=self.preselected_patient.id),
                initial=self.preselected_patient,
                widget=forms.HiddenInput(),
                required=True
            )

        # Filter packs based on context
        if self.surgery:
            # Filter to surgery packs
            surgery_type_mapping = {
                'Appendectomy': 'appendectomy',
                'Cholecystectomy': 'cholecystectomy',
                'Hernia Repair': 'hernia_repair',
                'Cesarean Section': 'cesarean_section',
                'Tonsillectomy': 'tonsillectomy',
            }

            surgery_type = surgery_type_mapping.get(self.surgery.surgery_type.name)
            if surgery_type:
                self.fields['pack'].queryset = MedicalPack.objects.filter(
                    is_active=True,
                    pack_type='surgery',
                    surgery_type=surgery_type
                )
            else:
                self.fields['pack'].queryset = MedicalPack.objects.filter(
                    is_active=True,
                    pack_type='surgery'
                )

        elif self.labor_record:
            # Filter to labor packs
            self.fields['pack'].queryset = MedicalPack.objects.filter(
                is_active=True,
                pack_type='labor'
            )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Handle patient field when disabled
        if 'patient_hidden' in self.fields:
            cleaned_data['patient'] = cleaned_data.get('patient_hidden')
        
        # Validate scheduled date
        scheduled_date = cleaned_data.get('scheduled_date')
        if scheduled_date and scheduled_date < timezone.now():
            raise ValidationError('Scheduled date cannot be in the past.')
            
        return cleaned_data
    
    def save(self, commit=True):
        pack_order = super().save(commit=False)
        
        # Set related objects
        if self.surgery:
            pack_order.surgery = self.surgery
        if self.labor_record:
            pack_order.labor_record = self.labor_record
            
        if commit:
            pack_order.save()
            
        return pack_order


class PackFilterForm(forms.Form):
    """Form for filtering medical packs"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search packs...'
        }),
        label='Search'
    )
    
    pack_type = forms.ChoiceField(
        choices=[('', 'All Types')] + MedicalPack.PACK_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Pack Type'
    )
    
    risk_level = forms.ChoiceField(
        choices=[('', 'All Risk Levels'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Risk Level'
    )
    
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
    )


class PackOrderFilterForm(forms.Form):
    """Form for filtering pack orders"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search orders...'
        }),
        label='Search'
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + PackOrder.ORDER_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Order Status'
    )
    
    pack_type = forms.ChoiceField(
        choices=[('', 'All Types')] + MedicalPack.PACK_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Pack Type'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='From Date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='To Date'
    )
