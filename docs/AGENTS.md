# AGENTS.md

Standing rules for every agent session in this repo. Read this file and `docs/HANDBOOK.md` before doing anything.

## Project

HRMS: a Headcount-style HR management system (employees, teams, time off, audit log).
Single company, one codebase, self-hostable with `docker compose up`.

## Stack (do not change without being asked)

- Backend: Django 5 + Django REST Framework, in `backend/`. API under `/api/v1/`.
- Frontend: React 18 + Vite + TypeScript, in `frontend/`. React Router, TanStack Query, react-hook-form + zod.
- UI: Tailwind + shadcn/ui only. Do not add MUI, Bootstrap or any other UI kit.
- Database: PostgreSQL 16.
- Auth: Django session auth + CSRF. React is served same-origin (Vite proxy in dev, reverse proxy in prod).
- Tooling: ruff + pytest-django (backend), eslint + vitest (frontend), GitHub Actions CI, docker compose.
- No FastAPI, no Node backend, no second API framework.

## Repo layout

```
backend/
  config/            settings (base/dev/prod), urls, wsgi
  apps/
    accounts/        User model, auth endpoints
    organization/    Team
    employees/       Employee model, serializers, viewsets
    timeoff/         LeaveType, LeaveBalance, LeaveRequest, Holiday, services.py
    audit/           AuditLog + signal writer
    core/            permissions, pagination, shared utils
  tests/
frontend/
  src/
    api/             HTTP client, query hooks
    auth/            session context, route guards
    pages/           one folder per page
    components/      shared UI built on shadcn/ui
docs/
  HANDBOOK.md        PRD, architecture, phases
  PERMISSIONS.md     every endpoint and the roles allowed (kept current)
docker-compose.yml
AGENTS.md
```

## Roles

`admin`, `hr`, `manager`, `employee`.

| Role | Scope |
|---|---|
| admin | Everything, including settings and roles |
| hr | All employees, teams, leave types, all leave requests |
| manager | Own team: view members, approve or reject their leave |
| employee | Own profile (limited edits) and own leave |

## Working rules

1. **One phase at a time.** Do only the phase named in the prompt. Do not add features from later phases and do not refactor unrelated code.
2. **Server-side permissions always.** Every API view has an explicit permission class. `get_queryset` is scoped by role (employee: own records, manager: own team, hr/admin: all). Hiding a button in React is never enough.
3. **Business logic in `services.py`.** Keep views thin and serializers about shape and validation. Leave logic, invites and balance changes live in service functions.
4. **Transactions for balances.** Anything that changes leave balances or request status runs inside `transaction.atomic()` and locks balance rows with `select_for_update()`.
5. **Database enforces what it can.** Use constraints (unique, CHECK, exclusion constraints) in addition to app-level validation.
6. **Soft delete people.** Employees are deactivated, never hard-deleted. Inactive users cannot log in.
7. **Audit everything that matters.** Create, update and delete on employees, teams, leave types and leave requests write an `AuditLog` row.
8. **Tests with the code.** New behavior ships with tests. Write tests first for `timeoff/services.py`. Do not edit or delete a test to make it pass unless the test itself is wrong, and say so if you do.
9. **Migrations are reviewed.** Generate with `makemigrations`, read the result, and flag anything destructive. Never edit an applied migration.
10. **Secrets in environment variables.** Never commit `.env`. Keep `.env.example` current.
11. **Dates are dates.** Store leave dates as `DateField`, not datetimes. Avoid time zone logic.
12. **Keep it small.** Typed code, small files, no dead code, no leftover TODO stubs, no unused dependencies.

## Frontend rules

- Use shadcn/ui components and Tailwind utilities. Keep spacing, type scale and colors consistent across pages.
- Every page handles loading (skeleton), empty and error states. Use toasts for action results.
- Forms use react-hook-form + zod with inline errors.
- Data fetching goes through TanStack Query hooks in `src/api/`. No fetch calls inside components.
- Route guards (`ProtectedRoute`, `RoleRoute`) are a UX layer only. The API is the real gate.
- Must work down to 375px wide.

## API conventions

- Base path `/api/v1/`. Plural nouns. Actions as `POST /resource/{id}/action/`.
- Pagination: 20 per page, page-number style.
- Error shape: `{"detail": "message", "code": "machine_code", "fields": {}}`.
- Document endpoints with drf-spectacular. Keep `docs/PERMISSIONS.md` in sync when adding or changing an endpoint.

## Commands

```
docker compose up --build                 # run everything
docker compose exec api pytest            # backend tests
docker compose exec api ruff check .      # backend lint
docker compose exec api python manage.py makemigrations
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_users
docker compose exec api python manage.py seed_demo
cd frontend && npm run lint && npm run test
```

## Before you finish any task

1. Run backend lint and tests, and frontend lint and tests. Fix failures.
2. Run the app and exercise the feature you built.
3. Confirm every new endpoint has a permission class and a role-scoped queryset.
4. Reply with: files changed, commands run, test results, and anything you did not do or are unsure about. Do not claim something works unless you ran it.

## Never

- Skip permission checks "for now".
- Put leave balance logic in views, serializers or the frontend.
- Add a dependency without saying why.
- Change `AUTH_USER_MODEL`, existing migrations or the stack without being asked.
- Build payroll, recruiting, attendance tracking or performance reviews (out of scope).
