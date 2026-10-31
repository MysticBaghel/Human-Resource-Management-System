# 02 · Getting started

[← Previous: Overview](../01-overview/README.md) · [Documentation index](../README.md) · **Next: [03 · Features →](../03-features/README.md)**

## Requirements

- Python 3.12+ (developed against 3.13)
- Node.js 20+ (developed against 24)
- PostgreSQL 16+ for the leave-overlap constraint (PostgreSQL 18 is what is
  running here). SQLite works for everything else.

## Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env       # then edit DJANGO_SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py seed_users
python manage.py seed_demo   # optional: a larger, idempotent demo company
python manage.py runserver 8000
```

The backend reads `backend/.env`. `DATABASE_URL` selects PostgreSQL; if it is
unset, Django uses the local `backend/db.sqlite3` file. Database creation,
Docker and migration details are in
[09 · Operations](../09-operations/README.md).

## Demo data

`seed_users` is idempotent and creates a believable demo company:

| Role | Email | Team | Manager |
|---|---|---|---|
| admin | `admin@hrms.test` | People Ops | — |
| hr | `hr@hrms.test` | People Ops | — |
| manager | `manager@hrms.test` | Engineering (lead) | — |
| employee | `employee@hrms.test` | Engineering | Meera Manager |
| employee | `employee2@hrms.test` | Engineering | Meera Manager |

It also creates three leave types (Annual, Sick, Unpaid), the current year's
holidays, one balance per active employee and leave type, and one pending annual
leave request for Esha so the approvals page has something in it.

`seed_demo` is a development-only, idempotent command that adds a larger company
on top of whatever is already there: 3 teams (Product, Sales, Support), 20 demo
employees with team managers, balances for the current and next year, and a mix
of pending, approved and rejected leave requests. It never deletes data and
suppresses audit writes, so generated demo data is not presented as user
activity. Its accounts are `demo01@hrms.test` … `demo20@hrms.test` (team leads
`demo01`, `demo09`, `demo15`), with the same password.

Everyone shares the password `DemoPass123!`. Only `admin@` is staff **and
superuser**, so only it can open and actually use the Django admin at `/admin/`.
The other roles use the React app; they are refused by the admin site.

The payroll and invoice modules deliberately do not seed salary, payroll, client
or invoice rows. Create those through the app (or the API) so the demo does not
present fake financial records as real data.

## Frontend setup

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

There is currently no ESLint/Vitest script; typecheck and build are the frontend
checks.

## First useful login

1. Open `http://localhost:5173/login`.
2. Sign in as `hr@hrms.test` / `DemoPass123!`.
3. Use **Employees**, **Approvals**, **Payroll** and **Invoices** from the
   sidebar.
4. Sign in as `employee@hrms.test` to see the employee-scoped version.

For invoice email sending, Gmail OAuth is optional in development: without
credentials, emails print in the backend terminal. The full setup is in
[06 · Invoices](../06-invoices/README.md).

## Tests

```bash
cd backend
pytest
```

The test suite uses in-memory SQLite by default. What it covers and the
PostgreSQL test command are in
[08 · Testing](../08-testing/README.md).

---

[← Previous: Overview](../01-overview/README.md) · [Documentation index](../README.md) · **Next: [03 · Features →](../03-features/README.md)**
