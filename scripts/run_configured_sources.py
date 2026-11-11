
"""Run configured V4Career Apify sources sequentially.

Features:
- India-only location validation
- Actor ID and approval checks
- Continues after individual source failures
- Prevents overlapping collection batches
- Writes per-source logs and a CSV summary
- Optional source exclusions through .env
"""

import argparse
import csv
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))

from collectors.source_catalog import JOB_PORTALS, DEFAULT_APIFY_ACTORS


RESULTS_DIR = ROOT / "test-results"
REPORT_PATH = RESULTS_DIR / "configured_sources_summary.csv"
LOG_DIR = RESULTS_DIR / "source_logs"


@contextmanager
def collection_lock():
    """Prevent overlapping collection batches."""
    lock_path = ROOT / ".collection.lock"
    handle = open(lock_path, "a+b")

    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()

        handle.seek(0)

        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(
                    handle.fileno(), msvcrt.LK_NBLCK, 1
                )
            else:
                import fcntl
                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
        except (OSError, BlockingIOError) as exc:
            raise SystemExit(
                "Another V4Career collection batch is already running."
            ) from exc

        yield

    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(
                    handle.fileno(), msvcrt.LK_UNLCK, 1
                )
            else:
                import fcntl
                fcntl.flock(
                    handle.fileno(), fcntl.LOCK_UN
                )
        except OSError:
            pass

        handle.close()


def get_actor_id(key):
    """Resolve an Actor ID from environment configuration or defaults."""
    actor_id = os.getenv(f"APIFY_ACTOR_{key}", "").strip()

    if key == "NAUKRI" and not actor_id:
        actor_id = os.getenv("APIFY_NAUKRI_ACTOR_ID", "").strip()

    if not actor_id:
        actor_id = DEFAULT_APIFY_ACTORS.get(key, "")

    return actor_id.strip()


def is_approved(key):
    """Only run sources explicitly approved in .env."""
    return (
        os.getenv(f"APIFY_ACCESS_APPROVED_{key}", "false")
        .strip()
        .lower()
        == "true"
    )


def get_excluded_keys():
    """Read optional comma-separated exclusions from .env."""
    value = os.getenv("APIFY_BATCH_EXCLUDE_KEYS", "")
    return {
        item.strip().upper()
        for item in value.split(",")
        if item.strip()
    }


def write_report(rows):
    """Write the current batch results to CSV."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "portal",
        "key",
        "status",
        "exit_code",
        "elapsed_seconds",
        "log_file",
        "started_at",
    ]

    with REPORT_PATH.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run_one_source(portal, args):
    """Run one portal and save its output to a log."""
    key = portal["key"]
    name = portal["name"].strip()
    runner = ROOT / "scripts" / "run_source_apify.py"

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    safe_key = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in key
    )
    log_path = LOG_DIR / f"{safe_key}.log"

    command = [
        sys.executable,
        str(runner),
        "--source", key,
        "--keyword", args.keyword,
        "--location", args.location,
        "--max-results", str(args.max_results),
    ]

    print(f"\n=== Collecting {name} ({key}) ===", flush=True)
    print(f"Requested maximum: {args.max_results}", flush=True)
    print(f"Log: {log_path}", flush=True)

    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    start = time.monotonic()

    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            log.write(f"Portal: {name}\n")
            log.write(f"Key: {key}\n")
            log.write(f"Started: {started_at}\n")
            log.write(f"Command: {subprocess.list2cmdline(command)}\n\n")
            log.flush()

            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            assert process.stdout is not None

            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()

            exit_code = process.wait()

    except OSError as exc:
        exit_code = 1
        with log_path.open(
            "a", encoding="utf-8", errors="replace"
        ) as log:
            log.write(f"\nFailed to launch source runner: {exc}\n")
        print(f"Could not launch scraper for {name}: {exc}", flush=True)

    elapsed = round(time.monotonic() - start, 2)
    status = "SUCCESS" if exit_code == 0 else "FAILED"

    print(
        f"\n{status}: {name} | exit={exit_code} "
        f"| elapsed={elapsed}s",
        flush=True,
    )

    return {
        "portal": name,
        "key": key,
        "status": status,
        "exit_code": exit_code,
        "elapsed_seconds": elapsed,
        "log_file": str(log_path.relative_to(ROOT)),
        "started_at": started_at,
    }


def run_batch(args):
    """Run every configured, approved portal in catalog order."""
    rows = []
    skipped = []
    excluded = get_excluded_keys()

    portals = JOB_PORTALS

    for portal in portals:
        key = portal["key"]
        name = portal["name"].strip()

        if key.upper() in excluded or name.upper() in excluded:
            skipped.append((name, "excluded by APIFY_BATCH_EXCLUDE_KEYS"))
            continue

        actor_id = get_actor_id(key)

        if not actor_id:
            skipped.append((name, "Actor ID missing"))
            continue

        if not is_approved(key):
            skipped.append((name, "approval flag is not true"))
            continue

        # Do not launch overlapping jobs from this batch.
        # A source failure is recorded and the next source is attempted.
        try:
            row = run_one_source(portal, args)
        except Exception as exc:
            row = {
                "portal": name,
                "key": key,
                "status": "FAILED",
                "exit_code": 1,
                "elapsed_seconds": 0,
                "log_file": "",
                "started_at": datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
            }
            print(f"Unexpected error for {name}: {exc}", flush=True)

        rows.append(row)
        write_report(rows)

    print("\n========== COLLECTION SUMMARY ==========")
    print(f"Configured and attempted: {len(rows)}")
    print(
        f"Successful: "
        f"{sum(row['status'] == 'SUCCESS' for row in rows)}"
    )
    print(
        f"Failed: "
        f"{sum(row['status'] == 'FAILED' for row in rows)}"
    )
    print(f"Skipped: {len(skipped)}")

    if skipped:
        print("\nSkipped sources:")
        for name, reason in skipped:
            print(f" - {name}: {reason}")

    print(f"\nCSV report: {REPORT_PATH}")
    print(f"Individual logs: {LOG_DIR}")

    if any(row["status"] == "FAILED" for row in rows):
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run approved V4Career Apify sources sequentially."
        )
    )
    parser.add_argument(
        "--keyword",
        default="Software Engineer",
        help="Search keyword (default: Software Engineer)",
    )
    parser.add_argument(
        "--location",
        default="India",
        help='India or an Indian location ending in ", India"',
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum requested results per source (1–500)",
    )
    args = parser.parse_args()

    location = args.location.strip()

    if (
        location.lower() != "india"
        and not location.lower().endswith(", india")
    ):
        parser.error(
            "India-only collection: use India or a city/state "
            'ending in ", India".'
        )

    if not 1 <= args.max_results <= 500:
        parser.error("--max-results must be between 1 and 500")

    if not os.getenv("APIFY_API_TOKEN", "").strip():
        raise SystemExit(
            "APIFY_API_TOKEN is missing from the project's .env file."
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with collection_lock():
        run_batch(args)


if __name__ == "__main__":
    main()
