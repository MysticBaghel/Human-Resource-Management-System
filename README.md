# HRMS

A full-stack Human Resource Management System for a single company. It covers
the employee lifecycle, teams, time off, payroll and payslips, client invoicing,
document uploads and a company-wide audit log.

Django + DRF backend · React + Vite frontend · PostgreSQL · ReportLab PDFs ·
Gmail API with OAuth 2.0.

## What is included

- Email/password authentication, roles and session + CSRF security
- Employees, teams, manager relationships and the invite flow
- Time off: balances, requests, approvals, calendar, half days and holidays
- Payroll: versioned salary structures, monthly runs, revisions, payments and PDF
  payslips
- Invoices: clients, line items, tax/discount, payments, reminders, uploads and
  PDF invoices
- Role-scoped dashboards, audit logging and the full JSON API
- Responsive React pages with loading, empty and error states

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit DJANGO_SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py seed_users
python manage.py runserver 8000
```

`python manage.py seed_demo` adds a larger, idempotent demo company.

### Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

The Vite dev server proxies `/api` to Django, so the browser only talks to
`http://localhost:5173`.

### Demo accounts

All seeded accounts use the password `DemoPass123!`.

| Role | Email |
|---|---|
| Admin | `admin@hrms.test` |
| HR | `hr@hrms.test` |
| Manager | `manager@hrms.test` |
| Employee | `employee@hrms.test` |
| Employee | `employee2@hrms.test` |

Only `admin@hrms.test` is staff and superuser, so only it can use Django admin at
`/admin/`.

## Documentation

**Start here → [docs/README.md](docs/README.md)**

Read the pages in order:

1. [Overview](docs/01-overview/README.md) — scope, architecture and layout
2. [Getting started](docs/02-getting-started/README.md) — setup, seeds, accounts
3. [Features](docs/03-features/README.md) — people, teams, invites and time off
4. [API](docs/04-api/README.md) — endpoints, roles, scoping and error shape
5. [Payroll](docs/05-payroll/README.md) — salary versions, runs, payslips
6. [Invoices](docs/06-invoices/README.md) — billing, reminders and Gmail OAuth
7. [Frontend](docs/07-frontend/README.md) — routes, pages and UI conventions
8. [Testing](docs/08-testing/README.md) — test suites and verified status
9. [Operations](docs/09-operations/README.md) — database, media, cron, deployment
10. [Limitations](docs/10-limitations/README.md) — known gaps and next steps

## Verification

Current local checks: **416 backend tests passed, 2 skipped**, `tsc --noEmit`
clean, and a production frontend build succeeds. See
[docs/08-testing/README.md](docs/08-testing/README.md) for exactly what was and
was not exercised, including the Gmail and PostgreSQL caveats.

**Next: [Documentation index →](docs/README.md)**
