"""Create the demo company: logins, teams, people and a year of time off."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.employees.models import Employee
from apps.organization.models import Team
from apps.timeoff import services as timeoff_services
from apps.timeoff.demo import ensure_holidays, ensure_leave_types
from apps.timeoff.models import LeaveRequest, LeaveType

User = get_user_model()

DEMO_PASSWORD = "DemoPass123!"

# email, role, first name, last name, team, job title, manager email
DEMO_USERS = [
    ("admin@hrms.test", "admin", "Aarti", "Admin", "People Ops", "Operations Lead", None),
    ("hr@hrms.test", "hr", "Harsh", "HR", "People Ops", "People Partner", None),
    (
        "manager@hrms.test",
        "manager",
        "Meera",
        "Manager",
        "Engineering",
        "Engineering Manager",
        None,
    ),
    (
        "employee@hrms.test",
        "employee",
        "Esha",
        "Employee",
        "Engineering",
        "Software Engineer",
        "manager@hrms.test",
    ),
    (
        "employee2@hrms.test",
        "employee",
        "Evan",
        "Employee",
        "Engineering",
        "QA Engineer",
        "manager@hrms.test",
    ),
]

# Team name -> lead email. The lead is set after the employees exist.
DEMO_TEAMS = {
    "Engineering": "manager@hrms.test",
    "People Ops": "hr@hrms.test",
}

# Everyone started on a different, believable date.
START_DATES = {
    "admin@hrms.test": date(2021, 3, 1),
    "hr@hrms.test": date(2022, 6, 13),
    "manager@hrms.test": date(2022, 1, 10),
    "employee@hrms.test": date(2023, 9, 4),
    "employee2@hrms.test": date(2024, 2, 19),
}


class Command(BaseCommand):
    help = "Create the demo users, teams and employees (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help="Password given to every demo user.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        password = options["password"]
        users = self._seed_users(password)
        teams = self._seed_teams()
        employees = self._seed_employees(users, teams)
        self._assign_leads(teams, employees)
        self._seed_timeoff(employees)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {User.objects.count()} users, "
                f"{Employee.objects.count()} employees, {Team.objects.count()} teams, "
                f"{LeaveType.objects.count()} leave types."
            )
        )
        self.stdout.write("Sign in at http://localhost:5173/login with:")
        for email, role, first_name, last_name, *extra in DEMO_USERS:
            self.stdout.write(f"  {role:<9} {email}  ({first_name} {last_name})")
        self.stdout.write(f"  password: {password}")
        self.stdout.write(
            "Only the admin@ user has Django admin access, at /admin/."
        )

    def _seed_users(self, password: str) -> dict[str, User]:
        users: dict[str, User] = {}
        for email, role, *_ in DEMO_USERS:
            user, _created = User.objects.get_or_create(
                email=email,
                defaults={"role": role, "is_active": True},
            )
            # Keep role in sync when re-running, and reset the password so a
            # reseeded database always has working demo logins.
            changed_fields = []
            if user.role != role:
                user.role = role
                changed_fields.append("role")
            if not user.is_active:
                user.is_active = True
                changed_fields.append("is_active")
            # The admin demo user must also be staff and superuser, otherwise
            # the Django admin at /admin/ either rejects the login or shows an
            # empty index because no model permissions are granted.
            wants_admin = role == User.Role.ADMIN
            if user.is_staff != wants_admin:
                user.is_staff = wants_admin
                changed_fields.append("is_staff")
            if user.is_superuser != wants_admin:
                user.is_superuser = wants_admin
                changed_fields.append("is_superuser")
            user.set_password(password)
            changed_fields.append("password")
            user.save(update_fields=changed_fields)
            users[email] = user
        return users

    def _seed_teams(self) -> dict[str, Team]:
        # Teams are created before the people so employees can point at them.
        return {
            name: Team.objects.get_or_create(name=name)[0] for name in DEMO_TEAMS
        }

    def _seed_employees(
        self, users: dict[str, User], teams: dict[str, Team]
    ) -> dict[str, Employee]:
        employees: dict[str, Employee] = {}
        for email, _role, first_name, last_name, team, job_title, _manager in DEMO_USERS:
            employee, _created = Employee.objects.get_or_create(
                user=users[email],
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "job_title": job_title,
                    "team": teams[team],
                    "start_date": START_DATES[email],
                    "employment_type": Employee.EmploymentType.FULL_TIME,
                    "status": Employee.Status.ACTIVE,
                },
            )
            employees[email] = employee

        # Managers are linked in a second pass now that every record exists.
        for email, _role, _first, _last, _team, _title, manager_email in DEMO_USERS:
            if not manager_email:
                continue
            employee = employees[email]
            manager = employees[manager_email]
            if employee.manager_id != manager.pk:
                employee.manager = manager
                employee.save(update_fields=["manager"])
        return employees

    def _assign_leads(self, teams: dict[str, Team], employees: dict[str, Employee]) -> None:
        # The lead is set once the people exist; a reseed points it back at the
        # demo leads if someone changed it.
        for name, lead_email in DEMO_TEAMS.items():
            team = teams[name]
            if team.lead_id != employees[lead_email].pk:
                team.lead = employees[lead_email]
                team.save(update_fields=["lead"])

    def _seed_timeoff(self, employees: dict[str, Employee]) -> None:
        """Leave types, current-year holidays, balances and one pending request."""
        year = timezone.localdate().year
        leave_types = ensure_leave_types()
        ensure_holidays(year)

        call_command("allocate_balances", year=year)

        self._seed_demo_request(
            employees["employee@hrms.test"], leave_types["Annual"], year
        )

    def _seed_demo_request(self, employee, leave_type, year: int) -> None:
        """One pending request so the approvals page has something in it."""
        if LeaveRequest.objects.filter(employee=employee).exists():
            return

        today = timezone.localdate()
        days_ahead = (7 - today.weekday()) % 7 or 7
        start = today + timedelta(days=days_ahead)
        end = start + timedelta(days=1)
        if end.year != year:
            return

        try:
            timeoff_services.request_leave(
                employee=employee,
                leave_type=leave_type,
                start_date=start,
                end_date=end,
            )
        except ValidationError:
            # A holiday or a year boundary can make the demo date unsuitable.
            # The seed still succeeds; the person can request leave in the UI.
            return
