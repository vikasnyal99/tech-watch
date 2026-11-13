# TechWatch — Codex handoff

For the running source-to-screen pipeline, importance tiers, unread Breaking
alerts, AI billing controls and a file-by-file change map, read the
[engine guide](docs/ENGINE_GUIDE.md).

TechWatch is a mobile-first technical briefing app for software engineers, platform and cloud engineers, DevOps, SREs, product managers and technical leaders.

## Run the current app

Run `docker compose up --build -d` and open `http://localhost:8000/`. The FastAPI service, PostgreSQL and a separate feed worker start together. Run `.venv/bin/python -m pytest -q` for tests. The normal feed shows published official-source briefings; on a fresh database with no live publications it falls back to clearly labeled fictional examples. Set `OFFLINE_MODE=1` to stop live collection during development.

For the EC2 public preview, use [DEPLOYMENT.md](DEPLOYMENT.md) and the separate `compose.prod.yaml`. The local Compose defaults are for development only.

The worker polls three urgent advisory feeds every 10 minutes, other official news feeds every 30 minutes, and the separate Python release parser hourly. Existing default intervals are migrated; operator-customized intervals are preserved. The [official source registry](docs/SOURCE_REGISTRY.md) has 43 sources, 42 enabled by default. Open **Settings → Source health** to inspect failures and delays. Urgent advisory fetches, consequential drafts, and second checks take precedence over routine work in the durable queue. See [implementation progress](docs/IMPLEMENTATION_PROGRESS.md) for limitations.

The **Health** bottom tab checks 14 official public status sources: AWS, Google Cloud, Azure, Cloudflare, Akamai, GitHub, npm, Vercel, MongoDB Cloud, HashiCorp, Grafana Cloud, DigitalOcean, OpenAI, and Claude/Anthropic. It shows a badge for current provider-reported impact without taking space from the briefing card. Results are cached for three minutes; failed checks are labeled explicitly. AWS, Google Cloud and Azure public reports can omit account-specific or limited regional issues. This is distinct from the feed collector's Source health page.

The worker also checks these incident sources about every five minutes and creates source-backed **drafts** when an active issue starts or changes. A reviewer must approve a briefing before it can appear in Feed or Trending. Provider-reported `major` and `critical` impacts rank as high and critical after approval; unknown impact stays out of Trending. When a provider confirms resolution, its incident briefing is withdrawn. A failed provider check never implies resolution. Health remains the immediate public status view.

For an incident with unknown machine-readable impact, a reviewer can set `severity` and supply an exact retained source quote in the same edit. The review CLI supports `edit ID --severity high --evidence-quote '...'`; the admin PATCH endpoint accepts the same fields. This records an evidence-checked editorial decision before publication.

AI-assisted RSS drafts require `OPENAI_API_KEY` **and** `AI_ENABLED=1` on the worker. The worker uses `gpt-6-luna` with no reasoning and at most 1,000 output tokens to draft each recent technical update. It skips community and promotional posts and caps all model calls at 50 per UTC day with a fixed $5 monthly application budget. Routine analysis can consume at most 30 of those calls, leaving 20 for urgent work if it arrives later. The model receives up to 4,000 characters of official source text and returns concise briefing copy plus exact source excerpts. With `AUTO_PUBLISH_ROUTINE=1`, recent low-risk updates that pass source, confidence, freshness, and length checks publish automatically. Consequential security and breaking updates receive a separate, bounded model call that checks the proposed title, summary, action, and severity against exact official-source excerpts. Only drafts that pass both the AI check and deterministic evidence checks publish; failures remain unpublished. Jobs delayed by a daily or monthly call limit resume after the UTC reset, with urgent work ahead of routine work. An important item can still wait if all 50 calls are used or the monthly cap is reached; a failed evidence check does not auto-publish. Human review is optional, never required for the pipeline to operate. Published Breaking stories remain in a compact in-app unread indicator until opened or dismissed, even when swiped past. The Health tab reads official provider status directly; brief incident stories with insufficient source detail remain out of the news feed. The worker revisits a few recent untouched drafts every six hours. Inspect usage with `python -m backend.review_cli ai-usage`; an operator may inspect `attention` or withdraw a published item if needed. Provider billing limits should be configured separately. No push delivery is implemented.

## Original handoff references

**Start here:** read `docs/01_PRODUCT_AND_FLOW.md`, `docs/02_CONTENT_ENGINE.md`, `docs/03_ARCHITECTURE_AND_DATA.md`, `docs/04_DESIGN_AND_SCREENS.md`, `docs/05_DELIVERY_AND_TESTS.md`, and `CODEX_PROMPT.md`, then inspect `design_references/`.

The original handoff supplied specifications, starter fixtures and raster design references. The screens are generated visual concepts, not editable Figma frames. No production credentials are included.

## Priority of references

1. `01_engineering_onboarding.png` and `02_technical_briefings.png` are the latest approved direction: lighter background and engineering audience.
2. `03_approved_feed_flow.png` and `04_four_feeds.png` clarify navigation. Earlier imagery and copy are illustrative; adapt them to technical briefings.
3. `05_discovery_and_list.png`, `06_stack_saved_settings.png`, `07_first_use_states.png`, and `08_original_onboarding_in_terracotta.png` cover additional structure; align with the newer onboarding, role, topic, stack, and alert requirements.
4. Original Inshorts references are for interaction inspiration only. Avoid copying brand or claiming tested app behavior.

## Core decisions

- Open to Feed in Cards mode after onboarding; first-run onboarding is optional and skippable.
- Four top tabs, in order: **Feed · Your Stack · Trending · AI**. Explicit Cards/List switch; vertical paging for cards; same section, filter, ordering and focused item on mode switch.
- The top-left dropdowns are temporary view filters. Feed can browse a topic or technology outside saved interests; Your Stack narrows only within followed technologies. Filters remain while switching tabs during a visit and reset on reload. Change permanent interests and follows in Settings.
- Audience: practitioners and technical leaders; cover releases, libraries, APIs, cloud, vulnerabilities, deprecations, and AI developments.
- Title must convey the actual update; brief plain-language summary preserves essential facts and uncertainty. Match products and versions carefully. Link to source.
- Design: light warm-white editorial backgrounds, white cards, restrained terracotta accents, serif titles, sans-serif body/controls, subtle depth.
- Source discovery uses curated official sources, APIs and feeds, supplemented by permitted discovery; no claim to crawl the whole web or guarantee completeness.
- Implemented backend: Python/FastAPI, PostgreSQL, background worker and Docker Compose. The mobile-first web client remains available, and `mobile/` contains the native Flutter Android client. See [mobile/README.md](mobile/README.md) for preview and Play release builds.
- References and timestamps in generated screens are example content, not verified news. Avoid invented dates and incidents in production.

## Directory

- `docs/`: product, navigation, content engine, schema, architecture, API, operations, security, phases and tests.
- `design_references/`: complete generated screen boards and user-provided reference screenshots. PNG/JPEG are references, not editable designs or licensed production news images.
- `fixtures/`: fictional example events for offline development, clearly labeled.
- `backend/`, `web/`, `migrations/`: runnable app, feed engine and storage.
- `CODEX_PROMPT.md`: original handoff prompt; `TECHWATCH_ENGINE_PROMPT.md`: backend implementation brief.

Source endpoints and publisher behavior can change; check source health before relying on coverage.
