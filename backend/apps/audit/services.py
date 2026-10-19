"""Explicit audit entries for events that are not a tracked model save.

Model saves are audited by signals. A few meaningful events are not a save of a
tracked model (accepting an invite changes only the User row), so they call this
helper instead. It uses the same AuditLog table and respects audit suppression.
"""

from .context import audit_suppressed
from .models import AuditLog


def record_event(*, actor, action: str, model: str, object_id, changes: dict):
    if audit_suppressed():
        return None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        model=model,
        object_id=str(object_id),
        changes=changes,
    )
