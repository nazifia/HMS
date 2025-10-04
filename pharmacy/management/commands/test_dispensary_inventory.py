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
                # Handle multiple inventory records by getting all and showing details
                active_inventories = ActiveStoreInventory.objects.filter(
                    medication=medication,
                    active_store=active_store
                )
                if active_inventories.exists():
                    total_stock = sum(inv.stock_quantity for inv in active_inventories)
                    self.stdout.write(f"Found {active_inventories.count()} ActiveStoreInventory records: {total_stock} total units")
                    for i, inv in enumerate(active_inventories):
                        self.stdout.write(f"  Record {i+1}: {inv.stock_quantity} units (Batch: {getattr(inv, 'batch_number', 'N/A')})")
                else:
                    self.stdout.write("No ActiveStoreInventory found")
            except Exception as e:
                self.stdout.write(f"Error accessing ActiveStoreInventory: {e}")
        
        self.stdout.write("Test completed successfully!")