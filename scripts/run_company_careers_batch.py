"""Run every explicitly approved and configured company career-site Actor."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from collectors.company_career_catalog import COMPANY_CAREER_SOURCES


def main():
    parser = argparse.ArgumentParser(description="Run configured company career-site collectors")
    parser.add_argument("--keyword", default="Software Engineer")
    parser.add_argument("--location", default="India")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()
    if not os.getenv("APIFY_API_TOKEN", "").strip():
        raise SystemExit("APIFY_API_TOKEN is missing from the local .env file.")
    runner = ROOT / "scripts" / "run_company_career_apify.py"
    skipped, failed, attempted = [], [], 0
    for source in COMPANY_CAREER_SOURCES:
        key = source["key"]
        if not os.getenv(f"APIFY_ACTOR_COMPANY_{key}", "").strip() or not os.getenv(f"APIFY_INPUT_COMPANY_{key}", "").strip() or os.getenv(f"APIFY_ACCESS_APPROVED_COMPANY_{key}", "false").lower() != "true":
            skipped.append(source["name"])
            continue
        attempted += 1
        command = [sys.executable, str(runner), "--source", key, "--keyword", args.keyword, "--location", args.location, "--max-results", str(args.max_results)]
        print(f"\n=== Collecting {source['name']} ===", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            failed.append(source["name"])
            print(f"Failed: {source['name']} (exit {result.returncode}); continuing.", flush=True)
    print("\n=== Company career collection summary ===")
    print(f"Attempted: {attempted}\nSkipped (missing Actor/input/approval): {len(skipped)}\nFailed: {len(failed)}")
    if skipped: print("Skipped: " + ", ".join(skipped))
    if failed: print("Failed: " + ", ".join(failed))
    if failed: raise SystemExit(1)


if __name__ == "__main__":
    main()
