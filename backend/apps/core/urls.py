"""Core URLs: health check and the API's catch-all 404.

The health check is deliberately unauthenticated.
"""

from django.urls import path
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness probe used by the React home page."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        return Response({"status": "ok"})


class ApiNotFoundView(APIView):
    """Anything unmatched under /api/v1/ returns the shared error shape.

    Without this, an unknown API path falls through to Django's HTML 404, which
    breaks the single-error-format convention the client relies on. The normal
    DRF dispatch is skipped on purpose (its per-method handlers only declare
    405); the response is still finalized so it renders as JSON.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        # Reproduce the parts of APIView.dispatch that own the error path, so
        # the 404 still renders through the normal content negotiation.
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            self.initial(request, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - routed to DRF's handler below
            response = self.handle_exception(exc)
        else:
            error = NotFound("No API endpoint matches this path.")
            response = self.handle_exception(error)

        return self.finalize_response(request, response, *args, **kwargs)


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    # Must stay last: it swallows every remaining path under /api/v1/.
    path("<path:unmatched>", ApiNotFoundView.as_view(), name="api-not-found"),
]
