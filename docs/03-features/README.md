# 03 · Features: people and time off

[← Previous: Getting started](../02-getting-started/README.md) · [Documentation index](../README.md) · **Next: [04 · API →](../04-api/README.md)**

## Employees

An `Employee` is linked one-to-one to a login and carries the person's name,
phone, job title, team, manager, start date, employment type and status.

- Employees are **never hard-deleted**. HR/admin deactivate them, which keeps
  history and switches off the login.
- HR/admin can create, update, deactivate and reactivate anyone.
- An employee may edit only their own phone number.
- Managers can read their team (and their own record); employees can read only
  themselves.
- Creating an employee creates the login inactive and sends a one-time invite.

## Teams

`Team` belongs to `organization` and has a name plus an optional lead, where the
lead is an `Employee` rather than a user. That keeps manager scoping tied to the
org chart.

- HR/admin manage teams.
- Managers can read only teams they lead.
- Deleting a team does not delete its people; their `team` becomes null.

## Invites

Creating an employee does **not** set a password. The API creates the login
(inactive), the person record and a one-time invite token, then emails a link to
`<FRONTEND_URL>/accept-invite?token=...`.

In development, Django's console email backend prints the link in the
`runserver` terminal; open it, choose a password and you are signed in as that
person.

- Links expire after 7 days.
- Links work once.
- Links are refused if the employee has been deactivated.
- Accepting an invite activates the user and records an audit event.

## Time off

### Working days and requests

- **Working days** are Monday to Friday minus holidays.
- A half day costs 0.5 and must be a single date.
- A request cannot span two calendar years.
- Requests store start/end dates, the leave type, a reason, status and reviewer.
- Everyone can request leave for themselves. HR/admin manage other people's
  leave from the **Leaves** directory and use its **My time off** button to open
  their own personal page.
- The balances API is personal by default: HR/admin must pass `mine=false` to
  read the company-wide list, so the personal page can never render everyone's
  cards by mistake.

### Overlaps

Overlaps are refused by the service **and** by a PostgreSQL exclusion constraint
(`btree_gist`, inclusive `daterange`), so two concurrent requests cannot slip
through. Cancelled requests do not block their dates.

### Balances and approvals

- Approving deducts the days from the balance.
- Rejecting changes nothing.
- Cancelling an approved request gives the days back.
- Balance and request rows are locked in one transaction, so double approval
  cannot deduct twice.
- A manager can approve their own team/direct reports; HR and admin can approve
  anyone; HR and admin can see every request.
- The reviewer and decision timestamp are recorded.
- Every state change writes an audit row.

Balances are read-only through the API. `python manage.py allocate_balances
--year 2026` creates them, including capped carry-over. Leave types are editable
by HR through `/api/v1/leave-types/`; holidays are managed in Django admin or by
the seed.

## Dashboard

The dashboard is computed from the database per role:

- **admin** — company headcount, teams, pending leave and people on leave today
- **HR** — the same counts plus requests without a manager and recent employee
  changes
- **manager** — team size, pending approvals, requests waiting too long,
  upcoming leave
- **employee** — own balances, pending requests and recent decisions

The employee payload contains no company-wide fields. The per-role assembly lives
in `apps/dashboard/services.py`.

## Audit log

`AuditLog` stores one immutable row per tracked create, update or delete, with
actor, action, model, object id and field-level changes.

- Audited models include employees, teams, leave types, leave requests, salary
  structures/revisions, payroll records, clients, invoices, invoice payments,
  invoice reminders and invoice attachments.
- A save that changes nothing writes nothing.
- Related changes can be folded into one row (for example a leave approval's
  balance movement or an invoice's line items).
- HR/admin can browse and filter the feed, and open a detail dialog with
  before/after values.
- Managers and employees receive 403 for the audit endpoints.

The API/UI endpoints are listed in [04 · API](../04-api/README.md); the audit
implementation is in `apps/audit/signals.py` and `apps/audit/summary.py`.

---

[← Previous: Getting started](../02-getting-started/README.md) · [Documentation index](../README.md) · **Next: [04 · API →](../04-api/README.md)**
