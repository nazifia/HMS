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
        # Explicitly skip admin requests - admin uses AdminBackend (username-based)
        if request and '/admin' in request.path:
            return None

        if not username or not password:
            return None

        try:
            # Look up by phone_number only. If no user has this phone number,
            # return None and let the next backend (AdminBackend) try username.
            user = CustomUser.objects.get(phone_number=username)
        except CustomUser.DoesNotExist:
            return None

        if user.check_password(password) and user.is_active:
            # Tenant gate: a hospital staff may only authenticate on their own
            # hospital's subdomain. Platform users (hospital is None) log in
            # anywhere. request.hospital is set by saas.TenantMiddleware.
            if user.hospital_id is not None:
                req_hospital = getattr(request, "hospital", None)
                if req_hospital is None or req_hospital.id != user.hospital_id:
                    return None
            return user
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
        if not username or not password:
            return None

        is_admin_request = bool(request and '/admin' in request.path)

        try:
            # Authenticate using the username field only (not phone number).
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return None

        if not user.check_password(password) or not user.is_active:
            return None

        # Admin login page is restricted to staff users.
        if is_admin_request and not user.is_staff:
            return None

        return user

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

    Permission-only backend: it must NOT attempt authentication. Inheriting
    ModelBackend.authenticate would run a full PBKDF2 "dummy" hash (~0.4s) on
    every login because the username lookup misses (USERNAME_FIELD is
    phone_number), needlessly slowing every login. Authentication is handled by
    AdminBackend and PhoneNumberBackend.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        return None

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

