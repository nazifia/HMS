"""A logged-in session must survive plain page loads.

Guards the cached_db-over-DatabaseCache regression: the cached copy of a session
could go empty while django_session still held the real one, and the request was
then served as anonymous -> redirect to /accounts/login/?next=... Reproduced at
~2-3% of requests, so this hits the same URL many times.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase


class SessionPersistenceTests(TestCase):
    def test_session_engine_matches_cache_backend(self):
        cached_db = settings.SESSION_ENGINE.endswith("cached_db")
        db_cache = "db.DatabaseCache" in settings.CACHES["default"]["BACKEND"]
        locmem = "LocMemCache" in settings.CACHES["default"]["BACKEND"]
        self.assertFalse(
            cached_db and (db_cache or locmem),
            "cached_db sessions need a real shared cache (Redis); over "
            "DatabaseCache/LocMemCache they drop logins.",
        )

    def test_login_survives_repeated_requests(self):
        user = get_user_model().objects.create_user(
            phone_number="08000000001", username="session_probe", password="pw12345!"
        )
        self.client.force_login(user)
        for _ in range(60):
            response = self.client.get("/dashboard/")
            self.assertNotIn(
                "/accounts/login/",
                response.get("Location", "") or "",
                "logged-in user was bounced to the login page",
            )
