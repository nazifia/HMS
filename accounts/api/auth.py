"""Token authentication with an age limit.

DRF tokens never expire: a phone left in a taxi stays signed into the ward's
data forever. `Token.created` is refreshed on every sign-in (`LoginView`), so
the limit below means "hours since the user last signed in", not "hours since
the key was first minted".

Set `API_TOKEN_TTL_HOURS=0` to switch expiry off.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


def token_ttl():
    return timedelta(hours=getattr(settings, "API_TOKEN_TTL_HOURS", 12))


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        ttl = token_ttl()
        if ttl and timezone.now() - token.created > ttl:
            raise AuthenticationFailed("Session expired. Sign in again.")
        return user, token
