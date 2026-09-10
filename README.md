# Gym Journal

A Django app for logging workouts, tracking sets, and managing an exercise library.

## Prerequisites

- Python 3.9+ (see `.python-version` for the version used locally)
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL (for local development)

## Setup

Install dependencies:

```bash
uv sync
```

Configure PostgreSQL connection via a [libpq service file](https://www.postgresql.org/docs/current/libpq-pgservice.html):

1. Copy the example service definition into your libpq config (typically `~/.pg_service.conf`):

   ```bash
   cp .pg_service.conf.example ~/.pg_service.conf
   ```

2. Create a `.my_pgpass` file in the project root with your database password:

   ```
   localhost:5432:gym_journal_development:gym_journal:YOUR_PASSWORD
   ```

   Restrict permissions so only you can read it:

   ```bash
   chmod 600 .my_pgpass
   ```

3. Create the PostgreSQL user and database (adjust as needed):

   ```sql
   CREATE USER gym_journal WITH PASSWORD 'YOUR_PASSWORD';
   CREATE DATABASE gym_journal_development OWNER gym_journal;
   ```

Apply migrations:

```bash
uv run python manage.py migrate
```

Seed muscle groups and starter exercises (safe to re-run):

```bash
uv run python manage.py seed_dev
```

Edit `src/gym_journal/seed_data.py` to add or change exercises.

## Running the app

Start the development server:

```bash
uv run python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser. Unauthenticated requests redirect to `/login/`.

Styles use the [Tailwind Play CDN](https://tailwindcss.com/docs/installation/play-cdn) with theme config in `base.html`. A small `base.css` covers form resets the CDN does not handle.

### Auth

There is no public signup. Provision users manually:

```bash
uv run python manage.py createsuperuser
```

Or create non-staff users in [Django admin](http://127.0.0.1:8000/admin/) after signing in as a superuser. Muscle and exercise data is shared; workouts and sets belong to the signed-in user.

### Django admin

Create a superuser (same command as above), then visit [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

### JSON API

Base path: `/api/v1/`. Authenticated requests send:

```http
Authorization: Token <your-token>
```

Obtain a token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "YOUR_USER", "password": "YOUR_PASSWORD"}'
```

## Tests

Install dev dependencies (pytest), then run the suite. Tests use in-memory SQLite and do not require PostgreSQL:

```bash
uv sync --group dev
uv run pytest
```

Run a single module or test:

```bash
uv run pytest src/gym_journal/tests/test_views.py
uv run pytest src/gym_journal/tests/test_views.py::IndexViewTests
```

Django’s runner still works if you prefer it:

```bash
uv run python manage.py test gym_journal --settings=config.test_settings
```

## Common commands

| Task | Command |
| --- | --- |
| Install / sync dependencies | `uv sync` |
| Apply migrations | `uv run python manage.py migrate` |
| Seed dev data | `uv run python manage.py seed_dev` |
| Create migrations after model changes | `uv run python manage.py makemigrations` |
| Run development server | `uv run python manage.py runserver` |
| Run tests | `uv sync --group dev` then `uv run pytest` |
| Django system checks | `uv run python manage.py check` |
| Open Django shell | `uv run python manage.py shell` |

## Deployment

Intended setup: nginx proxying to gunicorn server.

After the first manual install below, continuous deploys are handled by GitHub Actions (pytest, then SSH deploy on `main`). One-time CI setup (deploy user, secrets, GitHub deploy key) is in [DEPLOY.md](DEPLOY.md).

### 1. Copy the app

Install Python, [uv](https://docs.astral.sh/uv/), ensure nginx is running, and have postgres connection params ready. Clone the repository on to the box, then delete non-essential files (`**/tests/`).

Next, install dependencies into a local `.venv`:

```bash
uv sync
```

Create `.env` on the droplet (see below).

### 2. Environment (`.env`)

Production settings live in `config.production` and read secrets from a project-root `.env` file (not committed). Copy the example and fill in values:

```bash
cp .env.example .env
chmod 600 .env
```

| Key | Required | Example |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | yes | output of `uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_ALLOWED_HOSTS` | yes | `gym.example.com` |
| `DATABASE_URL` | yes | `postgres://user:pass@127.0.0.1:5432/gym_journal` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | `https://gym.example.com` (defaults to `https://` + each allowed host) |

`.env` is loaded from this app's directory and overrides inherited environment variables, so another Django app on the same box can have its own file.

Create a Postgres user/database that match `DATABASE_URL`. Keep Postgres listening on localhost only.

The process still needs `DJANGO_SETTINGS_MODULE=config.production` (in the systemd unit). That is not a secret.

### 3. Migrate, static files, checks

```bash
uv run python manage.py migrate --settings=config.production
uv run python manage.py collectstatic --noinput --settings=config.production
uv run python manage.py check --deploy --settings=config.production
uv run python manage.py createsuperuser --settings=config.production   # optional, for /admin/
uv run python manage.py seed_dev --settings=config.production          # optional starter data
```

With `DEBUG = False`, Django does not serve CSS/JS. After `collectstatic`, point nginx at `STATIC_ROOT` (`staticfiles/` in the project root) for `/static/`.

### 4. Gunicorn

Gunicorn is a Python dependency in this project (`uv sync` installs it). The Django project package `config/` lives at the repo root (not inside the installed `gym_journal` package), so gunicorn must run with that directory on `PYTHONPATH`. Use `--chdir` to the project root (where `manage.py` and `config/` live) so `.env` loads and imports succeed:

```bash
DJANGO_SETTINGS_MODULE=config.production \
  uv run gunicorn config.wsgi:application \
  --chdir /path/to/gym-journal \
  --bind 127.0.0.1:8000 \
  --workers 2
```

Example systemd unit (`/etc/systemd/system/gym-journal.service`):

```ini
[Unit]
Description=Gym Journal (Gunicorn)
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/gym-journal
Environment=DJANGO_SETTINGS_MODULE=config.production
ExecStart=/path/to/gym-journal/.venv/bin/gunicorn config.wsgi:application --chdir /path/to/gym-journal --bind 127.0.0.1:8000 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Adjust `User`, `WorkingDirectory`, `--chdir`, and `ExecStart` paths to match your deploy directory (the folder that contains `manage.py` and `config/`). If gunicorn fails with `ModuleNotFoundError: No module named 'config'`, the `--chdir` path is wrong or `config/` is missing on the server.

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gym-journal
```

### 5. nginx

Terminate TLS in nginx (e.g. certbot) and reverse-proxy to Gunicorn. Production settings expect HTTPS and read `X-Forwarded-Proto`.

```nginx
server {
    listen 443 ssl http2;
    server_name gym.example.com;

    # ssl_certificate / ssl_certificate_key managed by certbot

    location /static/ {
        alias /path/to/gym-journal/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Firewall: allow 80/443 publicly; keep Postgres and Gunicorn on localhost.

### 6. Continuous deploy (GitHub Actions)

[.github/workflows/deploy.yml](.github/workflows/deploy.yml) runs **pytest** on pushes and PRs to `main`. On push to `main` (or a manual workflow run), if tests pass it SSHs to the droplet and runs:

```bash
git pull --ff-only
uv sync
uv run python manage.py migrate --settings=config.production
uv run python manage.py collectstatic --noinput --settings=config.production
# SENTRY_RELEASE is updated automatically by CI; set manually if deploying by hand
sudo systemctl restart gym-journal
```

Required Actions secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`, `HEALTH_CHECK_HOST`. See [DEPLOY.md](DEPLOY.md).

After each deploy, GitHub Actions smoke-tests `GET /health/` on the public hostname.

## Observability

### Health check

`GET /health/` returns `200 {"status":"ok"}` when Postgres is reachable, or `503 {"status":"unavailable"}` otherwise. No authentication required.

### Sentry

Set `SENTRY_DSN` in production `.env`. Deploys write the current git commit SHA to `SENTRY_RELEASE` so errors group by release.

In Sentry project settings, configure alerts:

- **New issue** → email or Slack immediately
- **Issue frequency spike** → optional, after you have baseline traffic

### Uptime monitoring

Use an external uptime service (e.g. [Better Stack Uptime](https://betterstack.com/uptime)) to monitor production:

- URL: `https://<your-domain>/health/`
- Interval: every 1–5 minutes
- Alert on 2+ consecutive failures

This catches outages that are not tied to a deploy (droplet down, Gunicorn crash, database unavailable).

### Notes

- Styles load Tailwind from a CDN; only `base.css` and JS need `collectstatic` + the `/static/` alias.
