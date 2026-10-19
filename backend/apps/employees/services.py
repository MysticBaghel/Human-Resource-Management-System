"""Employee lifecycle rules.

Views stay thin: serializers own shape and field validation, this module owns
the rules that must hold for every caller (creating a login, inviting, role
changes, deactivation). Audit rows are not written here: the audit signals do
that, so one save is one row.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import Employee, EmployeeInvite

INVITE_TTL = timedelta(days=EmployeeInvite.INVITE_TTL_DAYS)


def assert_can_assign_role(actor, current_role: str | None, new_role: str) -> None:
    """Only an admin may grant or take away the admin role.

    HR needs to create managers and HR users, so it may assign every other
    role, but promoting someone to admin is an admin decision.
    """
    if new_role != User.Role.ADMIN and current_role != User.Role.ADMIN:
        return
    if getattr(actor, "role", None) != User.Role.ADMIN:
        raise PermissionDenied("Only an admin can grant or remove the admin role.")


@transaction.atomic
def create_employee(*, actor, data: dict) -> Employee:
    """Create the login, the person record and the one-time invite."""
    payload = dict(data)
    email = payload.pop("email").strip().lower()
    role = payload.pop("role", User.Role.EMPLOYEE)
    assert_can_assign_role(actor, None, role)

    user = User.objects.create_user(
        email=email,
        password=None,  # unusable until the invite is accepted
        role=role,
        is_active=False,
    )
    employee = Employee.objects.create(user=user, **payload)

    invite = EmployeeInvite.objects.create(
        user=user,
        expires_at=timezone.now() + INVITE_TTL,
    )
    send_invite_email(invite)
    return employee


@transaction.atomic
def update_employee(*, employee: Employee, actor, data: dict) -> Employee:
    """Update the person record and the login fields that belong to it."""
    payload = dict(data)
    user = employee.user
    user_changes: dict[str, dict] = {}

    email = payload.pop("email", None)
    if email is not None:
        normalized = email.strip().lower()
        if normalized != user.email:
            user_changes["email"] = {"before": user.email, "after": normalized}
            user.email = normalized

    role = payload.pop("role", None)
    if role is not None and role != user.role:
        assert_can_assign_role(actor, user.role, role)
        user_changes["role"] = {"before": user.role, "after": role}
        user.role = role

    if user_changes:
        user.save(update_fields=list(user_changes))

    for field, value in payload.items():
        setattr(employee, field, value)

    # The signal cannot see the user row, so hand it the email/role diff and it
    # folds it into the same single audit row.
    employee._audit_extra_changes = user_changes
    employee.save()
    return employee


@transaction.atomic
def deactivate_employee(employee: Employee, *, actor) -> Employee:
    """Deactivate instead of deleting: the person stays, the login stops."""
    if employee.user.role == User.Role.ADMIN and getattr(actor, "role", None) != User.Role.ADMIN:
        raise PermissionDenied("Only an admin can deactivate an admin.")

    if employee.status != Employee.Status.INACTIVE:
        employee.status = Employee.Status.INACTIVE
        employee.save(update_fields=["status"])

    user = employee.user
    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
    return employee


@transaction.atomic
def reactivate_employee(employee: Employee, *, actor) -> Employee:
    """Undo a deactivation. Deactivation must not be a dead end."""
    if employee.user.role == User.Role.ADMIN and getattr(actor, "role", None) != User.Role.ADMIN:
        raise PermissionDenied("Only an admin can reactivate an admin.")

    if employee.status != Employee.Status.ACTIVE:
        employee.status = Employee.Status.ACTIVE
        employee.save(update_fields=["status"])

    user = employee.user
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    return employee


@transaction.atomic
def accept_invite(*, invite: EmployeeInvite, password: str) -> User:
    """Set the first password and switch the account on.

    Validation (token, expiry, password rules) happens in the serializer, so this
    only applies an invite that is known to be good.
    """
    user = invite.user
    user.set_password(password)
    user.is_active = True
    user.save(update_fields=["password", "is_active"])

    invite.accepted_at = timezone.now()
    invite.save(update_fields=["accepted_at"])
    return user


def send_invite_email(invite: EmployeeInvite) -> None:
    """Email the accept link. The console backend prints it in development."""
    url = f"{settings.FRONTEND_URL}/accept-invite?token={invite.token}"
    employee = getattr(invite.user, "employee", None)
    greeting = employee.first_name if employee is not None else invite.user.email

    send_mail(
        subject="You are invited to HRMS",
        message=(
            f"Hello {greeting},\n\n"
            f"An HRMS account has been created for you. Use this link to choose "
            f"your password:\n{url}\n\n"
            f"The link expires in {EmployeeInvite.INVITE_TTL_DAYS} days and can "
            f"only be used once.\n"
            f"If you were not expecting this, you can ignore this email.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.user.email],
        fail_silently=False,
    )
