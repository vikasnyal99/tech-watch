# TechWatch news engine

This describes the running implementation. [02_CONTENT_ENGINE.md](02_CONTENT_ENGINE.md)
records broader product intent; this guide explains what the code does today.

## Source to screen

```text
official feed or status API → bounded fetch → canonical URL/title dedupe
→ immutable revision + source excerpt → draft → optional AI briefing
→ evidence and publication gate → published event → four feed selectors
→ unread Breaking indicator and per-installation reading state
```

`backend/worker.py` schedules and consumes durable jobs. `backend/engine.py`
owns fetch, dedupe, revisions, jobs, drafts and publication. Parsers live in
`backend/rss_source.py`, `backend/special_sources.py`,
`backend/python_source.py` and `backend/service_health.py`; network bounds are
in `backend/fetcher.py`. [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) lists sources.

An official feed establishes *who published the item* within the connector's
TLS and host checks. It does not prove a generated claim about blast radius,
affected versions or required action. AI treats source text as data, and
TechWatch checks its proposed claims against retained source excerpts.

## Priority before AI

AI eligibility needs a recent item, at least 100 source characters and no
promotional/community title signal. Security, outage and breaking terms in the
title or first 500 source characters raise **queue priority**; they are not a
final severity judgment. The worker orders second checks, urgent AI drafting,
urgent article/draft work, advisory source polls, ordinary source discovery,
normal article/draft work and routine AI. Fetching a normal source therefore
cannot get stuck behind an existing routine AI backlog.
Jobs have leases, bounded retries and idempotency keys. Quota-paused AI jobs
wait for the UTC reset without using a retry attempt. Three advisory sources
are polled every 10 minutes, other feeds every 30 minutes, and Python release
discovery hourly. Source errors appear in Settings → Source health.

Official provider status is a separate path. Health shows active incidents
directly, even if the related news draft has insufficient evidence. A provider
report of “major” or an AWS regional incident does not by itself prove global
impact. Polling intervals and the Health cache are not delivery guarantees.

## AI, publication and importance

`backend/intelligence.py` sends one bounded official-source excerpt per
eligible revision to `gpt-6-luna`. Its structured result contains a one-screen
title, 2–4 sentence summary, implication, action, severity, confidence,
unknowns and exact source quotes. AI is used to **interpret and summarize**;
it does not re-authenticate an official publisher.

`backend/publication_policy.py` checks freshness, length, uncertainty and
exact source support. A low-risk, supported routine item can publish after
one call. Consequential security, outage and breaking claims get one more AI
call that checks TechWatch's wording and severity against the same source.
If evidence is thin, contradictory or uncertain, the draft stays unpublished.
The second call checks our claims, not whether GitHub or another official
publisher really posted the item. Daily human review is not required for
routine operation; admin correction and withdrawal remain available.

Publication and importance are separate. `backend/feed_selection.py` assigns:

| Tier | Score | Rule |
| --- | ---: | --- |
| Breaking / Critical | 110 | Structured critical severity with a supporting second check, or source-backed editorial/official-status critical verdict |
| High | 85 | Serious security, disruption or breaking change. Keywords alone can reach High, never Breaking. |
| Notable | 70 or 65 | Meaningful medium impact, major/stable release or significant release score |
| Routine | 0 | Relevant to followers but no supported broad importance |

The AI prompt reserves `critical` for a **confirmed widespread outage** or
**active exploitation of a critical vulnerability**. A single-region AWS
issue or a Python advisory with unknown affected versions must keep that scope
explicit. The initial source score can influence order, but cannot promote a
story to Breaking by itself.

Trending considers all published stories, selects recent significant items,
and orders Breaking before High before Notable. It shows at most 20. Freshness,
source score, selected signals and diversity change order only *within* a
tier. Feed selects user topics and follows; roles are the fallback. Your Stack
requires a technology follow. AI filters by subject. A Breaking story can
therefore appear in Trending and the alert indicator without changing the
user's chosen Feed topics.

