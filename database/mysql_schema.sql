-- V4Career MySQL 8 schema. Creates tables only; does not delete existing data.
-- Do not run this against a database containing tables without reviewing first.
CREATE TABLE IF NOT EXISTS sources (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    base_url VARCHAR(2048) NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'job_website',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sources_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id BIGINT UNSIGNED NOT NULL,
    external_id VARCHAR(255) DEFAULT NULL,
    url_hash CHAR(64) NOT NULL,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255) DEFAULT NULL,
    location VARCHAR(255) DEFAULT NULL,
    experience VARCHAR(255) DEFAULT NULL,
    skills JSON DEFAULT NULL,
    description TEXT,
    job_url VARCHAR(2048) NOT NULL,
    posted_at DATETIME DEFAULT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    salary_min DECIMAL(15,2) DEFAULT NULL,
    salary_max DECIMAL(15,2) DEFAULT NULL,
    salary_currency CHAR(3) NOT NULL DEFAULT 'INR',
    salary_period VARCHAR(12) NOT NULL DEFAULT 'year',
    PRIMARY KEY (id),
    UNIQUE KEY uq_jobs_source_url (source_id, url_hash),
    UNIQUE KEY uq_jobs_source_external_id (source_id, external_id),
    KEY idx_jobs_title (title(150)),
    KEY idx_jobs_company (company),
    KEY idx_jobs_location (location),
    KEY idx_jobs_status (status),
    KEY idx_jobs_posted_at (posted_at),
    KEY idx_jobs_source_posted (source_id, posted_at, id),
    KEY idx_jobs_source_created (source_id, created_at),
    KEY idx_jobs_experience (experience),
    CONSTRAINT fk_jobs_source FOREIGN KEY (source_id) REFERENCES sources(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS collection_runs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id BIGINT UNSIGNED NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP NULL DEFAULT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'running',
    records_found INT UNSIGNED NOT NULL DEFAULT 0,
    records_inserted INT UNSIGNED NOT NULL DEFAULT 0,
    records_updated INT UNSIGNED NOT NULL DEFAULT 0,
    error_message TEXT,
    PRIMARY KEY (id),
    KEY idx_runs_source_started (source_id, started_at),
    KEY idx_collection_runs_started_at (started_at, id),
    CONSTRAINT fk_runs_source FOREIGN KEY (source_id) REFERENCES sources(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
