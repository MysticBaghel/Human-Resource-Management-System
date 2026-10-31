"""Human-readable labels and one-line summaries for audit rows."""

MODEL_LABELS = {
    "employees.employee": "Employee",
    "employees.employeeinvite": "Employee invite",
    "organization.team": "Team",
    "timeoff.leavetype": "Leave type",
    "timeoff.leaverequest": "Leave request",
    "payroll.salarystructure": "Salary structure",
    "payroll.salaryrevision": "Salary revision",
    "payroll.payrollrecord": "Payroll record",
    "invoices.client": "Client",
    "invoices.invoice": "Invoice",
    "invoices.invoicepayment": "Invoice payment",
    "invoices.invoicereminder": "Invoice reminder",
    "invoices.invoiceattachment": "Invoice attachment",
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

    if log.model == "payroll.payrollrecord":
        status = _status_change(changes)
        if status is not None and status.get("after") == "finalized":
            return f"Finalized payroll record #{log.object_id}"
        payment = (changes.get("changes") or {}).get("payment_status")
        if isinstance(payment, dict):
            if payment.get("after") == "paid":
                return f"Marked payroll #{log.object_id} paid"
            if payment.get("after") == "failed":
                return f"Marked payroll #{log.object_id} failed"
        if log.action == "create":
            return f"Generated payroll record #{log.object_id}"

    if log.model == "payroll.salaryrevision":
        after = changes.get("after") or {}
        employee_id = after.get("employee") or after.get("employee_id") or log.object_id
        return f"Revised salary structure for employee #{employee_id}"

    if log.model == "invoices.invoice":
        return _summarize_invoice(log, changes)

    if log.model == "invoices.invoicepayment":
        after = changes.get("after") or {}
        amount = after.get("amount")
        invoice_id = after.get("invoice") or log.object_id
        prefix = f"Recorded payment of {amount}" if amount else "Recorded a payment"
        return f"{prefix} on invoice #{invoice_id}"

    if log.model == "invoices.invoicereminder":
        after = changes.get("after") or {}
        invoice_id = after.get("invoice", log.object_id)
        return f"Sent payment reminder for invoice #{invoice_id}"

    if log.model == "invoices.invoiceattachment":
        if log.action == "delete":
            before = changes.get("before") or {}
            name = before.get("original_name") or f"#{log.object_id}"
        else:
            after = changes.get("after") or {}
            name = after.get("original_name") or f"#{log.object_id}"
        if log.action == "delete":
            return f"Removed invoice attachment {name}"
        return f"Uploaded invoice attachment {name}"

    label = model_label(log.model).lower()
    if log.action == "create":
        name = _display_name(changes.get("after") or {})
        return f"Created {label} #{log.object_id}" + (f" ({name})" if name else "")
    if log.action == "delete":
        name = _display_name(changes.get("before") or {})
        return f"Deleted {label} #{log.object_id}" + (f" ({name})" if name else "")
    return f"Updated {label} #{log.object_id}"


def _summarize_invoice(log, changes: dict) -> str:
    """Summary lines for generated, sent, paid and reminded invoices."""
    if log.action == "create":
        after = changes.get("after") or {}
        number = after.get("invoice_number") or f"#{log.object_id}"
        client = after.get("client_name")
        return f"Generated invoice {number}" + (f" for {client}" if client else "")

    after = changes.get("after") or {}
    number = after.get("invoice_number") or f"#{log.object_id}"
    status = _status_change(changes)
    if status is not None:
        next_status = status.get("after")
        if next_status == "sent":
            return f"Sent invoice {number}"
        if next_status == "partially_paid":
            return f"Recorded a payment on invoice {number}"
        if next_status == "paid":
            return f"Marked invoice {number} paid"
        if next_status == "cancelled":
            return f"Cancelled invoice {number}"

    if "reminder_count" in (changes.get("changes") or {}):
        return f"Sent payment reminder for invoice {number}"
    if "balance_due" in (changes.get("changes") or {}):
        return f"Recorded a payment on invoice {number}"
    return f"Updated invoice {number}"
