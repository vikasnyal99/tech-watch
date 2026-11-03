# TechWatch — Codex handoff

TechWatch is a mobile-first technical briefing app for software engineers, platform and cloud engineers, DevOps, SREs, product managers and technical leaders.

## Run the current app

Run `docker compose up --build -d` and open `http://localhost:8000/`. The FastAPI service, PostgreSQL and a separate feed worker start together. Run `.venv/bin/python -m pytest -q` for tests. The normal feed shows reviewed live briefings; on a fresh database with no live publications it falls back to clearly labeled fictional examples. Set `OFFLINE_MODE=1` to stop live collection during development.

For the EC2 public preview, use [DEPLOYMENT.md](DEPLOYMENT.md) and the separate `compose.prod.yaml`. The local Compose defaults are for development only.

The worker polls the [official source registry](docs/SOURCE_REGISTRY.md) hourly. The current registry has 29 RSS/Atom endpoints, 28 enabled by default, plus a separate Python release parser. Open **Settings → Source health** to see which sources are healthy, delayed, failing, paused or disabled. Every real item enters a review queue before publication. See [implementation progress](docs/IMPLEMENTATION_PROGRESS.md) for review commands, verified behavior and current limitations.

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
- Audience: practitioners and technical leaders; cover releases, libraries, APIs, cloud, vulnerabilities, deprecations, and AI developments.
- Title must convey the actual update; brief plain-language summary preserves essential facts and uncertainty. Match products and versions carefully. Link to source.
- Design: light warm-white editorial backgrounds, white cards, restrained terracotta accents, serif titles, sans-serif body/controls, subtle depth.
- Source discovery uses curated official sources, APIs and feeds, supplemented by permitted discovery; no claim to crawl the whole web or guarantee completeness.
- Implemented backend: Python/FastAPI, PostgreSQL, background worker and Docker Compose. The current client is mobile-first web; a native client has not been built.
- References and timestamps in generated screens are example content, not verified news. Avoid invented dates and incidents in production.

## Directory

- `docs/`: product, navigation, content engine, schema, architecture, API, operations, security, phases and tests.
- `design_references/`: complete generated screen boards and user-provided reference screenshots. PNG/JPEG are references, not editable designs or licensed production news images.
- `fixtures/`: fictional example events for offline development, clearly labeled.
- `backend/`, `web/`, `migrations/`: runnable app, feed engine and storage.
- `CODEX_PROMPT.md`: original handoff prompt; `TECHWATCH_ENGINE_PROMPT.md`: backend implementation brief.

Source endpoints and publisher behavior can change; check source health before relying on coverage.
