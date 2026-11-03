# MASTER IMPLEMENTATION PROMPT — DEVTECH UPDATE

## ROLE AND OBJECTIVE

You are a Principal Backend Architect, Senior Go Engineer, Senior Python Engineer, Data Engineer, Security Engineer, and DevOps Engineer.

Your task is to **design, implement, test, document, and prepare for deployment a production-minded MVP of DevTech Update**.

Do not stop after writing an architecture document. Implement working code, database migrations, APIs, background jobs, source adapters, tests, and Docker configuration.

The product automatically discovers important updates across programming languages, databases, frameworks, DevOps tools, cloud platforms, and AI providers.

It must:

1. Discover new releases and important changes from official sources.
2. Extract structured facts from release notes and changelogs.
3. Identify features, bug fixes, breaking changes, deprecations, reversions, security advisories, and end-of-support announcements.
4. Generate short, understandable developer updates.
5. Rank updates by importance.
6. Personalize updates based on the technologies and versions a developer follows.
7. Display updates through APIs suitable for a mobile application.
8. Notify users about important events.
9. Avoid duplicate articles, fabricated claims, unnecessary AI calls, and irrelevant notifications.
10. Support additional technologies through reusable adapters and configuration.

**Primary implementation goal:** Deliver a complete working Python release-monitoring vertical slice first. Then implement and test the generic adapters needed for additional technologies.

Do not claim a feature is complete unless its implementation and relevant tests exist.

---

# PART 1 — ARCHITECTURE

## 1.1 Technology stack

Use:

- API backend: Go + Gin
- Ingestion worker: Python
- Intelligence worker: Python
- Database: PostgreSQL
- Queue and cache: Redis
- HTTP client: httpx
- HTML parser: Beautiful Soup
- Article extraction: Trafilatura
- Optional AI: Provider abstraction with a configurable API
- Authentication: JWT access tokens with rotating refresh tokens
- Push notifications: Firebase Cloud Messaging
- Observability: OpenTelemetry-compatible logs, metrics, and traces
- Local infrastructure: Docker Compose
- Database migrations: Version-controlled SQL migrations
- Testing: pytest for Python and Go's standard testing framework

Do not introduce Kafka, Kubernetes, Elasticsearch, or unnecessary infrastructure in the MVP.

Use clean architecture, dependency injection, typed contracts, and clear module boundaries.

## 1.2 Three backend services

### Service A — Ingestion Service

Responsibilities:

- Technology source configuration
- Poll scheduling
- HTTP/API/RSS fetching
- Source-specific parsing
- HTML text extraction
- Release discovery
- Change detection
- Deduplication
- Raw source storage
- Publishing processing jobs

### Service B — Intelligence Service

Responsibilities:

- Detailed release-note analysis
- Fact extraction and classification
- Security advisory enrichment
- Affected-version interpretation
- Importance scoring
- Optional AI summarization
- Template-based fallback summarization
- Evidence verification
- Tech Short generation
- Publication lifecycle management

### Service C — API and Personalization Service

Responsibilities:

- Authentication
- User profiles
- Technology catalog
- Technology following
- User project and version tracking
- Personalized ranking
- Feed generation
- Search and filtering
- Bookmarks
- Read/unread tracking
- Notification preferences
- Notification scheduling and delivery
- Admin APIs

All services must communicate through well-defined database records and durable queue messages.

Do not create direct circular dependencies between services.

---

# PART 2 — COMPLETE END-TO-END EVENT FLOW

Implement the following pipeline:

```text
Official Technology Sources
          |
          v
Technology Source Registry
          |
          v
Scheduler
          |
          v
HTTP / API / RSS Fetcher
          |
          v
Raw Source Storage
          |
          v
Source-Specific Parser
          |
          v
Structured Data Normalizer
          |
          v
Change Detection + Deduplication
          |
          v
Durable Intelligence Job Queue
          |
          v
Release Intelligence
          |
          +----> Security Advisory Enrichment
          |
          v
Evidence Validation
          |
          v
Global Importance Scoring
          |
          v
Tech Short Generator
          |
          v
Content Verification
          |
          v
Publication
          |
          v
Personalization Engine
          |
          +----> User Technology Preferences
          |
          +----> Project Version Inventory
          |
          v
Personalized Feed
          |
          +----> Mobile API
          |
          +----> Search
          |
          +----> Notification Worker
          |
          v
User Feedback and Analytics
```

