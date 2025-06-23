from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Surgery, SurgerySchedule

@receiver(post_save, sender=Surgery)
def create_surgery_schedule(sender, instance, created, **kwargs):
    """
    Create a surgery schedule when a new surgery is created.
    """
    if created:
        # We don't automatically create a schedule as it requires specific timing information
        pass

@receiver(pre_save, sender=Surgery)
def update_theatre_availability(sender, instance, **kwargs):
    """
    Update theatre availability when surgery status changes.
    """
    if instance.pk:  # If this is an update, not a new instance
        try:
            old_instance = Surgery.objects.get(pk=instance.pk)
            # If status changed from scheduled/in_progress to completed/cancelled
            if old_instance.status in ['scheduled', 'in_progress'] and instance.status in ['completed', 'cancelled']:
                # Make theatre available again if it exists
                if instance.theatre:
                    instance.theatre.is_available = True
                    instance.theatre.save()
            # If status changed to in_progress
            elif old_instance.status != 'in_progress' and instance.status == 'in_progress':
                # Mark theatre as unavailable
                if instance.theatre:
                    instance.theatre.is_available = False
                    instance.theatre.save()
        except Surgery.DoesNotExist:
            pass  # This is a new instance, handled by post_save