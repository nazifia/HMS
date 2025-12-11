from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, CustomUserProfile


def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to create or update user profile when a CustomUser is saved.
    """
    if created:
        # Create profile for new user
        CustomUserProfile.objects.create(user=instance)
    else:
        # Ensure profile exists and save it for existing users
        try:
            instance.profile.save()
        except CustomUserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            CustomUserProfile.objects.create(user=instance)


# Manually connect the signal to ensure it's registered
post_save.connect(create_or_update_user_profile, sender=CustomUser)
