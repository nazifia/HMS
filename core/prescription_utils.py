"""
Utility functions for prescription management across all medical modules.
"""
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from pharmacy.models import Prescription, PrescriptionItem, Medication
from billing.models import Service, Invoice, InvoiceItem
from decimal import Decimal


def create_prescription_from_module(request, patient, doctor, diagnosis="", notes="", 
                                  module_name="", source_data=None):
    """
    Create a prescription from any medical module.
    
    Args:
        request: Django request object
        patient: Patient object
        doctor: Doctor/CustomUser object
        diagnosis: Diagnosis string
        notes: Additional notes
        module_name: Name of the module creating the prescription
        source_data: Optional data from the source module to include in notes
    
    Returns:
        Prescription object or None if failed
    """
    try:
        with transaction.atomic():
            # Create prescription
            prescription = Prescription.objects.create(
                patient=patient,
                doctor=doctor,
                prescription_date=timezone.now().date(),
                diagnosis=diagnosis,
                notes=notes,
                status='pending',
                prescription_type='outpatient'
            )
            
            # Add module-specific information to notes
            if module_name:
                prescription.notes = f"Created from {module_name} module. {notes}"
                prescription.save()
            
            # Create initial invoice for the prescription
            create_prescription_invoice(prescription)
            
            return prescription
            
    except Exception as e:
        if request:
            messages.error(request, f'Error creating prescription: {str(e)}')
        return None


def create_prescription_invoice(prescription):
    """
    Create an invoice for a prescription.
    
    Args:
        prescription: Prescription object
    
    Returns:
        Invoice object
    """
    try:
        # Get or create the medication dispensing service
        medication_service, created = Service.objects.get_or_create(
            name__iexact="Medication Dispensing",
            defaults={
                'name': "Medication Dispensing",
                'description': "Dispensing of prescribed medications",
                'price': Decimal('0.00'),
                'category': None,
                'is_active': True
            }
        )
        
        # Calculate total prescription price
        total_prescription_price = prescription.get_total_prescribed_price()
        
        # Create invoice
        invoice = Invoice.objects.create(
            patient=prescription.patient,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            created_by=prescription.doctor,
            subtotal=total_prescription_price,
            tax_amount=0,
            total_amount=total_prescription_price,
            status='pending',
            source_app='pharmacy'
        )
        
        # Create invoice item
        InvoiceItem.objects.create(
            invoice=invoice,
            service=medication_service,
            description=f'Invoice for Prescription #{prescription.id}',
            quantity=1,
            unit_price=total_prescription_price,
            tax_amount=0,
            total_amount=total_prescription_price,
        )
        
        # Link invoice to prescription
        prescription.invoice = invoice
        prescription.save()
        
        return invoice
        
    except Exception as e:
        # Handle the error appropriately in your application
        raise Exception(f"Error creating prescription invoice: {str(e)}")


def add_medication_to_prescription(prescription, medication_id, dosage, frequency, 
                                 duration, quantity, instructions=""):
    """
    Add a medication to an existing prescription.
    
    Args:
        prescription: Prescription object
        medication_id: ID of the medication
        dosage: Dosage information
        frequency: How often to take the medication
        duration: How long to take the medication
        quantity: Quantity prescribed
        instructions: Additional instructions
    
    Returns:
        PrescriptionItem object or None if failed
    """
    try:
        medication = get_object_or_404(Medication, id=medication_id)
        
        prescription_item = PrescriptionItem.objects.create(
            prescription=prescription,
            medication=medication,
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            instructions=instructions,
            quantity=quantity
        )
        
        return prescription_item
        
    except Exception as e:
        # Handle the error appropriately in your application
        raise Exception(f"Error adding medication to prescription: {str(e)}")


def get_patient_prescriptions(patient):
    """
    Get all prescriptions for a patient.
    
    Args:
        patient: Patient object
    
    Returns:
        QuerySet of prescriptions
    """
    return Prescription.objects.filter(patient=patient).order_by('-prescription_date')


def get_prescription_by_id(prescription_id):
    """
    Get a prescription by its ID.
    
    Args:
        prescription_id: ID of the prescription
    
    Returns:
        Prescription object or None if not found
    """
    try:
        return Prescription.objects.get(id=prescription_id)
    except Prescription.DoesNotExist:
        return None


def update_prescription_status(prescription, status):
    """
    Update the status of a prescription.
    
    Args:
        prescription: Prescription object
        status: New status
    
    Returns:
        Updated prescription object
    """
    prescription.status = status
    prescription.save()
    return prescription