Every stage must have explicit inputs, outputs, error handling, and processing states.

The pipeline must be retryable, idempotent, and observable.

---

# PART 3 — TECHNOLOGY SOURCE REGISTRY

Create a database-driven technology catalog.

Supported categories:

- Programming languages
- Runtimes
- Backend frameworks
- Frontend frameworks
- Mobile frameworks
- Databases
- Cache systems
- Message brokers
- DevOps tools
- Cloud platforms
- Observability tools
- Security tools
- AI providers and models

Initial technology catalog:

Programming languages:
Python, Java, JavaScript, TypeScript, Go, Rust, PHP, Ruby, C#, C++, Kotlin, Swift.

Databases and infrastructure:
Redis, MongoDB, PostgreSQL, MySQL, MariaDB, ClickHouse, Elasticsearch, Cassandra, DynamoDB, Kafka, RabbitMQ.

Frameworks:
Django, FastAPI, Flask, Spring Boot, Express, NestJS, Laravel, React, Next.js, Angular, Vue, Flutter.

DevOps and cloud:
Docker, Kubernetes, Terraform, Helm, Nginx, GitHub Actions, AWS, Azure, GCP, Cloudflare.

AI:
OpenAI, Anthropic Claude, Google Gemini, Meta Llama, Mistral, DeepSeek, xAI, Ollama.

These are catalog entries, not a claim that all integrations are implemented.

## Source configuration

Each source must support:

- Source ID
- Technology ID
- Official URL
- Source type
- Adapter name
- Polling interval
- Last successful check
- Next scheduled check
- HTTP ETag
- Last-Modified
- Last content hash
- Enabled status
- Source reliability classification
- Retry policy
- Parser version
- Last error

Source types:

1. GitHub Releases API
2. GitHub security advisories
3. RSS/Atom
4. HTML release page
5. HTML changelog
6. JSON API
7. Package registry
8. Security advisory API
9. AI provider changelog

Implement reusable adapter interfaces.

Never create one independent microservice per technology.

---

# PART 4 — PYTHON INTEGRATION: FIRST COMPLETE IMPLEMENTATION

Implement Python monitoring end to end before expanding the integration catalog.

## 4.1 Official sources

Start with:

- https://www.python.org/downloads/
- https://www.python.org/downloads/security/
- https://docs.python.org/3/whatsnew/
- https://devguide.python.org/versions/

Add relevant Python security records from OSV, NVD, and other authoritative advisory sources when applicable.

Validate each source's current structure before implementing selectors.

Do not assume the downloads page contains complete feature information.

## 4.2 Scheduler

Implement a persistent polling scheduler.

Example schedules:

- Python downloads: every 6 hours
- Python security: every 3 hours
- Python What's New: every 12 hours
- Python lifecycle: every 24 hours

Schedules must be configurable.

Requirements:

- Prevent concurrent polling of the same source.
- Support distributed locks or database leases.
- Persist scheduling state.
- Handle worker restarts.
- Add retry backoff and jitter.
- Respect API rate limits.
- Support manual rechecks.
- Avoid unbounded retries.

## 4.3 Fetcher

Implement a reusable HTTP fetcher.

Requirements:

- Connection and read timeouts
- Configurable retries
- Exponential backoff
- Conditional requests using ETag and Last-Modified
- HTTP 304 handling
- Rate limiting
- User-Agent identification
- Redirect limits
- Maximum response size
- Content-type validation
- Source URL allowlisting
- TLS verification
- Structured error handling
- Request duration metrics

Security:

- Prevent SSRF.
- Reject unexpected private/internal destinations.
- Validate redirects.
- Never accept arbitrary URLs from untrusted users as fetch targets.
- Respect applicable website access policies and terms.

Store the raw source response or a durable reference to it.

## 4.4 Python release extractor

Build a Python-specific adapter.

Extract:

- Technology name
- Version
- Release date
- Release URL
- Release type
- Release status
- Official release-note links
- Source identifier

