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
    gate against, so allow. Superusers are platform staff and log in on any
    hospital's URL. request.hospital is set by saas.TenantMiddleware."""
    if user.hospital_id is None or user.is_superuser:
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

        # Accept either username or phone number for admin login. Phone numbers
        # are globally unique; usernames are unique per hospital only, so the
        # tenant on the request disambiguates them.
        matches = CustomUser.objects.filter(
            Q(username=username) | Q(phone_number=username)
        )
        req_hospital = getattr(request, "hospital", None)
        if req_hospital is not None and matches.count() > 1:
            matches = matches.filter(hospital=req_hospital)
        user = matches.first() if matches.count() == 1 else None
        if user is None:
            # Either nothing matched, or the same username exists in several
            # hospitals and the request carries no tenant to pick one. Fall back
            # to the globally unique phone number.
            user = CustomUser.objects.filter(phone_number=username).first()
        if user is None:
            return None

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


class TenantAdminBackend(BaseBackend):
    """Grants every Django permission to a hospital's own admin.

    Permission-only backend (``authenticate`` returns None) so it adds no
    PBKDF2 cost to login. Having it here means DRF's model permissions,
    ``PermissionRequiredMixin``, ``{{ perms }}`` in templates and every
    ``user.has_perm()`` call agree with the in-app RBAC helpers: a tenant
    admin can use every feature of their hospital. Rows stay tenant-scoped by
    ``TenantManager``, and the Django admin site is still gated on
    ``is_staff``, so this grants no cross-tenant or platform power.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        return None

    def _is_admin(self, user_obj):
        from accounts.permissions import is_tenant_admin

        return bool(user_obj.is_active) and is_tenant_admin(user_obj)

    def has_perm(self, user_obj, perm, obj=None):
        return self._is_admin(user_obj)

    def has_module_perms(self, user_obj, app_label):
        return self._is_admin(user_obj)

    def get_all_permissions(self, user_obj, obj=None):
        if not self._is_admin(user_obj):
            return set()
        from django.contrib.auth.models import Permission

        return {
            f"{app_label}.{codename}"
            for app_label, codename in Permission.objects.values_list(
                "content_type__app_label", "codename"
            )
        }
