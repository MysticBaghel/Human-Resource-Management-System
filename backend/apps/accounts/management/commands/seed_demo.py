"""Create a larger, believable demo company on top of the existing database.

Development only. It never deletes anything and is safe to re-run: teams,
users, employee records and requests are matched by their stable keys, and
balances are created by the idempotent allocate command. Audit writes are
suppressed while it runs, so generating demo data does not masquerade as real
user activity.
"""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.context import suppress_audit
from apps.employees.models import Employee
from apps.organization.models import Team
from apps.timeoff import services
from apps.timeoff.demo import ensure_holidays, ensure_leave_types
from apps.timeoff.models import LeaveRequest, LeaveType

User = get_user_model()

DEMO_PASSWORD = "DemoPass123!"

TEAM_NAMES = ("Product", "Sales", "Support")

# first name, last name, team, job title. The first person of each team is its lead.
PEOPLE = [
    ("Aarav", "Sharma", "Product", "Product Lead"),
    ("Diya", "Patel", "Product", "Product Designer"),
    ("Kabir", "Rao", "Product", "Product Analyst"),
    ("Ananya", "Nair", "Product", "UX Researcher"),
    ("Rohan", "Mehta", "Product", "Product Manager"),
    ("Isha", "Kulkarni", "Product", "Data Analyst"),
    ("Vivaan", "Joshi", "Product", "Associate Product Manager"),
    ("Meera", "Iyer", "Product", "Product Operations"),
    ("Arjun", "Verma", "Sales", "Sales Lead"),
    ("Saanvi", "Gupta", "Sales", "Account Executive"),
    ("Aditya", "Menon", "Sales", "Sales Development Representative"),
    ("Kavya", "Reddy", "Sales", "Account Manager"),
    ("Neil", "D'Souza", "Sales", "Solutions Consultant"),
    ("Tara", "Bose", "Sales", "Sales Operations"),
    ("Dev", "Malhotra", "Support", "Support Lead"),
    ("Naina", "Chawla", "Support", "Support Specialist"),
    ("Yash", "Thakur", "Support", "Technical Support Engineer"),
    ("Riya", "Kapoor", "Support", "Customer Success Manager"),
    ("Om", "Prakash", "Support", "Support Analyst"),
    ("Zoya", "Khan", "Support", "Escalation Specialist"),
]

LEAD_INDEXES = {1, 9, 15}  # 1-based positions of the team leads in PEOPLE


