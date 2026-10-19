"""Production settings.

Hardening (HTTPS cookies, HSTS, login throttling) is Phase 4 work; this file
only makes the safe choices that must not be forgotten.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

if SECRET_KEY.startswith("unsafe-dev-key"):  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
