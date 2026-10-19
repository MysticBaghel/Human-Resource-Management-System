"""Human-readable labels and one-line summaries for audit rows."""

MODEL_LABELS = {
    "employees.employee": "Employee",
    "employees.employeeinvite": "Employee invite",
    "organization.team": "Team",
    "timeoff.leavetype": "Leave type",
    "timeoff.leaverequest": "Leave request",
}

ACTION_LABELS = {
    "create": "Create",
    "update": "Update",
    "delete": "Delete",
}

LEAVE_STATUS_VERBS = {
    "approved": "Approved",
    "rejected": "Rejected",
    "cancelled": "Cancelled",
}


def model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def action_label(action: str) -> str:
    return ACTION_LABELS.get(action, action.title())


def _display_name(values) -> str:
    if not isinstance(values, dict):
        return ""
    if values.get("first_name") or values.get("last_name"):
        return f"{values.get('first_name', '')} {values.get('last_name', '')}".strip()
    name = values.get("name")
    return str(name) if name else ""


def _status_change(changes: dict) -> dict | None:
    change = (changes.get("changes") or {}).get("status")
    return change if isinstance(change, dict) else None


def summarize(log) -> str:
    """One line a person can read in a table, e.g. "Approved leave request #3"."""
    changes = log.changes or {}

    if log.model == "timeoff.leaverequest":
        status = _status_change(changes)
        if status is not None:
            verb = LEAVE_STATUS_VERBS.get(str(status.get("after")))
            if verb:
                return f"{verb} leave request #{log.object_id}"

    if log.model == "employees.employee":
        status = _status_change(changes)
        if status is not None:
            if status.get("after") == "inactive":
                return f"Deactivated employee #{log.object_id}"
            if status.get("after") == "active":
                return f"Reactivated employee #{log.object_id}"

    if log.model == "employees.employeeinvite" and "accepted_at" in changes:
        return f"Accepted employee invite #{log.object_id}"

    label = model_label(log.model).lower()
    if log.action == "create":
        name = _display_name(changes.get("after") or {})
        return f"Created {label} #{log.object_id}" + (f" ({name})" if name else "")
    if log.action == "delete":
        name = _display_name(changes.get("before") or {})
        return f"Deleted {label} #{log.object_id}" + (f" ({name})" if name else "")
    return f"Updated {label} #{log.object_id}"
