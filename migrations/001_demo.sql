CREATE TABLE IF NOT EXISTS preferences (installation_id VARCHAR(100) PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bookmarks (installation_id VARCHAR(100) NOT NULL, event_id VARCHAR(100) NOT NULL, PRIMARY KEY (installation_id, event_id));
CREATE TABLE IF NOT EXISTS review_queue (id VARCHAR(100) PRIMARY KEY, payload TEXT NOT NULL, status VARCHAR(30) NOT NULL);
