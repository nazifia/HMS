from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.cors import CorsMiddleware

ORIGIN = "http://localhost:5000"


@override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN])
class CorsMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.inner_calls = 0

    def _middleware(self):
        def inner(request):
            self.inner_calls += 1
            return HttpResponse("ok")

        return CorsMiddleware(inner)

    def test_preflight_answered_without_reaching_the_view(self):
        request = self.rf.options(
            "/api/accounts/login/",
            HTTP_ORIGIN=ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        response = self._middleware()(request)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.inner_calls, 0)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
        self.assertIn("authorization", response["Access-Control-Allow-Headers"])

    def test_module_api_path_allowed_with_credentials(self):
        request = self.rf.get("/pharmacy/api/carts/", HTTP_ORIGIN=ORIGIN)
        response = self._middleware()(request)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
        self.assertIn("Origin", response["Vary"])

    def test_logout_allowed_so_the_web_client_can_end_its_session(self):
        request = self.rf.get("/accounts/logout/", HTTP_ORIGIN=ORIGIN)
        response = self._middleware()(request)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

    def test_non_api_path_is_not_exposed_cross_origin(self):
        request = self.rf.get("/patients/1/", HTTP_ORIGIN=ORIGIN)
        response = self._middleware()(request)
        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertEqual(self.inner_calls, 1)

    def test_other_origin_is_left_alone(self):
        request = self.rf.get("/pharmacy/api/carts/", HTTP_ORIGIN="http://evil.example")
        response = self._middleware()(request)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_disabled_when_no_origins_configured(self):
        with self.assertRaises(MiddlewareNotUsed):
            self._middleware()
