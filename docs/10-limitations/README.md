# 10 · Limitations and next steps

[← Previous: Operations](../09-operations/README.md) · [Documentation index](../README.md) · [Back to repository README](../../README.md)

This is the honest gap list. Anything claimed as working in the other pages has
a check behind it; the items below are not claimed as verified.

## Not verified

- **The React pages in a real browser.** The bundle compiles and the APIs behind
  every page were exercised over HTTP, but nobody has clicked through the payroll
  dialogs, salary revision history, employee portal, invoice dialogs, client
  directory or the 375px layout.
- **A real Gmail API send.** The OAuth token refresh, Gmail MIME payload and PDF
  attachment are covered by a mocked Gmail service test, but no Google Cloud
  project or real refresh token was available here, so no email was delivered
  through Google. The setup command was run only far enough to validate its
  missing-credential error.
- **The automated PostgreSQL test suite.** It was attempted, but the local
  development role lacks `CREATEDB`; the suite needs a superuser/CI database role.
  The migrations and live flows were still exercised against the development
  PostgreSQL database.
- **Django admin forms.** Access was checked for the seeded `admin@`; editing
  teams or uploading a company logo through the admin was not exercised.
- **Lint/test scripts on the frontend.** `npm run lint` and `npm run test` do not
  exist; ESLint and Vitest were not set up. Typecheck and build are the checks.
- **Historical PDFs.** Payroll and invoice PDFs are rendered on demand and not
  stored. If ReportLab output changes, there is no archived copy of an old PDF;
  the immutable database rows and snapshots remain the source of truth.
- **A real reminder scheduler.** The cron command and cooldown are covered by
  tests, but the command has not run under a production scheduler. Live invoice
  delivery used the locmem fallback, not Gmail.
- **Production file storage.** Uploaded invoice files are on the local
  filesystem. Production needs private media storage, backups and ideally a virus
  scanner; only extension/content-type/size checks exist now.
- **Multi-tenant behavior.** There is one company. Roles, teams and scopes assume
  a single organisation.

## Deliberate trade-offs

- **No invoice deletion.** Financial rows are cancelled, never removed. This
  keeps the audit trail and numbering intact, at the cost of not being able to
  erase a mistake.
- **Single tax rate per invoice.** Simpler than per-line GST/VAT, withholding or
  jurisdiction rules. Good enough for the current document, not a full tax
  engine.
- **No payment gateway.** Payments are recorded manually; no bank transfer, card
  or UPI integration is attempted.
- **Explicit services instead of generic CRUD.** More code than a ModelViewSet,
  but transactions, snapshots, number allocation and audit behavior stay in one
  place.
- **Responsive tables duplicated as desktop tables and mobile cards.** This
  follows the existing UI pattern and improves small-screen readability, but
  adds markup.
- **Development fallback email.** Without Gmail credentials, invoice emails print
  in the terminal. This is convenient locally but is not a production delivery
  mechanism.
- **Token in environment, not database.** A single deployment-level Gmail refresh
  token is simpler to operate for one company, but it is not per-user OAuth and
  must be rotated/reissued if revoked.

## Sensible next steps

1. Configure a Google Cloud project, run `gmail_oauth_setup`, and test a real
   send to an external address.
2. Add a browser E2E suite (Playwright) for login, leave approval, payroll and
   the invoice send/download flow.
3. Add a PostgreSQL service to CI so the exclusion constraint and invoice
   migrations are tested automatically.
4. Add frontend linting and component tests.
5. Decide whether invoice files should move to S3-compatible private storage with
   signed URLs and antivirus scanning.
6. If the product grows beyond one company, introduce tenant scoping at the
   queryset and model layers before adding customers/teams.
7. Consider email templates (HTML) and delivery webhooks/bounce handling if
   invoice volumes grow.

---

[← Previous: Operations](../09-operations/README.md) · [Documentation index](../README.md) · [Back to repository README](../../README.md)