The top-left controls in Briefs are temporary view filters. Feed can browse
any published topic or technology, including one outside the installation's
follows; the unfiltered Feed still uses onboarding preferences. Your Stack
can narrow to one or more *already followed* technologies; an empty selection
means all follows. Trending and AI filters narrow their existing sections.
These selections stay in client memory for the current page visit, remain when
switching tabs, and reset on reload or reopening the app. They never write
`/v1/preferences`. Permanent changes use Settings (or onboarding). The API
accepts `topic` and repeated `technology` parameters on `/v1/feed`; a Feed
view filter bypasses the normal preference inclusion gate, while the Stack
endpoint intersects its technology filter with saved follows.

## Reading and alerts

`GET /v1/alerts` exposes recent published Breaking items for three days, with
up to three items returned and a total unread count. `story_engagement`
stores `seen_at`, `read_at` and `dismissed_at` for each installation/event.
Four seconds of visible card time records *seen*. Swiping away does not clear
the alert. Opening Impact & actions or the original source records *read*;
the user can also dismiss the alert explicitly. The small header indicator
opens the story in Trending without inserting a duplicate tile or using
summary space. A later materially changed revision becomes a new event.

This is **in-app only**. There is no push delivery, account sync or cross-device
read state. The installation ID is in browser local storage. `DELETE /v1/me`
removes its preferences, bookmarks and reading state.

## AI billing and excerpt strategy

One source revision is one AI unit. The model receives at most 4,000 source
characters, not a whole day's RSS collection. The request also includes the
title, URL, instructions and strict output schema. Draft output is capped at
1,000 tokens; the optional second check at 450. Sending all news in one call
would mix events, delay urgent items and make retries and evidence attribution
harder. Chunking every article would add calls and repeat context. The pilot
uses bounded excerpts; if important facts are outside the excerpt, the draft
must be held. A future connector may select relevant paragraphs before the
4,000-character cap.

The app uses `store: false` and disables reasoning. It allows 50 calls per UTC
day, with at most 30 routine calls, and a fixed $5 monthly **app ledger** cap.
It reserves an estimated ceiling before each call. At a limit, even important
jobs wait. A draft older than the seven-day auto-publication window stays
unpublished. The provider's bill and limits are authoritative, so configure
a provider-side spending limit separately.

As checked against [OpenAI Standard pricing](https://developers.openai.com/api/docs/pricing)
on 2026-11-13, Luna costs $0.10 per million uncached input tokens and $0.50
per million output tokens; cached reads cost $0.01 per million input tokens.
The [prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)
lists a 1.25× charge for a 30-minute cache write. The ledger conservatively
charges input at $0.125 per million tokens, so cached reads are generally
overestimated. A 1,000-input/300-output call is about $0.00025 at uncached
Standard rates or $0.000275 in the ledger. Fifty such calls every day for
30 days are roughly $0.38–$0.41; actual token mix and provider billing vary.
Batch processing has a longer turnaround and is not used for urgent news.

Inspect usage with `docker compose -f compose.prod.yaml exec -T worker
python -m backend.review_cli ai-usage`. Prompt/schema changes need new
idempotency versions in `backend/ai_budget.py`. Change caps and prices there
after checking actual usage; update this guide at the same time.

## File map and change checks

| Change | Files | Verify |
| --- | --- | --- |
| Sources and parsing | `backend/rss_source.py`, `backend/special_sources.py`, `backend/python_source.py` | Parser tests, Source health |
| Polling, queue, dedupe, publication transitions | `backend/engine.py`, `backend/worker.py`, `migrations/008_job_priority.sql`, `migrations/010_discovery_priority.sql` | `tests/test_engine.py`, worker logs |
| AI prompt/schema/eligibility | `backend/intelligence.py` | AI and quote tests |
| Auto-publication evidence gates | `backend/publication_policy.py` | Positive and negative gate tests |
| Breaking/High/Notable ranking | `backend/feed_selection.py` | `tests/test_feed_selection.py` |
| API and reading state | `backend/main.py`, `migrations/009_story_engagement.sql` | API tests |
| Header alert and swipe UI | `web/app.js`, `web/breaking-alert.css` | Mobile browser preview |
| AI model, daily/monthly limits, ledger | `backend/ai_budget.py` | Budget tests and `ai-usage` |

Run `.venv/bin/python -m pytest -q` and `node --check web/app.js`. After a
deployment, check `/health`, Trending, `/v1/alerts`, worker status, Source
health and the AI ledger.
