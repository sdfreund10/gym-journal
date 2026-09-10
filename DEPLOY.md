# Automated deploy setup

One-time steps so GitHub Actions can SSH into an Ubuntu VM, pull, and restart the app.
Manual app install (nginx, gunicorn, `.env`, Postgres) is covered in [README.md](README.md#deployment).

## 1. Deploy user on the droplet

```shell
# Step 1: ssh to the VM as an admin user
# Step 2: create the deploy user (no password; SSH keys only)
sudo adduser --disabled-password --gecos "" gym-journal-deploy

# Step 3: (on your laptop) generate the CI → droplet SSH key
ssh-keygen -t ed25519 -C "gym-journal-github-actions" -f gym-journal-deploy-key -N ""

# Step 4: install the public key on the droplet
sudo mkdir -p /home/gym-journal-deploy/.ssh
sudo chmod 700 /home/gym-journal-deploy/.ssh
sudo nano /home/gym-journal-deploy/.ssh/authorized_keys   # paste gym-journal-deploy-key.pub
sudo chmod 600 /home/gym-journal-deploy/.ssh/authorized_keys
sudo chown -R gym-journal-deploy:gym-journal-deploy /home/gym-journal-deploy/.ssh

# Step 5: test SSH from your laptop (-i is the private key path)
ssh -i gym-journal-deploy-key gym-journal-deploy@YOUR_DROPLET_IP

# Step 6: give deploy user ownership of the app directory
sudo chown -R gym-journal-deploy:gym-journal-deploy /path/to/gym-journal
sudo chmod 600 /path/to/gym-journal/.env

# Step 7: limited passwordless sudo for restart only
sudo visudo -f /etc/sudoers.d/deploy-gym-journal
# add this line:
# gym-journal-deploy ALL=(root) NOPASSWD: /bin/systemctl restart gym-journal, /bin/systemctl status gym-journal
sudo chmod 440 /etc/sudoers.d/deploy-gym-journal
```

## 2. Droplet → GitHub (so `git pull` works without prompts)

This is a **second** key pair. Do not reuse the CI → droplet key.

As `gym-journal-deploy` on the droplet:

```shell
ssh-keygen -t ed25519 -C "gym-journal-droplet-git" -f ~/.ssh/id_ed25519 -N ""
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
cat ~/.ssh/id_ed25519.pub
```

In GitHub: repo → **Settings → Deploy keys → Add deploy key** → paste the `.pub` → leave write access off → save.

Then verify:

```shell
cd /path/to/gym-journal
git remote -v   # expect git@github.com:OWNER/gym-journal.git
# if https://..., switch:
# git remote set-url origin git@github.com:OWNER/gym-journal.git
ssh -T git@github.com
git pull --ff-only
uv sync
uv run python manage.py check --deploy --settings=config.production
```

## 3. GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions** → New repository secret:

| Secret | Corresponds to |
| --- | --- |
| `DEPLOY_HOST` | Droplet IP or hostname Actions SSHs to |
| `DEPLOY_USER` | Linux user on the droplet (`gym-journal-deploy`) |
| `DEPLOY_SSH_KEY` | Full private key from `gym-journal-deploy-key` (including `BEGIN`/`END` lines) |
| `DEPLOY_PATH` | Absolute path to the app on the droplet (directory with `manage.py`) |
| `HEALTH_CHECK_HOST` | Public hostname only (e.g. `gym.example.com`) — used for post-deploy `curl https://…/health/` |

Optional: if SSH is not on port 22, add a `port:` input to the deploy step in `.github/workflows/deploy.yml`.

Production `.env` values stay on the droplet. The droplet → GitHub key stays on the droplet; only its public half goes under **Deploy keys**, not Actions secrets.

## 4. CI behavior

After [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) is on `main`:

- Pushes and PRs to `main` run **pytest**.
- On push to `main` (or manual **workflow_dispatch**), if tests pass, Actions SSHs in and runs `git pull --ff-only`, `uv sync`, migrate, collectstatic, updates `SENTRY_RELEASE` in `.env`, and `systemctl restart gym-journal`.
- After restart, Actions curls `https://<HEALTH_CHECK_HOST>/health/` (with retries). The deploy job fails if the app does not return `{"status":"ok"}`.
