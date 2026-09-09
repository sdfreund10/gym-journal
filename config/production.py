"""Production settings.

Select with DJANGO_SETTINGS_MODULE=config.production.

Secrets and host config are read from the project-root `.env` file so
multiple Django apps on one machine do not share process environment.

Required keys:
    DJANGO_SECRET_KEY
    DJANGO_ALLOWED_HOSTS   comma-separated hostnames
    DATABASE_URL           postgres://user:pass@host:5432/dbname

Optional:
    DJANGO_CSRF_TRUSTED_ORIGINS   comma-separated origins, e.g. https://example.com
    DJANGO_CORS_ALLOWED_ORIGINS   comma-separated origins for the mobile/web API
    DJANGO_CONN_MAX_AGE           persistent DB connections, default 60
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from .database_url import database_from_url
from .settings import *  # noqa: F403

DEBUG = False


def _csv_env(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set.")

ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set.")

CSRF_TRUSTED_ORIGINS = _csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        f"https://{host.lstrip('.')}"
        for host in ALLOWED_HOSTS
        if host not in {"*", "localhost", "127.0.0.1"}
    ]

CORS_ALLOWED_ORIGINS = _csv_env("DJANGO_CORS_ALLOWED_ORIGINS")

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ImproperlyConfigured("DATABASE_URL must be set.")
DATABASES = {"default": database_from_url(database_url)}

STATIC_ROOT = BASE_DIR / "staticfiles"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
