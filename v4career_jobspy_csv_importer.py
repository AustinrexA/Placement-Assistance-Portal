#!/usr/bin/env python3
"""
Safe JobSpy CSV importer for V4Career.

Default mode is a local-only dry run. It reads the CSV, maps fields, validates
rows with V4Career's normalize_job(), and reports duplicates within the CSV.
It does not connect to a database unless BOTH write-confirmation flags are used.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

SOURCE_DETAILS = {
    "indeed": ("Indeed", "https://www.indeed.com"),
    "naukri": ("Naukri", "https://www.naukri.com"),
}


def source_details(site: str) -> tuple[str, str]:
    key = (site or "").strip().casefold()
    if key not in SOURCE_DETAILS:
        raise ValueError(
            f"Unsupported source '{site}'. This importer currently supports Indeed and Naukri only."
        )
    return SOURCE_DETAILS[key]


def map_row(row: dict[str, str]) -> dict:
    """Map JobSpy CSV columns into the raw shape expected by normalize_job()."""
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
        description="Dry-run or import JobSpy CSV data into V4Career."
    )
    parser.add_argument("--project-dir", required=True, help="Path to the V4Career project folder")
    parser.add_argument("--csv", required=True, help="JobSpy CSV file to inspect/import")
    parser.add_argument("--write", action="store_true", help="Persist normalized records to the configured database")
    parser.add_argument(
        "--confirm-database-write",
        action="store_true",
        help="Required together with --write to allow database changes",
    )
    args = parser.parse_args()

    if args.write != args.confirm_database_write:
        parser.error("For safety, database writes require BOTH --write and --confirm-database-write.")

    project_dir = Path(args.project_dir).expanduser().resolve()
    csv_path = Path(args.csv).expanduser().resolve()
    if not project_dir.is_dir():
        parser.error(f"Project directory does not exist: {project_dir}")
    if not csv_path.is_file():
        parser.error(f"CSV file does not exist: {csv_path}")

    sys.path.insert(0, str(project_dir))
    try:
        from collectors.normalization import normalize_job
    except Exception as exc:
        print(f"ERROR: Could not import V4Career normalization code: {exc}", file=sys.stderr)
        return 2

    grouped: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    duplicates_in_csv = 0
    invalid: list[tuple[int, str]] = []
    total_rows = 0

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                print("ERROR: CSV has no header row.", file=sys.stderr)
                return 2
            missing = {"site", "title", "job_url"}.difference(reader.fieldnames)
            if missing:
                print("ERROR: CSV is missing required columns: " + ", ".join(sorted(missing)), file=sys.stderr)
                return 2

            for row_number, row in enumerate(reader, start=2):
                total_rows += 1
                try:
                    source_name, base_url = source_details(row.get("site", ""))
                    normalized = normalize_job(map_row(row))
                    dedupe_key = (source_name.casefold(), normalized["url_hash"])
                    if dedupe_key in seen:
                        duplicates_in_csv += 1
                        continue
                    seen.add(dedupe_key)
                    normalized["__source_base_url"] = base_url
                    grouped[source_name].append(normalized)
                except Exception as exc:
                    invalid.append((row_number, str(exc)))
    except (OSError, csv.Error) as exc:
        print(f"ERROR: Could not read CSV: {exc}", file=sys.stderr)
        return 2

    valid_count = sum(len(items) for items in grouped.values())
    print("\nV4Career JobSpy CSV import report")
    print("--------------------------------")
    print(f"CSV file:                 {csv_path}")
    print(f"Total CSV rows:           {total_rows}")
    print(f"Valid unique rows:        {valid_count}")
    print(f"Duplicates within CSV:    {duplicates_in_csv}")
    print(f"Invalid/rejected rows:    {len(invalid)}")
    print("\nCounts by source:")
    for source_name in sorted(grouped):
        print(f"  {source_name}: {len(grouped[source_name])}")

    if invalid:
        print("\nFirst 20 rejected rows:")
        for row_number, reason in invalid[:20]:
            print(f"  Row {row_number}: {reason}")

    if not args.write:
        print("\nDRY RUN ONLY: no database connection was opened and no data was written.")
        print("Note: this report detects duplicates inside this CSV only, not existing database records.")
        return 0

    try:
        from dotenv import load_dotenv
        load_dotenv(project_dir / ".env", override=False)
    except ImportError:
        print("ERROR: python-dotenv is unavailable; cannot load the project .env safely.", file=sys.stderr)
        return 2

    try:
        from collectors.repository import save_jobs
    except Exception as exc:
        print(f"ERROR: Could not import V4Career repository: {exc}", file=sys.stderr)
        return 2

    print("\nDATABASE WRITE MODE enabled by explicit confirmation.")
    print("This calls V4Career's existing save_jobs() upsert pipeline.")
    for source_name in sorted(grouped):
        items = grouped[source_name]
        if not items:
            continue
        base_url = items[0].pop("__source_base_url")
        for item in items:
            item.pop("__source_base_url", None)
        result = save_jobs(source_name, base_url, items, source_type="job_website")
        print(
            f"{source_name}: found={result.get('found')}, "
            f"inserted={result.get('inserted')}, updated={result.get('updated')}"
        )
    print("\nImport finished. Verify the website and database counts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
