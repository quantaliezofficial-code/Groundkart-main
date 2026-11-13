# Deploying GroundKart (Hostinger VPS + Docker)

GroundKart is deployed the same way as Exotique: GitHub stores the code,
GitHub Actions connects to the VPS over SSH, the VPS keeps a rollback branch
and a database backup, rebuilds the containers, checks health, and rolls the
code back by itself if anything fails.

```text
Feature branch -> pull request (ci) -> merge to main
-> Build and test (ci.yml) -> SSH to the VPS
-> rollback branch + database backup -> docker compose up --build api web
-> health check -> automatic rollback if the build or health check fails
```

Ground rules (from the Exotique runbook, unchanged):

- **Never run `docker compose down -v`.** It deletes the database and uploads volumes.
- GitHub stores code. PostgreSQL stores bookings and accounts. Docker volumes store uploaded photos and owner documents. Never commit `.env`, uploads or database data.
- Secrets live in GitHub Actions secrets and in the server's `.env`, nowhere else.
- Back up the database before any migration. The deploy does this for you; a deploy that changes migrations stops if the backup fails.

## What runs where

```
Internet -> host nginx (TLS :443, shared with Exotique)
              -> 127.0.0.1:3002  web container (nginx + SPA)
                    /api, /uploads, /share, /sitemap.xml, /robots.txt -> api container (:8000)
                    everything else -> index.html
              api (also on 127.0.0.1:5001 for health checks) -> Postgres
```

| | Exotique | GroundKart |
|---|---|---|
| Folder | `/home/deploy/apps/exotique` | `/home/deploy/apps/groundkart` |
| Web | 127.0.0.1:3001 | 127.0.0.1:3002 (`WEB_PORT`) |
| API | 127.0.0.1:5000 | 127.0.0.1:5001 (`API_PORT`) |
| Health | `/api/health` | `/healthz` (API) and `/api/v1/health` (through web) |
| Compose project | exotique | `groundkart` (fixed in docker-compose.yml, so volume names never change) |

VPS: Hostinger KVM 1, ID 1877057, `srv1877057.hstgr.cloud`, 187.127.208.215.
Each API container runs one worker by default (`WEB_CONCURRENCY=1`), which suits the single vCPU.

Link-preview crawlers (WhatsApp, Facebook, LinkedIn, X, Slack, Telegram, Google) asking for `/venues/<slug>` or `/categories/<slug>` are routed to `/share/...`, which returns that venue's own Open Graph title, description, price and cover photo. People get the normal app.

## First-time setup

Do these once, in order. Commands run on the VPS as `root` unless marked **local**.

### 1. DNS

Point `groundkart.com` and `www.groundkart.com` (A records) at `187.127.208.215`, then check:

```bash
dig +short groundkart.com
dig +short www.groundkart.com
```

Both must print `187.127.208.215` before you request certificates. Use your real domain everywhere below if it is different.

### 2. Read-only deploy key so the VPS can pull the repository

```bash
mkdir -p /root/.ssh && chmod 700 /root/.ssh
ssh-keygen -t ed25519 -C "groundkart-vps-github-pull" -f /root/.ssh/groundkart_github_pull   # Enter twice
cat /root/.ssh/groundkart_github_pull.pub
```

GitHub: **Repository -> Settings -> Deploy keys -> Add deploy key**, title `GroundKart VPS pull key`, paste the `.pub` line, leave **Allow write access** off.

Append to `/root/.ssh/config` (keep the Exotique block that is already there):

```sshconfig
Host github.com-groundkart
    HostName github.com
    User git
    IdentityFile /root/.ssh/groundkart_github_pull
    IdentitiesOnly yes
```

```bash
chmod 600 /root/.ssh/config /root/.ssh/groundkart_github_pull
chmod 644 /root/.ssh/groundkart_github_pull.pub
ssh -T git@github.com-groundkart                      # "successfully authenticated ... no shell access" is correct
git ls-remote git@github.com-groundkart:YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git   # must list refs/heads/main
```

### 3. Clone and configure

```bash
mkdir -p /home/deploy/apps /home/deploy/backups/groundkart
cd /home/deploy/apps
git clone git@github.com-groundkart:YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git groundkart
cd groundkart
cp deploy/.env.production.example .env
nano .env          # fill every CHANGE value
chmod 600 .env
docker compose config -q && echo "compose OK"
```

