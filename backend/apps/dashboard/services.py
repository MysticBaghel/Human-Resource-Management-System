"""Role-aware dashboard data, computed from the database.

One response per role so the frontend makes one request and cannot assemble a
company-wide view for a role that is not allowed to see one. Every queryset here
is scoped by the caller's role; the employee variant never touches company-wide
aggregates.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.employees.models import Employee
from apps.organization.models import Team
from apps.timeoff.models import LeaveBalance, LeaveRequest
from apps.timeoff.serializers import LeaveBalanceSerializer, LeaveRequestSerializer

REVIEW_PENDING_AGE = timedelta(days=2)
RECENT_LIMIT = 6
LIST_LIMIT = 5


def _leave_queryset():
    return LeaveRequest.objects.select_related(
        "employee", "leave_type", "reviewer"
    )


def _pending():
    return _leave_queryset().filter(status=LeaveRequest.Status.PENDING)


def _approved_today():
    today = timezone.localdate()
    return _leave_queryset().filter(
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=today,
        end_date__gte=today,
    )


def _distinct_employee_count(queryset) -> int:
    return queryset.values("employee_id").distinct().count()


def _serialize_requests(queryset) -> list[dict]:
    return LeaveRequestSerializer(queryset, many=True).data


def _serialize_audit(queryset) -> list[dict]:
    return AuditLogSerializer(queryset, many=True).data


def _recent_audit(queryset=None, *, limit: int = RECENT_LIMIT) -> list[dict]:
    rows = (queryset or AuditLog.objects.all()).select_related("actor").order_by(
        "-created_at", "-id"
    )[:limit]
    return _serialize_audit(rows)


def build_dashboard(user) -> dict:
    role = getattr(user, "role", None)
    if role == User.Role.ADMIN:
        return _admin_dashboard()
    if role == User.Role.HR:
        return _hr_dashboard()
    if role == User.Role.MANAGER:
        return _manager_dashboard(user)
    if role == User.Role.EMPLOYEE:
        return _employee_dashboard(user)
    # Fail closed for an unknown role rather than leaking any aggregate.
    return {"role": role, "metrics": {}}


def _admin_dashboard() -> dict:
    return {
        "role": User.Role.ADMIN,
        "metrics": {
            "active_employees": Employee.objects.filter(
                status=Employee.Status.ACTIVE
            ).count(),
            "teams": Team.objects.count(),
            "pending_leave_requests": _pending().count(),
            "on_leave_today": _distinct_employee_count(_approved_today()),
        },
        "recent_activity": _recent_audit(),
    }


def _hr_dashboard() -> dict:
    pending = _pending()
    employee_changes = AuditLog.objects.filter(
        model="employees.employee",
        action__in=[AuditLog.Action.CREATE, AuditLog.Action.UPDATE],
    )
    return {
        "role": User.Role.HR,
        "metrics": {
            "active_employees": Employee.objects.filter(
                status=Employee.Status.ACTIVE
            ).count(),
            "teams": Team.objects.count(),
            "pending_leave_requests": pending.count(),
            # These are the ones whose manager is absent, so HR is the approver.
            "pending_without_manager": pending.filter(
                employee__manager__isnull=True
            ).count(),
            "on_leave_today": _distinct_employee_count(_approved_today()),
        },
        "recent_employee_changes": _recent_audit(employee_changes, limit=LIST_LIMIT),
        "recent_activity": _recent_audit(),
    }


def _review_scope(employee: Employee):
    """Requests this manager is allowed to decide.

    Their direct reports and the members of teams they lead, excluding their own
    leave (nobody approves their own request).
    """
    return (
        _leave_queryset()
        .filter(
            Q(employee__manager=employee) | Q(employee__team__lead=employee)
        )
        .exclude(employee=employee)
    )


def _manager_dashboard(user) -> dict:
    employee = getattr(user, "employee", None)
    if employee is None:
        return {
            "role": User.Role.MANAGER,
            "metrics": {
                "team_employees": 0,
                "pending_leave_requests": 0,
                "pending_attention": 0,
                "on_leave_today": 0,
            },
            "pending_requests": [],
            "upcoming_leave": [],
        }

    scope = _review_scope(employee)
    pending = scope.filter(status=LeaveRequest.Status.PENDING)
    today = timezone.localdate()

    return {
        "role": User.Role.MANAGER,
        "metrics": {
            "team_employees": Employee.objects.filter(team__lead=employee).count(),
            "pending_leave_requests": pending.count(),
            "pending_attention": pending.filter(
                created_at__lte=timezone.now() - REVIEW_PENDING_AGE
            ).count(),
            "on_leave_today": _distinct_employee_count(
                _approved_today()
                .filter(
                    Q(employee__manager=employee)
                    | Q(employee__team__lead=employee)
                )
                .exclude(employee=employee)
            ),
        },
        "pending_requests": _serialize_requests(
            pending.order_by("-created_at", "-id")[:LIST_LIMIT]
        ),
        "upcoming_leave": _serialize_requests(
            scope.filter(
                status=LeaveRequest.Status.APPROVED,
                start_date__gt=today,
            ).order_by("start_date", "employee__first_name")[:LIST_LIMIT]
        ),
    }


def _employee_dashboard(user) -> dict:
    employee = getattr(user, "employee", None)
    today = timezone.localdate()
    if employee is None:
        return {
            "role": User.Role.EMPLOYEE,
            "metrics": {"pending_leave_requests": 0, "upcoming_leave_count": 0},
            "balances": [],
            "pending_requests": [],
            "upcoming_leave": [],
            "recent_decisions": [],
        }

    own = _leave_queryset().filter(employee=employee)
    pending = own.filter(status=LeaveRequest.Status.PENDING)
    upcoming = own.filter(
        status=LeaveRequest.Status.APPROVED, start_date__gt=today
    ).order_by("start_date", "id")
    decisions = own.filter(reviewed_at__isnull=False).order_by(
        "-reviewed_at", "-id"
    )
    balances = (
        LeaveBalance.objects.filter(employee=employee, year=today.year)
        .select_related("leave_type")
        .order_by("leave_type__name")
    )

    return {
        "role": User.Role.EMPLOYEE,
        "metrics": {
            "pending_leave_requests": pending.count(),
            "upcoming_leave_count": upcoming.count(),
        },
        "balances": LeaveBalanceSerializer(balances, many=True).data,
        "pending_requests": _serialize_requests(
            pending.order_by("-created_at", "-id")[:LIST_LIMIT]
        ),
        "upcoming_leave": _serialize_requests(upcoming[:LIST_LIMIT]),
        "recent_decisions": _serialize_requests(decisions[:LIST_LIMIT]),
    }
