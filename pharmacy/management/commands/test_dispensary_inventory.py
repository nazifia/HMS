from django.core.management.base import BaseCommand
from pharmacy.models import Dispensary, Medication, MedicationInventory, ActiveStoreInventory

class Command(BaseCommand):
    help = 'Test dispensary selection and inventory checking functionality'

    def handle(self, *args, **options):
        self.stdout.write("Testing dispensary functionality...")
        
        # Check if THEATRE-PH dispensary exists
        try:
            theatre_ph = Dispensary.objects.get(name='THEATRE-PH')
            self.stdout.write(f"THEATRE-PH dispensary exists with ID: {theatre_ph.id}")
        except Dispensary.DoesNotExist:
            self.stdout.write("THEATRE-PH dispensary does not exist")
            return
        
        # Check if it has an active store
        active_store = getattr(theatre_ph, 'active_store', None)
        if active_store:
            self.stdout.write(f"THEATRE-PH has an active store: {active_store.name}")
        else:
            self.stdout.write("THEATRE-PH does not have an active store")
        
        # Get our test medication
        try:
            medication = Medication.objects.get(name='Test Medication For Dispensary Testing')
            self.stdout.write(f"Found test medication: {medication.name}")
        except Medication.DoesNotExist:
            self.stdout.write("Test medication not found")
            return
        
        # Test inventory lookup for both models
        # First test MedicationInventory (legacy)
        try:
            med_inventory = MedicationInventory.objects.get(
                medication=medication,
                dispensary=theatre_ph
            )
            self.stdout.write(f"Found MedicationInventory: {med_inventory.stock_quantity} units")
        except MedicationInventory.DoesNotExist:
            self.stdout.write("No MedicationInventory found")
        
        # Then test ActiveStoreInventory (new)
        if active_store:
            try:
                active_inventory = ActiveStoreInventory.objects.get(
                    medication=medication,
                    active_store=active_store
                )
                self.stdout.write(f"Found ActiveStoreInventory: {active_inventory.stock_quantity} units")
            except ActiveStoreInventory.DoesNotExist:
                self.stdout.write("No ActiveStoreInventory found")
        
        self.stdout.write("Test completed successfully!")