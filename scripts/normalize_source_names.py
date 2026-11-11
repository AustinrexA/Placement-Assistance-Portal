"""Safely consolidate the legacy 'Naukri via Apify' source into 'Naukri'.

Dry-run is the default. Pass --apply only after taking a MySQL backup.
The migration removes duplicate alias rows only when the canonical source
already has the same source-scoped URL hash; otherwise it reassigns the row.
"""
import argparse
from pathlib import Path
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.repository import get_connection
from collectors.db import is_mysql
from collectors.source_catalog import PORTAL_BY_KEY


def main():
    parser = argparse.ArgumentParser(description="Consolidate legacy V4Career source aliases")
    parser.add_argument("--apply", action="store_true", help="Apply changes; default is a read-only dry run")
    args = parser.parse_args()

    portal = PORTAL_BY_KEY["naukri"]
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM sources WHERE LOWER(TRIM(name)) = %s", ("naukri",))
        row = cursor.fetchone()
        canonical_id = row[0] if row else None
        cursor.execute("SELECT id, name FROM sources WHERE LOWER(TRIM(name)) IN (%s, %s)", ("naukri via apify", "naukri apify"))
        aliases = cursor.fetchall()

        if not aliases:
            print("No legacy Naukri source aliases found. No changes needed.")
            return

        if not canonical_id:
            print("Canonical Naukri source row is missing; it will be created only with --apply.")
        print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
        print(f"Legacy aliases found: {len(aliases)}")

        if not args.apply:
            for alias_id, alias_name in aliases:
                cursor.execute("SELECT COUNT(*) FROM jobs WHERE source_id = %s", (alias_id,))
                print(f"  {alias_name}: {cursor.fetchone()[0]} stored jobs")
            print("No changes made. Back up MySQL, then rerun with --apply to migrate.")
            return

        if not canonical_id:
            cursor.execute(
                "INSERT INTO sources (name, base_url, source_type, is_enabled) VALUES (%s, %s, 'job_website', TRUE)",
                (portal["name"], portal["base_url"]),
            )
            if is_mysql():
                canonical_id = cursor.lastrowid
            else:
                cursor.execute("SELECT id FROM sources WHERE name = %s", (portal["name"],))
                canonical_id = cursor.fetchone()[0]

        moved = 0
        removed_duplicates = 0
        for alias_id, alias_name in aliases:
            if is_mysql():
                cursor.execute(
                    """DELETE old_job FROM jobs old_job
                       INNER JOIN jobs canonical_job
                         ON canonical_job.source_id = %s
                        AND canonical_job.url_hash = old_job.url_hash
                       WHERE old_job.source_id = %s""",
                    (canonical_id, alias_id),
                )
            else:
                cursor.execute(
                    """DELETE FROM jobs old_job USING jobs canonical_job
                       WHERE canonical_job.source_id = %s
                         AND canonical_job.url_hash = old_job.url_hash
                         AND old_job.source_id = %s""",
                    (canonical_id, alias_id),
                )
            removed_duplicates += cursor.rowcount
            cursor.execute("UPDATE jobs SET source_id = %s WHERE source_id = %s", (canonical_id, alias_id))
            moved += cursor.rowcount
            cursor.execute("DELETE FROM sources WHERE id = %s", (alias_id,))
        connection.commit()
        print(f"Migration complete. Jobs reassigned: {moved}; duplicate alias rows removed: {removed_duplicates}.")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
