# 06 · Invoices

[← Previous: Payroll](../05-payroll/README.md) · [Documentation index](../README.md) · **Next: [07 · Frontend →](../07-frontend/README.md)**

The invoice module lives in `backend/apps/invoices` and is exposed under
`/api/v1/invoices/` and `/api/v1/clients/`. It is for **client invoices**
(accounts receivable), not employee expense claims or vendor bills. HR and admin
are the only roles that can reach it.

## Clients

A client stores name, contact, billing email, phone, address, tax ID and notes.
A client is deactivated rather than deleted once it has invoices. Billing details
are snapshotted onto an invoice when it is generated, so editing a client later
never rewrites an issued document.

## Generation

Pick a client, issue/due dates, reference, notes, terms and any number of line
items. Each line has a description, quantity and unit price; the API calculates
the line amount, subtotal, discount (before tax), tax at a percentage rate and
total with `Decimal`, never floating point.

- The invoice number is `INV-YYYY-NNNN`, allocated from a locked per-year
  sequence, so concurrent creates cannot collide.
- Drafts are editable; once sent the financial values are locked.
- The issue year cannot change after a number is allocated.

## Statuses

`draft`, `sent`, `partially_paid`, `paid` and `cancelled`.

`overdue` is derived from the due date and outstanding balance, never stored, so
nothing has to run at midnight to keep it accurate.

Invoices are financial records and cannot be deleted. Drafts and unpaid sent
invoices can be cancelled. A sent invoice with a recorded payment cannot be
cancelled.

## Sending invoices

`POST /invoices/{id}/send/` emails the invoice PDF and only then marks it
`sent`. Delivery goes through the Gmail API with an OAuth 2.0 refresh token
(`gmail.send` scope) when Gmail is configured.

A failed send leaves the invoice as a draft so it can be retried. The recipient,
provider and Gmail message id are stored on the invoice.

The UI uses a **Send invoice** dialog. The old “Mark as sent” action is gone.

## PDF invoice

ReportLab renders a one-page corporate invoice from the stored snapshot: company
profile/logo, bill-to, item table, totals, payments received, notes and terms.
PDFs are rendered on demand and never stored; the invoice row remains the source
of truth.

`GET /invoices/{id}/pdf/` downloads it. The endpoint accepts browser-style
`Accept` headers and returns `application/pdf` without a DRF 406.

## Payments

Record a full or partial payment with date, method (bank transfer, UPI, card,
cheque, cash or other), reference and note.

- The API refuses an amount above the balance due.
- Status, amount paid and balance update in the same transaction.
- A partial payment keeps the invoice open; a full payment marks it paid.
- No bank or gateway call is made.

## Payment reminders

Send a reminder email to the client (or a custom recipient) from the invoice
detail page, using the same Gmail API/OAuth 2.0 path as invoice sending.

- The service records recipient, subject, message, trigger and provider.
- It increments the reminder count and stamps the last-reminded time.
- A configurable cooldown (`INVOICE_REMINDER_COOLDOWN_DAYS`, default 3) stops
  repeat sends.
- `GET /invoices/reminder-queue/` lists invoices due within seven days or already
  overdue that are outside the cooldown.
- `GET /invoices/reminders/` lists reminder history.

Scheduled reminders:

```bash
cd backend
.venv/bin/python manage.py send_invoice_reminders --days 7
# preview:
.venv/bin/python manage.py send_invoice_reminders --days 7 --dry-run
```

A daily cron entry is enough:

```cron
0 9 * * * cd /path/to/backend && .venv/bin/python manage.py send_invoice_reminders
```

The command respects the same cooldown, so running it more often does not spam
clients.

## Uploads

Attach a PDF, PNG, JPG or WEBP (10 MB maximum) to any invoice as the original
invoice, signed copy, payment receipt or other document.

- Files are stored under `MEDIA_ROOT/invoices/<year>/` with a random on-disk
  name.
- The original name and uploader are kept on the row.
- Downloads go through the authenticated API.
- Deleting the row removes the file.
- Keep the invoice upload directory private in production: do not expose
  `MEDIA_ROOT` publicly (Django serves it in development for convenience), or use
  private object storage with signed URLs.

## Gmail API with OAuth 2.0

The real sender uses the Gmail API, not an app password or SMTP.

1. In Google Cloud, enable the **Gmail API**, configure the OAuth consent screen,
   and create an OAuth 2.0 Client ID of type **Desktop app** (or a web client with
   `http://localhost:8080/` as an allowed redirect URI).
2. Put `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `backend/.env`.
3. Run the one-time consent flow:

   ```bash
   cd backend
   .venv/bin/python manage.py gmail_oauth_setup
   # headless server:
   .venv/bin/python manage.py gmail_oauth_setup --manual
   ```

   The command requests the `gmail.send` scope with `access_type=offline`. It
   **prints** the env values; it does not edit `.env` and does not store the
   token in the database.
4. Add the printed values, plus the authorized account, to `backend/.env`:

   ```env
   GMAIL_CLIENT_ID=...
   GMAIL_CLIENT_SECRET=...
   GMAIL_REFRESH_TOKEN=...
   GMAIL_SENDER_EMAIL=you@gmail.com
   GMAIL_SENDER_NAME=Your Company
   ```

5. Restart Django after changing `.env` (the dev server does not reliably reload
   it). Check configuration with:

   ```bash
   .venv/bin/python manage.py shell -c \
     "from apps.invoices.gmail import gmail_configured; print(gmail_configured())"
   ```

6. Keep `INVOICE_EMAIL_FALLBACK=False` in production. When Gmail is not
   configured, a send returns a clear error and the invoice remains a draft.

In development and tests, `INVOICE_EMAIL_FALLBACK=True` is enabled by
`config/settings/dev.py` and `test.py`: emails are printed by the console backend
(or captured by locmem in tests). The fallback is never enabled implicitly in
production.

The OAuth token is sensitive. Do not commit it. If the Google app is in testing
mode, refresh tokens can expire; rerun the setup and replace the token.

## Audit

Clients, invoices, payments, reminders and attachments are tracked by the
existing audit signals. Invoice create and update rows include line items in the
audit detail. Invoice, payment, reminder and attachment resources appear in the
audit log's resource filter.

## Settings

- `INVOICE_DEFAULT_CURRENCY` (default `INR`)
- `INVOICE_REMINDER_COOLDOWN_DAYS` (default 3)
- `DEFAULT_FROM_EMAIL` (fallback sender, default `hrms@localhost`)
- `GMAIL_*` values described above

Tax is a single invoice-level percentage (for example 18% GST) applied after
discount. There is no per-line tax rate, withholding, multi-currency FX or
e-invoicing integration; currency is a label on the document and totals.

---

[← Previous: Payroll](../05-payroll/README.md) · [Documentation index](../README.md) · **Next: [07 · Frontend →](../07-frontend/README.md)**
