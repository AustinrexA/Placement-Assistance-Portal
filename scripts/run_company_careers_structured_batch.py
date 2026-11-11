"""Run the built-in official-site structured collector for all catalog companies."""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from collectors.company_career_catalog import COMPANY_CAREER_SOURCES


def main():
    parser = argparse.ArgumentParser(description="Run structured official career-site collection for all catalog companies")
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--source", help="Optional single company key/name")
    parser.add_argument("--workers", type=int, default=3, help="Parallel company collectors (1-6; default: 3)")
    args = parser.parse_args()
    if not 1 <= args.max_results <= 500:
        parser.error("--max-results must be between 1 and 500")
    if not 1 <= args.max_pages <= 200:
        parser.error("--max-pages must be between 1 and 200")
    if not 3 <= args.timeout <= 60:
        parser.error("--timeout must be between 3 and 60 seconds")
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")
    sources = COMPANY_CAREER_SOURCES
    if args.source:
        from collectors.company_career_catalog import COMPANY_CAREER_BY_KEY, COMPANY_CAREER_BY_NAME
        found = COMPANY_CAREER_BY_KEY.get(args.source.strip().upper()) or COMPANY_CAREER_BY_NAME.get(args.source.strip().casefold())
        if not found:
            parser.error("Unknown company source: " + args.source)
        sources = [found]
    runner = ROOT / "scripts" / "run_company_career_structured.py"

    def run_one(source):
        command = [sys.executable, str(runner), "--source", source["key"], "--max-results", str(args.max_results), "--max-pages", str(args.max_pages), "--timeout", str(args.timeout)]
        result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
        return source, result

    failed = []
    # A small worker pool reduces total wall-clock time without flooding career sites.
    worker_count = min(args.workers, len(sources))
    print(f"Running {len(sources)} company collectors with {worker_count} worker(s).", flush=True)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(run_one, source) for source in sources]
        for future in as_completed(futures):
            source, result = future.result()
            print(f"\n=== Official structured collection: {source['name']} ===", flush=True)
            if result.stdout:
                print(result.stdout.rstrip(), flush=True)
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr, flush=True)
            if result.returncode:
                failed.append(source["name"])
                print(f"Failed: {source['name']} (exit {result.returncode}); continuing.", flush=True)
    print("\n=== Structured company collection summary ===")
    print(f"Sources attempted: {len(sources)}\nWorkers: {worker_count}\nFailed: {len(failed)}")
    if failed:
        print("Failed sources: " + ", ".join(failed))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
