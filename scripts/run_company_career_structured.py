"""Collect real, schema.org JobPosting vacancies from one official company site.

This collector does not need an Apify Actor or token. It only accepts
JobPosting JSON-LD from an allowlisted official host and only keeps listings
whose structured location indicates India. If a site does not expose usable
public structured listings, it returns zero and reports that fact honestly.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from collectors.company_career_catalog import COMPANY_CAREER_SOURCES, COMPANY_CAREER_BY_KEY, COMPANY_CAREER_BY_NAME
from collectors.company_career_structured import collect_structured_jobs
from collectors.repository import record_failed_run, save_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Collect structured vacancies from an official company career site")
    parser.add_argument("--source", required=True, help="Company key or catalog name, e.g. TCS or 'TCS Careers'")
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    if not 1 <= args.max_results <= 500:
        parser.error("--max-results must be between 1 and 500")
    if not 1 <= args.max_pages <= 200:
        parser.error("--max-pages must be between 1 and 200")
    if not 3 <= args.timeout <= 60:
        parser.error("--timeout must be between 3 and 60 seconds")
    source = COMPANY_CAREER_BY_KEY.get(args.source.strip().upper()) or COMPANY_CAREER_BY_NAME.get(args.source.strip().casefold())
    if not source:
        parser.error("Unknown company source. Use: " + ", ".join(s["key"] for s in COMPANY_CAREER_SOURCES))
    try:
        jobs, stats = collect_structured_jobs(source, max_results=args.max_results, max_pages=args.max_pages, timeout=args.timeout)
        if stats["pages_fetched"] == 0:
            message = (
                "Could not successfully fetch any configured official career pages "
                f"(attempted={stats['pages_attempted']}, blocked={stats['pages_blocked']}, "
                f"network_errors={stats['pages_network_errors']}, http_errors={stats['pages_http_errors']}). "
                "This is a failed collection run, not a verified zero-vacancy result. "
                "Check site access and use a reviewed official feed/ATS or approved collection method."
            )
            record_failed_run(source["name"], source["base_url"], message)
            raise SystemExit(message)
    except SystemExit:
        raise
    except Exception as exc:
        try:
            record_failed_run(source["name"], source["base_url"], exc)
        except Exception as db_exc:
            logging.error("Could not record failed run: %s", db_exc)
        raise SystemExit(f"Company career collection failed for {source['name']}: {exc}") from exc
    # A successful zero-result run means pages were accessible but did not
    # expose valid India-located JobPosting JSON-LD; no vacancy is fabricated.
    result = save_jobs(source["name"], source["base_url"], jobs, source_type="company_career")
    print(json.dumps({"source": source["name"], "method": "official_jsonld_jobposting", **stats, **result}, indent=2))


if __name__ == "__main__":
    main()
