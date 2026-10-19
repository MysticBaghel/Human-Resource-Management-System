"""Make the request's user available to the audit signals."""

from .context import reset_current_user, set_current_user


class CurrentUserMiddleware:
    """Store the authenticated user for the duration of the request.

    Must run after AuthenticationMiddleware, which is what puts ``request.user``
    there in the first place.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_user(getattr(request, "user", None))
        try:
            return self.get_response(request)
        finally:
            reset_current_user(token)
