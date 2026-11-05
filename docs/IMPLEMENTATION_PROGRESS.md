# Backend implementation progress

## Decisions

- Product and UI: TechWatch; preserve the existing approved web experience.
- API and workers: Python + FastAPI, separate processes.
- Source-to-feed paths: Python releases plus curated official RSS/Atom feeds.
- Durable jobs: PostgreSQL job table for the initial scale. Redis is deferred until there is a measured need.
- AI, accounts and push: disabled in the first live-source milestone. Guest preferences remain supported.

## Current state

- The FastAPI demo, PostgreSQL preferences/bookmarks and four fictional cards work in Docker Compose.
- A separate worker schedules and processes durable database jobs. Its recorded Python release fixture passes discovery, parsing, revision and evidence storage, brief generation and publication.
- The guarded Python.org adapter can fetch official releases; that source is disabled by default. The [source registry](SOURCE_REGISTRY.md) lists 43 official sources across cloud providers, languages, frameworks, security, and infrastructure. Forty-two are enabled by default; Docker is disabled because TLS responses were intermittent here. Node.js, Anthropic and Kafka adapters fetch linked articles, and GitHub reviewed advisories provide structured package and patched-version evidence.
- The worker fetches each feed hourly with conditional requests, keeps bounded response bodies, strips feed HTML, rejects off-host links, deduplicates by canonical URL and same-day normalized title, classifies and scores items, and creates drafts with feed excerpts as evidence. Scores prioritize security, breaking changes, releases and recency; editorial review decides what is actually important.
- Every real item requires review before publication. The local review CLI and token-protected admin endpoints can show evidence, edit, publish or reject drafts; decisions are audited. The expanded editorial pass published 31 live briefings across 27 technologies; remaining feed entries are held for review.
- `backend/editorial_updates_20261105_new_sources.json` contains five source-checked briefings from the added Node.js, Anthropic, FastAPI, Terraform and GitHub advisory connectors. Apply it with `python -m backend.apply_editorial_updates backend/editorial_updates_20261105_new_sources.json` after those connectors have ingested their matching source records. The command validates source identity, copy limits and review status, then records edit and publication in the audit table.
- The feed API now returns up to 100 items with a next cursor, and the normal app view hides fictional fixtures whenever reviewed live items exist. This is still curated coverage, not a guarantee of every major story. Accounts, installed-version matching, article-level fact extraction, AI rewriting and push notifications remain to be built. Node.js feed items have no descriptions; the article adapter now extracts source text for review. Service incident monitoring remains separate and is not yet implemented.
- Settings → Source health shows each official source's current status, last successful check, and latest fetch error. `GET /v1/source-health` returns the same source-level states and a summary. A source is stale after more than two polling intervals plus five minutes without success; offline mode is shown as paused, and Docker remains disabled. Fetch failures are recorded separately from briefing-generation failures.
- The Health bottom tab uses `GET /v1/service-health` to display incidents from 14 official public status sources. Eleven use Statuspage-compatible JSON; AWS uses its public current-events JSON, Google Cloud its public incidents JSON, and Azure its public RSS feed. The API bounds requests, caches snapshots for three minutes, excludes stale Statuspage monitoring posts when the provider reports operational, and marks failed checks explicitly. Azure public RSS covers broad events and AWS/Google public status may omit account-specific impact. The badge counts provider-reported active issues; this feature is separate from collector Source health and from the editorial news feed.

## Acceptance gate for the first milestone

- A recorded Python release passes fetch/parse/revision/evidence/brief/review/feed with deterministic tests.
- Duplicate and unchanged source fetches do not produce duplicate cards.
- Real source publication requires authorized review.
- A failed source never creates a fabricated release.
- Compose starts the API and worker; the existing UI still runs.

## Run and inspect

Run `docker compose up --build -d`, then open `http://localhost:8000/`. The worker and API are separate services. `docker compose ps` shows their health and `docker compose logs -f worker` shows processing. Run `.venv/bin/python -m pytest -q` for the local test suite.

Set `OFFLINE_MODE=1` in Compose to stop live collection during offline development. The app can still show recorded fixture cards on a fresh database, and already-reviewed cards remain available from storage.

Review drafts locally with `docker compose exec api python -m backend.review_cli queue` and inspect full evidence with `docker compose exec api python -m backend.review_cli show ID`. Use `docker compose exec api python -m backend.review_cli edit ID --summary '...'` to fit the one-screen card budget, then `docker compose exec api python -m backend.review_cli publish ID` or `reject ID`. Check each entry's `source_url` and retained evidence before publishing; the queue is a draft list, not a verified claim of impact. Review changes appear in the app when the feed refreshes.

The four tabs now have separate selection rules in `backend/feed_selection.py`. Feed selects reviewed items matching explicitly chosen topics or followed technologies; if neither is chosen, role interests guide it, and a completely skipped setup receives a general feed. Your Stack matches followed technologies exactly. Trending draws from all reviewed items and selects security advisories, breaking changes, and significant releases, with freshness and source diversity in its order. Alert signal choices can raise matching stories in Trending; no view counts or popularity are fabricated. AI retains its subject filter. A story may appear in more than one tab when both rules genuinely apply.

Cards use an Editorial stack transition in both web and Flutter: the current full-screen briefing follows a vertical drag and lifts over the next card, then settles to one complete card. A short or cancelled drag returns to the current card. The web respects the saved Reduce motion choice and the operating-system preference; Flutter respects the saved choice and the platform accessibility setting. Buttons, wheel/keyboard paging on web, and list mode remain available.

The image carries a prominent Impact & actions button. It opens a sheet with Why it matters, What to check, and source context, leaving the card body for a longer summary. Editorial copy now targets roughly 400–500 characters where the official source supports that depth, with a 510-character hard limit; a sparse source may warrant a shorter, honest briefing. The fictional development fixtures demonstrate the expanded format without claiming a live event.

The UI creates an installation ID for guest preferences. API calls to `/v1/feed` must include a valid UUID in `X-Installation-ID`. Set a private `ADMIN_TOKEN` in the environment to use `/admin/*` endpoints; do not put that token into the browser client.
