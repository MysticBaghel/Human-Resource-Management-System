# HRMS

A small HR system for one company: employees, teams, time off and an audit log.
Django + DRF backend, React + Vite frontend, PostgreSQL.

**Current state: Phase 2 (teams, employees, invites, audit) is implemented.**
Phase 3 (time off) has not been started. What has actually been run is listed
under "Verified status" at the bottom — read that before trusting any claim.

## Layout

```
backend/
  config/settings/     base, dev, prod, test
  apps/accounts/       custom User (email login + role), auth endpoints, seed_users
  apps/organization/   Team model and /api/v1/teams/
  apps/employees/      Employee + EmployeeInvite, services, invite flow
  apps/audit/          AuditLog, the signals that write it, request-user middleware
  apps/core/           permissions, role scoping, pagination, error shape, health
  tests/               pytest tests
frontend/
  src/api/             HTTP client + TanStack Query hooks per resource
  src/auth/            session context, ProtectedRoute, RoleRoute
  src/components/      shadcn/ui style primitives, layout shell, shared states
  src/pages/           auth, dashboard, employees, teams
docs/
  AGENTS.md            standing rules
  PERMISSIONS.md       every endpoint, the roles allowed, how it is scoped
  Handbook.pdf         the build guide
  Phase01.pdf          Phase 1 development and test report
  Phase02.pdf          Phase 2 development and test report
```

## Requirements

- Python 3.12+ (developed against 3.13)
- Node.js 20+ (developed against 24)
- PostgreSQL 16 — optional for now, see "Database" below

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

Everyone shares the password `DemoPass123!`. Only `admin@` is staff **and
superuser**, so only it can open and actually use the Django admin at `/admin/`.
The other roles use the React app; they are refused by the admin site.

Run the tests:

```bash
cd backend
pytest
```

Tests use in-memory SQLite, so they pass without a database server. They cover
the role matrix, deactivation, the invite flow and the audit rows.

## Invites

Creating an employee does **not** set a password. The API creates the login
(inactive), the person record, and a one-time invite token, then emails a link
to `<FRONTEND_URL>/accept-invite?token=...`. In development Django's console
email backend prints the link in the `runserver` terminal; open it, choose a
password, and you are signed in as that person.

Links expire after 7 days, work once, and are refused if the employee has been
deactivated.

## Database

`DATABASE_URL` decides the database:

- **unset** — local SQLite file at `backend/db.sqlite3`. Handy for a first run.
- **set** — that Postgres instance. In `backend/.env`:
  ```
  DATABASE_URL=postgres://hrms:hrms@localhost:5432/hrms
  ```

Start Postgres however you prefer, for example:

```bash
docker run --name hrms-db -e POSTGRES_USER=hrms -e POSTGRES_PASSWORD=hrms \
  -e POSTGRES_DB=hrms -p 5432:5432 -d postgres:16
```

Phase 3's leave-overlap constraint needs Postgres, so those tests will be
skipped or marked accordingly when only SQLite is available.

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

Pages: dashboard, login/forgot/reset, employee list with search/team/status/role
filters and pagination, employee detail, employee create/edit form, teams with a
create/edit dialog, and accept-invite. All of them have loading, empty and error
states and work down to 375px (tables become cards on small screens).

## API

Everything lives under `/api/v1/`. Full role table: [docs/PERMISSIONS.md](docs/PERMISSIONS.md).
Auth is Django session + CSRF.

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

`/employees/{id}` has no DELETE: people are deactivated, never deleted. The
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
only — the API is the real gate.

## Verified status

Honest inventory of what has and has not been checked.

**Run, and passing:**

- `python manage.py check` — no issues.
- `python manage.py migrate` — applied on the dev SQLite database.
- `python manage.py seed_users` — created 5 users, 5 employees and 2 teams;
  re-running keeps the counts stable (covered by tests).
- `pytest` — **151 passed** in ~8s, including the role matrix on employees and
  teams, 404-vs-403 scoping, the invite/accept flow, deactivate/reactivate,
  filters, pagination and audit-row assertions.
- `tsc --noEmit` — clean.
- `npm run build` — production bundle built (455 kB JS, 139 kB gzip).
- An end-to-end pass against `runserver` on SQLite with a real HTTP client:
  login as HR, create an employee, read the invite token, accept it as the new
  hire, verify the employee sees only their own record, verify their own
  `job_title` PATCH is 403 while `phone` is 200, verify a manager cannot see
  another team (404) and cannot list teams they do not lead, verify DELETE is
  405, deactivate → login fails, reactivate → login works, and confirm the audit
  rows and their actors. The throwaway users were removed afterwards.

**Not verified:**

- PostgreSQL. Everything above ran on SQLite. The migrations contain nothing
  Postgres-specific yet, but they have not been applied to a real server.
- The React pages in a browser. The bundle compiles and the API behind every
  page was exercised over HTTP, but nobody has clicked through dialogs, filters
  or the 375px layout.
- The Django admin forms. Access was checked against the dev database — the
  seeded `admin@` opens the index, audit log, employees and teams (all 200), and
  a manager is redirected to the admin login — but editing through the admin was
  not exercised.
- `ruff` — declared in `requirements.txt` but not installed in `backend/.venv`,
  and installing it was blocked by this session's Windows sandbox. No lint run
  was possible.
- `npm run lint` / `npm run test` — those scripts do not exist yet; ESLint and
  Vitest were not set up in Phase 1. Typecheck and build are the checks used.

Anything claimed to work has one of the checks above behind it; the gaps are
listed rather than glossed over.
