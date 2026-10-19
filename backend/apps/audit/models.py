"""Who changed what, for the things that matter.

Every row is written by a signal; nothing in a view or service writes audit
rows by hand, so one save produces exactly one row. Employee and team changes
are tracked today; leave types and requests join them in Phase 3.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """One immutable record of one create, update or delete."""

    class Action(models.TextChoices):
        CREATE = "create", _("Create")
        UPDATE = "update", _("Update")
        DELETE = "delete", _("Delete")

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("actor"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        help_text=_("The signed-in user who made the change, when there was one."),
    )
    action = models.CharField(_("action"), max_length=10, choices=Action.choices)
    model = models.CharField(
        _("model"),
        max_length=64,
        help_text=_("App and model, for example 'employees.employee'."),
    )
    object_id = models.CharField(_("object id"), max_length=64)
    changes = models.JSONField(_("changes"), default=dict, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("audit log")
        verbose_name_plural = _("audit log")
        indexes = [
            models.Index(fields=["model", "object_id"]),
            models.Index(fields=["-created_at"], name="audit_created_at_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.model} #{self.object_id}"
