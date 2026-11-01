"""Production settings."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

if SECRET_KEY.startswith("unsafe-dev-key"):  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# CORS: allow the deployed React frontend.
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# HTTPS behind Render's reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Production email must not silently fall back to console.
INVOICE_EMAIL_FALLBACK = False