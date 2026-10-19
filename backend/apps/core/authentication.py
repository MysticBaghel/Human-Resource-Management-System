"""Authentication classes.

Session auth with one addition: a deactivated user must not keep working from
an existing session. Django's session backend keeps authenticating them until
the session expires, which the Handbook forbids ("inactive users cannot log in").
"""

from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication


class ActiveSessionAuthentication(SessionAuthentication):
    """SessionAuthentication that also rejects deactivated users."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, auth = result
        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                "This account has been deactivated.", code="inactive_user"
            )
        return user, auth
