## Setup
These setup steps assume the application is being deployed to an ubuntu VM.
### Configure Deploy User
```shell
# Step 1: ssh to VM
# Step 2: Crate the user (skipping password and user details)
sudo adduser --disabled-password --gecos "" gym-journal-deploy
# Step 3: (from dev machine) Generate an ssh key
ssh-keygen -t ed25519 -C "gym-journal-github-actions" -f gym-journal-deploy-key -N ""
# Step 4: Add ssh key to deploy user
sudo mkdir -p /home/gym-journal-deploy/.ssh
sudo chmod 700 /home/gym-journal-deploy/.ssh
sudo nano /home/gym-journal-deploy/.ssh/authorized_keys   # paste the .pub contents
sudo chmod 600 /home/gym-journal-deploy/.ssh/authorized_keys
sudo chown -R gym-journal-deploy:gym-journal-deploy /home/gym-journal-deploy/.ssh
# Step 5: Test ssh key
# note: arg after -i is the path to the ssh key
ssh -i gym-journal-deploy gym-journal-deploy@YOUR_DROPLET_IP
# Step 6: Give deploy user access to app directory
sudo chown -R gym-journal-deploy:gym-journal-deploy /path/to/gym-journal
sudo chmod 600 /path/to/gym-journal/.env

# Step 7: Give deploy user limited sudo access
sudo visudo -f /etc/sudoers.d/deploy-gym-journal # add sudo file for deploy user
# Paste - gym-journal-deploy ALL=(root) NOPASSWD: /bin/systemctl restart gym-journal, /bin/systemctl status gym-journal
sudo chmod 440 /etc/sudoers.d/deploy-gym-journal

# Step 8: ssh as deploy user and set up git access
cd /path/to/gym-journal
git status
git pull --ff-only
uv sync
uv run python manage.py check --deploy --settings=config.production
```

### Setup Github
1. Add action secrets in github
  - DEPLOY_HOST
  - DEPLOY_USER
  - DEPLOY_SSH_KEY (full private key, including header/footer)
  - DEPLOY_PATH
2. Generate ssh key for deploy user (to pull from github)
```shell
ssh-keygen -t ed25519 -C "gym-journal-droplet-git" -f ~/.ssh/id_ed25519 -N ""
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
cat ~/.ssh/id_ed25519.pub
```
3. Add deploy user's .pub key to Github
  - In GitHub: repo → Settings → Deploy keys → Add deploy key → paste the .pub → read-only → save
4. Test the ssh key as the deploy user
```shell
git remote -v   # expect git@github.com:OWNER/gym-journal.git
ssh -T git@github.com
git pull --ff-only
```