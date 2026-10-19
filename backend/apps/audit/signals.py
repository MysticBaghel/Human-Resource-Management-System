"""Audit rows are written here, and only here.

Two receivers per tracked model: ``pre_save`` stashes the values currently in
the database, ``post_save`` compares them with the new values and writes one
row. A save that changes nothing writes nothing, so one action can never
produce duplicate rows.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.employees.models import Employee
from apps.organization.models import Team
from apps.timeoff.models import LeaveRequest, LeaveType

from .context import audit_suppressed, get_current_user
from .models import AuditLog

# Models whose create/update/delete must be audited.
TRACKED_MODELS = (Employee, Team, LeaveType, LeaveRequest)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def snapshot(instance) -> dict[str, Any]:
    """The instance's stored fields, as JSON-safe values."""
    values: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key:
            continue
        values[field.name] = _json_safe(getattr(instance, field.attname))
    return values


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Field-level before/after for the fields that actually changed."""
    return {
        name: {"before": before.get(name), "after": value}
        for name, value in after.items()
        if before.get(name) != value
    }


def _stored_values(instance) -> dict[str, Any] | None:
    if instance.pk is None:
        return None
    try:
        return snapshot(type(instance)._default_manager.get(pk=instance.pk))
    except type(instance).DoesNotExist:
        return None


@receiver(pre_save)
def _capture_stored_values(sender, instance, **kwargs) -> None:
    if sender not in TRACKED_MODELS:
        return
    instance._audit_before = _stored_values(instance)


@receiver(post_save)
def _record_save(sender, instance, created: bool, raw: bool = False, **kwargs) -> None:
    if sender not in TRACKED_MODELS or raw or audit_suppressed():
        return

    after = snapshot(instance)
    before = getattr(instance, "_audit_before", None)
    extra = getattr(instance, "_audit_extra_changes", None) or {}

    if created or before is None:
        action = AuditLog.Action.CREATE
        changes: dict[str, Any] = {"after": after}
    else:
        diff = changed_fields(before, after)
        # A service can report changes that live outside the model row (a
        # user's email or role) so they land in the same single row.
        diff.update(extra)
        if not diff:
            instance._audit_before = after
            return
        action = AuditLog.Action.UPDATE
        changes = {"changes": diff}

    AuditLog.objects.create(
        actor=get_current_user(),
        action=action,
        model=instance._meta.label_lower,
        object_id=str(instance.pk),
        changes=changes,
    )
    instance._audit_before = after
    instance._audit_extra_changes = {}


@receiver(post_delete)
def _record_delete(sender, instance, **kwargs) -> None:
    if sender not in TRACKED_MODELS or audit_suppressed():
        return

    AuditLog.objects.create(
        actor=get_current_user(),
        action=AuditLog.Action.DELETE,
        model=instance._meta.label_lower,
        object_id=str(instance.pk),
        changes={"before": snapshot(instance)},
    )