class Command(BaseCommand):
    help = (
        "Create development demo data: 3 teams, 20 employees, balances and a "
        "mix of pending, approved and rejected leave. Idempotent."
    )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        year = timezone.localdate().year
        with suppress_audit():
            teams = self._seed_teams()
            records = self._seed_people(teams)
            self._assign_leads(teams, records)
            ensure_leave_types()
            ensure_holidays(year)
            ensure_holidays(year + 1)
            # The current year is the one the product talks about; next year is
            # allocated too so demo requests near December do not hit a missing
            # balance when they land in January.
            call_command("allocate_balances", year=year, stdout=StringIO())
            call_command("allocate_balances", year=year + 1, stdout=StringIO())
            self._seed_requests(records)

        demo_users = User.objects.filter(email__startswith="demo").count()
        demo_employees = Employee.objects.filter(
            user__email__startswith="demo"
        ).count()
        demo_requests = LeaveRequest.objects.filter(
            employee__user__email__startswith="demo"
        )
        counts = {
            status: demo_requests.filter(status=status).count()
            for status in LeaveRequest.Status.values
        }

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo company ready: {len(teams)} teams, {demo_users} demo users, "
                f"{demo_employees} demo employees, {demo_requests.count()} requests "
                f"({counts['pending']} pending, {counts['approved']} approved, "
                f"{counts['rejected']} rejected)."
            )
        )
        self.stdout.write(
            "Demo logins: demo01@hrms.test ... demo20@hrms.test "
            f"(team leads: demo01, demo09, demo15) - password {DEMO_PASSWORD}"
        )
        self.stdout.write(
            "Audit writes were suppressed while seeding; real activity is still "
            "recorded normally."
        )

    def _seed_teams(self) -> dict[str, Team]:
        return {
            name: Team.objects.get_or_create(name=name)[0] for name in TEAM_NAMES
        }

    def _seed_people(self, teams: dict[str, Team]) -> list[dict]:
        records: list[dict] = []
        for index, (first, last, team_name, job_title) in enumerate(
            PEOPLE, start=1
        ):
            email = f"demo{index:02d}@hrms.test"
            is_lead = index in LEAD_INDEXES
            role = User.Role.MANAGER if is_lead else User.Role.EMPLOYEE

            user, _ = User.objects.get_or_create(
                email=email,
                defaults={"role": role, "is_active": True},
            )
            changed = []
            if user.role != role:
                user.role = role
                changed.append("role")
            if not user.is_active:
                user.is_active = True
                changed.append("is_active")
            # Resetting the password keeps the documented demo logins working
            # after a re-run; it is the only field this command changes on User.
            user.set_password(DEMO_PASSWORD)
            changed.append("password")
            user.save(update_fields=list(dict.fromkeys(changed)))

            team = teams[team_name]
            employee, _ = Employee.objects.update_or_create(
                user=user,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "job_title": job_title,
                    "team": team,
                    "start_date": date(2023, 1, 9) + timedelta(days=index * 37),
                    "employment_type": Employee.EmploymentType.FULL_TIME,
                    "status": Employee.Status.ACTIVE,
                },
            )
            records.append(
                {"employee": employee, "team": team, "is_lead": is_lead}
            )
        return records

    def _assign_leads(self, teams: dict[str, Team], records: list[dict]) -> None:
        for name, team in teams.items():
            lead_record = next(
                record
                for record in records
                if record["team"].pk == team.pk and record["is_lead"]
            )
            lead = lead_record["employee"]
            if team.lead_id != lead.pk:
                team.lead = lead
                team.save(update_fields=["lead"])

            for record in records:
                if record["team"].pk != team.pk or record["is_lead"]:
                    continue
                employee = record["employee"]
                if employee.manager_id != lead.pk:
                    employee.manager = lead
                    employee.save(update_fields=["manager"])

    def _seed_requests(self, records: list[dict]) -> None:
        if LeaveRequest.objects.filter(
            employee__user__email__startswith="demo"
        ).exists():
            return

        annual = LeaveType.objects.get(name="Annual")
        base = self._next_monday()
        plans = {"pending": 1, "approved": 2, "rejected": 3}

        for team_name in TEAM_NAMES:
            members = [
                record
                for record in records
                if record["team"].name == team_name and not record["is_lead"]
            ]
            lead = next(
                record
                for record in records
                if record["team"].name == team_name and record["is_lead"]
            )["employee"]

            for status, weeks in plans.items():
                self._make_request(
                    employee=members[weeks - 1]["employee"],
                    leave_type=annual,
                    base=base,
                    weeks=weeks,
                    status=status,
                    reviewer=lead.user,
                )

        self._seed_today_leave(records, annual)

    def _make_request(
        self,
        *,
        employee,
        leave_type,
        base: date,
        weeks: int,
        status: str,
        reviewer,
    ):
        for attempt in range(4):
            start = base + timedelta(weeks=weeks + attempt * 4)
            end = start + timedelta(days=1)
            try:
                request = services.request_leave(
                    employee=employee,
                    leave_type=leave_type,
                    start_date=start,
                    end_date=end,
                )
            except ValidationError:
                continue

            if status == "approved":
                services.approve_leave(
                    request_id=request.pk,
                    reviewer=reviewer,
                    comment="Approved for the demo company.",
                )
            elif status == "rejected":
                services.reject_leave(
                    request_id=request.pk,
                    reviewer=reviewer,
                    comment="The team is short-staffed that week.",
                )
            return request
        return None

    def _seed_today_leave(self, records: list[dict], leave_type) -> None:
        """One approved request covering today, so the dashboard has a count."""
        today = timezone.localdate()
        if today.weekday() >= 5:
            return

        product = next(
            record
            for record in records
            if record["team"].name == "Product" and record["is_lead"]
        )
        members = [
            record
            for record in records
            if record["team"].name == "Product" and not record["is_lead"]
        ]
        if len(members) < 5:
            return

        try:
            request = services.request_leave(
                employee=members[4]["employee"],
                leave_type=leave_type,
                start_date=today,
                end_date=today,
            )
            services.approve_leave(
                request_id=request.pk,
                reviewer=product["employee"].user,
                comment="On leave today (demo data).",
            )
        except ValidationError:
            # A holiday or a weekend can make today unsuitable; the seed still
            # succeeds without this extra request.
            return

    @staticmethod
    def _next_monday() -> date:
        today = timezone.localdate()
        return today + timedelta(days=(7 - today.weekday()) % 7 or 7)
