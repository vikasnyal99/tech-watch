# TechWatch deployment

TechWatch runs on the existing EC2 host at
`https://techwatch.zivantaai.com/`. The hostname has an A record and a
publicly trusted HTTPS certificate. Use this URL for web and Android builds.
`compose.prod.yaml` keeps PostgreSQL and the worker on TechWatch's private
network. Only the API joins the host's existing Caddy network. No TechWatch
container publishes a host port.

## Server configuration

Clone this repository to `/opt/techwatch`. Create `/opt/techwatch/.env` with
mode `0600` and values for `POSTGRES_PASSWORD` and `ADMIN_TOKEN`; use separate
long random values, and keep the file out of Git. Set `OFFLINE_MODE=0` for live
source polling. The production Compose file rejects missing secrets.

For AI-assisted drafts, store a TechWatch project service-account key as
`OPENAI_API_KEY` in this server-side `.env` file. Do not put the key in Git,
the mobile app, or a message. Saving the key does not activate calls:
`AI_ENABLED` defaults to `0`. Once the separate project spending limit is
configured, set `AI_ENABLED=1` and recreate only the worker. The worker uses
`gpt-6-luna`; it has its own fixed $5 monthly budget, daily call limits, and
source eligibility checks. Run `docker compose -f compose.prod.yaml exec -T
worker python -m backend.review_cli ai-usage` to see usage without printing the
key. Provider billing is authoritative; the app ledger conservatively counts
unknown-usage failures at its request reservation ceiling.

Run:

```sh
cd /opt/techwatch
docker compose -f compose.prod.yaml config --quiet
docker compose -f compose.prod.yaml up --build -d
docker compose -f compose.prod.yaml ps
docker compose -f compose.prod.yaml exec api python -m backend.review_cli queue
```

The worker discovers official feed items but does not publish unreviewed items.
On a new database, the UI shows clearly marked fictional examples until an
editor publishes real briefings. See `docs/IMPLEMENTATION_PROGRESS.md` for the
review commands and limitations.

## Caddy and DNS

Attach the API to the existing external Docker network
`monitoring-service_default` (already configured in the production Compose
file). Add this site block to the server's Caddyfile and validate before reload:

```caddyfile
techwatch.zivantaai.com {
  encode gzip
  @private path /admin/* /docs /redoc /openapi.json
  respond @private 404
  reverse_proxy techwatch-api:8000
}

http://65.1.226.15 {
  redir https://techwatch.zivantaai.com{uri} permanent
}
```

Keep the A record for `techwatch.zivantaai.com` pointed at the instance's
public IP. The instance currently has an automatically assigned public IP,
so a stop/start can change it; update DNS or assign an Elastic IP before
relying on the hostname long term. Caddy obtains and renews the TLS certificate
while DNS and ports 80/443 remain correct. The old IP preview no longer serves
the app directly; its HTTP route redirects to the HTTPS hostname.

## Checks and rollback

Verify `/health`, `/v1/catalog`, the homepage and onboarding over HTTPS. Check
`docker compose -f compose.prod.yaml logs --tail=100 worker` and the app's
Settings → Source health page. Keep the Caddyfile backup until the new route is
confirmed. To withdraw only TechWatch, remove its Caddy block and reload
Caddy; then run `docker compose -f compose.prod.yaml stop`. Do not run `down -v`:
that would delete the PostgreSQL volume.

Back up PostgreSQL off the instance and test a restore before relying on any
user data. This public preview has guest preferences rather than user accounts.
The server installs `deploy/techwatch-backup.timer`, which runs a daily
`pg_dump` to the existing private S3 deployment bucket under
`techwatch/backups/`. Backups in that prefix expire after 30 days. Check
`systemctl status techwatch-backup.timer` and periodically restore a dump to
a disposable database to verify it.
