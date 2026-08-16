"""Token lifetime and login rate limiting.

The mobile client holds a DRF token in the device keystore. DRF never expires
one, so these pin the age limit added in `accounts/api/auth.py`: an old token is
refused with 401 (which is what bounces the app back to its login screen), a
sign-in restarts the clock, and the login endpoint itself cannot be hammered.
"""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.throttling import SimpleRateThrottle

from accounts.models import CustomUser, Role


@override_settings(STRICT_ACCESS_CONTROL=True, API_TOKEN_TTL_HOURS=12)
class TokenExpiryTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone_number="08016000001", username="drtoken", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="doctor")
        self.user.roles.add(role)

    def login(self):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": "08016000001", "password": "pw12345"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def auth(self, key):
        return {"HTTP_AUTHORIZATION": f"Token {key}"}

    def age_token(self, hours):
        token = Token.objects.get(user=self.user)
        Token.objects.filter(pk=token.pk).update(
            created=timezone.now() - timedelta(hours=hours)
        )
        return token.key

    def test_fresh_token_works(self):
        key = self.login().json()["token"]
        response = self.client.get("/api/accounts/staff/", **self.auth(key))
        self.assertEqual(response.status_code, 200, response.content)

    def test_expired_token_is_refused_with_401(self):
        key = self.login().json()["token"]
        self.age_token(13)
        response = self.client.get("/api/accounts/staff/", **self.auth(key))
        self.assertEqual(response.status_code, 401, response.content)
        # JSON, not an HTML login page — the app parses this.
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")

    def test_signing_in_again_restarts_the_clock(self):
        key = self.login().json()["token"]
        self.age_token(13)
        self.assertEqual(
            self.client.get("/api/accounts/staff/", **self.auth(key)).status_code, 401
        )

        again = self.login().json()
        self.assertEqual(again["token"], key)  # same key, refreshed timestamp
        self.assertEqual(again["expires_in"], 12 * 3600)
        self.assertEqual(
            self.client.get("/api/accounts/staff/", **self.auth(key)).status_code, 200
        )

    @override_settings(API_TOKEN_TTL_HOURS=0)
    def test_ttl_zero_disables_expiry(self):
        key = self.login().json()["token"]
        self.age_token(24 * 365)
        self.assertEqual(
            self.client.get("/api/accounts/staff/", **self.auth(key)).status_code, 200
        )


@override_settings(
    STRICT_ACCESS_CONTROL=True,
    # The throttle counts attempts in the cache; the deployed default is
    # DatabaseCache, whose table the test database does not carry.
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class LoginThrottleTest(TestCase):
    def setUp(self):
        cache.clear()  # the throttle counts live in the cache
        self.addCleanup(cache.clear)
        # DRF reads THROTTLE_RATES into a class attribute at import, so
        # override_settings(REST_FRAMEWORK=...) does not reach it.
        patch = mock.patch.dict(
            SimpleRateThrottle.THROTTLE_RATES, {"login": "3/min"}
        )
        patch.start()
        self.addCleanup(patch.stop)

    def attempt(self):
        return Client().post(
            "/api/accounts/login/",
            {"phone_number": "08016000009", "password": "wrong"},
            content_type="application/json",
        )

    def test_repeated_attempts_are_throttled(self):
        for _ in range(3):
            self.assertEqual(self.attempt().status_code, 401)
        self.assertEqual(self.attempt().status_code, 429)
