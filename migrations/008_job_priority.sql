ALTER TABLE processing_jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;
UPDATE processing_jobs SET priority=CASE
  WHEN kind='verify-brief' THEN 90
  WHEN kind='analyze-brief' AND payload LIKE '%"urgent": true%' THEN 80
  WHEN kind IN ('generate-rss-brief','fetch-article') AND
       (payload LIKE '%"urgent": true%' OR
        payload LIKE '%"kind": "security"%' OR payload LIKE '%"kind": "deprecation"%') THEN 70
  WHEN kind='fetch-index' AND (payload LIKE '%aws-security%' OR payload LIKE '%node-security%'
                                OR payload LIKE '%github-advisories%') THEN 60
  WHEN kind='analyze-brief' THEN 30
  WHEN kind IN ('generate-rss-brief','fetch-article') THEN 20
  ELSE 10 END;
CREATE INDEX IF NOT EXISTS idx_jobs_priority_due ON processing_jobs(status, priority, available_at);
