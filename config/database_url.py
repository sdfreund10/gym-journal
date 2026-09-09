"""Parse DATABASE_URL into a Django DATABASES entry."""

import os
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


def database_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql", "pgsql"}:
        raise ImproperlyConfigured("DATABASE_URL must be a postgres URL.")

    options = {}
    sslmode = parse_qs(parsed.query).get("sslmode", [None])[0]
    if sslmode:
        options["sslmode"] = sslmode

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": int(os.environ.get("DJANGO_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": options,
    }
