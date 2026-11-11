#!/usr/bin/env python3
"""
Five-minute JobSpy collector for Indeed + Naukri.
- Runs locally and uses no Apify credits.
- Does not connect to or write to V4Career's database.
- Saves completed results to CSV.
- Stops launching new searches at the time limit; an in-progress search is
  terminated at the deadline so the total run is bounded.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import time
from pathlib import Path

ROLES = [
    "Software Engineer",
    "Python Developer",
    "Java Developer",
    "Full Stack Developer",
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "Data Engineer",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "QA Engineer",
    "Cloud Engineer",
    "Android Developer",
    "React Developer",
    "Graduate Engineer Trainee",
]

LOCATIONS = [
    "Chennai",
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Delhi NCR",
]


def scrape_one(site_names, role, location, results_wanted, output_path, queue):
    """Worker process: write a completed search to its own CSV."""
    try:
        from jobspy import scrape_jobs

        jobs = scrape_jobs(
            site_name=site_names,
            search_term=role,
            location=location,
            results_wanted=results_wanted,
            country_indeed="India",
            description_format="plain",
            verbose=1,
        )
        jobs.to_csv(output_path, index=False, encoding="utf-8-sig")
        queue.put({
            "ok": True,
            "role": role,
            "location": location,
            "count": int(len(jobs)),
            "path": str(output_path),
            "errors": getattr(jobs, "attrs", {}).get("errors", {}),
            "warnings": getattr(jobs, "attrs", {}).get("warnings", {}),
        })
    except Exception as exc:
        queue.put({
            "ok": False,
            "role": role,
            "location": location,
            "error": f"{type(exc).__name__}: {exc}",
            "path": str(output_path),
        })


def main():
    parser = argparse.ArgumentParser(description="Fetch Indeed + Naukri jobs for up to five minutes.")
    parser.add_argument("--minutes", type=float, default=5.0, help="Total time budget (default: 5)")
    parser.add_argument("--results-per-site", type=int, default=100, help="Requested limit per site per search (default: 100)")
    parser.add_argument("--output-dir", default="jobspy_5min_results", help="Output folder")
    parser.add_argument("--roles", nargs="*", help="Optional roles to search instead of the default list")
    parser.add_argument("--locations", nargs="*", help="Optional locations to search instead of the default list")
    args = parser.parse_args()

    if args.minutes <= 0 or args.minutes > 5:
        parser.error("--minutes must be greater than 0 and no more than 5.")
    if args.results_per_site < 1 or args.results_per_site > 1000:
        parser.error("--results-per-site must be between 1 and 1000.")

    roles = args.roles or ROLES
    locations = args.locations or LOCATIONS
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = out_dir / "completed_searches"
    temp_dir.mkdir(exist_ok=True)

    combinations = [(role, location) for location in locations for role in roles]
    deadline = time.monotonic() + args.minutes * 60
    completed_paths = []
    completed_searches = 0
    total_rows = 0
    errors = []
    interrupted = None
    start = time.monotonic()

    print("Starting free local JobSpy run: Indeed + Naukri")
    print(f"Time budget: {args.minutes:g} minutes | requested per site/search: {args.results_per_site}")
    print(f"Search combinations available: {len(combinations)}")
    print("Results are saved to CSV only; the V4Career database will NOT be changed.\n")

    ctx = mp.get_context("spawn")
    for index, (role, location) in enumerate(combinations, start=1):
        remaining = deadline - time.monotonic()
        if remaining <= 2:
            break

        safe_role = "".join(c if c.isalnum() else "_" for c in role).strip("_")
        safe_location = "".join(c if c.isalnum() else "_" for c in location).strip("_")
        result_file = temp_dir / f"{index:03d}_{safe_role}_{safe_location}.csv"
        queue = ctx.Queue()
        process = ctx.Process(
            target=scrape_one,
            args=(["indeed", "naukri"], role, location, args.results_per_site, str(result_file), queue),
        )
        query_started = time.monotonic()
        process.start()
        process.join(timeout=min(40.0, max(0, deadline - time.monotonic())))

        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
            remaining_after_timeout = deadline - time.monotonic()
            if remaining_after_timeout <= 2:
                interrupted = (role, location)
                print(f"\nTime limit reached while searching '{role}' in '{location}'.")
                break
            message = "search exceeded the 40-second per-search limit and was stopped"
            errors.append(f"{role} | {location}: {message}")
            print(f"[timeout] {role} | {location}: {message}; moving to next search")
            continue

        result = None
        try:
            if not queue.empty():
                result = queue.get_nowait()
        except Exception:
            result = None
        finally:
            queue.close()

        elapsed = time.monotonic() - query_started
        if result and result.get("ok") and result_file.exists():
            completed_paths.append(result_file)
            completed_searches += 1
            total_rows += result["count"]
            print(f"[{completed_searches}] {role} | {location}: {result['count']} rows in {elapsed:.1f}s")
            if result.get("errors"):
                print(f"    Source errors: {result['errors']}")
            if result.get("warnings"):
                print(f"    Source warnings: {result['warnings']}")
        else:
            message = result.get("error") if result else f"worker exited with code {process.exitcode}"
            errors.append(f"{role} | {location}: {message}")
            print(f"[skip] {role} | {location}: {message}")

    # Combine every completed search into one output file.
    import pandas as pd

    combined_path = out_dir / "jobspy_5min_combined.csv"
    frames = []
    for file_path in completed_paths:
        try:
            frame = pd.read_csv(file_path)
            if not frame.empty:
                frames.append(frame)
        except Exception as exc:
            errors.append(f"Could not read {file_path.name}: {exc}")

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        before = len(combined)
        if "job_url" in combined.columns:
            combined = combined.drop_duplicates(subset=["job_url"], keep="first")
        combined.to_csv(combined_path, index=False, encoding="utf-8-sig")
        unique_rows = len(combined)
        duplicates_removed = before - unique_rows
    else:
        combined_path.write_text("", encoding="utf-8")
        unique_rows = 0
        duplicates_removed = 0

    elapsed_total = min(time.monotonic() - start, args.minutes * 60)
    print("\n--- FIVE-MINUTE RUN SUMMARY ---")
    print(f"Elapsed time:             {elapsed_total:.1f} seconds")
    print(f"Completed searches:       {completed_searches}")
    print(f"Raw rows from searches:   {total_rows}")
    print(f"Unique rows in combined:  {unique_rows}")
    print(f"Duplicates removed:       {duplicates_removed}")
    print(f"Combined CSV:             {combined_path}")
    if interrupted:
        print(f"Interrupted search:       {interrupted[0]} | {interrupted[1]}")
    if errors:
        print(f"Searches with errors:     {len(errors)}")
        for item in errors[:10]:
            print(f"  - {item}")
    print("\nNo database writes were performed.")
    print("Note: the time cap is strict; a search still running at the deadline is terminated and its partial results may be lost.")


if __name__ == "__main__":
    mp.freeze_support()
    main()
