"""
Authentication backends for HMS Application.
MINIMAL VERSION - No logging to prevent Windows OSError.
"""

from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.contrib.auth import get_user_model
from accounts.models import CustomUser, Role

User = get_user_model()


class PhoneNumberBackend(BaseBackend):
    """
    Authentication backend for regular application users using phone numbers.
    This backend is completely separate from admin authentication.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Explicitly skip admin requests
        if request and ('/admin/' in request.path or '/admin' in request.path):
            return None

        # Skip if this looks like a username-based login (likely admin)
        if username and '@' not in username and not username.isdigit() and len(username) < 10:
            return None

        if not username or not password:
            return None

        try:
            # Only authenticate using phone_number field
            user = CustomUser.objects.get(phone_number=username)
            if user.check_password(password):
                return user
            else:
                return None
        except CustomUser.DoesNotExist:
            return None
        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None


class AdminBackend(ModelBackend):
    """
    Authentication backend specifically for Django admin.
    Uses username-based authentication and only allows staff users.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Only handle admin requests OR username-based logins
        is_admin_request = request and ('/admin/' in request.path or '/admin' in request.path)
        is_username_login = username and '@' not in username and not username.isdigit() and len(username) < 15

        if not (is_admin_request or is_username_login):
            return None

        if not username or not password:
            return None

        try:
            # Authenticate using username field only (not phone number)
            user = CustomUser.objects.get(username=username)
            if user.check_password(password):
                # For admin requests, ensure user is staff
                if is_admin_request and not user.is_staff:
                    return None
                return user
            else:
                return None
        except CustomUser.DoesNotExist:
            return None
        except Exception:
            return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return super().has_perm(user_obj, perm, obj)

    def has_module_perms(self, user_obj, app_label):
        if not user_obj.is_active:
            return False
        return super().has_module_perms(user_obj, app_label)


class RolePermissionBackend(ModelBackend):
    """
    Backend that adds role-based permissions to the user.
    """
    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        # Use the standard Django _perm_cache if possible, or our own
        if not hasattr(user_obj, '_role_perm_cache'):
            perms = set()
            # Add permissions from roles
            if hasattr(user_obj, 'roles'):
                # Use select_related for efficiency
                for role in user_obj.roles.all().prefetch_related('permissions'):
                    # role.get_all_permissions() returns a set of Permission objects
                    for permission in role.get_all_permissions():
                        perms.add(f"{permission.content_type.app_label}.{permission.codename}")
            user_obj._role_perm_cache = perms
        return user_obj._role_perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm in self.get_all_permissions(user_obj, obj)

    def get_user(self, user_id):
        """Override to ensure cache is per-request/session friendly."""
        try:
            user = CustomUser.objects.get(pk=user_id)
            return user
        except CustomUser.DoesNotExist:
            return None

