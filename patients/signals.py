from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patient, PatientWallet

@receiver(post_save, sender=Patient)
def create_patient_wallet(sender, instance, created, **kwargs):
    if created:
        PatientWallet.objects.create(patient=instance)

@receiver(post_save, sender=Patient)
def save_patient_wallet(sender, instance, **kwargs):
    if hasattr(instance, 'wallet'):
        instance.wallet.save()
