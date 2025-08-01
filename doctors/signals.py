from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from accounts.models import CustomUser
from .models import Doctor
from accounts.models import CustomUserProfile

@receiver(post_save, sender=Doctor)
def update_user_profile_role(sender, instance, created, **kwargs):
    """
    When a doctor is created or updated, ensure the user has the 'doctor' role
    """
    if instance.user:
        from accounts.models import Role
        doctor_role, _ = Role.objects.get_or_create(name='doctor')
        if doctor_role not in instance.user.roles.all():
            instance.user.roles.add(doctor_role)

@receiver(post_delete, sender=Doctor)
def handle_doctor_delete(sender, instance, **kwargs):
    """
    When a doctor is deleted, remove the 'doctor' role from the user if needed
    """
    # This is only needed if we're not deleting the user along with the doctor
    try:
        if instance.user:
            from accounts.models import Role
            doctor_role = Role.objects.get(name='doctor')
            if doctor_role in instance.user.roles.all():
                instance.user.roles.remove(doctor_role)
    except User.DoesNotExist:
        # User was already deleted
        pass
    except Role.DoesNotExist:
        # Doctor role doesn't exist
        pass
