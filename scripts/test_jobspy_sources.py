"""Isolated, read-only smoke test for JobSpy-supported job boards.

This script never writes to the V4Career database. It saves test results only
as CSV files in jobspy_test_results/ so the source behavior can be reviewed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SUPPORTED = {
    "indeed", "naukri", "linkedin", "glassdoor", "zip_recruiter",
    "bayt", "bdjobs", "hellowork", "google",
}


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_") or "source"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test open-source JobSpy adapters without touching V4Career's database."
    )
    parser.add_argument(
        "--sites", default="indeed,naukri",
        help="Comma-separated JobSpy site names. Default: indeed,naukri",
    )
    parser.add_argument("--keyword", default="Software Engineer")
    parser.add_argument("--location", default="Bengaluru")
    parser.add_argument("--results", type=int, default=10,
                        help="Maximum requested per site for this test (1-50).")
    parser.add_argument("--hours-old", type=int, default=168,
                        help="Limit to listings from the last N hours; use 0 to omit.")
    parser.add_argument("--country-indeed", default="India")
    parser.add_argument("--output-dir", default="jobspy_test_results")
    args = parser.parse_args()

    if not 1 <= args.results <= 50:
        parser.error("--results must be between 1 and 50 for this initial test")
    if args.hours_old < 0:
        parser.error("--hours-old must be 0 or greater")

    requested = [x.strip().lower() for x in args.sites.split(",") if x.strip()]
    unsupported = [x for x in requested if x not in SUPPORTED]
    sites = [x for x in requested if x in SUPPORTED]
    if unsupported:
        print("Unsupported JobSpy site name(s) skipped:", ", ".join(unsupported))
    if not sites:
        print("No supported JobSpy sites requested. Supported names:", ", ".join(sorted(SUPPORTED)))
        return 2

    try:
        from jobspy import scrape_jobs
        import pandas as pd
    except ImportError:
        print("JobSpy is not installed. Run: python -m pip install -r requirements-jobspy-test.txt")
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    report = {
        "mode": "read-only JobSpy test; no database writes",
        "keyword": args.keyword,
        "location": args.location,
        "requested_results_per_site": args.results,
        "sites": [],
        "unsupported_requested_sites": unsupported,
    }

    for site in sites:
        entry = {"site": site, "status": "started", "rows": 0, "errors": {}, "warnings": {}}
        print(f"\nTesting {site}: keyword={args.keyword!r}, location={args.location!r}")
        try:
            kwargs = {
                "site_name": [site],
                "search_term": args.keyword,
                "location": args.location,
                "results_wanted": args.results,
                "country_indeed": args.country_indeed,
                "verbose": 1,
            }
            if args.hours_old:
                kwargs["hours_old"] = args.hours_old
            jobs = scrape_jobs(**kwargs)
            errors = getattr(jobs, "attrs", {}).get("errors", {}) or {}
            warnings = getattr(jobs, "attrs", {}).get("warnings", {}) or {}
            entry["errors"] = errors
            entry["warnings"] = warnings
            entry["rows"] = int(len(jobs)) if jobs is not None else 0
            entry["status"] = "error" if errors.get(site) else ("results" if entry["rows"] else "empty_or_blocked")

            if jobs is not None and len(jobs):
                jobs = jobs.copy()
                if "site" not in jobs.columns:
                    jobs["site"] = site
                path = out_dir / f"{safe_name(site)}_{safe_name(args.location)}_{safe_name(args.keyword)}.csv"
                jobs.to_csv(path, index=False, encoding="utf-8-sig")
                entry["csv"] = str(path)
                frames.append(jobs)
                show_cols = [c for c in ("title", "company", "location", "job_url") if c in jobs.columns]
                if show_cols:
                    print(jobs[show_cols].head(5).to_string(index=False))
            else:
                print("  No rows returned. Check warnings/errors below; this does not prove the portal has no jobs.")
            if errors:
                print("  Errors:", json.dumps(errors, ensure_ascii=False, default=str))
            if warnings:
                print("  Warnings:", json.dumps(warnings, ensure_ascii=False, default=str))
        except Exception as exc:
            entry["status"] = "exception"
            entry["errors"] = {site: f"{type(exc).__name__}: {exc}"}
            print(f"  ERROR: {type(exc).__name__}: {exc}")
        report["sites"].append(entry)
        # Small pause between sites to avoid a burst of requests.
        time.sleep(2)

    if frames:
        combined = pd.concat(frames, ignore_index=True, sort=False)
        combined_path = out_dir / "jobspy_combined_test.csv"
        combined.to_csv(combined_path, index=False, encoding="utf-8-sig")
        report["combined_rows_before_deduplication"] = int(len(combined))
        report["combined_csv"] = str(combined_path)
        if "job_url" in combined.columns:
            urls = combined["job_url"].dropna().astype(str).str.strip()
            report["unique_nonempty_job_urls"] = int(urls[urls.ne("")].nunique())
    else:
        report["combined_rows_before_deduplication"] = 0

    report_path = out_dir / "jobspy_test_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nSummary:")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"\nReport saved to: {report_path}")
    print("No V4Career database or production files were changed by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
