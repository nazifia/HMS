    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='To Date'
    )


class BulkMedicationTransferForm(forms.ModelForm):
    """Form for bulk transfer of medications from bulk store to active store"""
    
    class Meta:
        model = MedicationTransfer
        fields = ['medication', 'from_bulk_store', 'to_active_store', 'quantity', 'notes']
        widgets = {
            'medication': forms.Select(attrs={'class': 'form-control select2'}),
            'from_bulk_store': forms.Select(attrs={'class': 'form-control'}),
            'to_active_store': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active stores only
        if 'to_active_store' in self.fields:
            self.fields['to_active_store'].queryset = ActiveStore.objects.filter(is_active=True)
        # Filter bulk stores only  
        if 'from_bulk_store' in self.fields:
            self.fields['from_bulk_store'].queryset = BulkStore.objects.filter(is_active=True)
        # Filter active medications
        if 'medication' in self.fields:
            self.fields['medication'].queryset = Medication.objects.filter(is_active=True).order_by('name')
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise forms.ValidationError('Quantity must be greater than 0.')
        return quantity


class BulkStoreTransferForm(forms.Form):
    """Form for bulk selecting and transferring multiple medications from bulk store to active store"""
    
    bulk_store = forms.ModelChoiceField(
        queryset=BulkStore.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Source Bulk Store'
    )
    
    active_store = forms.ModelChoiceField(
        queryset=ActiveStore.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Target Active Store'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.medications = []
    
    def get_available_medications(self):
        """Get medications available in the selected bulk store"""
        bulk_store = self.cleaned_data.get('bulk_store')
        if bulk_store:
            self.medications = BulkStoreInventory.objects.filter(
                bulk_store=bulk_store,
                stock_quantity__gt=0
            ).select_related('medication').order_by('medication__name')
        return self.medications
