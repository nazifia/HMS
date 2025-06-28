from django import forms
from django.utils import timezone
from .models import (
    MedicationCategory, Medication, Supplier, Purchase,
    PurchaseItem, Prescription, PrescriptionItem, DispensingLog, Dispensary, MedicationInventory
)
from patients.models import Patient
from django.contrib.auth import get_user_model
from accounts.models import CustomUser
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
            'strength', 'manufacturer', 'price', 'stock_quantity', 'reorder_level',
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
        queryset=User.objects.filter(is_active=True, profile__role='doctor').distinct(),
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
            self.fields['patient'].widget = forms.HiddenInput()
        # All users can select any doctor now
        # Ensure all patients are available for selection
        self.fields['patient'].queryset = Patient.objects.all()

    class Meta:
        model = Prescription
        fields = [
            'patient', 'doctor', 'prescription_date', 'diagnosis', 'status', 'notes', 'prescription_type'
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

    def __init__(self, *args, **kwargs):
        self.prescription_item = kwargs.pop('prescription_item', None)
        super().__init__(*args, **kwargs)
        if self.prescription_item:
            self.fields['item_id'].initial = self.prescription_item.id
            remaining_qty = self.prescription_item.remaining_quantity_to_dispense
            
            is_fully_dispensed = self.prescription_item.is_dispensed # Based on new logic (qty_dispensed_so_far >= quantity)
            can_be_dispensed = remaining_qty > 0 and self.prescription_item.medication.stock_quantity > 0 and not is_fully_dispensed

            if not can_be_dispensed:
                self.fields['dispense_this_item'].widget.attrs['disabled'] = True
                self.fields['quantity_to_dispense'].widget.attrs['disabled'] = True
                self.fields['quantity_to_dispense'].initial = 0
                if is_fully_dispensed:
                    self.fields['dispense_this_item'].label = "Fully Dispensed"
                elif self.prescription_item.medication.stock_quantity == 0:
                     self.fields['dispense_this_item'].label = "Out of Stock"
            else:
                # Default to remaining quantity, capped by current stock
                initial_qty_to_dispense = min(remaining_qty, self.prescription_item.medication.stock_quantity)
                self.fields['quantity_to_dispense'].initial = initial_qty_to_dispense
                self.fields['quantity_to_dispense'].widget.attrs['max'] = min(remaining_qty, self.prescription_item.medication.stock_quantity)
                self.fields['quantity_to_dispense'].widget.attrs['min'] = 0 # Allow 0 if user unchecks

    def clean(self):
        cleaned_data = super().clean()
        dispense_this_item = cleaned_data.get('dispense_this_item')
        quantity_to_dispense = cleaned_data.get('quantity_to_dispense')

        if not self.prescription_item:
            # Should not happen if form is initialized correctly
            raise forms.ValidationError("Form not initialized with a prescription item.")

        remaining_qty = self.prescription_item.remaining_quantity_to_dispense
        is_fully_dispensed = self.prescription_item.is_dispensed
        can_be_dispensed = remaining_qty > 0 and self.prescription_item.medication.stock_quantity > 0 and not is_fully_dispensed

        if not can_be_dispensed and dispense_this_item:
            # This case should ideally be prevented by disabling the checkbox
            self.add_error(None, "This item cannot be dispensed (fully dispensed or out of stock).")
            return cleaned_data

        if dispense_this_item:
            if quantity_to_dispense is None or quantity_to_dispense <= 0:
                self.add_error('quantity_to_dispense', 'Quantity must be greater than 0 if selected for dispensing.')
            # Check against remaining quantity for this item
            elif quantity_to_dispense > remaining_qty:
                self.add_error('quantity_to_dispense', f'Cannot dispense more than remaining ({remaining_qty}).')
            # Check against available stock
            elif quantity_to_dispense > self.prescription_item.medication.stock_quantity:
                self.add_error('quantity_to_dispense', f'Not enough stock. Available: {self.prescription_item.medication.stock_quantity}.')
        
        return cleaned_data

from django.forms.formsets import BaseFormSet

class BaseDispenseItemFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        # Pop custom kwarg before calling super
        self.prescription_items_qs = kwargs.pop('prescription_items_qs', None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        # Pass the specific prescription_item to the form's __init__
        if self.prescription_items_qs and i < len(self.prescription_items_qs):
            # Ensure that prescription_items_qs is indexable (e.g., a list or queryset)
            try:
                kwargs['prescription_item'] = self.prescription_items_qs[i]
            except IndexError:
                # Handle case where i might be out of bounds, though formset_factory with extra=0 should align
                pass # Or log a warning
        return super()._construct_form(i, **kwargs)

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

    stock_status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('in_stock', 'In Stock'),
            ('low_stock', 'Low Stock'),
            ('out_of_stock', 'Out of Stock')
        ],
        required=False
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
    """Form for searching prescriptions"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by patient name or ID'})
    )

    status = forms.ChoiceField(
        choices=[('', 'All')] + list(Prescription.STATUS_CHOICES),
        required=False
    )

    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, profile__role='doctor').distinct(),
        required=False,
        empty_label="All Doctors"
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
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
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
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
        self.fields['manager'].queryset = User.objects.filter(is_staff=True)
        self.fields['manager'].empty_label = "Select Manager (Optional)"

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
