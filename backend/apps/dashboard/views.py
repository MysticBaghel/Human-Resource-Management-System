"""Dashboard endpoint."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_dashboard


class DashboardView(APIView):
    """One role-scoped payload for the signed-in user's dashboard."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        return Response(build_dashboard(request.user))
