import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription

try:
    prescription = Prescription.objects.get(id=2)
    print(f"✅ Prescription {prescription.id} found")
    print(f"   Patient: {prescription.patient.get_full_name()}")
    print(f"   Status: {prescription.status}")
    print(f"   Items: {prescription.items.count()}")
    print(f"   Pending items: {prescription.items.filter(is_dispensed=False).count()}")
    
    for item in prescription.items.filter(is_dispensed=False):
        print(f"   - {item.medication.name}: {item.remaining_quantity} remaining")
    
    print("✅ All data accessible - dispensing workflow ready!")
    
except Prescription.DoesNotExist:
    print("❌ Prescription 2 not found")
except Exception as e:
    print(f"❌ Error: {e}")
