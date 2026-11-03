# TechWatch deployment

The public preview runs on the existing EC2 host at `techwatch.zivantaai.com`.
`compose.prod.yaml` keeps PostgreSQL and the worker on TechWatch's private
network. Only the API joins the host's existing Caddy network. No TechWatch
container publishes a host port.

## Server configuration

Clone this repository to `/opt/techwatch`. Create `/opt/techwatch/.env` with
mode `0600` and values for `POSTGRES_PASSWORD` and `ADMIN_TOKEN`; use separate
long random values, and keep the file out of Git. Set `OFFLINE_MODE=0` for live
source polling. The production Compose file rejects missing secrets.

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
```

Create an A record for `techwatch.zivantaai.com` that points to the instance's
public IP before expecting HTTPS. The instance currently has an automatically
assigned public IP, so a stop/start can change it. Caddy obtains and renews
the TLS certificate once DNS is correct and ports 80/443 are reachable.

## Checks and rollback

Verify `/health`, `/v1/catalog`, the homepage and onboarding over HTTPS. Check
`docker compose -f compose.prod.yaml logs --tail=100 worker` and the app's
Settings → Source health page. Keep the Caddyfile backup until the new route is
confirmed. To withdraw only TechWatch, remove its Caddy block and reload
Caddy; then run `docker compose -f compose.prod.yaml stop`. Do not run `down -v`:
that would delete the PostgreSQL volume.

Back up PostgreSQL off the instance and test a restore before relying on any
user data. This public preview has guest preferences rather than user accounts.
