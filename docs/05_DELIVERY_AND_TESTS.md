# Delivery roadmap, validation and open decisions

## Iteration 0: inspect and plan
Read all docs and images, inspect existing repo, framework and instructions if present; preserve user work. Since this ZIP has no code, create a new project only where appropriate. Confirm assumptions in a concise task plan; do not block on routine decisions. Clearly distinguish committed requirements from suggestions. Define screen/flow coverage and runnable acceptance checks.

## Iteration 1: vertical slice
Build a runnable local workspace with mobile app (Flutter baseline), Python/FastAPI, PostgreSQL and worker/scheduler services under Docker Compose; keep code modular and stub external dependencies. Seed explicitly fictional fixture events. Deliver first-run optional onboarding → Feed/Cards → tab switching → card navigation → List mode with position continuity → Your Stack → saved local flow → source link mock, plus basic Explore. Implement source registry and ingestion contract with one safe RSS sample and a fixture source. No fabricated live results, no outbound network required for demo, no paid key required. Prefer real persisted API/preferences where practicable; state any mock transparently. Include build/run commands, dependency prerequisites, .env.example and seeded/demo mode. Runtime secrets never committed.

## Iteration 2: trustworthy pipeline
Per-source connector constraints, raw revision and dedupe, structured extraction, evidence validation, rule-based scoring, source health/retries, admin authentication, review/publish/correct and rejection flow. Add actual vetted connectors only after verifying API terms and configured keys. Separate deterministic offline AI adapter from optional configured model provider. Security items human reviewed initially. Version matching only with evidence and user-provided versions.

## Iteration 3: polish and production readiness
Search, filters, personal preferences across devices only if account chosen, notifications opt-in, offline behavior, accessibility, observability, backups/restore, secured deployment, budget controls, source license management and operating instructions. Larger-scale assumptions decided with measurements.

## Acceptance checks
- Onboarding can be skipped; permission requested only on explicit push opt-in; landing Feed/Cards, no account.
- All four tabs work; section positions preserved; up/down story navigation; explicit Cards/List maps same identity and ordering; restored state after source link/back; no conflict with OS gesture; stable feed when new items arrive.
- Technology aliases, exact version and CVE extraction; unknown version/config is unknown, never 'affected'; duplicates merge with provenance but separate releases do not; source correction creates revision and triggers re-review.
- Source HTTP timeout, rate limit, 304, malformed RSS, unreachable URL, malicious redirects/private IP, idempotent retry and queue lease recovery; no arbitrary scripts executed, no injection instructions obeyed.
- JSON schema, allowed facts/evidence, precision of versions and dates, rejection of unsupported claims; invalid model output, unavailable provider, no-source event and model timeout do not publish; review/audit enforced.
- Accessible labels, dynamic text/scroll without clipping, contrast, keyboard/touch and screen reader, reduced motion; small phones, offline and no-result states.
- Anonymous preference and bookmark semantics, deletion, opt-in permission denied, no notification spam, cursor pagination, stable concurrent updates. CI verifies migrations, meaningful unit/integration tests, formatting and Compose smoke test.

## Open questions (not resolved in conversation)
Target scale and country, launch timeline and budget; mobile team/framework; hosting and ownership; exact AI provider/model and editorial staffing; whether to launch authentication/sync, push or version-aware matching; exact sources and rights; measured latency goals; privacy and retention policy. Provide reasonable documented defaults and offline pilot; don't block general implementation solely for these.