Follow linked release pages and What's New documentation when necessary.

Use packaging.version or an appropriate PEP 440-compatible parser.

Do not use lexicographical string comparison for Python versions.

Distinguish:

- Alpha
- Beta
- Release candidate
- Stable
- Maintenance
- Security-only
- End-of-life

If a field cannot be verified, mark it unknown.

## 4.5 Change detection

Compare extracted records with existing database records.

Detect:

- Newly published release
- Updated release notes
- Changed publication metadata
- New security advisory
- Corrected advisory
- Withdrawn announcement
- Explicitly reverted feature
- End-of-support transition

Use stable identities and content hashes.

Avoid publishing duplicate updates when the same release appears in multiple official sources.

Preserve historical revisions and source provenance.

Do not infer a rollback merely because text disappeared from a page.

## 4.6 Python release intelligence

Fetch detailed release notes.

Extract and classify individual facts into:

- New feature
- Performance improvement
- Bug fix
- Security fix
- Breaking change
- Deprecation
- Removed functionality
- Reverted change
- Migration requirement
- Documentation-only update
- Lifecycle change

Every extracted fact must store:

- Fact ID
- Release ID
- Classification
- Original excerpt
- Source URL
- Source section
- Extracted description
- Confidence
- Verification status
- Parser version

Do not generate unsupported claims.

---

# PART 5 — SECURITY INTELLIGENCE

Build security intelligence as a module inside the Intelligence Service.

Sources:

- OSV
- NVD
- GitHub Security Advisories
- Official vendor security announcements

Extract:

- Advisory ID
- CVE ID, if present
- Affected product
- Package ecosystem
- Affected version ranges
- Fixed versions
- Severity
- CVSS score and vector, when available
- Publication date
- Last modified date
- Advisory URL
- Withdrawal status

Requirements:

1. Deduplicate advisories across providers.
2. Preserve all source references.
3. Normalize affected-version data.
4. Use ecosystem-aware version matching.
5. Distinguish unknown, unaffected, and affected versions.
6. Handle amended and withdrawn advisories.
7. Never fabricate CVE identifiers.
8. Never allow an AI-generated severity to override authoritative advisory metadata.
9. Support manual review of ambiguous advisories.
10. Generate security alerts only after verifying relevant facts.

A critical vulnerability affecting a user's installed version must be eligible for urgent delivery independently of ordinary feed ranking.

If the user's installed version is unknown, show an informational version-check recommendation rather than claiming they are affected.

---

# PART 6 — INTELLIGENCE AND FACT RANKING

Rank individual facts before creating the Tech Short.

Suggested initial fact priority:

- Verified critical security impact: 100
- High-impact breaking change: 90
- Confirmed feature rollback: 85
- Important deprecation: 75
- Major feature: 65
- Significant performance improvement: 55
- Routine bug fix: 30
- Documentation-only update: 10

These are initial heuristic values. Keep them configurable and test them against real examples.

Do not treat all security fixes as equally severe.

Store evidence and confidence separately from importance.

## Global update ranking

Use the following initial scoring dimensions:

- Security impact: 30
- Breaking-change impact: 20
- Release significance: 15
- Performance impact: 10
- Ecosystem impact: 10
- Recency: 10
- Source confidence: 5

Total: 100.

Source verification must also be a publication gate. An unverified article must not become publishable merely because it scores highly.

Persist the scoring factors, final score, scoring-rule version, and explanation.

Implement deterministic unit tests for scoring.

---

# PART 7 — TECH SHORT GENERATOR

Build a configurable summarization module supporting two modes.

## Mode A — No AI

Use:

- Verified extracted facts
- Source headings
- Rule-based classification
- Extractive sentence selection
- Predefined templates

Generate:

- Title
- One-line summary
- Top three important changes
- Why it matters
- Developer action
- Technology tags
- Update category
- Reading time
- Official source link

If source information is insufficient, omit unsupported sections.

## Mode B — Optional AI

Use a configurable LLM provider.

The AI must only rewrite verified facts into simple language.

Do not send entire raw webpages unless necessary.

Suggested input:

