# Deploying GroundKart (Hostinger VPS + Docker)

## What runs where

```
Internet ── host nginx (TLS, :443) ── web container (nginx + SPA, :8080)
                                          ├── /api, /uploads, /share, /sitemap.xml, /robots.txt ──> api container (:8000)
                                          └── everything else ──> index.html
                                       api ──> db (Postgres 16)   backup ──> nightly pg_dump, kept 14 days
```

Link-preview crawlers (WhatsApp, Facebook, LinkedIn, X, Slack, Telegram, Google) asking for `/venues/<slug>` or `/categories/<slug>` are routed to `/share/...`, which returns that venue's own Open Graph title, description, price and cover photo. People get the normal app.

## First deploy

1. On the VPS (Ubuntu 22.04/24.04): install Docker Engine and the compose plugin, nginx and certbot.
2. `git clone <repo> /opt/groundkart && cd /opt/groundkart`
3. `cp deploy/.env.production.example .env` and fill in every `CHANGE` value. Generate secrets with
   `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.
4. `docker compose up -d --build`
5. Create the super admin (the first admin created becomes the single super admin):
   ```
   docker compose exec -e ADMIN_EMAIL=you@example.com -e ADMIN_PHONE=98XXXXXXXX -e ADMIN_NAME="Your Name" api python -m scripts.admin_setup
   ```
   It prints a one-time password if `ADMIN_PASSWORD` is not set; you'll be asked to change it.
6. Host TLS: copy `deploy/nginx-host.conf` to `/etc/nginx/sites-available/groundkart`, link it into `sites-enabled`, run `sudo certbot --nginx -d groundkart.com -d www.groundkart.com`, then `sudo nginx -t && sudo systemctl reload nginx`.
7. Open `https://groundkart.com/admin`, sign in, and go to **Rules and fees** to confirm commission and refund settings.

## Automatic deploys from GitHub

`.github/workflows/deploy.yml` deploys `main` after the `ci` workflow passes (or on manual run). Add repository secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`. Each deploy takes a database dump first (last five kept in the checkout), rebuilds, restarts, and fails loudly if the API isn't healthy within two minutes.

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

## Backups and restore

Nightly dumps land in the `backups` volume:
```
docker compose exec backup ls -lh /backups
docker compose cp backup:/backups/groundkart-YYYYMMDD-HHMM.dump ./restore.dump
docker compose exec -T db pg_restore -U groundkart -d groundkart --clean --if-exists < restore.dump
```
Copy dumps off the server regularly (Hostinger snapshot, or rsync to another machine). Uploaded photos live in the `uploads` volume, or in object storage if `STORAGE_BACKEND=s3`.

## Images and speed

- Every photo and banner is decoded, stripped of metadata (including phone GPS), capped at 2000 px (banners 2400 px) and stored as WebP. Non-images are refused even if they claim an image type.
- Browsers shrink photos before uploading, so large phone photos upload quickly.
- Fonts are self-hosted; build output is fingerprinted and cached for a year; `index.html` is never cached, so a deploy is visible immediately.

## Health and logs

- `docker compose ps` — all services should be `healthy`/`running`.
- `docker compose logs -f api` — application logs.
- `GET /healthz` — API and database check.
