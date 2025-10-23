from django import forms
from django.core.exceptions import ValidationError
from .models import DispensaryTransfer, Medication, ActiveStore


class DispensaryTransferForm(forms.ModelForm):
    """Form for transferring medications from active store to dispensary"""
    
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_medication'}),
        label='Medication'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'id_quantity',
            'min': 1,
            'placeholder': 'Enter quantity'
        }),
        label='Quantity to Transfer'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'id_notes',
            'rows': 3,
            'placeholder': 'Add any notes or special instructions'
        }),
        label='Notes'
    )
    
    def __init__(self, active_store=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_store = active_store
        
        # Filter medications available in active store
        if active_store:
            from .models import ActiveStoreInventory
            available_medications = ActiveStoreInventory.objects.filter(
                active_store=active_store,
                stock_quantity__gt=0
            ).values_list('medication_id', flat=True)
            
            self.fields['medication'].queryset = Medication.objects.filter(
                id__in=available_medications,
                is_active=True
            )

    class Meta:
        model = DispensaryTransfer
        fields = ['medication', 'quantity', 'notes']

    def clean(self):
        cleaned_data = super().clean()
        
        medication = cleaned_data.get('medication')
        quantity = cleaned_data.get('quantity')
        
        if medication and quantity:
            # Check if sufficient stock exists in active store
            if self.active_store:
                from .models import ActiveStoreInventory
                active_inventory = ActiveStoreInventory.objects.filter(
                    medication=medication,
                    active_store=self.active_store,
                    stock_quantity__gte=quantity
                ).first()
                
                if not active_inventory:
                    raise ValidationError(
                        f'Insufficient stock in {self.active_store.name}. '
                        f'Available: {ActiveStoreInventory.objects.filter(
                            medication=medication, 
                            active_store=self.active_store
                        ).first().stock_quantity or 0}'
                    )
        
        return cleaned_data


class BulkStoreTransferForm(forms.Form):
    """Enhanced form for bulk transferring medications from bulk store to active store"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure queryset is up to date
        from .models import BulkStore
        self.fields['bulk_store'] = forms.ModelChoiceField(
            queryset=BulkStore.objects.filter(is_active=True),
            widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_bulk_store'}),
            label='Source Bulk Store',
            required=True,
            empty_label='Select bulk store'
        )