Store `JWT_SECRET_KEY`, `FIELD_ENCRYPTION_KEY` and the database password in your password manager as well. **If `FIELD_ENCRYPTION_KEY` is lost, the encrypted ID and bank numbers cannot be recovered.**

### 4. Choose the database layout (`DB_MODE` in `.env`)

**A. Bundled (default, recommended to start).** GroundKart runs its own Postgres container with its own volume (`groundkart_pgdata`) and nightly dumps (`backup` service, 14 days). Nothing is shared with Exotique.

```bash
docker compose up -d db backup
```

**B. Shared, like Exotique.** An isolated database and user inside the VPS's existing PostgreSQL container. Find its container and network:

```bash
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i postgres
docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' <postgres-container>
```

Create the database and user (pick a long password):

```bash
docker exec -it <postgres-container> psql -U postgres -c "CREATE USER groundkart_user WITH PASSWORD 'CHANGE';"
docker exec -it <postgres-container> psql -U postgres -c "CREATE DATABASE groundkart_db OWNER groundkart_user;"
docker exec -it <postgres-container> psql -U postgres -c "REVOKE ALL ON DATABASE groundkart_db FROM PUBLIC;"
```

Then in `.env` set `DB_MODE=shared` and uncomment and fill `COMPOSE_FILE`, `DATABASE_URL` and the `SHARED_DB_*` lines. The bundled `db` and `backup` services are never started in this mode, so add a nightly backup to root's crontab (`crontab -e`):

```cron
30 2 * * * cd /home/deploy/apps/groundkart && sh deploy/hostinger/backup-db.sh nightly >> /var/log/groundkart-backup.log 2>&1
```

### 5. First start

```bash
cd /home/deploy/apps/groundkart
docker compose up -d --build --no-deps api web      # migrations run when the API starts
curl -fsS http://127.0.0.1:5001/healthz && echo
curl -fsS http://127.0.0.1:3002/api/v1/health && echo
docker compose ps
```

Never run `scripts/seed_dataset.py` here. Production refuses to start if demo rows or known development passwords are present.

### 6. Super admin and two-step sign-in

```bash
docker compose exec -e ADMIN_EMAIL=you@example.com -e ADMIN_PHONE=98XXXXXXXX -e ADMIN_NAME="Your Name" api python -m scripts.admin_setup
```

It prints a one-time password (unless `ADMIN_PASSWORD` is set) and asks you to change it at first sign-in. With `ADMIN_2FA_REQUIRED=true`, every admin must then enrol an authenticator app before the console opens. Keep the recovery codes it shows.

Then in the console: **Rules and fees** (commission, refund tiers, hold time) and **Settings -> Legal and business details** (legal name, CIN, address, Grievance Officer, jurisdiction; these fill the placeholders on the legal pages and footer).

### 7. Host nginx and HTTPS

The VPS already runs nginx for Exotique on 80/443. Add GroundKart beside it:

```bash
cp deploy/nginx-host.conf /etc/nginx/sites-available/groundkart
ln -s /etc/nginx/sites-available/groundkart /etc/nginx/sites-enabled/groundkart
# Comment out the two "listen 443" server blocks until the certificate exists, then:
nginx -t && systemctl reload nginx
certbot certonly --nginx -d groundkart.com -d www.groundkart.com
# Uncomment the 443 blocks:
nginx -t && systemctl reload nginx
curl -I https://groundkart.com
```

Do not touch the Exotique site file.

### 8. GitHub Actions access to the VPS

**Local** computer:

```bash
ssh-keygen -t ed25519 -C "github-actions-groundkart-vps" -f ~/.ssh/groundkart_github_actions   # Enter twice
cat ~/.ssh/groundkart_github_actions.pub
```

On the VPS, add that line to `/root/.ssh/authorized_keys` (`chmod 600`). Test from **local**: `ssh -i ~/.ssh/groundkart_github_actions root@srv1877057.hstgr.cloud`.

GitHub: **Settings -> Secrets and variables -> Actions -> New repository secret**:

| Secret | Value |
|---|---|
| `VPS_HOST` | `srv1877057.hstgr.cloud` |
| `VPS_USER` | `root` |
| `VPS_PORT` | `22` |
| `VPS_SSH_KEY` | full contents of `~/.ssh/groundkart_github_actions` (the private key, not `.pub`) |

The secret names are the same as Exotique's, but they are per repository, so the keys stay separate.

