# HRMS

A small HR system for one company: employees, teams, time off and an audit log.
Django + DRF backend, React + Vite frontend, PostgreSQL.

**Current state: Phase 4 plus the payroll and payslip module is implemented.**
Salary structures, revisions, monthly payroll, PDF payslips and the employee
payslip portal are integrated with the existing auth, roles, audit log and UI.
What has actually been run is listed under "Verified status" at the bottom —
read that before trusting any claim.

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
  apps/payroll/        salary structures, revisions, payroll records, ReportLab payslips
  apps/core/           permissions, role scoping, pagination, error shape, health
  tests/               pytest tests
frontend/
  src/api/             HTTP client + TanStack Query hooks per resource
  src/auth/            session context, ProtectedRoute, RoleRoute
  src/components/      shadcn/ui style primitives, layout shell, shared states
  src/pages/           auth, dashboard, employees, teams, time off, audit, payroll
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

## Payroll

The payroll module lives in `backend/apps/payroll` and is exposed under
`/api/v1/payroll/`. It uses `DecimalField`/`Decimal` for every amount; no salary
calculation touches floating point.

- **Salary structure** — basic salary, HRA, conveyance, medical, special and other
  allowances; PF, professional tax, income tax/TDS and other deductions. Gross,
  total deductions and net are calculated from the components. An employee can
  have one active structure; editing creates a new active version and marks the
  previous row inactive.
- **Revision history** — `SalaryRevision` stores the previous and new component
  snapshots, effective date, the user who revised it and the timestamp. Revision
  effective dates cannot move backwards, which keeps "newest effective version
  wins" unambiguous.
- **Payroll generation** — HR/admin choose a month/year and either one employee or
  all eligible active employees. The applicable structure is the newest version
  effective on or before the period end. Every component, the employee name, ID,
  designation, department and joining date are snapshotted into the payroll row.
  A database unique constraint on `(employee, year, month)` prevents duplicates.
- **Draft and finalized** — adjustments (positive or negative, with a note) are
  allowed only on drafts. Finalizing locks the snapshot, records who finalized it
  and when, and cannot be undone. Later structure revisions never touch existing
  payroll records, draft or finalized.
- **Payments** — statuses are `pending`, `paid` and `failed`; HR/admin can record
  a payment date and reference. No bank transfer or gateway call is made.
- **Payslips** — each payroll record has a unique payslip number. ReportLab
  generates a one-page corporate PDF with the company name/logo, employee
  details, earnings, deductions, adjustment, net pay and payment status. The
  company name and logo come from `organization.CompanyProfile` (Django admin);
  if no profile exists the `PAYROLL_COMPANY_NAME` setting is used.
- **Employee portal** — the "My payslips" page shows the signed-in person's own
  salary structure (read-only), finalized payroll history and PDF downloads.
  Employees and managers only ever see their own records; drafts and other
  people's records are hidden by the API queryset, not by the UI.

Set `PAYROLL_COMPANY_NAME` (default `HRMS`) in the environment, and create the
company profile in `/admin/organization/companyprofile/` for the logo. Payslips
use INR; the frontend and the PDF rendering share that currency. In production
serve the uploaded logo from `MEDIA_URL`/`MEDIA_ROOT` (Django serves it in
development). PDF files are never stored: they are rendered on demand from the
snapshotted payroll row.

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
accept invite, **My time off**, **Approvals**, **Team calendar**, the **Audit log**
for HR and admin, and the payroll pages: **Payroll dashboard**, **Salary
structures**, **Monthly payroll** (HR/admin) and **My payslips** (everyone).

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
  search, pagination, and a detail dialog with before/after changes. Payroll
  structures, revisions and records are included in the resource filter.
- Payroll dashboard: employees with structures, this month's payroll total, paid
  and pending amounts, draft/finalized counts, failed payments and recent
  activity.
- Salary structures: current structure per employee, create/revise dialogs with a
  live total preview, and revision history with before/after values.
- Monthly payroll: month/year selector, generate (one or all), filters, draft
  adjustment and finalization, bulk finalize, payment status dialog and PDF
  download.
- My payslips: own salary breakdown, finalized history, payment status and PDF
  downloads, with loading, empty and error states.

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

The audit endpoints are read-only: POST, PATCH and DELETE return 405, and
managers/employees get 403. Dashboard data is one role-scoped payload; the
employee response contains no company-wide fields.

`/employees/{id}` has no DELETE: people are deactivated, never deleted.
`/leave-requests/{id}` has no DELETE either: requests are cancelled. The
`auth/probe/*` endpoints exist only so the role matrix is testable.

## Roles

| Role | Scope |
|---|---|
| admin | Everything, including roles, settings and payroll |
| hr | All employees and teams, leave types, all leave requests, all payroll |
| manager | Own team: view members, approve or reject their leave; own payslips only |
| employee | Own profile (limited edits), own leave, own salary structure and finalized payslips |

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
- `python manage.py makemigrations --check --dry-run` — no pending changes
  (the payroll and company-profile migrations are committed).
- `python manage.py migrate` — applied on the local SQLite development database.
- `pytest` — **353 passed, 2 skipped** on SQLite. The 54 payroll tests cover
  calculations, permissions, revisions, generation, duplicates, adjustments,
  finalization, payment statuses, ownership restrictions, PDF generation, the
  dashboard and audit rows. The two skips are the Postgres-only exclusion
  constraint tests.
- `ruff check --select E,F` on the changed payroll/backend files — clean.
- `tsc --noEmit` — clean.
- `npm run build` — production bundle built (557 kB JS, 160 kB gzip; Vite warns
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
- Live payroll HTTP checks against `runserver` on the development database: HR
  read the payroll dashboard, salary structures, payroll records and downloaded a
  PDF (`application/pdf`, one page); an employee account read only its own
  finalized record and structure, downloaded its own payslip, and received 403
  for the dashboard/revisions/finalize and 404 for another employee's structure
  and record.
- A generated payslip was rendered with `pdftoppm` and inspected: company header,
  employee details, earnings/deductions tables, adjustment, net pay, payment
  details and footer all fit on one A4 page.

**Not verified:**

- The React pages in a browser. The bundle compiles and the API behind every
  page was exercised over HTTP, but nobody has clicked through the payroll
  dialogs, salary revision history, employee portal or the 375px layout.
- The new payroll migrations have not been re-run against PostgreSQL in this
  session: the local server accepts connections but no database credentials were
  available. The SQLite suite passes; the constraints are standard partial-unique,
  check and foreign-key constraints.
- The Django admin forms. Access was checked earlier for the seeded `admin@`;
  editing teams or uploading a company logo through the admin was not exercised.
- `npm run lint` / `npm run test` — those scripts do not exist yet; ESLint and
  Vitest were not set up in Phase 1. Typecheck and build are the checks used.
- Payroll PDFs are generated on demand and not stored, so there is no historical
  copy of a PDF if reportlab's output changes in a future release; the payroll
  row and all of its snapshots remain immutable, which is the source of truth.

Anything claimed to work has one of the checks above behind it; the gaps are
listed rather than glossed over.

## Data notes

- `LeaveRequest.reviewed_at` was added in Phase 4. Requests approved or rejected
  before that migration have no decision timestamp and therefore do not appear in
  the employee dashboard's "Recent decisions" list.
- `seed_demo` resets the demo accounts' passwords and the demo employees' profile
  fields on every run so the documented logins keep working. It never deletes a
  row and never touches non-demo accounts.
- The payroll module deliberately adds no salary or payroll rows to `seed_users`
  or `seed_demo`: payroll data must be created by HR through the module, not
  shipped as mock production data.
