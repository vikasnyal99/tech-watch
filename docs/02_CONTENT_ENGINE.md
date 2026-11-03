# Source discovery and briefing pipeline

## Flow
Scheduler → source-specific connector → raw-source record → normalized candidate → exact and semantic deduplication/grouping → relevance/quality filter → structured fact extraction → draft → evidence-backed validation and risk gating → editorial review when required → publish → rank for each feed → optional alerts → monitor and revisit source changes.

## Source registry and collection
Admin controls source ID, domain/URLs, type, fetch mechanism, source priority, coverage topics, terms and permissions, rate limits, schedule, status, last success, checkpoints, ETag/Last-Modified where offered, retries/backoff and owner. Prefer official APIs, RSS/Atom, vendor release notes, registries, project advisories and permitted page discovery. Respect rate limits, robots and content rights separately; robots permission alone is not a content license. Do not bypass paywalls or technical access controls. Store only permitted content/metadata; retain original URLs, publication/revision/check timestamps and provenance. Treat fetched source content as untrusted data and never follow embedded instructions.

Start with a proposed 30–50-source pilot, not a commitment or claim of full internet coverage. Monitor official Kubernetes, Python/PyPI, JavaScript/Node, PHP, PostgreSQL, AWS/cloud, OpenAI, Anthropic, security advisories; verify exact available endpoints, polling and redistribution terms before enabling. Add Github release collectors where appropriate (some Git tags are not GitHub Releases); use authenticated conditional requests and documented limits, webhooks only where configuration rights exist. PyPI project and update RSS feeds; OSV/NVD and vendor advisories for vulnerability enrichment. Use community mentions as discovery leads, not proof. Source health dashboard reports stale, failed, throttled and changed sources.

## Event/fact record
Capture stable source item ID, URL/canonical URL, publisher, published/updated/discovered times, locale, technology IDs and aliases, event category, title, extracted text if permitted, evidence spans/links, source revision/content hash, extraction confidence and unknown fields. Specific evidence is required for version, CVE, exposure, mitigation, availability, price and timing. Source changes generate new immutable source revisions and may trigger reevaluation and corrections.

## Deduplicate
First canonical IDs/URLs, then advisory IDs / package+ecosystem+version / official announcement and aliases, then candidate similarity subject to confidence thresholds. Different versions, updates or contradictory advisories must not be blindly merged. Group many reports under one canonical event with separate sources and updated timestamps. Require manual adjudication when uncertain.

## AI usage and rules
Rules preserve structured source facts. Model receives only the necessary approved source excerpts marked untrusted, extraction schema and instructions. Produce structured JSON: update_type, headline, brief_summary, technology IDs, why_matters, next_action, exact versions and identifiers, uncertainties, evidence references, risk flags and proposed review status. Unknowns are null. JSON schema/length validation; compare identifiers and version strings to evidence; check source dates and URL, retain provenance and model/prompt versions. Never invent claims, imply a user is affected solely because technology is followed, or infer exploitability. Separate fact extraction from copy editing; plain language and concise meaningful titles, while retaining essential constraints. Do not let model instructions embedded in sources control tools or output policy. Avoid sending user secrets or private repo data to model providers.

For example (fictional): 'Kubernetes [version] removes an older API: what teams should check'. Summary: 'The release removes a previously deprecated API. Teams using it should check their manifests before upgrading.' Only publish if source supports these facts. If critical fact unsupported, hold/mark unknown rather than guess. A model-based check can help but is not independent proof.

## Review, publication and updates
Statuses discovered → extracted → drafted → validated → review_pending/published/rejected → corrected/withdrawn. Initially queue security, affected-version, breaking-change and pricing items and all low-confidence material for human review; configure fast-track only after measured quality. Duplicate task handling is idempotent. Errors have bounded retries/backoff and dead-letter queue. Never silently publish failed or partial validations. Publishing events version the card and retain provenance. Changes to a live source can trigger re-extraction, correction, withdrawal and notification policy. In-app source access and label reflect corrected/withdrawn status.

## Ranking and matching
Rule-based scoring initially: explicit technology match + topic/role + event severity/importance supported by evidence + freshness + source quality + diversity − duplicate/seen penalties. Explain eligibility separately from score; Your Stack requires technology association, not a guessed installation. Version-aware matching only with explicit user-provided versions and ecosystem-aware range parser; return match/does-not-match/unknown and respect configuration caveats. Trending uses configurable editorial importance and qualified independent source/community signals, no fabricated counts. Persist per-tab ordering/cursors and section position; avoid reshuffling active read. For version 1 summaries compute once globally; optional role-specific explanatory line only when evidence supports it, no need for per-user generation.

## External official starting references (verify current docs)
- GitHub releases: https://docs.github.com/en/rest/releases/releases
- GitHub API best practices/rate limits: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- PyPI feeds: https://docs.pypi.org/api/feeds/
- OSV: https://osv.dev/ ; NVD https://nvd.nist.gov/ ; CISA KEV https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- PostgreSQL text search https://www.postgresql.org/docs/current/textsearch.html

## Editorial style
Lead with technology + the specific change. A card summary should explain the change and its scope in roughly 18–25 plain-language words. Put the practical implication in “Why it matters” and one concrete step in “What to check”; do not repeat the same sentence across fields. Preserve exact versions, CVEs, affected conditions and uncertainty when they are essential. Avoid hype, filler and unsupported user-impact claims. Source-specific revision dates belong in the sourced metadata when available. Never use illustrative placeholder content as live production news.

The one-screen card has a hard copy budget, enforced by `backend/briefing_copy.py`: title ≤55 characters, summary ≤145, “Why it matters” ≤70, “What to check” ≤65, and all four fields together ≤280. These are publication limits, not instructions to truncate. If essential facts cannot fit, hold the item for an editor to rewrite or design a separate detail view before publishing it. The offline fixtures and ingestion preview both use this validation. Check the final rendered card at narrow phone sizes before accepting a new card layout.
