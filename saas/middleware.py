"""Resolve tenant from a /t/<sub>/ path prefix, set it, gate on subscription.

Path-based (not subdomain-based) tenancy: PythonAnywhere serves no valid TLS
cert for nested subdomains (testhospital.nazhms.pythonanywhere.com), so every
tenant lives under one cert, e.g. nazhms.pythonanywhere.com/t/testhospital/.

ponytail: re-add the stripped prefix via Django's script-prefix so reverse()
keeps emitting /t/<sub>/... links with zero changes to urls.py. Move to real
subdomains only if you get wildcard TLS (custom domain + paid host).
"""
import re

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import get_script_prefix, reverse, set_script_prefix

from .current import clear_current_hospital, set_current_hospital
from .models import Hospital

_TENANT_PATH = re.compile(r"^/t/([\w-]+)(/.*)?$")

# Path prefixes (post-strip) a tenant may hit even with a lapsed subscription.
_ALLOWED_WHEN_LAPSED = (
    "/saas/billing",
    "/saas/request-activation",
    "/accounts/logout",
    "/static",
    "/media",
)

# Paths an unregistered tenant may hit (so signup itself doesn't loop).
_ALLOWED_WHEN_UNREGISTERED = ("/saas/signup", "/static", "/media")


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.hospital = None
        request.tenant_sub = None
        request.is_tenant_host = False
        outer_prefix = get_script_prefix()
        self._resolve(request)
        denied = self._bind_user_tenant(request) or self._block_django_admin(request)
        set_current_hospital(request.hospital)
        try:
            if denied is not None:
                return denied
            gate = self._gate(request)
            if gate is not None:
                return gate
            return self._reprefix_redirect(request, self.get_response(request))
        finally:
            clear_current_hospital()
            # The script prefix is thread-local. Handlers normally reset it per
            # request, but restoring it here keeps one request's tenant prefix
            # from compounding onto the next on the same thread.
            set_script_prefix(outer_prefix)

    def _bind_user_tenant(self, request):
        """Pin the tenant to the logged-in user's own hospital.

        The session cookie is host-wide, so path-based tenancy alone does not
        isolate an authenticated user: staff of hospital A could walk to
        /t/b/... and read B's rows, or drop the prefix entirely and hit the
        bare host, where TenantManager falls open and returns every tenant's
        rows. Platform users (hospital_id None) keep roaming, and so do
        superusers: they are platform staff and may enter any tenant by typing
        /t/<sub>/ (see saas.views.hospitals for the picker), even if a
        hospital was stamped on their row at creation time.
        """
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return None
        if user.is_superuser:
            return None
        if user.hospital_id is None:
            return None
        if request.hospital is None:
            if not request.is_tenant_host:
                request.hospital = user.hospital  # bare host: scope to own tenant
            return None
        if request.hospital.id != user.hospital_id:
            return HttpResponseForbidden("This account belongs to another hospital.")
        return None

    @staticmethod
    def _block_django_admin(request):
        """Keep tenant staff out of /admin/.

        Tenant admins carry is_staff (the app's own admin flag), which is also
        Django's "may open /admin/" flag. Model querysets there are tenant
        scoped, but the platform tables — Hospital, Plan, Subscription, Role,
        Permission — are not. Tenants manage their hospital through the app UI;
        /admin/ stays a platform-superuser tool.
        """
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False) or user.is_superuser:
            return None
        if user.hospital_id and request.path_info.startswith("/admin"):
            return HttpResponseForbidden("The Django admin is platform staff only.")
        return None

    def _reprefix_redirect(self, request, response):
        """Put /t/<sub> back on absolute-path redirects.

        Views (and Django itself: APPEND_SLASH, the LOGIN_URL redirect) build
        Location from the *stripped* path, so an un-prefixed '/foo/' would send
        a tenant user to the bare host. reverse()-built links already carry the
        prefix via the script prefix and are left alone.
        """
        if not request.is_tenant_host or "Location" not in response.headers:
            return response
        loc = response.headers["Location"]
        prefix = "/t/" + request.tenant_sub
        if not loc.startswith("/") or loc.startswith("//"):
            return response  # absolute or protocol-relative URL
        if loc == prefix or loc.startswith(prefix + "/"):
            return response  # already prefixed
        response.headers["Location"] = prefix + loc
        return response

    def _resolve(self, request):
        m = _TENANT_PATH.match(request.path_info)
        if not m:
            return  # bare host = marketing / signup / app shell, no tenant
        sub = m.group(1).lower()
        request.tenant_sub = sub
        request.is_tenant_host = True

        # Strip /t/<sub> from the path the URL resolver sees, then push it onto
        # the script prefix so reverse() prepends it back into generated links.
        prefix = "/t/" + sub
        request.path_info = m.group(2) or "/"
        request.path = request.path_info
        set_script_prefix(get_script_prefix().rstrip("/") + prefix + "/")

        request.hospital = Hospital.objects.filter(
            subdomain=sub, is_active=True
        ).first()

    def _gate(self, request):
        # Gate on the resolved hospital, not on the URL shape: a lapsed tenant
        # must not slip past the paywall by dropping the /t/<sub> prefix (the
        # user binding above still scopes them to their own hospital).
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return None  # platform staff inspect lapsed tenants too
        path = request.path_info  # already stripped of /t/<sub>
        hospital = request.hospital
        if hospital is None:
            if not request.is_tenant_host:
                return None  # bare host, no tenant: marketing / signup / login
            # Unregistered tenant → global signup, which lives on the bare host
            # (not under /t/<sub>/), so use a literal path: reverse() would wrongly
            # prepend the active tenant prefix here.
            if not path.startswith(_ALLOWED_WHEN_UNREGISTERED):
                return redirect("/saas/signup/")
            return None
        if path.startswith(_ALLOWED_WHEN_LAPSED):
            return None
        sub = getattr(hospital, "subscription", None)
        if sub is None or not sub.is_current():
            return redirect(reverse("saas:billing"))
        return None
