# Product requirements and experience

## Product and audience
Short practical technical updates for developers, backend/frontend engineers, platform/cloud/DevOps/SRE/security/data practitioners, engineering managers, product managers and CTOs. Users need the concrete change, whether it matters, and what to do next without deciphering long release notes. This is a technology-intelligence product, not general consumer news. Accessible wording must not remove crucial technical details.

## Onboarding (optional, skippable)
1. Welcome / role: choose one or more of software engineer, platform engineer, DevOps/cloud engineer, SRE, product manager, engineering leader; optional other roles. No account needed.
2. Focus areas: backend/APIs, frontend/web, cloud infrastructure, Kubernetes/containers, CI/CD/developer tools, reliability/observability, security, AI models/APIs, data/databases, architecture/strategy. Broad topics, not package names.
3. Your Stack: searchable languages/runtimes, platforms, frameworks/libraries, AI providers/APIs, databases, observability. Multi-select. Example choices Python, PHP, Kubernetes, AWS, OpenAI and Anthropic; no default selection that implies use.
4. Signals: security, breaking changes/deprecations, major releases, AI model/API updates; in-app by default. Push is opt-in and native permission requested only after selection. Both enabled and declined permission end in the Feed, with graceful fallback. Users can skip any optional step, navigate back, and modify preferences later.

## Feed and navigation
After initial setup/skip, open directly to Feed in Cards by default. Pinned tabs in exact order Feed, Your Stack, Trending, AI. One vertically paged update per card, swipe up/down to next/previous; provide accessible next/previous actions. Visible Cards/List control; switching mode preserves current section, filter, ordering and focused story. Each tab retains its own position during a session; persistent behavior across relaunch is configurable, while default first open remains Feed/Cards. Do not steal iOS back gestures; horizontal section swipe is optional and must not conflict with system navigation or Cards/List. Navigation: Briefs, Explore, Saved; profile/settings accessible from header.

- Feed: fresh relevant mix with role/interests relevance, diversity and importance; new users receive a useful general engineering feed.
- Your Stack: update matches followed technology, with 'Why you see this'. Unknown installed version means potentially relevant, never assert affected. Empty state: choose technologies or browse Feed.
- Trending: freshness, meaningful importance, credible source diversity and configurable signals; no unsupported popularity counts. Do not equate virality with relevance.
- AI: model launches, product/API changes, tooling and infrastructure, appropriate sources.
- Same event can occur in multiple tabs but each feed should avoid duplicates; stale/new indicators should not disrupt reading.
- Explore: topics, search, follow technologies and manage stack. Search results include stories/topics/technologies; topic filter is local to active feed, not a change to followed interests.
- Saved: local-first bookmarks; sync/account optional, not a requirement for first release. Reading preferences: accessible text size and reduced motion. Guest mode remains useful.

## Card contents and copy
Meaningful headline = technology + actual change + significance when supported; never vague clickbait, invent version/CVE/dates or assume applicability. Display update type, relevant version, short plain-language summary (~40–75 words as a target, never truncate facts), why it matters, next action if supported, source/published or updated time, and Read source, Save, Share. A security card includes affected version/range, conditions, fixed version or mitigations where confirmed; explicitly mark unknowns. Use 'You follow PHP', not 'you are affected' without sufficient version/config evidence. AI updates note model/API availability and pricing only when supported and dated. Original source links and publisher names are visible; images have a neutral fallback.

## States and acceptance
Handle loading/skeleton, unavailable source, offline and retry, search no results, no stack, no saved stories, no matching results, caught up, disabled/denied notifications, corrections/withdrawals, longer accessibility text and small screens. New updates do not abruptly reorder the story being read; offer 'New updates'. Preserve card vs list continuity. Include event accessibility labels, touch targets, dynamic type and reduced motion. Example/mock updates must be conspicuously marked, never presented as live facts.

## Product boundaries
The design names and branding are working choices. Android/iOS are expected. Target launch scale, business model, account provider, server location, launch date, latency and budget are **not specified**; propose and label estimates, do not borrow assumptions from other products. Do not require a personal ChatGPT account or end-user API key; server-side provider credentials remain private.
