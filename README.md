# HRMS

A small HR system for one company: employees, teams, time off and an audit log.
Django + DRF backend, React + Vite frontend, PostgreSQL.

**Current state: Phase 4 (role-aware dashboard, audit log browsing, demo data) is
implemented.** Post-MVP features have not been started. What has actually been run
is listed under "Verified status" at the bottom — read that before trusting any
claim.

## Layout

```
backend/
  config/settings/     base, dev, prod, test, test_postgres
  apps/accounts/       custom User (email login + role), auth endpoints, seed_users
  apps/organization/   Team model and /api/v1/teams/
  apps/employees/      Employee + EmployeeInvite, services, invite flow
  apps/timeoff/        LeaveType, LeaveBalance, LeaveRequest, Holiday, services,
                       allocate_balances, /api/v1/leave-*/
  apps/dashboard/      role-scoped /api/v1/dashboard/ service
  apps/audit/          AuditLog, signals, middleware, /api/v1/audit-logs/
  apps/core/           permissions, role scoping, pagination, error shape, health
  tests/               pytest tests
frontend/
  src/api/             HTTP client + TanStack Query hooks per resource
  src/auth/            session context, ProtectedRoute, RoleRoute
  src/components/      shadcn/ui style primitives, layout shell, shared states
  src/pages/           auth, dashboard, employees, teams, time off, audit
```

## Requirements

- Python 3.12+ (developed against 3.13)
- Node.js 20+ (developed against 24)
- PostgreSQL 16+ for the leave-overlap constraint (PostgreSQL 18 is what is
  running here). SQLite works for everything else.

## Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env       # then edit DJANGO_SECRET_KEY
python manage.py migrate
python manage.py seed_users
python manage.py seed_demo   # optional: a larger, idempotent demo company
python manage.py runserver 8000
```

`seed_users` is idempotent and creates a small believable company:

| Role | Email | Team | Manager |
|---|---|---|---|
| admin | admin@hrms.test | People Ops | — |
| hr | hr@hrms.test | People Ops | — |
| manager | manager@hrms.test | Engineering (lead) | — |
| employee | employee@hrms.test | Engineering | Meera Manager |
| employee | employee2@hrms.test | Engineering | Meera Manager |

It also creates three leave types (Annual, Sick, Unpaid), the current year's
holidays, one balance per active employee and leave type, and one pending annual
leave request for Esha so the approvals page has something in it.

`seed_demo` is a development-only, idempotent command that adds a larger company on
top of whatever is already there: 3 teams (Product, Sales, Support), 20 demo
employees with team managers, balances for the current and next year, and a mix of
pending, approved and rejected leave requests. It never deletes data and suppresses
audit writes, so generated demo data is not presented as user activity. Its
accounts are `demo01@hrms.test` … `demo20@hrms.test` (team leads `demo01`,
`demo09`, `demo15`), same password.

Everyone shares the password `DemoPass123!`. Only `admin@` is staff **and
superuser**, so only it can open and actually use the Django admin at `/admin/`.
The other roles use the React app; they are refused by the admin site.

Run the tests:

```bash
cd backend
pytest
```

Tests use in-memory SQLite by default, so they pass without a database server.
They cover the role matrix, deactivation, the invite flow, audit rows, working
days, overlaps, half days, balance movement, approvals, cancellation, the
calendar, the dashboard payload for every role, audit API authorization and
filters, audit exactly-once and transaction behaviour, and the demo seed.

The two tests that exercise the Postgres exclusion constraint are skipped on
SQLite. To run the whole suite against Postgres (pytest-django creates and drops
a separate `test_hrms` database):

```bash
DATABASE_URL=postgres://postgres:postgres@localhost:5432/hrms \
  pytest --ds=config.settings.test_postgres
