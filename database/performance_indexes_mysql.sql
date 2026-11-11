-- Safe, non-destructive performance indexes for existing V4Career MySQL 8 databases.
-- Check SHOW INDEX FROM jobs / collection_runs first; skip any index that already exists.
CREATE INDEX idx_jobs_source_posted ON jobs (source_id, posted_at, id);
CREATE INDEX idx_jobs_source_created ON jobs (source_id, created_at);
CREATE INDEX idx_jobs_experience ON jobs (experience);
CREATE INDEX idx_collection_runs_started_at ON collection_runs (started_at, id);
