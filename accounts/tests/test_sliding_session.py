"""Sliding session expiry must survive replacing SESSION_SAVE_EVERY_REQUEST."""

import time

from django.contrib.sessions.models import Session
from django.test import TestCase

from accounts.models import CustomUser


class SlidingSessionTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="slideuser", password="pw-slide-12345", phone_number="08010000001"
        )
        self.client.force_login(self.user)

    def _expiry(self):
        return Session.objects.get(session_key=self.client.session.session_key).expire_date

    def test_no_session_write_on_ordinary_request(self):
        self.client.get("/dashboard/")
        before = self._expiry()
        self.client.get("/dashboard/")
        self.assertEqual(self._expiry(), before, "session rewritten on every request")

    def test_expiry_slides_once_half_spent(self):
        self.client.get("/dashboard/")
        before = self._expiry()
        # Pretend the last slide happened long enough ago to be due.
        session = self.client.session
        session["_last_slide"] = time.time() - 10**6
        session.save()
        self.client.get("/dashboard/")
        self.assertGreater(self._expiry(), before, "expiry did not slide")