GitHub: **Settings -> Environments -> New environment** `production`. Optionally add yourself as a required reviewer so every production deploy waits for your approval.

### 9. Protect `main`

**Settings -> Branches -> Add branch protection rule** for `main`: require a pull request, require status checks (`backend`, `frontend`, `deploy-script`, `security-scan` from `ci`), require conversation resolution, block force pushes and deletion.

### 10. Test the pipeline

1. **Build only:** push a branch with a harmless README change and open a pull request. `ci` must pass.
2. **Manual deploy:** merge, then **Actions -> Deploy GroundKart -> Run workflow -> main**.
3. **Automatic deploy:** the next merge to `main` deploys by itself.

Before relying on it, run the rollback dry-run locally: `python3 deploy/hostinger/simulate_deploy.py` (no VPS needed; CI runs it too).

## Everyday changes

```bash
git checkout main && git pull --ff-only origin main
git checkout -b feature/my-change
# work, then: backend pytest, frontend npm test && npm run build
git push -u origin feature/my-change      # open a pull request into main
```

Merge when `ci` is green. The deploy then:

1. stops if the server has uncommitted edits (commit them to GitHub first);
2. records the running commit and creates `backup/production-YYYYMMDD-HHMMSS` at it (the newest 20 are kept);
3. pulls `main` with `--ff-only` and validates the compose file;
4. dumps the database to `/home/deploy/backups/groundkart/` and verifies the dump (10 kept);
5. rebuilds and restarts only `api` and `web` (`--no-deps`; the database container is never restarted);
6. waits up to 150 seconds for `/healthz`, `/api/v1/health` through the web container, and the home page, then runs `check_exposure.sh` (nothing private may answer over HTTP);
7. on any failure, checks out the previous commit and rebuilds it. If the release contained migrations, the log prints the exact restore command for the backup taken in step 4.

## Rollback by hand

If the site is broken and the workflow did not roll back:

```bash
cd /home/deploy/apps/groundkart
git branch --list 'backup/production-*'          # newest last
git checkout --detach backup/production-YYYYMMDD-HHMMSS
docker compose up -d --build --no-deps api web
docker compose ps
curl -fsS http://127.0.0.1:5001/healthz && echo
curl -I https://groundkart.com
```

The backup branches exist only on the VPS, so use the local name (no `origin/`). When the fix is merged, the next deploy returns the server to `main` by itself, or by hand:

```bash
git checkout main && git pull --ff-only origin main && docker compose up -d --build --no-deps api web
```

A code rollback does not undo a migration. If the old code cannot run on the new schema, restore the dump from before the deploy:

```bash
ls -lt /home/deploy/backups/groundkart/
sh deploy/hostinger/restore-db.sh /home/deploy/backups/groundkart/groundkart-predeploy-YYYYMMDD-HHMMSS.dump --yes
```

`restore-db.sh` saves the current state first (`groundkart-pre-restore-*.dump`), stops the API, restores, and starts it again. Bookings made between the deploy and the restore are in that pre-restore file, not in the restored database; re-enter them from it if needed.

## Database migrations

Migrations live in `backend/alembic/versions` and run when the API container starts.

1. Test the migration locally against a copy of production-like data.
2. Ship it in its own pull request, without unrelated changes.
3. The deploy takes and verifies a backup first; if the backup fails, the deploy stops before building.
4. After the deploy, check the admin console and one booking.
5. A migration that rewrites sensitive data (for example the encryption in `j2_encrypt_sensitive_fields`) also needs `backend/scripts/backup_before_migration.sh` run by hand first and the dump copied off the server.

## Nothing private by URL

The web container (`frontend/nginx.conf`) and the host nginx (`deploy/nginx-host.conf`) both refuse:

- hidden files and folders such as `/.env` and `/.git/` (only `/.well-known/` is allowed);
- source maps, configs, logs, database files, dumps, backups and archives (`.map`, `.env`, `.sql`, `.dump`, `.bak`, `.zip`…);
- server source paths (`/backend`, `/deploy`, `/docs`, `/scripts`, `/backups`, `/private-uploads`…);
- the API's interactive docs and schema (`/docs`, `/redoc`, `/openapi.json`), which are also switched off in the API itself in production (`EXPOSE_API_DOCS`).

