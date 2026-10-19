"""Employee endpoints: scoped CRUD, deactivation and invite acceptance."""

from django.contrib.auth import login as django_login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.core.permissions import EmployeePermission
from apps.core.scoping import scope_employees

from . import services
from .models import Employee
from .serializers import (
    AcceptInviteSerializer,
    EmployeeSerializer,
    EmployeeWriteSerializer,
)


class EmployeeViewSet(viewsets.ModelViewSet):
    """Employees, scoped by role.

    There is no DELETE: people are deactivated with ``POST {id}/deactivate/``.
    """

    permission_classes = [EmployeePermission]
    filter_backends = [SearchFilter]
    search_fields = ["first_name", "last_name", "user__email", "job_title"]

    def destroy(self, request, *args, **kwargs):
        """People are never hard-deleted, whatever role asks."""
        raise MethodNotAllowed(
            "DELETE",
            detail="Employees are deactivated, not deleted. Use the deactivate action.",
        )

    def get_queryset(self):
        queryset = (
            Employee.objects.select_related("user", "team", "manager")
            .order_by("first_name", "last_name")
        )
        queryset = scope_employees(queryset, self.request.user)

        params = self.request.query_params
        team = params.get("team")
        if team:
            try:
                team_id = int(team)
            except ValueError as exc:
                raise ValidationError({"team": ["Enter a valid team id."]}) from exc
            queryset = queryset.filter(team_id=team_id)

        status_value = params.get("status")
        if status_value:
            if status_value not in Employee.Status.values:
                raise ValidationError({"status": ["Unknown employee status."]})
            queryset = queryset.filter(status=status_value)

        role = params.get("role")
        if role:
            if role not in User.Role.values:
                raise ValidationError({"role": ["Unknown role."]})
            queryset = queryset.filter(user__role=role)

        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return EmployeeWriteSerializer
        return EmployeeSerializer

    def create(self, request, *args, **kwargs):
        serializer = EmployeeWriteSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        employee = services.create_employee(
            actor=request.user, data=dict(serializer.validated_data)
        )
        return Response(
            EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        employee = self.get_object()
        serializer = EmployeeWriteSerializer(
            data=request.data,
            partial=partial,
            context={**self.get_serializer_context(), "employee": employee},
        )
        serializer.is_valid(raise_exception=True)
        employee = services.update_employee(
            employee=employee, actor=request.user, data=dict(serializer.validated_data)
        )
        return Response(EmployeeSerializer(employee).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        employee = self.get_object()
        employee = services.deactivate_employee(employee, actor=request.user)
        return Response(EmployeeSerializer(employee).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        employee = self.get_object()
        employee = services.reactivate_employee(employee, actor=request.user)
        return Response(EmployeeSerializer(employee).data)


class AcceptInviteView(APIView):
    """Public endpoint behind the link in the invite email.

    Accepting sets the password, activates the account and signs the person in,
    so the React page can go straight to the dashboard.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    # A public state-changing endpoint needs CSRF enforced explicitly, for the
    # same reason as login.
    @method_decorator(csrf_protect)
    def post(self, request) -> Response:
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.accept_invite(
            invite=serializer.validated_data["invite"],
            password=serializer.validated_data["password"],
        )
        django_login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
