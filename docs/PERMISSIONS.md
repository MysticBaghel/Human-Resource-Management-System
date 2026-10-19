# Permissions

Every endpoint below has an explicit DRF permission class and a queryset scoped
by role. The React route guards only hide things; this table is what the API
actually enforces.

Base path: `/api/v1/`. Errors use one shape:
`{"detail": str, "code": str, "fields": {}}`.

## How scoping works

| Role | Employees | Teams |
|---|---|---|
| employee | own record only | no access (403) |
| manager | members of teams they lead, plus their own record | teams they lead |
| hr | everyone, including inactive people | every team |
| admin | everyone, including inactive people | every team |

Out-of-scope records are filtered out of the queryset rather than denied one by
one, so a record outside your scope returns **404**, not 403. That is deliberate:
a 403 would confirm the record exists.

`apps/core/scoping.py` is the single place that decides this
(`scope_employees`, `scope_teams`), and `apps/core/permissions.py` holds the
permission classes.

## Auth

| Method | Path | Allowed | Notes |
|---|---|---|---|
| GET | `/health/` | public | liveness probe |
| GET | `/auth/csrf/` | public | sets the CSRF cookie |
| POST | `/auth/login/` | public | session login; CSRF enforced |
| POST | `/auth/logout/` | any signed-in user | destroys the session |
| GET | `/auth/me/` | any signed-in user | current user |
| POST | `/auth/password-reset/` | public | emails a reset link; CSRF enforced |
| POST | `/auth/password-reset/confirm/` | public | sets a new password; CSRF enforced |
| POST | `/auth/accept-invite/` | public | one-time invite token; CSRF enforced |
| GET | `/auth/probe/`, `/auth/probe/{role}/` | see view | test-only probes that prove role checks run |

Invite links last 7 days, work once, and are refused for an employee who has
already been deactivated. Accepting signs the person in.

## Employees

`/api/v1/employees/` uses `EmployeePermission`.

| Method | Path | Allowed | Notes |
|---|---|---|---|
| GET | `/employees/` | employee, manager, hr, admin | scoped; `search`, `team`, `status`, `role`, `page`, `page_size` |
| GET | `/employees/{id}/` | employee, manager, hr, admin | scoped |
| POST | `/employees/` | hr, admin | creates the login, the record and a 7-day invite; no password is set by HR |
| PATCH / PUT | `/employees/{id}/` | hr, admin | any editable field |
| PATCH | `/employees/{id}/` | employee | **own record, `phone` only** |
| DELETE | `/employees/{id}/` | nobody | 405; deactivate instead |
| POST | `/employees/{id}/deactivate/` | hr, admin | sets the record and login inactive |
| POST | `/employees/{id}/reactivate/` | hr, admin | restores both |

Field rules:

- `status` is read-only on the API; deactivation and reactivation are actions so
  the employee record and the login can never disagree.
- `role` may be set by HR except `admin`; granting or removing `admin` is
  admin-only. The same rule protects deactivating/reactivating an admin.
- An employee may PATCH only `phone` on their own record. Any other field, or a
  mix with `phone`, is a 403, not a silent no-op.
- A person cannot be their own manager.

Every create, update and deactivate/reactivate writes exactly one `AuditLog`
row, attributed to the signed-in user.

## Teams

`/api/v1/teams/` uses `TeamPermission`.

| Method | Path | Allowed | Notes |
|---|---|---|---|
| GET | `/teams/` | manager, hr, admin | manager sees only teams they lead; `search`, `page_size` |
| GET | `/teams/{id}/` | manager, hr, admin | scoped |
| POST | `/teams/` | hr, admin | name is unique, case-insensitively |
| PATCH / PUT | `/teams/{id}/` | hr, admin | name, optional lead |
| DELETE | `/teams/{id}/` | hr, admin | members keep their record; their team becomes empty |

A team's lead is an employee. Setting a lead is optional; the teams they lead are
what scopes a manager's view.

## Audit log

There is no audit API or page yet. Rows are written by signals and are
browsable, read-only, in the Django admin at `/admin/audit/auditlog/`, which
only staff/superuser accounts (the seeded `admin@`) can reach. That page is left
for a later phase.

## Invariants worth remembering

- Deactivated users cannot log in, and an existing session stops working
  immediately (`ActiveSessionAuthentication`).
- Employees are never hard-deleted.
- Only admins may grant or remove the `admin` role.
