"""Role-based queryset scoping.

One place decides what a role may see, so no viewset invents its own rule.

Each strategy takes ``(queryset, user)`` and returns the narrowed queryset.
``scope_queryset`` handles models that hang off an employee (leave requests in
Phase 3); ``scope_employees`` and ``scope_teams`` handle the Phase 2 records
themselves. Every function fails closed: an unknown role sees nothing.
"""

from collections.abc import Callable

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet

ScopeStrategy = Callable[[object, object], object]


def _empty_like(queryset):
    """An empty queryset of the same model.

    ``queryset.none()`` fails when handed an already-empty queryset (``none()``
    is only on managers), so go through the model's default manager instead.
    """
    return queryset.model._default_manager.none()


def scope_for_own(queryset, user):
    """Rows belonging to the user, matched on a `user` field.

    Requires the model to have a `user` foreign key (Employee does; User does
    not). Models that hang off a different field need their own strategy, which
    is why the role map is a single place to change.
    """
    return queryset.filter(user=user)


def scope_for_own_team(queryset, user):
    """Rows whose employee is in a team led by the user.

    This is the Phase 3 leave-request scope; Employee and Team have their own
    functions below because they do not hang off an ``employee`` field.
    """
    return queryset.filter(employee__team__lead__user=user)


def scope_for_none(queryset, user):
    return _empty_like(queryset)


def _is_hr_or_admin(user) -> bool:
    return getattr(user, "role", None) in {"hr", "admin"}


def scope_employees(queryset: QuerySet, user) -> QuerySet:
    """Narrow employee records to what `user` may see.

    - employee: their own record only.
    - manager: the members of teams they lead, plus their own record.
    - hr, admin: everyone, including inactive people.
    """
    role = getattr(user, "role", None)

    if _is_hr_or_admin(user):
        return queryset
    if role == "manager":
        return queryset.filter(Q(team__lead__user=user) | Q(user=user))
    if role == "employee":
        return queryset.filter(user=user)
    return _empty_like(queryset)


def scope_teams(queryset: QuerySet, user) -> QuerySet:
    """Narrow teams to what `user` may see.

    - manager: the teams they lead.
    - hr, admin: every team.
    - employee: none; teams are an HR surface.
    """
    if _is_hr_or_admin(user):
        return queryset
    if getattr(user, "role", None) == "manager":
        return queryset.filter(lead__user=user)
    return _empty_like(queryset)


def scope_leave_requests(queryset: QuerySet, user) -> QuerySet:
    """Narrow leave requests, independent of their status.

    - employee: their own requests.
    - manager: their own plus requests from the teams they lead.
    - hr, admin: everything.
    """
    if _is_hr_or_admin(user):
        return queryset
    if getattr(user, "role", None) == "manager":
        return queryset.filter(Q(employee__team__lead__user=user) | Q(employee__user=user))
    if getattr(user, "role", None) == "employee":
        return queryset.filter(employee__user=user)
    return _empty_like(queryset)


def scope_leave_balances(queryset: QuerySet, user) -> QuerySet:
    """Balances are personal: everyone sees their own, HR and admin see all."""
    if _is_hr_or_admin(user):
        return queryset
    if getattr(user, "role", None) in {"employee", "manager"}:
        return queryset.filter(employee__user=user)
    return _empty_like(queryset)


def scope_calendar_requests(queryset: QuerySet, user) -> QuerySet:
    """Approved leave visible on the team calendar.

    - employee: their own team's calendar, plus their own leave.
    - manager: the teams they lead, plus their own leave.
    - hr, admin: everyone.
    """
    if _is_hr_or_admin(user):
        return queryset
    if getattr(user, "role", None) == "manager":
        return queryset.filter(Q(employee__team__lead__user=user) | Q(employee__user=user))

    employee = getattr(user, "employee", None)
    if employee is None:
        return _empty_like(queryset)
    if employee.team_id:
        return queryset.filter(
            Q(employee__team_id=employee.team_id) | Q(employee__user=user)
        )
    return queryset.filter(employee__user=user)


ROLE_SCOPES: dict[str, dict[str, ScopeStrategy]] = {
    "employee": {
        "own": scope_for_own,
        "own_team": scope_for_none,
    },
    "manager": {
        "own": scope_for_own,
        "own_team": scope_for_own_team,
    },
    "hr": {
        "own": scope_for_own,
        "own_team": lambda queryset, user: queryset,
    },
    "admin": {
        "own": scope_for_own,
        "own_team": lambda queryset, user: queryset,
    },
}


def scope_queryset(queryset, user, scope: str = "own_team"):
    """Narrow `queryset` to what `user`'s role may see.

    ``scope`` names the kind of scoping, not the role:
      - ``"own_team"``: employee -> own records, manager -> own team, hr/admin -> all.
      - ``"own"``:      employee/manager -> own records, hr/admin -> all.
    """
    if scope not in {"own", "own_team"}:
        raise ImproperlyConfigured(
            f"Unknown scope {scope!r}; expected 'own' or 'own_team'."
        )

    role = getattr(user, "role", None)
    strategy = ROLE_SCOPES.get(role, {}).get(scope)
    if strategy is None:
        # Fail closed: an unrecognised role, or an anonymous user, sees nothing.
        return _empty_like(queryset)
    return strategy(queryset, user)
