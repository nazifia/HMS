"""The HTML login form must stop unlimited password guessing.

The API login is covered by DRF's ScopedRateThrottle (tests_token_expiry);
this covers the session login view.
"""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from accounts.views import LOGIN_ATTEMPT_LIMIT


class LoginThrottleTest(TestCase):
    def setUp(self):
        cache.clear()  # the counter lives in the cache
        self.url = reverse("accounts:login")
        self.user = CustomUser.objects.create_user(
            phone_number="08000000001", username="staff", password="correct-horse"
        )

    def _post(self, password):
        return self.client.post(
            self.url, {"username": "08000000001", "password": password}
        )

    def test_repeated_failures_are_locked_out(self):
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self._post("wrong")

        # Even the correct password is refused once the limit is hit.
        response = self._post("correct-horse")
        self.assertEqual(response.status_code, 200)  # re-rendered form, no redirect
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_success_before_the_limit_clears_the_counter(self):
        for _ in range(LOGIN_ATTEMPT_LIMIT - 1):
            self._post("wrong")

        self.assertEqual(self._post("correct-horse").status_code, 302)

        # Counter reset, so a fresh run of failures is needed to lock out again.
        self.client.logout()
        self.assertEqual(self._post("wrong").status_code, 200)
        self.assertEqual(self._post("correct-horse").status_code, 302)
