CREATE TABLE IF NOT EXISTS technology_sources (
 id TEXT PRIMARY KEY, technology TEXT NOT NULL, url TEXT NOT NULL, adapter TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 0, interval_seconds INTEGER NOT NULL DEFAULT 21600,
 next_due_at TEXT, etag TEXT, last_modified TEXT, last_hash TEXT, last_error TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_fetches (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES technology_sources(id),
 url TEXT NOT NULL, status_code INTEGER, content_hash TEXT, fetched_at TEXT NOT NULL, error TEXT
);
CREATE TABLE IF NOT EXISTS technology_releases (
 id TEXT PRIMARY KEY, technology TEXT NOT NULL, version TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES technology_sources(id), canonical_url TEXT NOT NULL,
 release_type TEXT NOT NULL, published_at TEXT, latest_hash TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(technology, version)
);
CREATE TABLE IF NOT EXISTS release_revisions (
 id TEXT PRIMARY KEY, release_id TEXT NOT NULL REFERENCES technology_releases(id),
 content_hash TEXT NOT NULL, raw_text TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(release_id, content_hash)
);
CREATE TABLE IF NOT EXISTS release_facts (
 id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES release_revisions(id),
 kind TEXT NOT NULL, description TEXT NOT NULL, evidence_excerpt TEXT NOT NULL,
 evidence_url TEXT NOT NULL, confidence TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tech_briefs (
 id TEXT PRIMARY KEY, release_id TEXT NOT NULL REFERENCES technology_releases(id),
 revision_id TEXT NOT NULL REFERENCES release_revisions(id),
 title TEXT NOT NULL, summary TEXT NOT NULL, why_it_matters TEXT NOT NULL,
 next_action TEXT NOT NULL, score INTEGER NOT NULL, status TEXT NOT NULL,
 fictional INTEGER NOT NULL DEFAULT 0, source_label TEXT NOT NULL, source_url TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(revision_id)
);
CREATE TABLE IF NOT EXISTS processing_jobs (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
 status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
 available_at TEXT NOT NULL, lease_until TEXT, idempotency_key TEXT NOT NULL UNIQUE,
 last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_audit (
 id TEXT PRIMARY KEY, brief_id TEXT NOT NULL REFERENCES tech_briefs(id),
 action TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_due ON processing_jobs(status, available_at);
CREATE INDEX IF NOT EXISTS idx_sources_due ON technology_sources(enabled, next_due_at);
CREATE INDEX IF NOT EXISTS idx_briefs_status ON tech_briefs(status, score, created_at);
CREATE INDEX IF NOT EXISTS idx_revisions_release ON release_revisions(release_id, created_at);
