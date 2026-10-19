"""Employee records: the person data behind a login.

An Employee is never deleted: the person is deactivated and their user is
switched off. New employees get a one-time invite so they choose their own
password; nobody types a password on someone else's behalf.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Employee(models.Model):
    """A person in the company, linked one-to-one to a login."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", _("Full time")
        PART_TIME = "part_time", _("Part time")
        CONTRACT = "contract", _("Contract")
        INTERN = "intern", _("Intern")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee",
        verbose_name=_("user"),
    )
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100)
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    job_title = models.CharField(_("job title"), max_length=120, blank=True)
    team = models.ForeignKey(
        "organization.Team",
        verbose_name=_("team"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    manager = models.ForeignKey(
        "self",
        verbose_name=_("manager"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_reports",
        help_text=_("Approves this person's leave. HR approves when there is none."),
    )
    start_date = models.DateField(_("start date"))
    employment_type = models.CharField(
        _("employment type"),
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text=_("Inactive employees cannot log in. Use the deactivate action."),
    )

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name = _("employee")
        verbose_name_plural = _("employees")

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class EmployeeInvite(models.Model):
    """A one-time link that lets a new employee set their first password.

    The user is created inactive and the invite is the only way in. Accepting
    the invite switches the user on.
    """

    INVITE_TTL_DAYS = 7

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_invite",
        verbose_name=_("user"),
    )
    token = models.UUIDField(_("token"), default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("expires at"))
    accepted_at = models.DateTimeField(_("accepted at"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("employee invite")
        verbose_name_plural = _("employee invites")

    def __str__(self) -> str:
        state = "accepted" if self.is_accepted else "pending"
        return f"Invite for {self.user_id} ({state})"

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
