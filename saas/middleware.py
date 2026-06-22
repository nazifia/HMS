"""Resolve tenant from a /t/<sub>/ path prefix, set it, gate on subscription.

Path-based (not subdomain-based) tenancy: PythonAnywhere serves no valid TLS
cert for nested subdomains (testhospital.nazhms.pythonanywhere.com), so every
tenant lives under one cert, e.g. nazhms.pythonanywhere.com/t/testhospital/.

ponytail: re-add the stripped prefix via Django's script-prefix so reverse()
keeps emitting /t/<sub>/... links with zero changes to urls.py. Move to real
subdomains only if you get wildcard TLS (custom domain + paid host).
"""
import re

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
        self._resolve(request)
        set_current_hospital(request.hospital)
        try:
            gate = self._gate(request)
            return gate if gate is not None else self.get_response(request)
        finally:
            clear_current_hospital()

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
        if not request.is_tenant_host:
            return None
        path = request.path_info  # already stripped of /t/<sub>
        hospital = request.hospital
        if hospital is None:
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
