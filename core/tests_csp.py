from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.csp import ContentSecurityPolicyMiddleware

ORIGIN = "http://localhost:5000"
POLICY = {"default-src": "'self'", "object-src": "'none'"}


@override_settings(CSP_ENABLED=True, CSP_POLICY=POLICY, CSP_ENFORCE=False)
class CspMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def _middleware(self, response=None):
        def inner(request):
            page = response or HttpResponse("<html></html>")
            page.setdefault("X-Frame-Options", "DENY")
            return page

        return ContentSecurityPolicyMiddleware(inner)

    def _page(self):
        return self._middleware()(self.rf.get("/dashboard/"))

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_framing_denied_and_x_frame_options_kept_without_a_web_client(self):
        page = self._page()
        self.assertEqual(page["Content-Security-Policy"], "frame-ancestors 'none'")
        self.assertEqual(page["X-Frame-Options"], "DENY")

    @override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN])
    def test_configured_origin_may_frame_the_page(self):
        page = self._page()
        self.assertEqual(
            page["Content-Security-Policy"], f"frame-ancestors 'self' {ORIGIN}"
        )
        self.assertNotIn("X-Frame-Options", page)

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_policy_only_reports_until_enforced(self):
        page = self._page()
        self.assertIn("object-src 'none'", page["Content-Security-Policy-Report-Only"])
        self.assertNotIn("object-src", page["Content-Security-Policy"])

    @override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN], CSP_ENFORCE=True)
    def test_enforcing_sends_one_header_with_framing_included(self):
        page = self._page()
        self.assertIn("object-src 'none'", page["Content-Security-Policy"])
        self.assertIn(f"frame-ancestors 'self' {ORIGIN}", page["Content-Security-Policy"])
        self.assertNotIn("Content-Security-Policy-Report-Only", page)

    @override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN])
    def test_json_responses_are_left_alone(self):
        middleware = self._middleware(JsonResponse({"ok": True}))
        response = middleware(self.rf.get("/pharmacy/api/carts/"))
        self.assertNotIn("Content-Security-Policy", response)
        self.assertEqual(response["X-Frame-Options"], "DENY")

    @override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN])
    def test_a_views_own_policy_wins(self):
        page = HttpResponse("<html></html>")
        page["Content-Security-Policy"] = "default-src 'none'"
        response = self._middleware(page)(self.rf.get("/dashboard/"))
        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'")

    @override_settings(CSP_ENABLED=False)
    def test_disabled_by_setting(self):
        with self.assertRaises(MiddlewareNotUsed):
            self._middleware()
