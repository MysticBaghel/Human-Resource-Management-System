"""seed_demo tests: idempotence, audit suppression and preserved data."""

from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.employees.models import Employee
from apps.organization.models import Team
from apps.timeoff.models import LeaveBalance, LeaveRequest, LeaveType


def seed_demo():
    call_command("seed_demo", stdout=StringIO())


class TestSeedDemo:
    def test_creates_the_demo_company(self, db):
        year = timezone.localdate().year
        seed_demo()

        assert Team.objects.filter(name__in=["Product", "Sales", "Support"]).count() == 3
        assert User.objects.filter(email__startswith="demo").count() == 20
        assert Employee.objects.filter(user__email__startswith="demo").count() == 20
        assert LeaveType.objects.count() == 3
        assert (
            LeaveBalance.objects.filter(
                year=year, employee__user__email__startswith="demo"
            ).count()
            == 60
        )

        requests = LeaveRequest.objects.filter(
            employee__user__email__startswith="demo"
        )
        assert requests.exists()
        assert set(requests.values_list("status", flat=True)) >= {
            "pending",
            "approved",
            "rejected",
        }
        assert requests.filter(status="approved", reviewer__isnull=False).exists()
        assert requests.filter(status="approved", reviewed_at__isnull=False).exists()
        assert requests.filter(status="pending", reviewer__isnull=True).exists()

        managers = User.objects.filter(
            email__startswith="demo", role=User.Role.MANAGER
        )
        assert managers.count() == 3
        assert Team.objects.get(name="Product").lead.user.email == "demo01@hrms.test"

    def test_suppresses_audit_rows(self, db):
        seed_demo()

        assert AuditLog.objects.count() == 0

    def test_is_idempotent(self, db):
        year = timezone.localdate().year
        seed_demo()
        counts = {
            "users": User.objects.count(),
            "employees": Employee.objects.count(),
            "teams": Team.objects.count(),
            "balances": LeaveBalance.objects.count(),
            "requests": LeaveRequest.objects.count(),
            "audit": AuditLog.objects.count(),
        }

        seed_demo()

        assert User.objects.count() == counts["users"]
        assert Employee.objects.count() == counts["employees"]
        assert Team.objects.count() == counts["teams"]
        assert LeaveBalance.objects.count() == counts["balances"]
        assert LeaveRequest.objects.count() == counts["requests"]
        assert AuditLog.objects.count() == counts["audit"] == 0
        assert (
            LeaveBalance.objects.filter(
                year=year, employee__user__email__startswith="demo"
            ).count()
            == 60
        )

    def test_preserves_existing_data_and_its_audit_history(self, db):
        existing_team = Team.objects.create(name="Keep Me")
        existing_user = User.objects.create_user(
            email="existing@example.com", password="ExistingPass!23", role="employee"
        )
        audit_before = AuditLog.objects.count()
        assert audit_before == 1  # the team creation above

        seed_demo()

        assert Team.objects.filter(pk=existing_team.pk).exists()
        assert User.objects.filter(pk=existing_user.pk).exists()
        assert AuditLog.objects.count() == audit_before

    def test_demo_account_can_log_in(self, db, auth_client):
        seed_demo()
        user = User.objects.get(email="demo01@hrms.test")

        auth_client(user, password="DemoPass123!")

    def test_can_run_after_seed_users(self, db):
        call_command("seed_users", stdout=StringIO())
        seed_demo()

        assert User.objects.filter(email__startswith="demo").count() == 20
        assert Team.objects.filter(name__in=["Product", "Sales", "Support"]).count() == 3
        assert Employee.objects.filter(user__email="employee@hrms.test").exists()
        assert LeaveRequest.objects.filter(
            employee__user__email="employee@hrms.test"
        ).exists()
