# 08 · Testing and verified status

[← Previous: Frontend](../07-frontend/README.md) · [Documentation index](../README.md) · **Next: [09 · Operations →](../09-operations/README.md)**

## Run the tests

```bash
cd backend
pytest
```

Tests use in-memory SQLite by default, so they need no database server. They
cover the role matrix, deactivation, the invite flow, audit rows, working days,
overlaps, half days, balance movement, approvals, cancellation, the calendar, the
dashboard payload for every role, audit API authorization and filters, audit
exactly-once and transaction behavior, the demo seed, payroll, and invoices.

The two tests that exercise the Postgres exclusion constraint are skipped on
SQLite. To run the whole suite against Postgres (pytest-django creates and drops a
separate `test_hrms` database):

```bash
DATABASE_URL=postgres://postgres:postgres@localhost:5432/hrms \
  pytest --ds=config.settings.test_postgres
```

The PostgreSQL role needs `CREATEDB` for that command. In this environment the
development role does not have it, so the automated Postgres suite remains a CI
step; the invoice and payroll migrations were still applied to the development
PostgreSQL database and exercised with live API checks.

## Verified in this checkout

Honest inventory of what has and has not been checked.

**Run, and passing:**

- `python manage.py check` — no issues.
- `python manage.py makemigrations --check --dry-run` — no pending changes.
- `python manage.py migrate` — applied on the dev PostgreSQL database, including
  the `btree_gist` extension and the exclusion constraint on
  `timeoff_leaverequest`, `reviewed_at` on leave requests, the audit created-at
  index, and both invoice migrations.
- `python manage.py seed_users` — 5 users, 5 employees, 2 teams, 3 leave types,
  4 holidays, 15 balances (5 people × 3 types) and 1 pending request; re-running
  keeps the counts stable.
- `python manage.py seed_demo` — 3 teams, 20 demo users/employees and 10 requests
  (3 pending, 4 approved, 3 rejected); audit writes suppressed; re-running keeps
  the counts stable and deletes nothing.
- `python manage.py showmigrations payroll organization` — payroll `0001`,
  organization `0001` and `0002` are applied on the local PostgreSQL database.
- `pytest` — **407 passed, 2 skipped** on SQLite.
  - 51 invoice tests cover client CRUD and permissions, exact totals, number
    sequencing, client snapshots, draft editing, sent locks, cancellation,
    partial/full payments, overpayment refusal, invoice sending with PDF
    attachment, Gmail MIME payload construction, fallback refusal when
    unconfigured, reminder emails/cooldown/queue/dashboard, the scheduled
    command, uploads (type, size, download, delete), PDFs (including
    `Accept: application/pdf`), audit rows and role restrictions.
  - 54 payroll tests cover calculations, permissions, revisions, generation,
    duplicates, adjustments, finalization, payment statuses, ownership
    restrictions, PDF generation, the dashboard and audit rows.
  - The two skips are the Postgres-only exclusion constraint tests.
- `ruff check --select E,F` on the changed invoice/audit/backend files — clean
  (generated migrations excluded).
- `tsc --noEmit` — clean.
- `npm run build` — production bundle built (623.43 kB JS, 174.49 kB gzip; Vite
  warns that the single chunk is just over 500 kB).
- `python manage.py migrate` — `invoices.0001_initial` and `invoices.0002`
  (delivery metadata) applied on the local PostgreSQL database.
- A live PDF request for an existing invoice with `Accept: application/pdf`
  returned 200 with `Content-Type: application/pdf`; the same endpoint also
  returned 200 for a browser-style `Accept: text/html`. This verifies the 406
  content-negotiation fix.
- Live invoice checks against the development PostgreSQL database through
  Django's test client: HR created a client and an invoice with two lines,
  checked subtotal 49,000, tax 8,775 and total 57,525, sent its PDF through the
  locmem fallback backend, recorded a 10,000 partial payment (balance 47,525),
  sent a reminder (also captured by locmem), uploaded and downloaded a signed
  PDF, generated and inspected the invoice PDF, saw the outstanding/overdue
  dashboard figures, had the just-reminded invoice correctly excluded from the
  reminder queue by the cooldown, and the created invoice had four audit rows.
  The transaction was rolled back afterwards.
- The generated invoice PDF was rendered with `pdftoppm` and inspected: company
  header, bill-to, item table, totals, payment history, notes and footer all fit
  on one A4 page (temporary check artifacts were deleted).
- Live checks against the dev PostgreSQL database: HR dashboard returned 25
  active employees, 5 teams, 3 pending requests and 2 people on leave today; the
  audit feed returned 23 events and the
  `action=create&model=employees.employee` filter returned 5; the manager
  dashboard returned 3 team members; the employee dashboard returned their own
  metrics; a manager request to the audit feed returned 403.
- A live time-off run on Postgres still holds: HR sees 3 leave types and 15
  balances; Evan previews a 2-day request (and a 0.5 half day), creates it, is
  refused an overlapping request and refused approving his own; the manager sees
  it, approves it and the balance drops to 18; the November calendar shows the
  approved leave; Evan cancels and the balance returns to 20; cancelling twice
  is refused; the seeded request stays pending; the audit rows are create
  (Evan), approve (manager), cancel (Evan).
- Live payroll HTTP checks: HR read the payroll dashboard, salary structures,
  payroll records and downloaded a PDF (`application/pdf`, one page); an
  employee account read only its own finalized record and structure, downloaded
  its own payslip, and received 403 for the dashboard/revisions/finalize and 404
  for another employee's structure and record.
- A generated payslip was rendered with `pdftoppm` and inspected: company header,
  employee details, earnings/deductions tables, adjustment, net pay, payment
  details and footer all fit on one A4 page.

**Not verified:** see [10 · Limitations](../10-limitations/README.md). It lists
the browser click-through gap, the real Gmail delivery gap, the browser test
suite absence and the remaining operational caveats.

---

[← Previous: Frontend](../07-frontend/README.md) · [Documentation index](../README.md) · **Next: [09 · Operations →](../09-operations/README.md)**
