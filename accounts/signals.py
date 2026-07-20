import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import CustomUser, CustomUserProfile, Role

logger = logging.getLogger(__name__)


def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to create or update user profile when a CustomUser is saved.
    """
    if kwargs.get("raw"):
        # Fixture loading (loaddata/restore): profiles come from the fixture,
        # auto-creating one here collides with the unique user_id constraint
        return
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


def clear_shared_user_cache(user_pks):
    """Drop the cross-request context-processor cache entries for these users."""
    from django.core.cache import cache
    pks = [pk for pk in user_pks if pk]
    cache.delete_many([f'page_user_ctx_{pk}' for pk in pks])
    return len(pks)


def clear_user_permission_cache(users):
    """
    Clear permission caches for the given *in-memory* CustomUser instances.

    _role_perm_cache / _perm_cache / _cached_roles are per-instance, so this is
    only effective when the caller holds the same object the request is using —
    which is exactly the case for the user-side m2m signal below.
    """
    for user in users:
        user.clear_permission_cache()
    return clear_shared_user_cache([getattr(u, 'pk', None) for u in users])


def clear_role_permission_cache(sender, instance, **kwargs):
    """
    Clear cached permission context for all users holding a role when that
    role's permissions (or parent) change, so changes take effect immediately.

    Only the shared cache is bust-able here: the users are looked up fresh, so
    their per-instance caches are on throwaway objects. That is fine — those
    caches die with the request that owns them anyway.
    """
    pks = list(instance.customuser_roles.values_list('pk', flat=True))
    cleared_count = clear_shared_user_cache(pks)
    logger.info(
        f"[Signal] Cleared permission cache for {cleared_count} users "
        f"with role '{instance.name}' (ID: {instance.id})"
    )


def clear_user_role_cache(sender, instance, **kwargs):
    """
    Clear cached permission context when a user's role assignments change.

    m2m_changed fires for both directions of CustomUser.roles: instance is a
    CustomUser on user.roles.add(...), but a Role on role.customuser_roles.add(...).
    Dispatch on the type rather than assuming a user.
    """
    if isinstance(instance, Role):
        clear_role_permission_cache(sender, instance, **kwargs)
        return
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


# The three cache-clearing signals above are wired by @receiver alone. The
# duplicate .connect() calls that used to sit here registered the *undecorated*
# functions as separate receivers, so every role save and every m2m change ran
# the clear twice, with an extra customuser_roles query each time.

post_save.connect(create_or_update_user_profile, sender=CustomUser)
