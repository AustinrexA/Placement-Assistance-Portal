-- Safe, non-destructive performance indexes for existing V4Career PostgreSQL/Neon databases.
-- Run once in the target database. CREATE INDEX IF NOT EXISTS leaves existing data unchanged.
CREATE INDEX IF NOT EXISTS idx_jobs_source_posted ON jobs (source_id, posted_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source_created ON jobs (source_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_experience ON jobs (experience);
CREATE INDEX IF NOT EXISTS idx_collection_runs_started_at ON collection_runs (started_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_collection_runs_source_started ON collection_runs (source_id, started_at DESC, id DESC);