```

## Invites

Creating an employee does **not** set a password. The API creates the login
(inactive), the person record, and a one-time invite token, then emails a link
to `<FRONTEND_URL>/accept-invite?token=...`. In development Django's console
email backend prints the link in the `runserver` terminal; open it, choose a
password, and you are signed in as that person.

Links expire after 7 days, work once, and are refused if the employee has been
deactivated.

## Time off

- **Working days** are Monday to Friday minus holidays; a half day costs 0.5 and
  must be a single date. A request cannot span two calendar years.
- **Overlaps** are refused by the service and by a PostgreSQL exclusion
  constraint (`btree_gist`, inclusive `daterange`), so two concurrent requests
  cannot slip through. Cancelled requests do not block their dates.
- **Approving** deducts the days from the balance; **rejecting** changes nothing;
  **cancelling** an approved request gives the days back. Balance and request
  rows are locked in one transaction, so double approval cannot deduct twice.
- **Who approves:** a manager can approve their own team / direct reports; HR and
  admin can approve anyone; HR and admin can see every request. The reviewer is
  recorded, and every state change writes an audit row.
- **Balances** are read-only through the API. `python manage.py allocate_balances
  --year 2026` creates them (including capped carry-over). Leave types are
  editable by HR through `/api/v1/leave-types/`; holidays are managed in the
  Django admin or by the seed.

## Database

`DATABASE_URL` decides the database:

- **unset** — local SQLite file at `backend/db.sqlite3`.
- **set** — that Postgres instance. In `backend/.env`:
  ```
  DATABASE_URL=postgres://hrms:hrms@localhost:5432/hrms
  ```

Check which one Django is actually using:

```bash
python manage.py shell -c "from django.db import connection; d=connection.settings_dict; print(connection.vendor, d['NAME'])"
```

If Postgres is already installed locally, create the app role and database once
(as the `postgres` superuser), then run migrations and seed:

```sql
CREATE ROLE hrms LOGIN PASSWORD 'hrms';
CREATE DATABASE hrms OWNER hrms;
```

```bash
python manage.py migrate
python manage.py seed_users
```

A fresh Postgres database is empty until those two commands run — that is the
expected "no tables" state. The time-off migration creates the `btree_gist`
extension (as the database owner) before adding the exclusion constraint.

Start Postgres however you prefer, for example:

```bash
docker run --name hrms-db -e POSTGRES_USER=hrms -e POSTGRES_PASSWORD=hrms \
  -e POSTGRES_DB=hrms -p 5432:5432 -d postgres:16
```

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Vite proxies `/api` to `http://localhost:8000` (override with
`VITE_API_PROXY_TARGET`), so the browser only ever talks to `:5173` and no CORS
configuration is needed.

Scripts:

```bash
npm run typecheck   # tsc --noEmit
npm run build       # tsc -b && vite build
```

Pages: role-aware dashboard, login/forgot/reset, employee list/detail/form, teams,
accept invite, **My time off**, **Approvals**, **Team calendar**, and the **Audit
log** for HR and admin.

- The dashboard is computed from the database per role: admin and HR get company
  counts and activity, managers get their team's pending approvals and upcoming
  leave, employees get their balances, pending requests and recent decisions.
- My time off: employees and managers see only their own balances and requests.
  HR and admin get a searchable employee-name directory; clicking a person opens
  that person's balance boxes and requests.
- HR and admin see every leave request on the Approvals page as a ledger, newest
  first, with statuses and decisions; managers get their pending queue.
- The request dialog calls the API for a live working-day and balance preview.
- The team calendar is a month grid, coloured by leave type, with holidays.
- The audit log page has filters for action, resource, actor and date range,
  search, pagination, and a detail dialog with before/after changes.

All pages have loading, empty and error states and work down to 375px.

## API

Everything lives under `/api/v1/`. The role matrix is summarized under "Roles"
below. Auth is Django session + CSRF.

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

The audit endpoints are read-only: POST, PATCH and DELETE return 405, and
managers/employees get 403. Dashboard data is one role-scoped payload; the
employee response contains no company-wide fields.

