CREATE TABLE IF NOT EXISTS story_engagement (
 installation_id VARCHAR(100) NOT NULL,
 event_id VARCHAR(100) NOT NULL,
 seen_at TEXT,
 read_at TEXT,
 dismissed_at TEXT,
 updated_at TEXT NOT NULL,
 PRIMARY KEY (installation_id,event_id)
);
CREATE INDEX IF NOT EXISTS idx_story_engagement_event ON story_engagement(event_id);
