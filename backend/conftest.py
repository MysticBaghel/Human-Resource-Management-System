"""Shared pytest fixtures."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


def _prime_csrf(client):
    """Fetch the CSRF cookie the way the React client does on startup.

    Public POST endpoints use csrf_protect, so without this a client would get
    a 403 from every login attempt.
    """
    client.get("/api/v1/auth/csrf/")
    return client


@pytest.fixture
def api_client(db):
    """Client that mirrors the browser: CSRF cookie primed, token sent.

    Depends on `db` because priming the CSRF cookie happens during fixture
    setup, which pytest-django otherwise blocks from touching the database.
    """
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=True)
    return _prime_csrf(client)


def _csrf_headers(client) -> dict:
    cookie = client.cookies.get("csrftoken")
    return {"HTTP_X_CSRFTOKEN": cookie.value} if cookie else {}


@pytest.fixture
def csrf_client():
    """Client with CSRF checks enforced but no cookie fetched yet.

    Used to prove the protection is actually on.
    """
    from rest_framework.test import APIClient

    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def make_user(db):
    """Create a user with any role. Password defaults to a known value."""

    def _make_user(
        email: str,
        role: str = User.Role.EMPLOYEE,
        password: str = "test-pass-12345",
        **extra,
    ):
        return User.objects.create_user(
            email=email, password=password, role=role, **extra
        )

    return _make_user


@pytest.fixture
def admin_user(make_user):
    return make_user("admin@example.com", role=User.Role.ADMIN)


@pytest.fixture
def hr_user(make_user):
    return make_user("hr@example.com", role=User.Role.HR)


@pytest.fixture
def manager_user(make_user):
    return make_user("manager@example.com", role=User.Role.MANAGER)


@pytest.fixture
def employee_user(make_user):
    return make_user("employee@example.com", role=User.Role.EMPLOYEE)


@pytest.fixture
def auth_client(api_client):
    """Log the CSRF-aware client in via the real login endpoint."""

    def _login(user, password: str = "test-pass-12345"):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": password},
            format="json",
            **_csrf_headers(api_client),
        )
        assert response.status_code == 200, response.data
        return api_client

    return _login


@pytest.fixture
def api_write(api_client):
    """Send a write on the signed-in client, with its current CSRF token.

    ``auth_client`` logs in first, which rotates the token, so this reads the
    cookie at call time rather than once at setup.
    """

    def _write(method: str, path: str, data: dict | None = None):
        return getattr(api_client, method)(
            path,
            data if data is not None else {},
            format="json",
            **_csrf_headers(api_client),
        )

    return _write


@pytest.fixture
def make_team(db):
    """Create a team, optionally with a lead."""
    from apps.organization.models import Team

    def _make_team(name: str = "Engineering", lead=None):
        return Team.objects.create(name=name, lead=lead)

    return _make_team


@pytest.fixture
def make_employee(db, make_user):
    """Create an employee record, creating a user when one is not supplied."""
    from datetime import date

    from apps.employees.models import Employee

    def _make_employee(
        user=None,
        *,
        email: str | None = None,
        team=None,
        manager=None,
        first_name: str = "Test",
        last_name: str = "Person",
        **extra,
    ):
        if user is None:
            user = make_user(
                email or f"{first_name.lower()}.{last_name.lower()}@example.com"
            )
        extra.setdefault("start_date", date(2023, 1, 2))
        return Employee.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            team=team,
            manager=manager,
            **extra,
        )

    return _make_employee


@pytest.fixture
def demo_org(db, make_user, make_employee, make_team):
    """Two teams and three people: Engineering is led by the manager.

    Sales has no lead, so a manager must not be able to see it.
    """
    from types import SimpleNamespace

    admin = make_user("admin@example.com", role="admin")
    hr = make_user("hr@example.com", role="hr")
    manager_user = make_user("manager@example.com", role="manager")
    employee_user = make_user("employee@example.com", role="employee")
    sales_user = make_user("sales@example.com", role="employee")

    engineering = make_team("Engineering")
    sales = make_team("Sales")

    meera = make_employee(
        user=manager_user,
        first_name="Meera",
        last_name="Manager",
        team=engineering,
        job_title="Engineering Manager",
    )
    engineering.lead = meera
    engineering.save(update_fields=["lead"])

    esha = make_employee(
        user=employee_user,
        first_name="Esha",
        last_name="Employee",
        team=engineering,
        manager=meera,
        job_title="Software Engineer",
        phone="+1 555 0100",
    )
    sam = make_employee(
        user=sales_user,
        first_name="Sam",
        last_name="Sales",
        team=sales,
        job_title="Account Executive",
    )

    return SimpleNamespace(
        admin=admin,
        hr=hr,
        manager_user=manager_user,
        employee_user=employee_user,
        sales_user=sales_user,
        engineering=engineering,
        sales=sales,
        meera=meera,
        esha=esha,
        sam=sam,
    )


@pytest.fixture
def leave_types(db):
    """Annual, sick and unpaid leave types for the time-off tests."""
    from decimal import Decimal

    from apps.timeoff.models import LeaveType

    return SimpleNamespace(
        annual=LeaveType.objects.create(
            name="Annual",
            annual_days=Decimal("20"),
            carry_over_max=Decimal("5"),
        ),
        sick=LeaveType.objects.create(
            name="Sick",
            annual_days=Decimal("10"),
            carry_over_max=Decimal("0"),
        ),
        unpaid=LeaveType.objects.create(
            name="Unpaid",
            annual_days=Decimal("0"),
            is_paid=False,
        ),
    )


@pytest.fixture
def holidays(db):
    """One company holiday, on Wednesday 6 May 2026."""
    from datetime import date

    from apps.timeoff.models import Holiday

    return [Holiday.objects.create(date=date(2026, 5, 6), name="Founders Day")]


@pytest.fixture
def make_balance(db):
    """Create a leave balance for one employee/type/year."""
    from decimal import Decimal

    from apps.timeoff.models import LeaveBalance

    def _make(
        employee,
        leave_type,
        *,
        year: int = 2026,
        allocated="20",
        used="0",
    ):
        return LeaveBalance.objects.create(
            employee=employee,
            leave_type=leave_type,
            year=year,
            allocated=Decimal(str(allocated)),
            used=Decimal(str(used)),
        )

    return _make


@pytest.fixture
def leave_org(db, demo_org, leave_types, holidays, make_balance):
    """The demo company with leave types, a holiday and 2026 balances."""
    from types import SimpleNamespace

    for employee in (demo_org.esha, demo_org.meera, demo_org.sam):
        for leave_type in (
            leave_types.annual,
            leave_types.sick,
            leave_types.unpaid,
        ):
            make_balance(employee, leave_type, allocated=leave_type.annual_days)
    return SimpleNamespace(org=demo_org, types=leave_types, holidays=holidays)
