"""
Signal handlers for core app.
Handles cache invalidation when UI permissions are modified.
"""

from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender='core.UIPermission_required_roles')
def clear_cache_on_role_change(sender, instance, action, **kwargs):
    """
    Clear cache when roles are added/removed from a UIPermission.
    This ensures users immediately see correct menu items after role changes.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Clear cache for this specific permission
        try:
            instance.clear_cache()
            logger.info(f"Cache cleared for {instance.element_id} after role change (action: {action})")
        except Exception as e:
            logger.error(f"Error clearing cache for {instance.element_id}: {e}")
            # Fallback: clear all caches
            cache.clear()
            logger.info("Cleared entire cache as fallback")


@receiver(m2m_changed, sender='core.UIPermission_required_permissions')
def clear_cache_on_permission_change(sender, instance, action, **kwargs):
    """
    Clear cache when permissions are added/removed from a UIPermission.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Clear cache for this specific permission
        try:
            instance.clear_cache()
            logger.info(f"Cache cleared for {instance.element_id} after permission change (action: {action})")
        except Exception as e:
            logger.error(f"Error clearing cache for {instance.element_id}: {e}")
            # Fallback: clear all caches
            cache.clear()
            logger.info("Cleared entire cache as fallback")