```json
{
  "technology": "python",
  "version": "X.Y.Z",
  "event_type": "release",
  "verified_facts": [
    {
      "type": "feature",
      "description": "Source-backed feature",
      "source_url": "official URL"
    }
  ],
  "target_words": 60,
  "audience": "software_engineers"
}
```

Required output:

```json
{
  "title": "Python X.Y.Z Update",
  "short_description": "...",
  "highlights": [],
  "why_it_matters": "...",
  "developer_action": "...",
  "tags": [],
  "reading_time_seconds": 30
}
```

AI rules:

- Use strict structured output.
- Do not invent features.
- Do not invent benchmarks.
- Do not invent security vulnerabilities.
- Do not invent migration requirements.
- Do not invent release dates.
- Do not fabricate future model launches.
- Preserve technical meaning.
- Use simple developer-friendly English.
- Keep summaries short.
- Validate generated claims against extracted facts.
- Mark uncertain output for review.
- Fall back to templates when AI fails.

## AI cost optimization

- Generate once per unique update.
- Cache using normalized fact-content hashes and prompt/model versions.
- Never regenerate per user.
- Use small models for ordinary summaries.
- Batch eligible jobs where appropriate.
- Track input and output tokens.
- Set maximum token budgets.
- Limit retries.
- Record estimated and actual API cost.
- Allow AI to be disabled through configuration.

---

# PART 8 — PERSONALIZATION ENGINE

Implement deterministic personalization.

Each user can follow:

- Technologies
- Technology categories
- AI providers
- Security alerts
- Release announcements
- Breaking changes
- Performance updates

Optionally, users can provide installed versions.

Example:

```json
{
  "user_id": 101,
  "role": "backend_engineer",
  "technologies": [
    {
      "name": "python",
      "version": "3.12"
    },
    {
      "name": "redis",
      "version": "7"
    },
    {
      "name": "mongodb",
      "version": null
    }
  ],
  "interests": [
    "security",
    "performance",
    "breaking_changes"
  ]
}
```

## Personalized scoring

Consider:

- Followed technology
- Installed version
- Confirmed vulnerability impact
- Developer interests
- Global importance
- Recency
- Read/unread status
- Previous user feedback

Calculate a personalized score from 0–100.

Keep the algorithm deterministic, configurable, and explainable.

Do not assume that a user is affected by a vulnerability just because they follow a technology.

## Example

Python release discovered.

User A:
- Follows Python
- Runs an affected version
- Interested in security

Result: High-priority security alert.

User B:
- Uses Java and React
- Does not follow Python

Result: Usually omit from personalized feed.

User C:
- Follows Python
- Installed version unknown

Result: Show release summary with an optional version-check recommendation.

Implement the three scenarios as automated tests.

---

# PART 9 — NOTIFICATIONS

Implement notification eligibility and delivery.

Channels:

- In-app
- Push notification
- Email digest

Notification categories:

- Critical security
- High-impact breaking change
- Major release
- Deprecation
- End-of-support
- Daily digest
- Weekly digest

Requirements:

- User opt-in preferences
- Deduplication
- Rate limiting
- Quiet hours
- Time-zone support
- Retry handling
- Delivery status
- Provider failure handling
- Notification audit records

Do not send notifications directly from the HTTP request path.

Use durable background jobs.

If Firebase credentials are not configured, provide a working mock notification provider and integration tests.

---

# PART 10 — DATABASE DESIGN

Use PostgreSQL.

Create migrations for at least:

1. technologies
2. technology_sources
3. source_fetches
4. raw_documents
5. technology_releases
6. release_revisions
7. release_facts
8. security_advisories
9. advisory_affected_versions
10. tech_shorts
11. users
12. user_sessions
13. user_technologies
14. user_projects
15. project_dependencies
16. personalized_feed_events
17. notification_preferences
18. notification_deliveries
19. user_feedback
20. processing_jobs
21. ai_usage_logs

For each table:

- Choose appropriate data types.
- Add primary keys.
- Add foreign keys.
- Add necessary unique constraints.
- Add useful indexes.
- Define timestamps.
- Document lifecycle and retention policies.

Use transactions for multi-record operations that must remain consistent.

Avoid storing duplicate summaries for each user.

Use stable IDs and idempotency keys.