`/employees/{id}` has no DELETE: people are deactivated, never deleted.
`/leave-requests/{id}` has no DELETE either: requests are cancelled. The
`auth/probe/*` endpoints exist only so the role matrix is testable.

## Roles

| Role | Scope |
|---|---|
| admin | Everything, including roles and settings |
| hr | All employees and teams, leave types, all leave requests |
| manager | Own team: view members, approve or reject their leave |
| employee | Own profile (limited edits) and own leave |

Permissions are enforced by DRF permission classes on every view, and querysets
are narrowed by `apps/core/scoping.py`. Route guards in React are a UX layer
only — the API is the real gate. The dashboard payload is assembled per role in
`apps/dashboard/services.py`; the audit feed is HR/admin only in
`apps/audit/views.py`.

## Verified status

Honest inventory of what has and has not been checked.

**Run, and passing:**

- `python manage.py check` — no issues.
- `python manage.py makemigrations --check --dry-run` — no pending changes.
- `python manage.py migrate` — applied on the dev PostgreSQL database, including
  the `btree_gist` extension and the exclusion constraint on
  `timeoff_leaverequest`, `reviewed_at` on leave requests, and the audit
  created-at index.
- `python manage.py seed_users` — 5 users, 5 employees, 2 teams, 3 leave types,
  4 holidays, 15 balances (5 people × 3 types) and 1 pending request; re-running
  keeps the counts stable.
- `python manage.py seed_demo` — 3 teams, 20 demo users/employees and 10 requests
  (3 pending, 4 approved, 3 rejected); audit writes suppressed; re-running keeps
  the counts stable and deletes nothing.
- `pytest` — **299 passed, 2 skipped** on SQLite (the two skips are the
  Postgres-only exclusion-constraint tests).
- `pytest --ds=config.settings.test_postgres` — **301 passed** against
  PostgreSQL 18, including both exclusion-constraint tests.
- `tsc --noEmit` — clean.
- `npm run build` — production bundle built (502 kB JS, 148 kB gzip; Vite warns
  that the single chunk is just over 500 kB).
- Live checks against the dev PostgreSQL database through Django's test client:
  HR dashboard returned 25 active employees, 5 teams, 3 pending requests and 2
  people on leave today; the audit feed returned 23 events and the
  `action=create&model=employees.employee` filter returned 5; the manager
  dashboard returned 3 team members and the employee dashboard returned their own
  metrics; a manager request to the audit feed returned 403.
- A live end-to-end run against `runserver` on Postgres (Phase 3) still holds: HR
  sees 3 leave types and 15 balances; Evan previews a 2-day request (and a 0.5 half
  day), creates it, is refused an overlapping request and refused approving his
  own; the manager sees it, approves it and the balance drops to 18; the November
  calendar shows the approved leave; Evan cancels and the balance returns to 20;
  cancelling twice is refused; the seeded request stays pending; the audit rows
  are create (Evan), approve (manager), cancel (Evan).

**Not verified:**

- The React pages in a browser. The bundle compiles and the API behind every
  page was exercised over HTTP, but nobody has clicked through the dashboard
  cards, audit filters, detail dialog or the 375px layout.
- The Django admin forms. Access was checked earlier for the seeded `admin@`;
  editing through the admin was not exercised.
- `ruff` — declared in `requirements.txt` but not installed in `backend/.venv`,
  and installing it was blocked by this session's Windows sandbox. No lint run
  was possible.
- `npm run lint` / `npm run test` — those scripts do not exist yet; ESLint and
  Vitest were not set up in Phase 1. Typecheck and build are the checks used.

Anything claimed to work has one of the checks above behind it; the gaps are
listed rather than glossed over.

## Data notes

- `LeaveRequest.reviewed_at` was added in Phase 4. Requests approved or rejected
  before that migration have no decision timestamp and therefore do not appear in
  the employee dashboard's "Recent decisions" list.
- `seed_demo` resets the demo accounts' passwords and the demo employees' profile
  fields on every run so the documented logins keep working. It never deletes a
  row and never touches non-demo accounts.
