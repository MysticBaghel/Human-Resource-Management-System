# 09 · Operations

[← Previous: Testing](../08-testing/README.md) · [Documentation index](../README.md) · **Next: [10 · Limitations →](../10-limitations/README.md)**

## Database

`DATABASE_URL` decides the database:

- **unset** — local SQLite file at `backend/db.sqlite3`.
- **set** — that Postgres instance. In `backend/.env`:

  ```env
  DATABASE_URL=postgres://hrms:hrms@localhost:5432/hrms
  ```

Check which one Django is actually using:

```bash
python manage.py shell -c \
  "from django.db import connection; d=connection.settings_dict; print(connection.vendor, d['NAME'])"
```

If PostgreSQL is installed locally, create the app role and database once (as
the `postgres` superuser), then run migrations and seed:

```sql
CREATE ROLE hrms LOGIN PASSWORD 'hrms';
CREATE DATABASE hrms OWNER hrms;
```

```bash
python manage.py migrate
python manage.py seed_users
```

A fresh Postgres database is empty until those commands run; that is the expected
"no tables" state. The time-off migration creates the `btree_gist` extension (as
the database owner) before adding the exclusion constraint.

Start Postgres however you prefer, for example:

```bash
docker run --name hrms-db -e POSTGRES_USER=hrms -e POSTGRES_PASSWORD=hrms \
  -e POSTGRES_DB=hrms -p 5432:5432 -d postgres:16
```

## Migrations and seeds

```bash
cd backend
python manage.py migrate
python manage.py seed_users
python manage.py seed_demo          # optional, development only
python manage.py allocate_balances --year 2026
```

Both seed commands are idempotent and never delete data. `seed_demo` suppresses
audit writes so demo data does not look like real user activity.

Payroll and invoices are deliberately not seeded. Create clients, invoices,
salary structures and payroll through the app or API so financial records are not
fake production data.

## Gmail and reminders

The real email path is Gmail API OAuth 2.0; see
[06 · Invoices](../06-invoices/README.md) for the full setup. The short version:

```bash
cd backend
.venv/bin/python manage.py gmail_oauth_setup
```

The setup command prints env values but **does not edit `.env`**. Add
`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`,
`GMAIL_SENDER_EMAIL` and optionally `GMAIL_SENDER_NAME`, then restart Django.
Keep `INVOICE_EMAIL_FALLBACK=False` in production.

Scheduled reminders:

```cron
0 9 * * * cd /path/to/backend && .venv/bin/python manage.py send_invoice_reminders
```

Use `--dry-run` to preview. The command respects `INVOICE_REMINDER_COOLDOWN_DAYS`.

## Media and uploads

- Company logos live under `MEDIA_ROOT`.
- Invoice attachments live under `MEDIA_ROOT/invoices/<year>/`.
- Django serves `MEDIA_ROOT` only in development through the static handler.
- In production, serve logos from your web server or object storage.
- Keep invoice attachments private, or use private object storage with signed
  URLs. They are downloaded through the authenticated API, but a publicly served
  `MEDIA_ROOT` would expose the files by URL.
- There is no virus scan or image/PDF content inspection beyond extension,
  content-type and size checks.

## Django admin

Only `admin@hrms.test` is staff and superuser. Use `/admin/` for:

- company profile and logo
- teams
- leave types and holidays
- read-only payroll/invoice inspection

The financial rows are written by services so snapshots, totals and audit rows
stay consistent; the admin is intentionally read-only for them.

## Deployment checklist

1. Set a real `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, allowed hosts and CSRF
   trusted origins.
2. Point `DATABASE_URL` at PostgreSQL and run `migrate`.
3. Run `collectstatic` and serve `STATIC_ROOT`.
4. Serve `MEDIA_ROOT` for logos; keep invoice uploads private.
5. Configure Gmail OAuth values and set `INVOICE_EMAIL_FALLBACK=False`.
6. Run the reminder command from cron or a scheduler.
7. Back up the database and the invoice upload directory.
8. Put the app behind HTTPS.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `DisallowedHost` | Add the host to `DJANGO_ALLOWED_HOSTS` |
| 403 on POST login | Fetch `/api/v1/auth/csrf/` first and send `X-CSRFToken` |
| Postgres "no tables" | Run `python manage.py migrate` |
| PDF 406 “Accept header” | Fixed by `apps/core/negotiation.py`; make sure the backend reloaded |
| Invoice send says email not configured | Set Gmail OAuth values or enable the dev fallback |
| Invoice email printed in terminal | Gmail is not configured in dev; fallback is active |
| Test database cannot be created | The Postgres role needs `CREATEDB` |
| Uploaded invoice file 404 | The file is missing from storage or `MEDIA_ROOT` changed |

## Data notes

- `LeaveRequest.reviewed_at` was added in Phase 4. Requests approved or rejected
  before that migration have no decision timestamp and therefore do not appear in
  the employee dashboard's "Recent decisions" list.
- `seed_demo` resets the demo accounts' passwords and demo employees' profile
  fields on every run so the documented logins keep working. It never deletes a
  row and never touches non-demo accounts.
- Invoice numbering is per issue year and never reused: the
  `InvoiceNumberSequence` row is locked while a number is allocated. A rollback
  rolls the number back with the invoice.
- Tax is a single invoice-level percentage (for example 18% GST) applied after
  discount. There is no per-line tax rate, withholding, multi-currency FX or
  e-invoicing integration; currency is a label on the document and totals.
- Payroll and invoice PDFs are generated on demand and not stored. The database
  rows and snapshots remain the source of truth.

---

[← Previous: Testing](../08-testing/README.md) · [Documentation index](../README.md) · **Next: [10 · Limitations →](../10-limitations/README.md)**
