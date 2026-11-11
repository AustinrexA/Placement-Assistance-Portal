#!/usr/bin/env python3
"""Run JobSpy for Indeed + Naukri and save completed results to V4Career's DB.

Run from the V4Career project root:
  python scripts/run_jobspy.py --results-per-site 50

Database writes are enabled by default. Use --dry-run to collect and report without
writing to the database. By default there is no overall runtime limit; each individual
search still has a 40-second timeout. Use --minutes N to set an optional overall budget.
The script uses the existing .env, normalize_job(), and save_jobs() functions.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import json
import logging
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from collectors.normalization import normalize_job
from collectors.repository import save_jobs

ROLES = [
    "Software Engineer", "Software Developer", "Graduate Engineer Trainee",
    "Graduate Trainee", "Software Developer Intern", "Python Developer",
    "Java Developer", "C++ Developer", "C Developer", ".NET Developer",
    "PHP Developer", "Node.js Developer", "Full Stack Developer",
    "Frontend Developer", "Backend Developer", "Web Developer",
    "UI Developer", "React Developer", "Angular Developer", "Android Developer",
    "iOS Developer", "Data Analyst", "Data Analyst Intern", "Business Analyst",
    "Product Analyst", "Data Engineer", "Data Scientist", "Machine Learning Engineer",
    "AI Engineer", "NLP Engineer", "MLOps Engineer", "DevOps Engineer",
    "Site Reliability Engineer", "Platform Engineer", "Cloud Engineer",
    "Cloud Support Associate", "Cybersecurity Analyst", "Information Security Analyst",
    "Network Engineer", "System Administrator", "IT Support Engineer",
    "Technical Support Engineer", "Application Support Engineer",
    "Database Administrator", "SQL Developer", "QA Engineer", "QA Analyst",
    "Manual Tester", "Automation Test Engineer", "SDET", "Salesforce Developer",
    "SAP Consultant", "Technical Writer",
]
LOCATIONS = ["Chennai", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "Delhi NCR",
    "Noida", "Gurugram", "Kolkata", "Ahmedabad", "Jaipur", "Kochi",
    "Thiruvananthapuram", "Coimbatore", "Mysuru", "Mangalore", "Indore",
    "Bhubaneswar", "Chandigarh", "Lucknow", "Nagpur", "Visakhapatnam",
    "Vadodara", "Surat", "Trichy", "Madurai", "Vijayawada", "Gandhinagar",]

SOURCE_INFO = {
    "indeed": ("Indeed", "https://in.indeed.com/"),
    "naukri": ("Naukri", "https://www.naukri.com/"),
    "linkedin": ("LinkedIn Jobs", "https://www.linkedin.com/jobs/"),
    "glassdoor": ("Glassdoor", "https://www.glassdoor.co.in/Job/"),
    "bayt": ("Bayt", "https://www.bayt.com/"),
    
}



def scrape_one(sites, role, location, results_wanted, hours_old, output_path, queue):
    """Worker runs one combined site query and returns rows plus portal errors."""
    captures = {}

    class _PortalLogCapture(logging.Handler):
        def __init__(self):
            super().__init__(level=logging.WARNING)
            self.messages = []
        def emit(self, record):
            self.messages.append(record.getMessage())

    try:
        # Capture JobSpy warnings so HTTP 429/406 blocks are visible even when
        # scrape_jobs returns an empty DataFrame instead of raising.
        for portal in ("jobspy.linkedin", "jobspy.naukri"):
            handler = _PortalLogCapture()
            logging.getLogger(portal).addHandler(handler)
            captures[portal] = handler

        from jobspy import scrape_jobs
        jobs = scrape_jobs(
            site_name=sites,
            search_term=role,
            location=location,
            results_wanted=results_wanted,
            country_indeed="India",
            description_format="plain",
            fetch_description=True,
            hours_old=hours_old,
            verbose=0,
        )
        jobs.to_csv(output_path, index=False, encoding="utf-8-sig")

        errors = getattr(jobs, "attrs", {}).get("errors", {}) or {}
        log_messages = {
            portal: handler.messages for portal, handler in captures.items()
        }
        requested_sites = {str(site).casefold() for site in sites}
        blocked_sites = set()

        for site, error in errors.items():
            message = str(error).casefold()
            if any(code in message for code in ("429", "406", "captcha", "recaptcha", "blocked", "rate limit")):
                blocked_sites.add(str(site).casefold())

        for portal, messages in log_messages.items():
            site = portal.rsplit(".", 1)[-1]
            if site not in requested_sites:
                continue
            if any(any(term in msg.casefold() for term in
                       ("429", "406", "recaptcha required", "captcha", "blocked", "rate limited"))
                   for msg in messages):
                blocked_sites.add(site)

        queue.put({
            "ok": True,
            "count": int(len(jobs)),
            "errors": errors,
            "blocked_sites": sorted(blocked_sites),
            "portal_messages": log_messages,
        })
    except Exception as exc:
        queue.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        for portal, handler in captures.items():
            logging.getLogger(portal).removeHandler(handler)


def nonempty(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.casefold() in {"nan", "none", "nat"}:
        return None
    return value


def row_to_job(row):
    site = (nonempty(row.get("site")) or "").casefold()
    if site not in SOURCE_INFO:
        raise ValueError(f"Unsupported JobSpy site: {site!r}")
    raw = {
        "external_id": nonempty(row.get("id") or row.get("job_id")),
        "title": nonempty(row.get("title")),
        "company": nonempty(row.get("company")),
        "location": nonempty(row.get("location")),
        "experience": nonempty(row.get("experience_range") or row.get("experience")),
        "salary_min": nonempty(row.get("min_amount")),
        "salary_max": nonempty(row.get("max_amount")),
        "salary_currency": nonempty(row.get("currency")) or "INR",
        "salary_period": nonempty(row.get("interval")) or "year",
        "skills": nonempty(row.get("skills")),
        "description": nonempty(row.get("description")),
        "job_url": nonempty(row.get("job_url") or row.get("url")),
        "posted_at": nonempty(row.get("date_posted") or row.get("posted_at")),
        "status": "active",
    }
    return site, normalize_job(raw)


def save_completed_csv(csv_path, dry_run, seen_hashes, totals):
    grouped = defaultdict(list)
    row_errors = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                site, job = row_to_job(row)
                if job["url_hash"] in seen_hashes[site]:
                    totals["duplicates_in_run"] += 1
                    continue
                seen_hashes[site].add(job["url_hash"])
                grouped[site].append(job)
            except (ValueError, TypeError, AttributeError) as exc:
                row_errors += 1
                if row_errors <= 5:
                    print(f"  Skipped invalid CSV row: {exc}")
    totals["invalid_rows"] += row_errors

    for site, jobs in grouped.items():
        source_name, base_url = SOURCE_INFO[site]
        if dry_run:
            print(f"  DRY RUN {source_name}: {len(jobs)} validated unique jobs; database unchanged")
            totals["validated"] += len(jobs)
            continue
        try:
            result = save_jobs(source_name, base_url, jobs, source_type="job_website")
            totals["validated"] += len(jobs)
            totals["inserted"] += int(result.get("inserted", 0))
            totals["updated"] += int(result.get("updated", 0))
            print(
                f"  DB saved {source_name}: found={result.get('found', 0)}, "
                f"inserted={result.get('inserted', 0)}, updated={result.get('updated', 0)}"
            )
        except Exception as exc:
            totals["db_errors"] += 1
            print(f"  DATABASE SAVE FAILED for {source_name}: {type(exc).__name__}: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Collect Indeed + Naukri + LinkedIn + Glassdoor jobs and save directly to V4Career DB.")
    parser.add_argument("--minutes", type=float, default=0, help="Optional overall run budget in minutes; 0 means run all combinations (default: no overall limit)")
    parser.add_argument("--sites", nargs="+", choices=sorted(SOURCE_INFO), default=["indeed", "naukri", "linkedin", "glassdoor","bayt"], help="JobSpy sites to query (default: all four configured sites)")
    parser.add_argument("--results-per-site", type=int, default=100, help="Requested results per site/search (default 100)")
    parser.add_argument("--output-dir", default=str(ROOT / "jobspy_results"), help="Directory for run CSVs")
    parser.add_argument("--roles", nargs="*", help="Optional role list")
    parser.add_argument("--locations", nargs="*", help="Optional location list")
    parser.add_argument("--hours-old", type=int, default=None, help="Optional posting-age filter in hours, if supported by installed JobSpy")
    parser.add_argument("--dry-run", action="store_true", help="Collect and validate without database writes")
    parser.add_argument("--restart", action="store_true", help="Restart search rotation from the first role/location instead of resuming progress")
    args = parser.parse_args()
    if args.minutes < 0:
        parser.error("--minutes must be 0 (no overall limit) or greater")
    if not 1 <= args.results_per_site <= 1000:
        parser.error("--results-per-site must be between 1 and 1000")
    if args.hours_old is not None and args.hours_old < 1:
        parser.error("--hours-old must be at least 1")

    roles = args.roles or ROLES
    locations = args.locations or LOCATIONS
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = out_dir / "completed_searches"
    temp_dir.mkdir(exist_ok=True)
    # Round-robin locations for each role, rather than exhausting Chennai first.
    # Example order: Software Engineer/Chennai, Software Engineer/Bengaluru, ...
    combinations = [(role, location) for role in roles for location in locations]
    progress_path = out_dir / "jobspy_progress.json"
    signature = {"roles": roles, "locations": locations, "sites": args.sites}
    start_index = 0
    if args.restart:
        try:
            progress_path.unlink()
        except FileNotFoundError:
            pass
        print("Progress reset: starting from the first role/location combination.")
    elif progress_path.exists():
        try:
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            if progress.get("signature") == signature:
                start_index = int(progress.get("next_index", 0)) % max(1, len(combinations))
                if start_index:
                    print(f"Resuming at combination {start_index + 1} of {len(combinations)}.")
            else:
                print("Saved progress belongs to a different role/location list; starting from the first combination.")
        except (OSError, ValueError, TypeError):
            print("Saved progress could not be read; starting from the first combination.")
    deadline = (time.monotonic() + args.minutes * 60) if args.minutes > 0 else None
    ctx = mp.get_context("spawn")
    completed_files = []
    seen_hashes = defaultdict(set)
    totals = Counter()
    start = time.monotonic()
    interrupted = None

    print("Starting JobSpy: " + ", ".join(args.sites))
    print(f"Time budget: {args.minutes:g} minutes" if args.minutes > 0 else "Time budget: no overall limit (40-second per-search timeout remains)")
    print(f"Requested per site/search: {args.results_per_site}")
    print(f"Database mode: {'DRY RUN (no writes)' if args.dry_run else 'LIVE WRITE using V4Career .env database'}")
    print(f"Search combinations available: {len(combinations)}")

    for index0 in range(start_index, len(combinations)):
        index = index0 + 1
        role, location = combinations[index0]
        remaining = (deadline - time.monotonic()) if deadline is not None else None
        if remaining is not None and remaining <= 2:
            break
        safe_role = "".join(c if c.isalnum() else "_" for c in role).strip("_")
        safe_location = "".join(c if c.isalnum() else "_" for c in location).strip("_")
        result_file = temp_dir / f"{index:03d}_{safe_role}_{safe_location}.csv"
        queue = ctx.Queue()
        process = ctx.Process(target=scrape_one, args=(args.sites, role, location, args.results_per_site, args.hours_old, str(result_file), queue))
        query_started = time.monotonic()
        process.start()
        wait_seconds = 40.0 if deadline is None else min(40.0, max(0, deadline - time.monotonic()))
        process.join(timeout=wait_seconds)
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
            if deadline is not None and deadline - time.monotonic() <= 2:
                interrupted = (role, location)
                print(f"Time limit reached while searching {role} | {location}.")
                # Retry this combination at the start of the next run.
                progress_path.write_text(json.dumps({"signature": signature, "next_index": index0}, indent=2), encoding="utf-8")
                break
            totals["timed_out_searches"] += 1
            print(f"[timeout] {role} | {location}; moving to next search")
            progress_path.write_text(json.dumps({"signature": signature, "next_index": (index0 + 1) % len(combinations)}, indent=2), encoding="utf-8")
            continue
        result = None
        try:
            if not queue.empty():
                result = queue.get_nowait()
        except Exception:
            pass
        finally:
            queue.close()
        elapsed = time.monotonic() - query_started
        if not result or not result.get("ok") or not result_file.exists():
            totals["failed_searches"] += 1
            print(f"[failed] {role} | {location}: {(result or {}).get('error', 'worker returned no result')}")
            progress_path.write_text(json.dumps({"signature": signature, "next_index": (index0 + 1) % len(combinations)}, indent=2), encoding="utf-8")
            continue
        blocked_sites = result.get("blocked_sites", [])
        if blocked_sites:
            totals["blocked_searches"] += 1
            print(f"[BLOCKED] {', '.join(blocked_sites)} | {role} | {location}")
        for site, error in (result.get("errors") or {}).items():
            print(f"  [portal error] {site}: {error}")
        for portal, messages in (result.get("portal_messages") or {}).items():
            site = portal.rsplit(".", 1)[-1]
            if site in blocked_sites:
                for message in messages[:2]:
                    print(f"  {site}: {message}")

        # Keep partial rows from non-blocked portals even if another portal
        # in the combined JobSpy request was blocked.
        completed_files.append(result_file)
        totals["completed_searches"] += 1
        totals["raw_rows"] += result.get("count", 0)
        status = "partial (one or more portals blocked)" if blocked_sites else "completed"
        print(f"[{status}] {role} | {location}: {result.get('count', 0)} raw rows in {elapsed:.1f}s")
        # Crucial: save each completed search immediately, so a later timeout does not lose prior results.
        save_completed_csv(result_file, args.dry_run, seen_hashes, totals)
        progress_path.write_text(json.dumps({"signature": signature, "next_index": (index0 + 1) % len(combinations)}, indent=2), encoding="utf-8")

    # Combined CSV is retained as an audit/export artifact, not required for DB saving.
    import pandas as pd
    frames = []
    for file_path in completed_files:
        try:
            frame = pd.read_csv(file_path)
            if not frame.empty:
                frames.append(frame)
        except Exception as exc:
            print(f"Warning: unable to read {file_path.name} for combined CSV: {exc}")
    combined_path = out_dir / "jobspy_combined_latest.csv"
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        if "job_url" in combined.columns:
            combined = combined.drop_duplicates(subset=["job_url"], keep="first")
        combined.to_csv(combined_path, index=False, encoding="utf-8-sig")
        totals["combined_unique_rows"] = len(combined)
    else:
        combined_path.write_text("", encoding="utf-8")
        totals["combined_unique_rows"] = 0

    print("\n--- JOBSPY RUN SUMMARY ---")
    print(f"Elapsed seconds: {time.monotonic() - start:.1f}")
    for key in ("completed_searches", "blocked_searches", "raw_rows", "combined_unique_rows", "validated", "inserted", "updated", "duplicates_in_run", "invalid_rows", "timed_out_searches", "failed_searches", "db_errors"):
        print(f"{key.replace('_', ' ').title()}: {totals.get(key, 0)}")
    print(f"Combined CSV: {combined_path}")
    print(f"Resume progress: {progress_path} (use --restart to start over)")
    if interrupted:
        print(f"Interrupted search at deadline: {interrupted[0]} | {interrupted[1]}")
    if args.dry_run:
        print("DRY RUN finished: no database writes were performed.")
    elif totals.get("db_errors", 0):
        print("WARNING: one or more database saves failed; see messages above.")
    elif totals.get("inserted", 0) or totals.get("updated", 0):
        print("Database saving completed through V4Career's existing repository.")
    elif totals.get("validated", 0):
        print("Search results were validated; no database inserts or updates were needed.")
    else:
        print("No jobs were collected and no database changes were made.")


if __name__ == "__main__":
    mp.freeze_support()
    main()
