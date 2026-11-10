UPDATE technology_sources SET interval_seconds=600, next_due_at=NULL
WHERE id IN ('aws-security','node-security','github-advisories') AND interval_seconds=3600;
UPDATE technology_sources SET interval_seconds=1800, next_due_at=NULL
WHERE id NOT IN ('aws-security','node-security','github-advisories') AND interval_seconds=3600 AND adapter!='python_downloads';
UPDATE technology_sources SET interval_seconds=3600, next_due_at=NULL
WHERE adapter='python_downloads' AND interval_seconds=21600;
