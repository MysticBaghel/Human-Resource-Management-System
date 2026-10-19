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
(`scope_employees`, `scope_teams`, `scope_leave_requests`,
`scope_leave_balances`, `scope_calendar_requests`), and
`apps/core/permissions.py` holds the permission classes.

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

## Time off

`/api/v1/leave-types/`, `/leave-balances/`, `/leave-requests/` and
`/api/v1/leave-calendar/`.

| Role | Leave requests | Balances | Calendar |
|---|---|---|---|
| employee | own | own | own team's approved leave, plus their own |
| manager | own, plus the teams they lead | own | teams they lead, plus their own |
| hr, admin | all | all | all |

Leave types are readable by everyone (the request dialog needs them) and
writable by hr/admin. Balances are read-only through the API: only
`allocate_balances` and the approval/cancellation services move them.

| Method | Path | Allowed | Notes |
|---|---|---|---|
| GET | `/leave-types/` | any signed-in user | `search` |
| POST / PATCH / PUT / DELETE | `/leave-types/{id}/` | hr, admin | deleting a type with requests is a 400 |
| GET | `/leave-balances/` | any signed-in user, scoped | `year`, `employee` (HR/admin); read-only |
| GET | `/leave-requests/` | any signed-in user, scoped | `mine`, `status`, `leave_type`, `employee`, `year`; paginated |
| POST | `/leave-requests/` | any signed-in user with an employee record | always for yourself; an `employee` field is ignored |
| POST | `/leave-requests/preview/` | same | days, remaining, sufficient and overlap; writes nothing |
| POST | `/leave-requests/{id}/approve/` | manager (own team/direct report), hr, admin | deducts the balance |
| POST | `/leave-requests/{id}/reject/` | manager (own team/direct report), hr, admin | a comment is required; no balance change |
| POST | `/leave-requests/{id}/cancel/` | the owner, or admin | cancels pending or approved; restores an approved balance |
| GET | `/leave-calendar/` | any signed-in user, scoped | approved leave for `year` + `month`, plus holidays |
| DELETE | `/leave-requests/{id}/` | nobody | 405; cancel instead |

Rules the service enforces for every caller:

- Working days are Monday to Friday minus holidays; a half day costs 0.5 and must
  be a single date. Dates with no working days and requests spanning two calendar
  years are refused.
- Overlapping non-cancelled requests are refused, and PostgreSQL's exclusion
  constraint (inclusive `daterange`, `btree_gist`) enforces the same rule at the
  database level. Cancelled requests do not block their dates.
- Approve deducts, reject changes nothing, and cancelling an approved request
  restores the days. The request and balance rows are locked inside one
  transaction, so approving twice cannot deduct twice.
- A manager may review a request when the employee reports to them or is in a team
  they lead. HR and admin may review anyone. A manager outside the team gets a 404
  from the scoped queryset; an employee is stopped by the permission class.
- Only the owner (or an admin) may cancel. HR cannot cancel someone else's leave.
- Every state change writes exactly one audit row with the signed-in actor.

The React app mirrors this: employees and managers see only their own requests on
"My time off" (`mine=true`, which narrows even a manager's team scope); HR and
admin get an employee-name directory and open one person's balances with the
`employee` filter; HR and admin see every request, newest first, on the Approvals
page, while managers see their pending queue.

## Audit log

There is no audit API or page yet. Rows are written by signals for employees,
teams, leave types and leave requests, and are browsable, read-only, in the
Django admin at `/admin/audit/auditlog/`, which only staff/superuser accounts
(the seeded `admin@`) can reach. That page is left for a later phase.

## Invariants worth remembering

- Deactivated users cannot log in, and an existing session stops working
  immediately (`ActiveSessionAuthentication`).
- Employees are never hard-deleted.
- Only admins may grant or remove the `admin` role.
