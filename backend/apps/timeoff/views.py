"""Time-off API: leave types, balances, requests, actions and the calendar."""

import calendar as calendar_module
from datetime import date

from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import (
    IsHROrAdminOrReadOnly,
    LeaveRequestPermission,
)
from apps.core.scoping import (
    scope_calendar_requests,
    scope_leave_balances,
    scope_leave_requests,
)

from . import services
from .models import Holiday, LeaveBalance, LeaveRequest, LeaveType
from .serializers import (
    CalendarLeaveSerializer,
    HolidaySerializer,
    LeaveBalanceSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
    LeaveReviewSerializer,
    LeaveTypeSerializer,
)


def _current_employee(user):
    employee = getattr(user, "employee", None)
    if employee is None:
        raise ValidationError(
            "Your account is not linked to an employee record, so it cannot "
            "request leave."
        )
    return employee


def _int_param(request, name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({name: ["Enter a whole number."]}) from exc
    if not minimum <= value <= maximum:
        raise ValidationError({name: [f"Must be between {minimum} and {maximum}."]})
    return value


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """Leave types: everyone reads (the request dialog needs them), HR writes."""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsHROrAdminOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "This leave type has requests and cannot be deleted."
            ) from exc


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Balances are read-only; allocate_balances and approvals move them."""

    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = LeaveBalance.objects.select_related("leave_type", "employee")
        queryset = scope_leave_balances(queryset, self.request.user)

        params = self.request.query_params
        year = params.get("year")
        if year:
            try:
                year_value = int(year)
            except ValueError as exc:
                raise ValidationError({"year": ["Enter a whole year."]}) from exc
            queryset = queryset.filter(year=year_value)

        # Used by the HR/admin employee time-off page. The scope above already
        # prevents anyone else from reading another employee's balances.
        employee = params.get("employee")
        if employee:
            try:
                employee_id = int(employee)
            except ValueError as exc:
                raise ValidationError(
                    {"employee": ["Enter a whole number."]}
                ) from exc
            queryset = queryset.filter(employee_id=employee_id)
        return queryset


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """Requests: read scoped, create for yourself, approve/reject/cancel."""

    permission_classes = [LeaveRequestPermission]

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            "DELETE",
            detail="Leave requests are cancelled, not deleted.",
        )

    def get_queryset(self):
        queryset = LeaveRequest.objects.select_related(
            "employee__user", "employee__team", "leave_type", "reviewer"
        ).order_by("-created_at", "-id")
        queryset = scope_leave_requests(queryset, self.request.user)

        params = self.request.query_params
        status_value = params.get("status")
        if status_value:
            if status_value not in LeaveRequest.Status.values:
                raise ValidationError({"status": ["Unknown leave status."]})
            queryset = queryset.filter(status=status_value)

        # "My time off" must never show a manager's team or HR's whole company
        # when the page is asking for the caller's own requests.
        mine = params.get("mine")
        if mine is not None:
            normalized = mine.lower()
            if normalized in {"true", "1"}:
                employee = getattr(self.request.user, "employee", None)
                queryset = (
                    queryset.filter(employee=employee)
                    if employee is not None
                    else queryset.none()
                )
            elif normalized not in {"false", "0"}:
                raise ValidationError({"mine": ["Use true or false."]})

        for name, column in (("leave_type", "leave_type_id"), ("employee", "employee_id")):
            raw = params.get(name)
            if not raw:
                continue
            try:
                value = int(raw)
            except ValueError as exc:
                raise ValidationError({name: ["Enter a whole number."]}) from exc
            queryset = queryset.filter(**{column: value})

        year = params.get("year")
        if year:
            try:
                year_value = int(year)
            except ValueError as exc:
                raise ValidationError({"year": ["Enter a whole year."]}) from exc
            queryset = queryset.filter(start_date__year=year_value)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveRequestCreateSerializer
        return LeaveRequestSerializer

    def create(self, request, *args, **kwargs):
        employee = _current_employee(request.user)
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave = services.request_leave(
            employee=employee, **serializer.validated_data
        )
        return Response(
            LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Day count, remaining balance and overlap for the request dialog."""
        employee = _current_employee(request.user)
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            services.preview_leave(employee=employee, **serializer.validated_data)
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave = self.get_object()
        payload = LeaveReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = services.approve_leave(
            request_id=leave.pk,
            reviewer=request.user,
            comment=payload.validated_data.get("comment", ""),
        )
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave = self.get_object()
        payload = LeaveReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = services.reject_leave(
            request_id=leave.pk,
            reviewer=request.user,
            comment=payload.validated_data.get("comment", ""),
        )
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        leave = self.get_object()
        leave = services.cancel_leave(request_id=leave.pk, actor=request.user)
        return Response(LeaveRequestSerializer(leave).data)


class LeaveCalendarView(APIView):
    """Approved leave for one month, scoped to the caller, plus holidays."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        today = timezone.localdate()
        year = _int_param(
            request, "year", today.year, minimum=1, maximum=9999
        )
        month = _int_param(request, "month", today.month, minimum=1, maximum=12)

        first = date(year, month, 1)
        last = date(year, month, calendar_module.monthrange(year, month)[1])

        queryset = (
            LeaveRequest.objects.filter(
                status=LeaveRequest.Status.APPROVED,
                start_date__lte=last,
                end_date__gte=first,
            )
            .select_related("employee", "leave_type")
            .order_by("start_date", "employee__first_name")
        )
        queryset = scope_calendar_requests(queryset, request.user)
        holidays = Holiday.objects.filter(date__range=(first, last))

        return Response(
            {
                "year": year,
                "month": month,
                "results": CalendarLeaveSerializer(queryset, many=True).data,
                "holidays": HolidaySerializer(holidays, many=True).data,
            }
        )
