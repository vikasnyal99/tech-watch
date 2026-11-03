# TechWatch local vertical slice

## Preview

With Docker Compose:

```sh
docker compose up --build
```

Open <http://localhost:8000>. The API docs are at <http://localhost:8000/docs>. Stop with `docker compose down`.

Without Docker (Python 3.12):

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

This uses a local SQLite database. `python -m pytest` runs checks. The browser client is a responsive web app; add to home screen for a phone-sized preview. No Flutter SDK is installed here, so a native binary is not part of this slice.

## Scope and data

The entire experience runs offline after loading local files. Every story is marked fictional, and original source actions are disabled because the fixtures have no genuine source URL. Preferences and bookmarks persist under a locally generated installation ID in the API database. The browser stores that ID. Cards/List state and tab positions last for the current page session. In Cards mode, one briefing fills the available phone screen. Swipe up, scroll down, press the down arrow, or use the on-screen control to advance one briefing at a time. The briefing image and typography compact on short screens so the card does not scroll internally. There is no account, sync, push, or live coverage.

New briefing copy must pass `backend/briefing_copy.py` before it can appear in the offline feed or be accepted by the ingestion preview. The summary is specific and concise; supporting facts and actions have their own fields. Overlong copy is held for editing, never silently shortened. See the editorial limits in `docs/02_CONTENT_ENGINE.md`.

`/v1/sources` lists a fixture connector and a disabled RSS template. `backend/pipeline.py` defines a safe URL policy, exact source-item dedupe, evidence checks and a human-review gate. Set `ADMIN_TOKEN` to use `/admin/ingest-preview`; it is preview-only and publishes nothing. This is the initial review path, not a production admin system. The first demo migration creates three tables at startup; a migration runner and broader event/source tables remain to implement. A PostgreSQL service is included in Compose. No worker or scheduler runs because external collection is deliberately disabled.

## Next work

1. Build the Flutter Android/iOS client against the same feed contract and verify device accessibility.
2. Add versioned PostgreSQL migrations, source revisions, evidence records, a protected review UI, and worker job leases.
3. Vet official source endpoints and rights before enabling RSS/API collectors. Add real original links only with validated provenance.
4. Decide hosting, scale, budget, account/sync, editorial staffing, AI provider and notification provider. No choices are assumed here.

## Visual reference pass

The responsive screens use the four supplied raster boards as layout references. The four illustrations under `web/images/` were generated for this local fictional preview using the supplied boards as style references. They depict orchestration, security, AI infrastructure and an onboarding briefing clipboard. They are not real news images or source evidence. The interface icons in `web/icons.svg` are code-native SVG symbols. To revisit onboarding after completing it, use <http://localhost:8000/?onboarding=1> or Settings → Edit onboarding choices.

## Onboarding technology icons

The stack selector uses local SVG technology marks downloaded from [Simple Icons](https://simpleicons.org/) (Python, TypeScript, PHP, Node.js, Kubernetes, Anthropic, PostgreSQL, Redis, React, Django, Grafana). The AWS icon comes from [Devicon](https://github.com/devicons/devicon); the OpenAI mark is from Simple Icons v15. These are identification marks in a fictional offline demo, not endorsements. Check each vendor's current brand rules before a public launch. The app does not request these assets from a CDN at runtime.

## Logo assets

The header lockup, monogram and browser icon in `web/branding/` are resized, tightly cropped derivatives of the user-supplied `Terracotta TechWatch monogram lockup.png`. The original file in Downloads was left untouched.
