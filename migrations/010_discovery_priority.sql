UPDATE processing_jobs SET priority=CASE
  WHEN kind='fetch-index' AND priority<50 THEN 50
  WHEN kind IN ('generate-rss-brief','fetch-article','fetch-release','generate-brief') AND priority<40 THEN 40
  ELSE priority END
WHERE status IN ('pending','processing');
