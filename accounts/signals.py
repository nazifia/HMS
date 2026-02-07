from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import CustomUser, CustomUserProfile, Role


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


def clear_user_permission_cache(users):
    """
    Clear permission cache for specified users.
    """
    for user in users:
        if hasattr(user, '_role_perm_cache'):
            delattr(user, '_role_perm_cache')


def clear_role_permission_cache(sender, instance, **kwargs):
    """
    Clear permission cache for all users associated with a role when its permissions change.
    This ensures that permission changes take effect immediately.
    """
    # Clear the _role_perm_cache for all users having this role
    users = instance.customuser_roles.all()
    clear_user_permission_cache(users)


def clear_user_role_cache(sender, instance, **kwargs):
    """
    Clear permission cache for a user when their roles change.
    """
    clear_user_permission_cache([instance])


# Signal for when role permissions are modified (many-to-many relationship)
m2m_changed.connect(
    clear_role_permission_cache,
    sender=Role.permissions.through
)

# Also clear cache when role is saved (in case parent role changes which affect get_all_permissions)
post_save.connect(
    clear_role_permission_cache,
    sender=Role
)

# Clear user cache when their role assignments change
m2m_changed.connect(
    clear_user_role_cache,
    sender=CustomUser.roles.through
)

# Manually connect the signal to ensure it's registered
post_save.connect(create_or_update_user_profile, sender=CustomUser)
