# 07 · Frontend

[← Previous: Invoices](../06-invoices/README.md) · [Documentation index](../README.md) · **Next: [08 · Testing →](../08-testing/README.md)**

The frontend is React 18 + TypeScript + Vite. Data fetching is TanStack Query;
forms use React Hook Form + Zod; UI primitives follow the shadcn/ui style. There
is no separate CSS framework setup beyond Tailwind.

## Running it

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Vite proxies `/api` to `http://localhost:8000` (override with
`VITE_API_PROXY_TARGET`), so the browser only ever talks to `:5173` and no CORS
configuration is needed.

```bash
npm run typecheck   # tsc --noEmit
npm run build       # tsc -b && vite build
```

ESLint and Vitest are not configured yet; typecheck and build are the current
frontend checks.

## Page map

| Area | Pages |
|---|---|
| Auth | Login, forgot password, reset password, accept invite |
| Dashboard | Role-aware dashboard |
| Employees | List, detail, create/edit |
| Teams | Team list and management |
| Time off | My time off, approvals, team calendar, employee time-off view |
| Audit | Audit log (HR/admin) |
| Payroll | Payroll dashboard, salary structures, monthly payroll, my payslips |
| Invoices | Invoice ledger, client directory, invoice detail (HR/admin) |

Routes are wrapped in `ProtectedRoute` (session required) and `RoleRoute`
(role-based UX). These guards are not the security boundary; the API scopes and
permissions are.

## Notable UI behaviour

- The dashboard is computed per role and never shows company-wide fields to an
  employee payload.
- My time off limits employees/managers to their own balances and requests; HR
  and admin get an employee-name directory.
- HR/admin see every leave request on Approvals; managers get their pending
  queue.
- The request dialog calls the API for a live working-day and balance preview.
- The team calendar is a month grid, coloured by leave type, with holidays.
- The audit log has action/resource/actor/date filters, search, pagination and a
  detail dialog with before/after changes.
- Payroll dashboard shows structures, current-month totals, paid/pending
  amounts, draft/finalized counts, failed payments and recent activity.
- Salary structures supports create/revise dialogs with a live total preview and
  revision history.
- Monthly payroll supports month/year selection, generate one/all, filters,
  draft adjustment, finalization, bulk finalize, payment status and PDF download.
- My payslips shows the employee's own structure, finalized history, payment
  status and PDF downloads.
- Invoices includes receivable metrics, a reminder queue, filters and a
  responsive ledger.
- Invoice detail includes line items, totals, payment history, reminder history,
  PDF download, upload/download/delete, send, record payment, cancel and
  edit-draft actions.
- Clients is a searchable billing directory with active/inactive status,
  create/edit and delete only for clients with no invoices.

All pages have loading, empty and error states and work down to 375px. Lists
render a desktop table and a mobile card layout.

## Key frontend files

```text
src/api/client.ts             fetch wrapper, CSRF, downloads, uploads
src/api/invoices.ts           invoice/client types and hooks
src/auth/                     AuthContext, ProtectedRoute, RoleRoute
src/components/invoices/      client, invoice, payment, reminder and upload dialogs
src/pages/invoices/           Invoices, Clients, Invoice detail
src/pages/payroll/            Payroll dashboard, structures, monthly, my payslips
src/lib/                      date, money, query and formatting helpers
```

## Downloads

PDF and uploaded-file downloads go through `apiDownload`, which sends the session
cookie and `Accept: */*`. The backend also has a permissive negotiation class for
binary endpoints, so a direct browser request for a PDF works too.

---

[← Previous: Invoices](../06-invoices/README.md) · [Documentation index](../README.md) · **Next: [08 · Testing →](../08-testing/README.md)**
