"""Content Security Policy for the server-rendered pages.

Two jobs, and they are enforced differently on purpose:

* ``frame-ancestors`` replaces ``X_FRAME_OPTIONS`` and is *always* enforced --
  report-only mode ignores that directive, and an iframe'd web client needs a
  real answer. It names the browser origins in ``CORS_ALLOWED_ORIGINS``, or
  ``'none'`` when there are none, matching the X-Frame-Options default.
* The rest of the policy (``CSP_POLICY``) ships report-only until
  ``CSP_ENFORCE`` is turned on, so a missed CDN shows up in the browser console
  instead of blanking a ward's screen. Watch the console, fix the policy, then
  enforce.

Only HTML responses get the header: JSON, static files and downloads have
nothing to restrict.
"""

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        if not getattr(settings, "CSP_ENABLED", True):
            raise MiddlewareNotUsed
        self.get_response = get_response

        origins = list(getattr(settings, "CORS_ALLOWED_ORIGINS", ()))
        # Only drop X-Frame-Options where framing is actually wanted: browsers
        # that predate frame-ancestors would otherwise keep blocking the iframe.
        self.framing_allowed = bool(origins)
        sources = " ".join(["'self'", *origins]) if origins else "'none'"
        self.frame_ancestors = f"frame-ancestors {sources}"

        policy = getattr(settings, "CSP_POLICY", {})
        self.policy = "; ".join(f"{name} {value}" for name, value in policy.items())
        self.enforce = getattr(settings, "CSP_ENFORCE", False)

    def __call__(self, request):
        response = self.get_response(request)
        if not response.get("Content-Type", "").startswith("text/html"):
            return response
        if "Content-Security-Policy" in response:
            # A view set its own, tighter policy; leave it be.
            return response

        if self.enforce and self.policy:
            response["Content-Security-Policy"] = f"{self.policy}; {self.frame_ancestors}"
        else:
            response["Content-Security-Policy"] = self.frame_ancestors
            if self.policy:
                response["Content-Security-Policy-Report-Only"] = self.policy

        if self.framing_allowed:
            response.headers.pop("X-Frame-Options", None)
        return response
