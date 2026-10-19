"""Authentication endpoints: session login, logout, me and password reset.

Session auth plus CSRF is the chosen scheme, so React is served same-origin.
"""

from django.conf import settings
from django.contrib.auth import get_user_model, login as django_login, logout as django_logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.core.permissions import IsAdmin, IsEmployee, IsHR, IsManager

from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)

User = get_user_model()


class CsrfView(APIView):
    """Sets the CSRF cookie so the browser can send it back on login.

    Django only sets the cookie on a rendered page; React is a separate origin
    in dev, so the client calls this once before its first unsafe request.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request) -> Response:
        return Response({"detail": "CSRF cookie set."})


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    # DRF's APIView is csrf_exempt and its SessionAuthentication only enforces
    # CSRF once a user is authenticated. Without this, an anonymous POST here
    # would be unprotected (login CSRF).
    @method_decorator(csrf_protect)
    def post(self, request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # authenticate() rejects inactive users, so no extra check is needed here.
        django_login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request) -> Response:
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request) -> Response:
        return Response(UserSerializer(request.user).data)


class PasswordResetRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    # Public state-changing endpoint, so CSRF is enforced explicitly for the
    # same reason as LoginView.
    @method_decorator(csrf_protect)
    def post(self, request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Reset your HRMS password",
                message=(
                    f"Hello,\n\n"
                    f"Use this link to choose a new password:\n{reset_url}\n\n"
                    f"If you did not ask for this, you can ignore this email.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        # Always the same answer, so the endpoint cannot be used to enumerate users.
        return Response(
            {"detail": "If that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @method_decorator(csrf_protect)
    def post(self, request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class RoleProbeView(APIView):
    """Test-only endpoint used to prove role permissions are enforced.

    Phase 1 keeps this because the permission matrix cannot be tested without
    some protected resource; Phase 2 replaces it with the real viewsets.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        return Response({"role": request.user.role, "detail": "authenticated"})


class AdminProbeView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request) -> Response:
        return Response({"detail": "admin only"})


class HRProbeView(APIView):
    permission_classes = [IsHR]

    def get(self, request) -> Response:
        return Response({"detail": "hr only"})


class ManagerProbeView(APIView):
    permission_classes = [IsManager]

    def get(self, request) -> Response:
        return Response({"detail": "manager only"})


class EmployeeProbeView(APIView):
    permission_classes = [IsEmployee]

    def get(self, request) -> Response:
        return Response({"detail": "employee only"})
