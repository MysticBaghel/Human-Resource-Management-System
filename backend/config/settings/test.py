"""Settings used by pytest.

Tests run on in-memory SQLite so they need no database server. Phase 3 leave
tests that rely on the Postgres exclusion constraint must run against Postgres
and will be marked accordingly.
"""

from .base import *  # noqa: F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tests exercise the fallback path unless a test explicitly configures Gmail.
INVOICE_EMAIL_FALLBACK = True
GMAIL_CLIENT_ID = ""
GMAIL_CLIENT_SECRET = ""
GMAIL_REFRESH_TOKEN = ""
GMAIL_SENDER_EMAIL = ""
