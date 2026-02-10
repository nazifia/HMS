import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import CustomUser, CustomUserProfile, Role

logger = logging.getLogger(__name__)


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
    cleared_count = 0
    for user in users:
        if hasattr(user, '_role_perm_cache'):
            delattr(user, '_role_perm_cache')
            cleared_count += 1
        if hasattr(user, '_perm_cache'):
            delattr(user, '_perm_cache')
    return cleared_count


def clear_role_permission_cache(sender, instance, **kwargs):
    """
    Clear permission cache for all users associated with a role when its permissions change.
    This ensures that permission changes take effect immediately.
    """
    logger.info(f"[Signal] Clearing permission cache for role '{instance.name}' (ID: {instance.id})")
    # Clear the _role_perm_cache for all users having this role
    users = list(instance.customuser_roles.all())
    cleared_count = clear_user_permission_cache(users)
    logger.info(f"[Signal] Cleared permission cache for {cleared_count} users with role '{instance.name}'")


def clear_user_role_cache(sender, instance, **kwargs):
    """
    Clear permission cache for a user when their roles change.
    """
    logger.info(f"[Signal] Clearing permission cache for user '{instance}' (ID: {instance.id})")
    cleared_count = clear_user_permission_cache([instance])
    logger.info(f"[Signal] Cleared {cleared_count} cache entries for user '{instance}'")


@receiver(m2m_changed, sender=Role.permissions.through)
def on_role_permissions_changed(sender, instance, action, **kwargs):
    """
    Signal handler for when role permissions are modified.
    Only acts on post_add, post_remove, and post_clear actions.
    """
    if action in ('post_add', 'post_remove', 'post_clear'):
        logger.info(f"[Signal] Role permissions changed for '{instance.name}' - action: {action}")
        clear_role_permission_cache(sender, instance, **kwargs)


@receiver(post_save, sender=Role)
def on_role_saved(sender, instance, **kwargs):
    """
    Signal handler for when a role is saved (in case parent role changes).
    """
    logger.info(f"[Signal] Role saved: '{instance.name}' (ID: {instance.id})")
    # Clear cache when role is saved (in case parent role changes which affect get_all_permissions)
    clear_role_permission_cache(sender, instance, **kwargs)


@receiver(m2m_changed, sender=CustomUser.roles.through)
def on_user_roles_changed(sender, instance, action, **kwargs):
    """
    Signal handler for when a user's role assignments change.
    Only acts on post_add, post_remove, and post_clear actions.
    """
    if action in ('post_add', 'post_remove', 'post_clear'):
        logger.info(f"[Signal] User roles changed for '{instance}' - action: {action}")
        clear_user_role_cache(sender, instance, **kwargs)


# Also keep the old-style connections for backwards compatibility
# These will be caught by the @receiver decorators above, but we keep them
# in case there are edge cases where decorators don't fire
m2m_changed.connect(
    clear_role_permission_cache,
    sender=Role.permissions.through
)

post_save.connect(
    clear_role_permission_cache,
    sender=Role
)

m2m_changed.connect(
    clear_user_role_cache,
    sender=CustomUser.roles.through
)

# Manually connect the signal to ensure it's registered
post_save.connect(create_or_update_user_profile, sender=CustomUser)
