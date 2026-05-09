from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Patient, PatientWallet

@receiver(post_save, sender=Patient)
def create_patient_wallet(sender, instance, created, **kwargs):
    if created:
        PatientWallet.objects.create(patient=instance)

@receiver(post_save, sender=Patient)
def save_patient_wallet(sender, instance, **kwargs):
    if hasattr(instance, 'wallet'):
        instance.wallet.save()

@receiver(post_save, sender=Patient)
@receiver(post_delete, sender=Patient)
def invalidate_patients_context_cache(sender, **kwargs):
    cache.delete('ctx_all_patients')