Provide migration-up and rollback support.

---

# PART 11 — API IMPLEMENTATION

Build REST APIs using Go + Gin.

## Technology APIs

GET /api/v1/technologies

GET /api/v1/technologies/:slug

GET /api/v1/technologies/:slug/releases

GET /api/v1/technologies/:slug/security

## Authentication APIs

POST /api/v1/auth/register

POST /api/v1/auth/login

POST /api/v1/auth/refresh

POST /api/v1/auth/logout

## User APIs

GET /api/v1/me

PATCH /api/v1/me

GET /api/v1/me/technologies

POST /api/v1/me/technologies

DELETE /api/v1/me/technologies/:slug

GET /api/v1/me/preferences

PATCH /api/v1/me/preferences

## Feed APIs

GET /api/v1/feed

GET /api/v1/feed/trending

GET /api/v1/feed/security

GET /api/v1/feed/ai

GET /api/v1/updates/:id

POST /api/v1/updates/:id/bookmark

POST /api/v1/updates/:id/read

POST /api/v1/updates/:id/feedback

## Project APIs

GET /api/v1/projects

POST /api/v1/projects

POST /api/v1/projects/:id/dependencies

GET /api/v1/projects/:id/impact

## Admin APIs

POST /api/v1/admin/sources

PATCH /api/v1/admin/sources/:id

POST /api/v1/admin/sources/:id/recheck

GET /api/v1/admin/processing-jobs

GET /api/v1/admin/review-queue

POST /api/v1/admin/updates/:id/publish

POST /api/v1/admin/updates/:id/reject

Admin APIs must require appropriate authorization.

Requirements for every endpoint:

- Request validation
- Consistent error responses
- Pagination
- Authentication where appropriate
- Authorization
- Rate limiting
- Structured logging
- API documentation
- Unit and integration tests

Generate an OpenAPI specification.

---

# PART 12 — QUEUE AND PROCESSING STATES

Use Redis Streams or a reliable job-queue implementation.

Define processing states:

```text
DISCOVERED
FETCHED
EXTRACTED
NORMALIZED
QUEUED
ANALYZING
VERIFIED
SUMMARY_GENERATED
REVIEW_REQUIRED
PUBLISHED
FAILED
RETRACTED
```

Define allowed transitions.

Implement:

- Durable message processing
- Consumer acknowledgments
- Retry policy
- Dead-letter handling
- Idempotency
- Job timeouts
- Recovery after worker crashes
- Duplicate-job protection
- Failure audit logs

Important: PostgreSQL and Redis do not share a transaction. Use a transactional outbox or an equivalent reliable publishing mechanism when database writes and queue publication must remain consistent.

---

# PART 13 — COMPLETE PYTHON TEST SCENARIO

Build a deterministic end-to-end test using recorded or synthetic fixtures.

Do not depend on a live website for CI tests.

## Test case 1 — New release

Initial database:

Python release A already exists.

Fixture:

Python release B is published.

Expected:

1. Scheduler creates fetch job.
2. Fetcher loads source.
3. Parser extracts release B.
4. Change Detector identifies a new release.
5. Database stores the candidate.
6. Intelligence job is created.
7. Release facts are extracted.
8. Summary is generated.
9. Global score is calculated.
10. Update becomes publishable after verification.
11. Personalized feed includes the update for Python followers.

## Test case 2 — No changes

Source returns HTTP 304 or identical normalized content.

Expected:

- No duplicate release.
- No unnecessary AI call.
- No duplicate notification.

## Test case 3 — Updated release notes

Existing release notes change.

Expected:

- New revision recorded.
- Meaningful changes identified.
- Summary regenerated only when necessary.
- Prior evidence retained.

## Test case 4 — Critical security advisory

A synthetic advisory affects Python version A but not B.

Expected:

- Correct version-range matching.
- Affected user receives urgent-alert eligibility.
- Unaffected user does not receive an affected-version alert.
- Unknown version remains unknown.

## Test case 5 — AI failure

AI provider times out.

Expected:

- Bounded retries.
- Template fallback.
- No invented content.
- Processing state recorded.

## Test case 6 — Parser failure

Official HTML structure changes.

