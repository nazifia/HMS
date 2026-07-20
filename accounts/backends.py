"""
Authentication backends for HMS Application.
MINIMAL VERSION - No logging to prevent Windows OSError.
"""

from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from accounts.models import CustomUser, Role
from core.validators import normalize_nigerian_phone

User = get_user_model()


def _tenant_allowed(user, request):
    """Tenant gate: hospital staff may only authenticate on their own
    hospital's subdomain. Platform users (hospital is None) log in anywhere.
    When no tenant is resolved (localhost / bare domain) there is nothing to
    gate against, so allow. request.hospital is set by saas.TenantMiddleware."""
    if user.hospital_id is None:
        return True
    req_hospital = getattr(request, "hospital", None)
    return req_hospital is None or req_hospital.id == user.hospital_id


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
            # Normalize so users can log in typing +234... against stored 0... form.
            user = CustomUser.objects.get(
                phone_number=normalize_nigerian_phone(username)
            )
        except CustomUser.DoesNotExist:
            return None

        if user.check_password(password) and user.is_active:
            if not _tenant_allowed(user, request):
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
            # Accept either username or phone number for admin login.
            user = CustomUser.objects.get(
                Q(username=username) | Q(phone_number=username)
            )
        except CustomUser.DoesNotExist:
            return None
        except CustomUser.MultipleObjectsReturned:
            # Same string is one user's username and another's phone: prefer username.
            user = CustomUser.objects.get(username=username)

        if not user.check_password(password) or not user.is_active:
            return None

        # Admin login page is restricted to staff users.
        if is_admin_request and not user.is_staff:
            return None

        # Same tenant gate as PhoneNumberBackend — without it, this backend
        # (which runs first and also matches phone numbers) lets hospital A
        # staff log in on hospital B's subdomain.
        if not _tenant_allowed(user, request):
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

        if not hasattr(user_obj, '_role_perm_cache'):
            user_obj._role_perm_cache = self._collect_role_perms(user_obj)
        return user_obj._role_perm_cache

    @staticmethod
    def _collect_role_perms(user_obj):
        """Permission strings from the user's roles plus every ancestor role.

        Previously this called Role.get_all_permissions() per role, which walks
        the parent chain issuing one query per ancestor per role. The role table
        holds tens of rows, so loading the whole id->parent_id map once and
        walking it in memory costs three queries total regardless of depth.
        """
        if not hasattr(user_obj, 'roles'):
            return set()

        role_ids = set(user_obj.roles.values_list('id', flat=True))
        if not role_ids:
            return set()

        parent_of = dict(Role.objects.values_list('id', 'parent_id'))
        wanted = set()
        pending = list(role_ids)
        while pending:
            role_id = pending.pop()
            if role_id in wanted:
                continue  # also breaks any accidental parent cycle
            wanted.add(role_id)
            parent_id = parent_of.get(role_id)
            if parent_id is not None:
                pending.append(parent_id)

        return {
            f"{app_label}.{codename}"
            for app_label, codename in Role.permissions.through.objects.filter(
                role_id__in=wanted
            ).values_list(
                'permission__content_type__app_label', 'permission__codename'
            )
        }

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

