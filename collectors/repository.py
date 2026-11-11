"""Database repository for V4Career job collection and persistence."""
import json
from collectors.db import get_connection, is_mysql

NAUKRI_SOURCE_NAMES = ("Naukri", "Naukri via Apify")


def is_naukri_source(name, base_url):
    normalized_name = (name or "").strip().casefold()
    normalized_url = (base_url or "").strip().casefold()
    return normalized_name in {item.casefold() for item in NAUKRI_SOURCE_NAMES} and "naukri.com" in normalized_url


def _in_clause(values):
    return ",".join(["%s"] * len(values))


def ensure_source(cursor, name, base_url, source_type="job_website"):
    """Create or update a source and return its ID without engine-specific upsert SQL."""
    if is_naukri_source(name, base_url):
        names = [item.casefold() for item in NAUKRI_SOURCE_NAMES]
        cursor.execute(
            f"SELECT id FROM sources WHERE LOWER(name) IN ({_in_clause(names)}) AND LOWER(base_url) LIKE %s ORDER BY CASE WHEN LOWER(name) = %s THEN 0 ELSE 1 END, id LIMIT 1",
            tuple(names) + ("%naukri.com%", "naukri via apify"),
        )
        row = cursor.fetchone()
        if row is not None:
            return row[0]
    cursor.execute("SELECT id FROM sources WHERE name = %s LIMIT 1", (name,))
    row = cursor.fetchone()
    if row:
        if source_type == "company_career":
            cursor.execute("UPDATE sources SET base_url = %s, source_type = %s, is_enabled = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (base_url, source_type, row[0]))
        else:
            cursor.execute("UPDATE sources SET base_url = %s, source_type = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (base_url, source_type, row[0]))
        return row[0]
    if is_mysql():
        cursor.execute("INSERT INTO sources (name, base_url, source_type, is_enabled) VALUES (%s, %s, %s, TRUE)", (name, base_url, source_type))
        return cursor.lastrowid
    cursor.execute("INSERT INTO sources (name, base_url, source_type, is_enabled) VALUES (%s, %s, %s, TRUE) RETURNING id", (name, base_url, source_type))
    return cursor.fetchone()[0]


def get_naukri_source_ids(cursor, name, base_url):
    if not is_naukri_source(name, base_url):
        return []
    names = [item.casefold() for item in NAUKRI_SOURCE_NAMES]
    cursor.execute(f"SELECT id FROM sources WHERE LOWER(name) IN ({_in_clause(names)}) AND LOWER(base_url) LIKE %s", tuple(names) + ("%naukri.com%",))
    return [row[0] for row in cursor.fetchall()]


def start_run(cursor, source_id):
    if is_mysql():
        cursor.execute("INSERT INTO collection_runs (source_id, status) VALUES (%s, 'running')", (source_id,))
        return cursor.lastrowid
    cursor.execute("INSERT INTO collection_runs (source_id, status) VALUES (%s, 'running') RETURNING id", (source_id,))
    return cursor.fetchone()[0]


def _serialized_skills(job):
    skills = job.get("skills")
    return json.dumps(skills) if isinstance(skills, (list, dict)) else skills



def update_existing_job(cursor, job_id, job):
    """Update an existing job while keeping SQL compatible with MySQL and PostgreSQL.

    Use a bound boolean for salary presence instead of testing untyped NULL
    parameters in SQL; PostgreSQL cannot infer the type of those parameters.
    """
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    has_salary = salary_min is not None or salary_max is not None
    salary_currency = job.get("salary_currency") or "INR"
    salary_period = job.get("salary_period") or "year"

    cursor.execute("""
        UPDATE jobs SET
            external_id = COALESCE(%s, external_id),
            url_hash = COALESCE(%s, url_hash),
            title = %s,
            company = %s,
            location = %s,
            experience = %s,
            salary_min = COALESCE(%s, salary_min),
            salary_max = COALESCE(%s, salary_max),
            salary_currency = CASE
                WHEN %s THEN %s ELSE salary_currency END,
            salary_period = CASE
                WHEN %s THEN %s ELSE salary_period END,
            skills = %s,
            description = %s,
            job_url = %s,
            posted_at = COALESCE(%s, posted_at),
            status = %s,
            last_seen_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (
        job.get("external_id"),
        job.get("url_hash"),
        job["title"],
        job.get("company"),
        job.get("location"),
        job.get("experience"),
        salary_min,
        salary_max,
        has_salary,
        salary_currency,
        has_salary,
        salary_period,
        _serialized_skills(job),
        job.get("description"),
        job["job_url"],
        job.get("posted_at"),
        job.get("status", "unknown"),
        job_id,
    ))


def upsert_job(cursor, source_id, job, naukri_source_ids=None):
    """Insert/update safely, checking URL hash before source-scoped external ID."""
    cursor.execute("SELECT id FROM jobs WHERE source_id = %s AND url_hash = %s LIMIT 1", (source_id, job["url_hash"]))
    existing = cursor.fetchone()
    if existing:
        update_existing_job(cursor, existing[0], job)
        return "updated"

    # Some Actors reuse a stable external ID while their URL changes. Check it
    # before INSERT so uq_jobs_source_external_id cannot abort the entire run.
    external_id = job.get("external_id")
    if external_id not in (None, ""):
        cursor.execute("SELECT id FROM jobs WHERE source_id = %s AND external_id = %s LIMIT 1", (source_id, str(external_id)))
        existing_external = cursor.fetchone()
        if existing_external:
            update_existing_job(cursor, existing_external[0], job)
            return "updated"
    alias_ids = [int(value) for value in (naukri_source_ids or []) if int(value) != int(source_id)]
    if alias_ids:
        cursor.execute(f"SELECT id FROM jobs WHERE url_hash = %s AND source_id IN ({_in_clause(alias_ids)}) ORDER BY id LIMIT 1", (job["url_hash"], *alias_ids))
        alias = cursor.fetchone()
        if alias:
            update_existing_job(cursor, alias[0], job)
            return "updated"
    cursor.execute("""INSERT INTO jobs (source_id, external_id, url_hash, title, company, location, experience,
        salary_min, salary_max, salary_currency, salary_period, skills, description, job_url, posted_at, status, last_seen_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)""",
        (source_id, job.get("external_id"), job["url_hash"], job["title"], job.get("company"), job.get("location"),
         job.get("experience"), job.get("salary_min"), job.get("salary_max"), job.get("salary_currency", "INR"),
         job.get("salary_period", "year"), _serialized_skills(job), job.get("description"), job["job_url"],
         job.get("posted_at"), job.get("status", "unknown")))
    return "inserted"


def finish_run(cursor, run_id, status, found, inserted, updated, error=None):
    cursor.execute("""UPDATE collection_runs SET finished_at = CURRENT_TIMESTAMP, status = %s,
        records_found = %s, records_inserted = %s, records_updated = %s, error_message = %s WHERE id = %s""",
        (status, found, inserted, updated, error, run_id))


def save_jobs(source_name, base_url, jobs, source_type="job_website"):
    """Persist collected jobs and collection-run metrics."""
    connection = cursor = None
    run_id = None
    found, inserted, updated = len(jobs), 0, 0
    try:
        connection = get_connection()
        cursor = connection.cursor()
        source_id = ensure_source(cursor, source_name, base_url, source_type)
        naukri_source_ids = get_naukri_source_ids(cursor, source_name, base_url)
        run_id = start_run(cursor, source_id)
        connection.commit()
        for job in jobs:
            outcome = upsert_job(cursor, source_id, job, naukri_source_ids=naukri_source_ids)
            inserted += outcome == "inserted"
            updated += outcome == "updated"
        finish_run(cursor, run_id, "success", found, inserted, updated)
        connection.commit()
        return {"source": source_name, "found": found, "inserted": inserted, "updated": updated}
    except Exception as exc:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        if connection and run_id is not None:
            try:
                if cursor is None:
                    cursor = connection.cursor()
                finish_run(cursor, run_id, "failed", found, 0, 0, str(exc)[:60000])
                connection.commit()
            except Exception:
                try:
                    connection.rollback()
                except Exception:
                    pass
        raise
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if connection:
            try: connection.close()
            except Exception: pass


def record_failed_run(source_name, base_url, error, source_type="company_career"):
    """Record a collector failure in the existing cross-database run history."""
    connection = cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        source_id = ensure_source(cursor, source_name, base_url, source_type)
        run_id = start_run(cursor, source_id)
        finish_run(cursor, run_id, "failed", 0, 0, 0, str(error)[:60000])
        connection.commit()
        return {"source": source_name, "status": "failed", "error": str(error)}
    except Exception:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection:
            try:
                connection.close()
            except Exception:
                pass
