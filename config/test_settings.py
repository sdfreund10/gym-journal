"""Settings used by the test suite.

Uses an in-memory SQLite database so tests do not require PostgreSQL.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
