"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True

# Invite links and password-reset mails are printed to the console in dev.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "hrms@localhost"

# Without Gmail OAuth credentials, invoice emails are printed by the console
# backend rather than failing. Configure the GMAIL_* values to use the real
# Gmail API path in development too.
INVOICE_EMAIL_FALLBACK = True

# The Vite dev server proxies /api, so requests reach Django from either origin.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *CSRF_TRUSTED_ORIGINS,  # noqa: F405
]

# Postgres is required by the stop-time exclusion constraint added in Phase 3.
# Until then SQLite is fine locally, but never use it for those tests.
