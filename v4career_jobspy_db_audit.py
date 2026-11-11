#!/usr/bin/env python3
"""
Read-only audit: compare normalized JobSpy CSV URLs with existing V4Career jobs.

This script performs SELECT queries only. It does not insert, update, or delete
jobs, sources, or collection_runs. It prints matching job titles/source names,
not database credentials.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_DETAILS = {
    "indeed": ("Indeed", "https://www.indeed.com"),
    "naukri": ("Naukri", "https://www.naukri.com"),
}


def map_row(row: dict[str, str]) -> dict:
    return {
        "external_id": (row.get("id") or "").strip() or None,
        "title": (row.get("title") or "").strip(),
        "company": (row.get("company") or "").strip() or None,
        "location": (row.get("location") or "").strip() or None,
        "job_url": (row.get("job_url") or row.get("url") or "").strip(),
        "description": (row.get("description") or "").strip() or None,
        "posted_at": (row.get("date_posted") or "").strip() or None,
        "salary_min": (row.get("min_amount") or "").strip() or None,
        "salary_max": (row.get("max_amount") or "").strip() or None,
        "salary_currency": (row.get("currency") or "INR").strip().upper(),
        "salary_period": (row.get("interval") or "year").strip().lower(),
        "skills": (row.get("skills") or "").strip() or None,
        "experience": (row.get("experience_range") or "").strip() or None,
        "status": "unknown",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only comparison of JobSpy CSV jobs against V4Career database."
    )
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    csv_path = Path(args.csv).expanduser().resolve()
    if not project_dir.is_dir():
        parser.error(f"Project directory does not exist: {project_dir}")
    if not csv_path.is_file():
        parser.error(f"CSV file does not exist: {csv_path}")

    try:
        from dotenv import load_dotenv
        load_dotenv(project_dir / ".env", override=False)
    except ImportError:
        print("ERROR: python-dotenv is not installed in this Python environment.", file=sys.stderr)
        return 2

    sys.path.insert(0, str(project_dir))
    try:
        from collectors.normalization import normalize_job
        from collectors.db import get_connection
    except Exception as exc:
        print(f"ERROR: Could not import V4Career database/normalization modules: {exc}", file=sys.stderr)
        return 2

    jobs_by_hash: dict[str, list[dict]] = defaultdict(list)
    rejected = 0
    rows_read = 0

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"site", "title", "job_url"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                print("ERROR: CSV must contain site, title, and job_url columns.", file=sys.stderr)
                return 2
            for row in reader:
                rows_read += 1
                site = (row.get("site") or "").strip().casefold()
                if site not in SOURCE_DETAILS:
                    rejected += 1
                    continue
                try:
                    normalized = normalize_job(map_row(row))
                    jobs_by_hash[normalized["url_hash"]].append({
                        "site": SOURCE_DETAILS[site][0],
                        "title": normalized["title"],
                        "company": normalized.get("company") or "",
                        "url_hash": normalized["url_hash"],
                    })
                except Exception:
                    rejected += 1
    except (OSError, csv.Error) as exc:
        print(f"ERROR: Could not read CSV: {exc}", file=sys.stderr)
        return 2

    if not jobs_by_hash:
        print("No valid supported Indeed/Naukri rows were found.")
        return 2

    hashes = list(jobs_by_hash)
    connection = cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        placeholders = ",".join(["%s"] * len(hashes))
        cursor.execute(
            f"""SELECT j.url_hash, s.name, j.title, j.company
                FROM jobs j
                LEFT JOIN sources s ON s.id = j.source_id
                WHERE j.url_hash IN ({placeholders})""",
            tuple(hashes),
        )
        records = cursor.fetchall()
    except Exception as exc:
        print(f"ERROR: Read-only database query failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    existing_by_hash: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        url_hash, source_name, title, company = record
        existing_by_hash[str(url_hash)].append({
            "source": source_name or "(unknown source)",
            "title": title or "",
            "company": company or "",
        })

    same_source = 0
    cross_source_only = 0
    not_found = 0
    details = []

    for url_hash, csv_jobs in jobs_by_hash.items():
        existing = existing_by_hash.get(url_hash, [])
        for csv_job in csv_jobs:
            same = [item for item in existing if (item["source"] or "").casefold() == csv_job["site"].casefold()]
            cross = [item for item in existing if (item["source"] or "").casefold() != csv_job["site"].casefold()]
            if same:
                same_source += 1
                status = "EXISTS_IN_SAME_SOURCE"
                matches = same
            elif cross:
                cross_source_only += 1
                status = "URL_EXISTS_IN_OTHER_SOURCE"
                matches = cross
            else:
                not_found += 1
                status = "NOT_FOUND_BY_URL"
                matches = []
            details.append((status, csv_job, matches))

    print("\nV4Career JobSpy database audit (READ ONLY)")
    print("-----------------------------------------")
    print(f"CSV rows read:                 {rows_read}")
    print(f"Valid supported rows:          {sum(len(v) for v in jobs_by_hash.values())}")
    print(f"Rejected/unsupported rows:     {rejected}")
    print(f"Matching existing records:     {len(records)} database row(s)")
    print(f"Already in same source:        {same_source}")
    print(f"URL found in another source:   {cross_source_only}")
    print(f"URL not found in database:     {not_found}")
    print("\nFirst 30 row-level results:")
    for status, csv_job, matches in details[:30]:
        print(f"- {status}: [{csv_job['site']}] {csv_job['title']} — {csv_job['company']}")
        for match in matches[:3]:
            print(f"    DB: [{match['source']}] {match['title']} — {match['company']}")

    print("\nREAD ONLY: this script ran SELECT queries only. No data was changed.")
    print("Note: 'URL not found' means the normalized URL hash was not found; it does not prove job relevance or freshness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
