# Architecture, data and operations

## Practical architecture
Modular monolith API (Python/FastAPI), PostgreSQL, scheduled collectors and processing workers, queue table using transactional claims or a proven Postgres-backed job library, optional S3-compatible object storage, small admin web app, mobile Flutter baseline, all containerized via Compose for local/deployment. Choose compatible versions after verifying current official docs. Mobile choice is provisional until existing project/team constraints are inspected. Split components only when volume or operational isolation warrants it. No local GPU requirement is assumed. API model provider and budget are undecided for this project; support an offline deterministic development adapter and a server-side configurable model provider. Never hardcode credentials or log sensitive content.

## Logical data model
- `sources`: policy, connector settings, scheduling, health, cursor, access rules.
- `source_items`, `source_revisions`: stable source identifiers, URLs, permitted content, timestamps, hashes and provenance.
- `technologies`, `technology_aliases`, `topics`, `event_technologies`: stable canonical IDs; ecosystem-aware ambiguity resolution.
- `events`, `event_sources`, `event_revisions`, `evidence`: normalized event, distinct source links, immutable facts/brief versions, status, confidence and reviewer actions.
- `users` or anonymous installation identity, `preferences`, `follows`, optional `followed_versions`, role, settings; avoid storing more than needed.
- `bookmarks`, `feed_positions`, `reading_state`, `notification_preferences`, `notifications`.
- `jobs`, `job_attempts`, `audit_events`, `source_health`; uniqueness/idempotency keys and transactional state transitions.

Design DB migrations, timestamps UTC, unique constraints for source+external ID, appropriate indexes, encrypted TLS transport, backups and a tested restore process. Store per-user identifiers and stack preferences with access control and retention policy; no public production admin. Follow optional sync only when account support implemented; initial guest data can be local with documented limits.

## API contract (proposed; validate during implementation)
`GET /v1/feed?section=feed|stack|trending|ai&mode=cards|list&topic=&cursor=` returns ordered canonical events and cursor. `GET /v1/events/{id}` returns card, status, source attribution, evidence and version. `GET /v1/search?q=&kind=`. `GET/PUT /v1/preferences`, `GET/POST/DELETE /v1/follows`, `GET/POST/DELETE /v1/bookmarks`, `PUT /v1/reading-position`, `GET/PUT /v1/notification-preferences`. Use a consistent mode-independent feed identity and stable cursor snapshot. No user-specific identity inferred from device without explicit policy. Admin endpoints are separate, authenticated and authorized: source CRUD/health, candidates, review/publish/reject/correct, job replay and audit. For initial offline demo, implement documented fixture-backed responses; do not pretend APIs or real-time feeds exist.

## Suggested components
`api` handles feed/preferences/admin; `scheduler` leases due sources; `collectors` use per-source policy and bounded requests; `processor` does normalizing/grouping/extraction/validation; `review` gates publication; `notification-worker` schedules and deduplicates opt-in pushes; admin UI reviews evidence. Postgres is source of truth. Jobs claim atomically, handle lease expiration, have idempotent writes, exponential backoff, bounded retries and dead-letter view. Use explicit UTC schedules and injected clock for tests.

## Security and privacy
Provider keys server-side in environment/secret manager, never mobile/ZIP; .env.example only dummy values. Admin role-based authentication, audit publication and configuration changes; protect APIs against abuse. Untrusted URLs fetched with strict outbound controls to mitigate SSRF, redirect checks, allowlist, IP checks, timeouts, response/body size and decompression limits; prevent local/metadata IP access. No execution of crawled JS; scripts in pages cannot direct the model or tool calls. Redact logs; minimize retention of raw text; honor source terms and privacy/deletion requirements. Query secrets through approved environment, no credentials requested in chat.

## Reliability
Instrument queue lag, fetch success/failure/throttling, source freshness, candidate/group count, evidence/validation failures, review backlog, publication latency, AI token spend, errors and push delivery. Health endpoints, circuit breakers, per-source limits and conditional fetch. Schedule important sources with policy-based intervals (illustrative security 10–15 min, releases 30–60 min, others hours), respect source limits. Storage retention, periodic integrity verification and restore test. Publication times are not SLAs.

## Cost controls
Collect/fetch incrementally; filter and dedupe before model use; summarize once per canonical event; set prompt/token limits, per-source spend, daily budget and retry caps; caching/version keyed by source revision and prompt; review queue backpressure. Budget/rate/model/provider remain TBD. Do not provide fabricated price estimates.
