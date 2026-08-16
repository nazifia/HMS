"""Telling API callers apart from browsers.

Access-control middleware runs before the view, so when it denies a request it
has to answer for itself. A browser should get a redirect or an error page; an
API client (the mobile app, fetch/XHR) must get JSON — a 302 to the login page
reads as a successful HTML response and produces a confusing parse error on the
client instead of "you are not permitted".
"""
from django.http import JsonResponse


def wants_json(request):
    """True when the caller expects JSON rather than a page."""
    path = request.path
    if path.startswith("/api/") or "/api/" in path:
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    # `Accept: application/json` without text/html is a programmatic client.
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def json_error(message, detail="", status=403):
    return JsonResponse({"error": message, "detail": detail}, status=status)