Expected:

- Parse failure detected.
- Existing published data preserved.
- Source health warning generated.
- No fabricated release.

## Test case 7 — Explicit retraction

A verified source retracts an announcement.

Expected:

- Existing event marked retracted.
- Feed updated.
- Previously notified users can receive a correction when appropriate.

## Test case 8 — Concurrent workers

Two workers process the same release.

Expected:

- One canonical release record.
- No duplicate Tech Short.
- No duplicate notification.

---

# PART 14 — OBSERVABILITY

Add structured logs with:

- service_name
- job_id
- source_id
- technology_id
- release_id
- request_id
- correlation_id
- trace_id
- duration_ms
- processing_status
- error_code

Track metrics:

- Source fetch success rate
- Fetch latency
- Parser failure rate
- New releases detected
- Duplicate events skipped
- Intelligence processing latency
- AI tokens used
- AI cost
- Summary validation failures
- Queue depth
- Retry count
- Dead-letter count
- Notification delivery success
- Feed API latency

Expose health and readiness endpoints.

Do not log credentials, access tokens, or sensitive user data.

---

# PART 15 — SECURITY REQUIREMENTS

Implement:

- JWT validation
- Rotating refresh tokens
- Secure password hashing
- Authorization for user-owned resources
- Admin role checks
- Rate limiting
- Input validation
- SQL parameterization
- Secret management
- HTTP security configuration
- SSRF protection
- Dependency vulnerability scanning
- Safe external URL handling
- Audit logs for privileged operations

Treat crawled webpages and AI responses as untrusted input.

Never execute code extracted from release notes.

Do not allow source text to override system instructions or internal processing rules.

---

# PART 16 — DOCKER AND DEPLOYMENT

Create:

- Dockerfile for ingestion
- Dockerfile for intelligence
- Dockerfile for API
- docker-compose.yml
- .env.example
- PostgreSQL migrations
- Database seed scripts
- Local startup commands
- Health checks
- Graceful shutdown
- Persistent volumes
- Restart policies

Local development must support:

```bash
docker compose up --build
```

Document the required environment variables.

Do not hardcode secrets.

Include instructions for deploying to a single Linux VM initially.

Provide backup, restore, and recovery guidance for PostgreSQL.

---

# PART 17 — PROJECT STRUCTURE

Use a monorepo:

