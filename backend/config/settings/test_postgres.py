"""Test settings that run on PostgreSQL instead of the SQLite default.

The default suite runs on in-memory SQLite. This module points the same tests
at a real Postgres server so the btree_gist exclusion constraint is exercised:

    DATABASE_URL=postgres://user:password@localhost:5432/hrms \
        pytest --ds=config.settings.test_postgres

pytest-django creates and drops a separate ``test_<database>`` database, so the
development data is untouched.
"""

from .base import env
from .test import *  # noqa: F403

DATABASES = {"default": env.db("DATABASE_URL")}