Signed-in areas (`/admin`, `/owner`, `/broker`, `/account`, `/my-bookings`, guest booking links) are sent with `X-Robots-Tag: noindex` and `Cache-Control: no-store`; their data comes only from API calls that need a signed-in account with the right role. The production build has no source maps. Postgres has no published port, and the API and web ports listen on 127.0.0.1 only. The login refresh cookie is `HttpOnly`, `Secure` in production, `SameSite=Lax` and limited to `/api/v1/auth`. `.dockerignore` keeps `.env` files, dumps and `.git` out of the images.

Admin **Database studio** hides passwords, tokens, two-step secrets, ID and bank numbers and IP data in the table browser, CSV export and query results, and every view, export and query is written to the audit log. The free-form SQL console is off in production (`ADMIN_SQL_CONSOLE`).

Check a running site at any time (the deploy also runs this and rolls back if it fails):

```bash
sh deploy/hostinger/check_exposure.sh https://groundkart.com
sh deploy/hostinger/check_exposure.sh http://127.0.0.1:3002      # on the VPS
```

## Roles

| Role | Created by | Can |
|---|---|---|
| Super admin (one) | `scripts.admin_setup` | Everything, plus: add/suspend admins, set partner rates and status, regenerate partner codes, default partner rate |
| Admin | Super admin (Admin team) | Run the console: approvals, payments, refunds, payouts, partners (add, details, payouts), banners, records, rules |
| Referral partner | Admin or super admin | Own dashboard: code, referred venues, bookings, earnings, payouts, exports |
| Owner / customer | Self sign-up | As before |

New admins and partners get a one-time set-password link (24 hours). Nobody else sees their password. If it's lost: Referral partners → open the partner → *New sign-in link*; for an admin, Passwords.

To move the super admin role to another account:
`docker compose exec -e ADMIN_EMAIL=new@example.com -e ADMIN_PHONE=... -e ADMIN_SUPER=transfer api python -m scripts.admin_setup`

## Backups

| What | Where | Kept |
|---|---|---|
| Before every deploy | `/home/deploy/backups/groundkart/groundkart-predeploy-*.dump` | 10 newest |
| Nightly (bundled mode) | `backups` volume (`docker compose exec backup ls -lh /backups`) | 14 days |
| Nightly (shared mode) | cron job above, `groundkart-nightly-*.dump` | 10 newest |
| Uploaded photos and owner documents | `uploads` and `private_uploads` volumes, or object storage when `STORAGE_BACKEND=s3` | until deleted |

A backup on the same VPS does not survive losing the VPS. Copy dumps off the server regularly (Hostinger snapshots, or `rsync` to another machine), and back up the two upload volumes, for example:

```bash
docker run --rm -v groundkart_uploads:/u -v /home/deploy/backups/groundkart:/b alpine tar czf /b/uploads-$(date +%F).tgz -C /u .
docker run --rm -v groundkart_private_uploads:/u -v /home/deploy/backups/groundkart:/b alpine tar czf /b/private-uploads-$(date +%F).tgz -C /u .
```

The private-uploads archive holds owner identity documents: keep it encrypted at rest and delete old copies on the schedule in `docs/compliance/drafts/retention-schedule.md`.

## Verification checklist after a deploy

- [ ] `docker compose ps`: `api` healthy, `web` running, `db` running (bundled mode)
- [ ] `git log -1 --oneline` is the commit you merged
- [ ] `curl -fsS http://127.0.0.1:5001/healthz` returns `"status": "ok"`
- [ ] `curl -I https://groundkart.com` returns 200 with `strict-transport-security` and `content-security-policy` headers
- [ ] Home page loads with photos; no `DEMO DATA` bar at the bottom
- [ ] Admin sign-in asks for the authenticator code
- [ ] One venue page and the checkout price break-up open
- [ ] `/privacy`, `/terms`, `/refunds`, `/grievance` open, and the footer shows the legal details (no `OWNER TO FILL`)
- [ ] `sh deploy/hostinger/check_exposure.sh https://groundkart.com` ends with "All exposure checks passed."

## Images and speed

- Every photo and banner is decoded, stripped of metadata (including phone GPS), capped at 2000 px (banners 2400 px) and stored as WebP. Non-images are refused even if they claim an image type.
- Browsers shrink photos before uploading, so large phone photos upload quickly.
- Fonts are self-hosted; build output is fingerprinted and cached for a year; `index.html` is never cached, so a deploy is visible immediately.

## Health and logs

- `docker compose ps` — all services should be `healthy`/`running`.
- `docker compose logs -f api` — application logs.
- `GET /healthz` — API and database check.
