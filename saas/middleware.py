"""Resolve tenant from subdomain, set it for the request, gate on subscription."""
from django.shortcuts import redirect
from django.urls import reverse

from .current import clear_current_hospital, set_current_hospital
from .models import Hospital

# Hosts/subdomains that are NOT tenants (marketing, signup, app shell).
RESERVED_SUBDOMAINS = {"www", "app", "admin", "api", "localhost", "127", "testserver"}

# Path prefixes a tenant may hit even with a lapsed subscription.
_ALLOWED_WHEN_LAPSED = ("/saas/billing", "/accounts/logout", "/static", "/media")

# Paths an unregistered subdomain may hit (so signup itself doesn't loop).
_ALLOWED_WHEN_UNREGISTERED = ("/saas/signup", "/static", "/media")


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.hospital = self._resolve(request)
        set_current_hospital(request.hospital)
        try:
            gate = self._gate(request)
            return gate if gate is not None else self.get_response(request)
        finally:
            clear_current_hospital()

    def _resolve(self, request):
        host = request.get_host().split(":")[0]
        parts = host.split(".")
        # Need at least sub.domain.tld (3 parts) for a tenant subdomain.
        if len(parts) < 3:
            return None
        sub = parts[0].lower()
        if sub in RESERVED_SUBDOMAINS:
            return None
        # Tenant-shaped host: a non-reserved subdomain. If no hospital exists for
        # it, it's an unregistered tenant — send them to signup, not login.
        request.is_tenant_host = True
        return Hospital.objects.filter(subdomain=sub, is_active=True).first()

    def _gate(self, request):
        hospital = request.hospital
        if hospital is None:
            # Unregistered tenant subdomain → registration page first.
            if getattr(request, "is_tenant_host", False) and not request.path.startswith(
                _ALLOWED_WHEN_UNREGISTERED
            ):
                return redirect(reverse("saas:signup"))
            return None
        if request.path.startswith(_ALLOWED_WHEN_LAPSED):
            return None
        sub = getattr(hospital, "subscription", None)
        if sub is None or not sub.is_current():
            return redirect(reverse("saas:billing"))
        return None
