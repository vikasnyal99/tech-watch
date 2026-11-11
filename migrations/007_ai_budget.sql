CREATE TABLE IF NOT EXISTS ai_budget_months (
 month TEXT PRIMARY KEY, cap_microusd INTEGER NOT NULL,
 reserved_microusd INTEGER NOT NULL DEFAULT 0,
 spent_microusd INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ai_requests (
 id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES release_revisions(id),
 prompt_version TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL,
 priority TEXT NOT NULL,
 month TEXT NOT NULL REFERENCES ai_budget_months(month),
 reserved_microusd INTEGER NOT NULL, spent_microusd INTEGER NOT NULL DEFAULT 0,
 input_tokens INTEGER, output_tokens INTEGER, error TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(revision_id,prompt_version)
);
CREATE INDEX IF NOT EXISTS idx_ai_requests_month ON ai_requests(month,created_at);
