# 01 · Overview

**HRMS** is a full-stack Human Resource Management System for a single company.
It is a complete internal application rather than a starter demo: it has
role-aware APIs, a React UI, payroll calculations, PDF documents, email delivery,
file uploads and an audit trail.

[Documentation index](../README.md) · **Next: [02 · Getting started →](../02-getting-started/README.md)**

## Scope

The system covers:

- authentication, roles and session security
- employees, teams and manager relationships
- employee invites and account activation
- time off: types, balances, requests, approvals, holiday calendar
- payroll: salary structures, revisions, monthly runs, payments, PDF payslips
- client invoices: billing details, line items, tax, payments, reminders, PDFs,
  uploaded documents
- role-scoped dashboards and a company audit log

It is not a multi-tenant SaaS, a recruitment/ATS product, an expense-claims tool
or a general ledger. Invoice support is specifically for **client invoices**
(accounts receivable), not vendor bills or employee reimbursements.

## Architecture at a glance

```text
React + Vite (frontend/src)
        │  fetch, cookies, CSRF
        ▼
Django REST Framework (/api/v1)
        │  permissions → scoped querysets → services
        ▼
Django apps (backend/apps)
        │  ORM, transactions, constraints
        ▼
PostgreSQL (SQLite also supported for local/test)
```

The backend owns every business rule. React route guards are a UX layer only;
all authorization and scoping is enforced again by the API.

## Repository layout

```text
backend/
  config/settings/     base, dev, prod, test, test_postgres
  apps/accounts/       custom User (email login + role), auth endpoints, seed_users
  apps/organization/   Team model and /api/v1/teams/
  apps/employees/      Employee + EmployeeInvite, services, invite flow
  apps/timeoff/        LeaveType, LeaveBalance, LeaveRequest, Holiday, services,
                       allocate_balances, /api/v1/leave-*/
  apps/dashboard/      role-scoped /api/v1/dashboard/ service
  apps/audit/          AuditLog, signals, middleware, /api/v1/audit-logs/
  apps/payroll/        salary structures, revisions, payroll records, PDF payslips
  apps/invoices/       clients, invoices, payments, reminders, uploads, PDFs
  apps/core/           permissions, role scoping, pagination, error shape, health
  tests/               pytest tests
frontend/
  src/api/             HTTP client + TanStack Query hooks per resource
  src/auth/            session context, ProtectedRoute, RoleRoute
  src/components/      UI primitives, layout shell, shared states
  src/pages/           auth, dashboard, employees, teams, time off, audit,
                       payroll, invoices
docs/                  this documentation set
```

## Design principles

- **Services own invariants.** Views are thin; payroll, leave and invoice writes
  go through service functions in transactions. This is why the code is explicit
  instead of generic CRUD.
- **Money is `Decimal`.** No salary or invoice calculation goes through floating
  point. Totals are rounded with financial rounding.
- **History is snapshotted.** Salary components and client details are copied
  onto payroll records and invoices so later edits do not rewrite old documents.
- **The database is a second gate.** Unique constraints, check constraints,
  protected foreign keys and a Postgres exclusion constraint back up the service
  rules.
- **Audit is automatic.** Tracked model saves flow through one signal-based
  audit path, with explicit events for non-model changes.
- **Fail closed.** Unknown roles see empty querysets; write endpoints declare
  explicit permission classes.
- **Tests protect the rules.** The suite covers calculations, permissions,
  transactions, PDFs, uploads, reminders and audit behavior.

## Where to go next

If you are setting up the project, continue to
[02 · Getting started](../02-getting-started/README.md). If you want the feature
tour first, jump to [03 · Features](../03-features/README.md).

---

[Documentation index](../README.md) · **Next: [02 · Getting started →](../02-getting-started/README.md)**
