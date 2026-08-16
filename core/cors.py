"""Cross-origin API access for the Flutter web client.

The server-rendered site is same-origin and the mobile client sends no Origin
header, so nothing here runs for either: with ``CORS_ALLOWED_ORIGINS`` empty
(the default) the middleware removes itself from the stack entirely.

Only the API paths in ``CORS_ALLOWED_PATHS`` answer cross-origin. The
server-rendered pages are reached by iframe navigation, which is not a CORS
request at all -- framing is governed by ``core.csp`` instead.
"""

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers

# What the Flutter client actually sends; token auth needs Authorization, the
# WebView pages post forms with the CSRF token.
ALLOWED_HEADERS = "authorization, content-type, x-csrftoken, x-requested-with"
ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

# Every module exposes its endpoints under `<module>/api/`, so one substring
# covers them; the client also ends its session through the logout view.
DEFAULT_PATHS = ("/api/", "/accounts/logout/")


class CorsMiddleware:
    def __init__(self, get_response):
        self.allowed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", ()))
        if not self.allowed:
            raise MiddlewareNotUsed
        self.paths = tuple(getattr(settings, "CORS_ALLOWED_PATHS", DEFAULT_PATHS))
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        if origin not in self.allowed or not any(p in request.path for p in self.paths):
            return self.get_response(request)

        preflight = (
            request.method == "OPTIONS"
            and "Access-Control-Request-Method" in request.headers
        )
        # A preflight carries neither cookie nor token, so it must not reach the
        # access control middleware -- answer it here and skip the rest of the
        # stack, or every cross-origin call is refused before the real request.
        response = HttpResponse(status=204) if preflight else self.get_response(request)

        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        patch_vary_headers(response, ["Origin"])

        if preflight:
            response["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            response["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            response["Access-Control-Max-Age"] = "86400"
        return response
