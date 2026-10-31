# 05 · Payroll

[← Previous: API](../04-api/README.md) · [Documentation index](../README.md) · **Next: [06 · Invoices →](../06-invoices/README.md)**

The payroll module lives in `backend/apps/payroll` and is exposed under
`/api/v1/payroll/`. It uses `DecimalField`/`Decimal` for every amount; no salary
calculation touches floating point.

## Salary structure

A structure contains:

- **Earnings** — basic salary, HRA, conveyance, medical, special and other
  allowances
- **Deductions** — PF, professional tax, income tax/TDS and other deductions

Gross, total deductions and net are calculated from the components. An employee
can have one active structure; editing creates a new active version and marks the
previous row inactive.

## Revision history

`SalaryRevision` stores the previous and new component snapshots, effective date,
the user who revised it and the timestamp. Revision effective dates cannot move
backwards, which keeps "newest effective version wins" unambiguous.

## Payroll generation

HR/admin choose a month/year and either one employee or all eligible active
employees. The applicable structure is the newest version effective on or before
the period end. Every component, the employee name, ID, designation, department
and joining date are snapshotted into the payroll row. A database unique
constraint on `(employee, year, month)` prevents duplicates.

## Draft and finalized

- Adjustments (positive or negative, with a note) are allowed only on drafts.
- Finalizing locks the snapshot, records who finalized it and when, and cannot be
  undone.
- Later structure revisions never touch existing payroll records, draft or
  finalized.
- Bulk finalization finalizes every draft in a month in one transaction.

## Payments

Statuses are `pending`, `paid` and `failed`. HR/admin can record a payment date
and reference. No bank transfer or gateway call is made.

## Payslips

Each payroll record has a unique payslip number. ReportLab generates a one-page
corporate PDF with the company name/logo, employee details, earnings,
deductions, adjustment, net pay and payment status.

- The company name and logo come from `organization.CompanyProfile` (Django
  admin).
- If no profile exists, the `PAYROLL_COMPANY_NAME` setting is used.
- Payslips use INR; the frontend and PDF rendering share that currency.
- PDFs are rendered on demand and never stored; the payroll row is the source of
  truth.
- The API and PDF actions are listed in [04 · API](../04-api/README.md).
- Binary downloads use the shared content-negotiation fix, so `Accept:
  application/pdf` does not return 406.

## Employee portal

The **My payslips** page shows the signed-in person's own salary structure
(read-only), finalized payroll history and PDF downloads. Employees and managers
only ever see their own records; drafts and other people's records are hidden by
the API queryset, not by the UI.

## Company profile and settings

Set `PAYROLL_COMPANY_NAME` (default `HRMS`) in the environment, and create the
company profile at `/admin/organization/companyprofile/` for the logo.

In production, serve the uploaded logo from `MEDIA_URL`/`MEDIA_ROOT` (Django
serves it in development). The payslip itself is generated on demand and is not
written to media storage.

## Access

- HR/admin manage salary structures and payroll records.
- Employees and managers can read only their own active structure and finalized
  payroll records.
- Salary versions are never deleted.
- Payroll records are never deleted.
- Every payroll state change is audited.

## Tests

The payroll tests cover calculations, permissions, revisions, generation,
duplicates, adjustments, finalization, payment statuses, ownership restrictions,
PDF generation, the dashboard and audit rows. See
[08 · Testing](../08-testing/README.md) for how to run them.

---

[← Previous: API](../04-api/README.md) · [Documentation index](../README.md) · **Next: [06 · Invoices →](../06-invoices/README.md)**
