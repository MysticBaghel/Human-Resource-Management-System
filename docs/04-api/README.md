# 04 · API

[← Previous: Features](../03-features/README.md) · [Documentation index](../README.md) · **Next: [05 · Payroll →](../05-payroll/README.md)**

Everything lives under `/api/v1/`. Authentication is Django session + CSRF:
the React client fetches `/auth/csrf/`, sends the `X-CSRFToken` header on unsafe
requests and includes cookies.

All errors use one shape:

```json
{
  "detail": "A readable message.",
  "code": "invalid",
  "fields": {
    "email": ["This field is required."]
  }
}
```

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health/` | public | liveness probe |
| GET | `/auth/csrf/` | public | sets the CSRF cookie |
| POST | `/auth/login/` | public | session login (email + password) |
| POST | `/auth/logout/` | session | destroys the session |
| GET | `/auth/me/` | session | current user |
| POST | `/auth/password-reset/` | public | emails a reset link |
| POST | `/auth/password-reset/confirm/` | public | sets a new password |
| POST | `/auth/accept-invite/` | public | sets the first password from an invite |
| GET | `/dashboard/` | session | role-scoped dashboard metrics and lists |
| GET | `/employees/` | session, scoped | list/search/filter employees |
| POST | `/employees/` | hr, admin | create a person + login + invite |
| GET | `/employees/{id}/` | session, scoped | one employee |
| PATCH / PUT | `/employees/{id}/` | hr, admin (employee: own phone) | update |
| POST | `/employees/{id}/deactivate/` | hr, admin | deactivate, keep the record |
| POST | `/employees/{id}/reactivate/` | hr, admin | undo a deactivation |
| GET | `/teams/` | manager, hr, admin | list teams (manager: only those they lead) |
| POST | `/teams/` | hr, admin | create a team |
| GET | `/teams/{id}/` | manager, hr, admin | one team |
| PATCH / PUT | `/teams/{id}/` | hr, admin | rename, change lead |
| DELETE | `/teams/{id}/` | hr, admin | delete a team (people keep their record) |
| GET | `/leave-types/` | session | every leave type |
| POST / PATCH / DELETE | `/leave-types/{id}/` | hr, admin | manage types (in-use types cannot be deleted) |
| GET | `/leave-balances/` | session, scoped | balances; `year` and `employee` (HR/admin) filters |
| GET | `/leave-requests/` | session, scoped | requests; `mine`, `status`, `leave_type`, `employee`, `year` filters |
| POST | `/leave-requests/` | session | request leave for yourself |
| POST | `/leave-requests/preview/` | session | days, remaining, sufficient and overlap for the dialog |
| POST | `/leave-requests/{id}/approve/` | manager (own team), hr, admin | approve and deduct |
| POST | `/leave-requests/{id}/reject/` | manager (own team), hr, admin | reject; a comment is required |
| POST | `/leave-requests/{id}/cancel/` | owner, admin | cancel; restores an approved balance |
| GET | `/leave-calendar/` | session, scoped | approved leave for a month, plus holidays |
| GET | `/audit-logs/` | hr, admin | audit feed; `action`, `model`, `actor`, `date_from`, `date_to`, `search`, `page` |
| GET | `/audit-logs/{id}/` | hr, admin | one audit event with its changes |
| GET | `/audit-logs/actors/` | hr, admin | distinct actors for the filter |
| GET | `/payroll/dashboard/` | hr, admin | current-month payroll metrics and recent activity |
| GET | `/payroll/salary-structures/` | session, scoped | list structures; employee/manager see only their own |
| POST | `/payroll/salary-structures/` | hr, admin | create an employee's first structure |
| GET | `/payroll/salary-structures/{id}/` | session, scoped | one structure |
| PATCH / PUT | `/payroll/salary-structures/{id}/` | hr, admin | revise; creates a new active version |
| DELETE | `/payroll/salary-structures/{id}/` | — | 405; versions are kept |
| GET | `/payroll/salary-revisions/` | hr, admin | revision history, filter by `employee` |
| GET | `/payroll/records/` | session, scoped | payroll history; `mine`, `year`, `month`, `status`, `payment_status`, `employee`, `search` |
| PATCH | `/payroll/records/{id}/` | hr, admin | adjust a draft (`adjustment_amount`, `adjustment_note`) |
| POST | `/payroll/records/generate/` | hr, admin | generate drafts for one employee or all eligible |
| POST | `/payroll/records/{id}/finalize/` | hr, admin | freeze one draft |
| POST | `/payroll/records/finalize-period/` | hr, admin | freeze every draft in a month |
| POST | `/payroll/records/{id}/payment/` | hr, admin | record `pending`/`paid`/`failed`, date and reference |
| GET | `/payroll/records/{id}/payslip/` | owner or hr/admin | PDF payslip for a finalized record (HR can preview drafts) |
| GET | `/invoices/dashboard/` | hr, admin | receivable metrics and recent invoices |
| GET / POST | `/clients/` | hr, admin | list/search clients, or add one |
| GET / PATCH / DELETE | `/clients/{id}/` | hr, admin | read/edit; delete only a client with no invoices |
| GET / POST | `/invoices/` | hr, admin | list/filter/search invoices, or generate one |
| GET | `/invoices/{id}/` | hr, admin | full invoice with items, payments, reminders and files |
| PATCH / PUT | `/invoices/{id}/` | hr, admin | edit a draft only; sent invoices are locked |
| POST | `/invoices/{id}/send/` | hr, admin | email the PDF via Gmail and mark a draft as sent |
| POST | `/invoices/{id}/cancel/` | hr, admin | cancel an unpaid draft/sent invoice |
| POST | `/invoices/{id}/payment/` | hr, admin | record a full or partial payment |
| POST | `/invoices/{id}/reminder/` | hr, admin | email and record a payment reminder |
| GET | `/invoices/{id}/pdf/` | hr, admin | generated PDF invoice |
| GET / POST | `/invoices/{id}/attachments/` | hr, admin | list or upload invoice files |
| GET | `/invoices/{id}/attachments/{attachment_id}/download/` | hr, admin | download an uploaded file |
| DELETE | `/invoices/{id}/attachments/{attachment_id}/` | hr, admin | remove an uploaded file |
| GET | `/invoices/reminder-queue/` | hr, admin | due/overdue invoices ready for a reminder |
| GET | `/invoices/reminders/` | hr, admin | reminder history, filter by `invoice` or `trigger` |

The audit endpoints are read-only: POST, PATCH and DELETE return 405, and
managers/employees get 403. Dashboard data is one role-scoped payload; the
employee response contains no company-wide fields.

`/employees/{id}` has no DELETE: people are deactivated, never deleted.
`/leave-requests/{id}` has no DELETE either: requests are cancelled. The
`auth/probe/*` endpoints exist only so the role matrix is testable.

## Roles and scoping

| Role | Scope |
|---|---|
| admin | Everything, including roles, settings, payroll and invoices |
| hr | All employees and teams, leave types, all leave requests, all payroll and invoices |
| manager | Own team: view members, approve or reject their leave; own payslips only |
| employee | Own profile (limited edits), own leave, own salary structure and finalized payslips |

Invoice and client endpoints are HR/admin only. Managers and employees get 403
for every invoice route, including the PDF and uploaded files, independently of
the React navigation.

Permissions are enforced by DRF permission classes on every view, and querysets
are narrowed by `apps/core/scoping.py`. Route guards in React are a UX layer
only — the API is the real gate. The dashboard payload is assembled per role in
`apps/dashboard/services.py`; the audit feed is HR/admin only in
`apps/audit/views.py`.

## Binary downloads

PDF and uploaded-file endpoints return a Django `HttpResponse`/`FileResponse`
directly. They use a permissive content-negotiation class so browser
`Accept: application/pdf` and `Accept: text/html` requests both reach the binary
handler instead of getting a DRF 406 before the file is built. See
`apps/core/negotiation.py`.

---

[← Previous: Features](../03-features/README.md) · [Documentation index](../README.md) · **Next: [05 · Payroll →](../05-payroll/README.md)**
