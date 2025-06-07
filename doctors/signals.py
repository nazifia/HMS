from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Doctor
from accounts.models import CustomUserProfile

@receiver(post_save, sender=Doctor)
def update_user_profile_role(sender, instance, created, **kwargs):
    """
    When a doctor is created or updated, ensure the user's profile role is set to 'doctor'
    """
    if instance.user:
        profile = UserProfile.objects.get(user=instance.user)
        if profile.role != 'doctor':
            profile.role = 'doctor'
            profile.save()

@receiver(post_delete, sender=Doctor)
def handle_doctor_delete(sender, instance, **kwargs):
    """
    When a doctor is deleted, update the user's profile role if needed
    """
    # This is only needed if we're not deleting the user along with the doctor
    try:
        if instance.user:
            profile = UserProfile.objects.get(user=instance.user)
            # Only change the role if there's no specific reason to keep it as doctor
            if profile.role == 'doctor':
                profile.role = None
                profile.save()
    except User.DoesNotExist:
        # User was already deleted
        pass
    except UserProfile.DoesNotExist:
        # Profile was already deleted
        pass
