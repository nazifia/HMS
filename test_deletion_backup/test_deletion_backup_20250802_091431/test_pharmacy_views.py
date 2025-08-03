import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

try:
    # Test importing all pharmacy components
    print("Testing pharmacy imports...")
    from pharmacy import views, models, forms, admin
    
    
    # Test the specific line that was causing the error (line 8 in views.py)
    from pharmacy.models import (
        MedicationCategory, Medication, Supplier, Purchase,
        PurchaseItem, Prescription, PrescriptionItem, DispensingLog, PurchaseApproval, Dispensary
    )
    print("✓ All model imports from views.py line 8 successful")
    
    # Test the forms import
    from pharmacy.forms import (
        MedicationCategoryForm, MedicationForm, SupplierForm, PurchaseForm,
        PurchaseItemForm, PrescriptionForm, PrescriptionItemForm,
        DispenseItemForm, BaseDispenseItemFormSet, MedicationSearchForm, PrescriptionSearchForm,
        DispensedItemsSearchForm, DispensaryForm
    )
    print("✓ All form imports successful")
    
    # Test the specific view function that uses Dispensary
    dispensaries = Dispensary.objects.all().order_by('name')
    print(f"✓ Dispensary query successful, found {dispensaries.count()} dispensaries")
    
    # Test creating a DispensaryForm
    form = DispensaryForm()
    print("✓ DispensaryForm creation successful")
    
    
    
except Exception as e:
    
    import traceback
    traceback.print_exc()