```text
devtech-update/
├── services/
│   ├── ingestion/
│   │   ├── adapters/
│   │   ├── fetchers/
│   │   ├── extractors/
│   │   ├── scheduler/
│   │   ├── change_detection/
│   │   ├── repositories/
│   │   └── tests/
│   │
│   ├── intelligence/
│   │   ├── classification/
│   │   ├── security/
│   │   ├── ranking/
│   │   ├── summarization/
│   │   ├── verification/
│   │   ├── repositories/
│   │   └── tests/
│   │
│   └── api/
│       ├── cmd/
│       ├── internal/
│       │   ├── auth/
│       │   ├── users/
│       │   ├── technologies/
│       │   ├── feed/
│       │   ├── personalization/
│       │   ├── notifications/
│       │   ├── projects/
│       │   └── admin/
│       └── tests/
│
├── shared/
│   ├── contracts/
│   └── schemas/
│
├── migrations/
├── fixtures/
├── deployment/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

Use this as a starting structure. Adjust only when there is a clear technical reason.

---

# PART 18 — IMPLEMENTATION ORDER

Work in the following order.

## Milestone 1 — Foundation

- Inspect existing repository.
- Identify existing conventions.
- Create implementation plan.
- Set up services.
- Set up PostgreSQL and Redis.
- Create migrations.
- Define shared schemas.
- Add Docker Compose.
- Add basic health checks.

## Milestone 2 — Python ingestion

- Register Python sources.
- Implement scheduler.
- Implement HTTP fetcher.
- Implement Python release parser.
- Persist raw documents.
- Normalize release records.
- Detect changes.
- Publish durable jobs.
- Write unit and integration tests.

## Milestone 3 — Intelligence

- Extract release facts.
- Classify changes.
- Integrate security advisory data.
- Implement global ranking.
- Implement template summaries.
- Add optional AI summarization.
- Validate summaries.
- Implement publication workflow.
- Write tests.

## Milestone 4 — API and personalization

- Implement authentication.
- Implement technology catalog APIs.
- Implement user follow preferences.
- Implement version tracking.
- Implement personalized ranking.
- Implement feed endpoints.
- Add bookmarks and read status.
- Write tests.

## Milestone 5 — Notifications

- Implement notification preferences.
- Add in-app notification records.
- Add FCM provider abstraction.
- Implement digest generation.
- Add retries and deduplication.
- Write tests.

## Milestone 6 — Additional technologies

After Python works, add:

- Redis
- Node.js
- MongoDB

Reuse the existing services.

Implement source adapters and fixture-based tests for each.

Do not claim these integrations are complete until they have passed their own tests.

## Milestone 7 — Production preparation

- Security review
- Failure recovery
- Load testing
- Observability
- API documentation
- Database backup instructions
- Deployment guide
- Final end-to-end verification

---

# PART 19 — DEFINITION OF DONE

The MVP is complete only when:

- All three backend services start successfully.
- PostgreSQL migrations execute successfully.
- Redis job processing works.
- Python release ingestion works using verified source structures.
- New releases are detected.
- Duplicate releases are prevented.
- Release facts are stored with source evidence.
- Security matching handles affected, unaffected, and unknown versions.
- Tech Shorts are generated.
- AI can be disabled without breaking the pipeline.
- Global ranking works.
- Personalized ranking works.
- APIs return valid responses.
- Notifications respect user preferences.
- Tests cover success and failure cases.
- Docker Compose starts the full system.
- Documentation explains local setup and deployment.

Provide evidence for completed requirements.

Do not silently skip missing functionality.

---

# PART 20 — CODING AGENT EXECUTION RULES

Follow these rules throughout implementation.

1. **Inspect before modifying.** Read the existing repository and relevant configuration before making changes.
2. **Implement real functionality.** Do not replace core functionality with TODO comments or hardcoded mock responses.
3. **Use fixtures only for tests and explicitly identified demos.**
4. **Work milestone by milestone.** Complete and test each milestone before proceeding.
5. **Maintain a progress file.** Create `docs/IMPLEMENTATION_PROGRESS.md` recording completed tasks, pending tasks, failures, and decisions.
6. **Keep architecture documentation updated.** Document service responsibilities, database relationships, event contracts, and workflows.
7. **Run tests after meaningful changes.** Fix failures before claiming completion.
8. **Avoid unnecessary dependencies.** Prefer stable, maintained libraries.
9. **Keep secrets out of source code.**
10. **Make external integrations configurable.** Do not assume credentials are available.
11. **Do not fabricate live release data.** Use official sources when available and recorded fixtures for deterministic tests.
12. **Record blockers accurately.** If network access, API keys, Firebase credentials, or deployment permissions are unavailable, complete the testable portions and document exactly what remains.
13. **Do not stop after producing a plan.** Continue implementing as far as the available environment permits.
14. **Do not make destructive changes to existing infrastructure or data without authorization.**
15. **Do not mark tests as passed unless they actually ran and passed.**

At the end of every milestone, provide:

- Files created or modified
- Functionality implemented
- Database changes
- Tests executed and results
- Remaining issues
- Next milestone

---

# PART 21 — FINAL DELIVERY

When implementation is complete, provide:

1. Architecture overview.
2. Full repository structure.
3. Service responsibilities.
4. Database schema and migrations.
5. API documentation.
6. Queue and event contracts.
7. Python source integration details.
8. Security verification design.
9. AI and non-AI summarization modes.
10. Ranking and personalization formulas.
11. Test results.
12. Docker startup instructions.
13. Deployment instructions.
14. Known limitations.
15. Future expansion plan.

Also demonstrate the following end-to-end scenario:

**A new Python release is discovered → official release notes are extracted → important facts are identified → a Tech Short is generated → the update is ranked → a Python-following user receives it in their personalized feed.**

Show the corresponding database records, queue transitions, and API response.

The first release must work even with AI disabled.

**Begin by inspecting the repository and creating the implementation plan. Then execute Milestone 1 and continue through the remaining milestones, validating each stage.**
