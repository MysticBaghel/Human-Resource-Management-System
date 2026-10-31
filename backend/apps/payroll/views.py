"""Payroll API: salary structures, revisions, monthly payroll and payslips."""

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import (
    IsHROrAdmin,
    PayrollRecordPermission,
    SalaryStructurePermission,
)
from apps.core.scoping import scope_employee_owned

from . import services
from .models import PayrollRecord, SalaryRevision, SalaryStructure
from .payslip import render_payslip
from .serializers import (
    PayrollAdjustmentSerializer,
    PayrollGenerateSerializer,
    PayrollPaymentSerializer,
    PayrollPeriodSerializer,
    PayrollRecordSerializer,
    SalaryRevisionSerializer,
    SalaryStructureSerializer,
    SalaryStructureWriteSerializer,
)


def _bool_param(request, name: str, default: bool = False) -> bool:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    normalized = raw.lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValidationError({name: ["Use true or false."]})


def _int_param(request, name: str) -> int | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError({name: ["Enter a whole number."]}) from exc


class SalaryStructureViewSet(viewsets.ModelViewSet):
    """Salary structures: HR/admin manage, everyone reads their own.

    A revision never edits the old row: it deactivates it and creates a new
    active version, leaving the history intact.
    """

    permission_classes = [SalaryStructurePermission]
    filter_backends = [SearchFilter]
    search_fields = [
        "employee__first_name",
        "employee__last_name",
        "employee__user__email",
        "employee__job_title",
        "employee__team__name",
    ]

    def get_queryset(self):
        queryset = SalaryStructure.objects.select_related(
            "employee__user", "employee__team", "created_by"
        ).order_by("employee__first_name", "employee__last_name", "-effective_date")

        mine = _bool_param(self.request, "mine")
        queryset = scope_employee_owned(queryset, self.request.user, mine=mine)

        employee = _int_param(self.request, "employee")
        if employee is not None:
            queryset = queryset.filter(employee_id=employee)

        if "active" in self.request.query_params:
            queryset = queryset.filter(is_active=_bool_param(self.request, "active"))

        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return SalaryStructureWriteSerializer
        return SalaryStructureSerializer

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            "DELETE",
            detail="Salary structures are versioned, not deleted.",
        )

    def create(self, request, *args, **kwargs):
        serializer = SalaryStructureWriteSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        structure = services.create_salary_structure(
            actor=request.user, data=dict(serializer.validated_data)
        )
        return Response(
            SalaryStructureSerializer(structure).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        structure = self.get_object()
        serializer = SalaryStructureWriteSerializer(
            data=request.data,
            partial=partial,
            context={**self.get_serializer_context(), "structure": structure},
        )
        serializer.is_valid(raise_exception=True)
        new_structure, _revision = services.revise_salary_structure(
            structure=structure,
            actor=request.user,
            data=dict(serializer.validated_data),
        )
        return Response(SalaryStructureSerializer(new_structure).data)


class SalaryRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    """Salary revision history, visible to HR and admin."""

    serializer_class = SalaryRevisionSerializer
    permission_classes = [IsHROrAdmin]

    def get_queryset(self):
        queryset = SalaryRevision.objects.select_related(
            "employee", "previous_structure", "new_structure", "updated_by"
        ).order_by("-created_at", "-id")

        employee = _int_param(self.request, "employee")
        if employee is not None:
            queryset = queryset.filter(employee_id=employee)
        return queryset


class PayrollRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Monthly payroll.

    HR/admin see every record. Employees and managers see only their own
    finalized records, enforced by the queryset, not by the UI.
    """

    permission_classes = [PayrollRecordPermission]
    filter_backends = [SearchFilter]
    search_fields = [
        "employee_name",
        "employee_code",
        "payslip_number",
        "designation",
        "department",
    ]

    def get_queryset(self):
        queryset = PayrollRecord.objects.select_related(
            "employee__user",
            "employee__team",
            "generated_by",
            "finalized_by",
            "salary_structure",
        ).order_by(
            "-payroll_year",
            "-payroll_month",
            "employee__first_name",
            "employee__last_name",
        )

        mine = _bool_param(self.request, "mine")
        queryset = scope_employee_owned(queryset, self.request.user, mine=mine)

        # Draft payroll is internal to HR/admin. Employees, managers and an
        # HR/admin person looking at their own portal all see finalized only.
        restricted = self.request.user.role not in {"hr", "admin"} or mine
        if restricted:
            queryset = queryset.filter(status=PayrollRecord.Status.FINALIZED)

        year = _int_param(self.request, "year")
        if year is not None:
            queryset = queryset.filter(payroll_year=year)
        month = _int_param(self.request, "month")
        if month is not None:
            queryset = queryset.filter(payroll_month=month)

        status_value = self.request.query_params.get("status")
        if status_value:
            if status_value not in PayrollRecord.Status.values:
                raise ValidationError({"status": ["Unknown payroll status."]})
            queryset = queryset.filter(status=status_value)

        payment_status = self.request.query_params.get("payment_status")
        if payment_status:
            if payment_status not in PayrollRecord.PaymentStatus.values:
                raise ValidationError({"payment_status": ["Unknown payment status."]})
            queryset = queryset.filter(payment_status=payment_status)

        employee = _int_param(self.request, "employee")
        if employee is not None:
            queryset = queryset.filter(employee_id=employee)

        return queryset

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return PayrollAdjustmentSerializer
        return PayrollRecordSerializer

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            "DELETE",
            detail="Payroll records are kept for audit and cannot be deleted.",
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        record = self.get_object()
        serializer = PayrollAdjustmentSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        record = services.adjust_payroll(
            record=record,
            adjustment_amount=serializer.validated_data.get(
                "adjustment_amount", record.adjustment_amount
            ),
            adjustment_note=serializer.validated_data.get(
                "adjustment_note", record.adjustment_note
            ),
        )
        return Response(PayrollRecordSerializer(record).data)

    def _result(self, result: dict) -> dict:
        return {
            "generated_count": result["generated_count"],
            "skipped_count": result["skipped_count"],
            "generated": PayrollRecordSerializer(result["generated"], many=True).data,
            "skipped": result["skipped"],
        }

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Generate draft payroll for one employee or all eligible people."""
        payload = PayrollGenerateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        result = services.generate_payroll(
            actor=request.user,
            month=payload.validated_data["month"],
            year=payload.validated_data["year"],
            employee=payload.validated_data.get("employee"),
        )
        body = self._result(result)
        http_status = (
            status.HTTP_201_CREATED if body["generated_count"] else status.HTTP_200_OK
        )
        return Response(body, status=http_status)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        record = services.finalize_payroll(record=self.get_object(), actor=request.user)
        return Response(PayrollRecordSerializer(record).data)

    @action(detail=False, methods=["post"], url_path="finalize-period")
    def finalize_period(self, request):
        """Finalize every draft record for a month in one transaction."""
        payload = PayrollPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        records = services.finalize_payroll_period(
            month=payload.validated_data["month"],
            year=payload.validated_data["year"],
            actor=request.user,
        )
        return Response(
            {
                "finalized_count": len(records),
                "records": PayrollRecordSerializer(records, many=True).data,
            }
        )

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):
        """Record a payment outcome. No bank transfer is attempted."""
        record = self.get_object()
        payload = PayrollPaymentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        data = payload.validated_data
        if "payment_date" in data:
            payment_date = data["payment_date"]
        elif data["payment_status"] == PayrollRecord.PaymentStatus.PAID:
            payment_date = record.payment_date
        else:
            payment_date = None

        record = services.update_payment_status(
            record=record,
            payment_status=data["payment_status"],
            payment_date=payment_date,
            payment_reference=data.get("payment_reference", record.payment_reference),
        )
        return Response(PayrollRecordSerializer(record).data)

    @action(detail=True, methods=["get"], url_path="payslip")
    def payslip(self, request, pk=None):
        """Download the authenticated employee's (or HR's) PDF payslip."""
        record = self.get_object()
        pdf = render_payslip(record)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="payslip-{record.payslip_number}.pdf"'
        )
        response["Content-Length"] = str(len(pdf))
        return response


class PayrollDashboardView(APIView):
    """HR/admin payroll dashboard for the current month."""

    permission_classes = [IsHROrAdmin]

    def get(self, request) -> Response:
        data = services.build_payroll_dashboard()
        data["recent_activity"] = PayrollRecordSerializer(
            data.pop("recent_activity"), many=True
        ).data
        data["as_of"] = timezone.localdate().isoformat()
        return Response(data)
