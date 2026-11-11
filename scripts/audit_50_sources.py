"""Audit readiness of the 25 portal and 25 company catalogs without exposing secrets."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from collectors.source_catalog import JOB_PORTALS, DEFAULT_APIFY_ACTORS
from collectors.company_career_catalog import COMPANY_CAREER_SOURCES

def truthy(name):
    return os.getenv(name, "false").strip().lower() == "true"

def main():
    token_present = bool(os.getenv("APIFY_API_TOKEN", "").strip())
    print("V4Career source readiness audit (does not start scraping)")
    print(f"Apify token configured: {'yes' if token_present else 'no'}")
    print("\nJOB PORTALS")
    portal_ready = 0
    for p in JOB_PORTALS:
        key = p["key"]
        actor = os.getenv(f"APIFY_ACTOR_{key}", "").strip()
        if key == "NAUKRI" and not actor:
            actor = os.getenv("APIFY_NAUKRI_ACTOR_ID", "").strip()
        actor = actor or DEFAULT_APIFY_ACTORS.get(key, "")
        approved = truthy(f"APIFY_ACCESS_APPROVED_{key}")
        input_json = os.getenv(f"APIFY_INPUT_{key}", "").strip()
        # A built-in schema is provided for these Actors; still requires explicit approval and a test run.
        built_in = key in {"NAUKRI", "INDEED", "FOUNDIT", "INTERNSHALA", "TIMESJOBS", "WELLFOUND", "CUTSHORT", "INSTAHYRE", "HIRIST", "APNA", "SHINE_COM", "IIMJOBS", "WORKINDIA", "GLASSDOOR", "LINKEDIN_JOBS", "FRESHERSWORLD", "NATIONAL_CAREER_SERVICE_NCS", "JOOBLE", "QUIKRJOBS", "JORA"}
        ready = bool(token_present and actor and approved and (input_json or built_in))
        portal_ready += int(ready)
        if not actor:
            reason = "missing Actor ID"
        elif not approved:
            reason = "approval flag is off"
        elif not (input_json or built_in):
            reason = "needs verified APIFY_INPUT JSON"
        elif not token_present:
            reason = "missing APIFY_API_TOKEN"
        else:
            reason = "configured; still requires a test run"
        print(f"- {p['name']}: {'READY-TO-TEST' if ready else 'PENDING'} ({reason})")

    print("\nCOMPANY CAREER SITES")
    print("The structured runner attempts public official pages for all catalog companies.")
    print("It saves only valid India-located schema.org JobPosting entries; zero jobs may mean")
    print("the page has no supported JSON-LD, not that the company has no vacancies.")
    for c in COMPANY_CAREER_SOURCES:
        print(f"- {c['name']}: STRUCTURED-COLLECTOR-AVAILABLE (live extraction not yet verified)")
    print("\nSUMMARY")
    print(f"Portal catalog: {len(JOB_PORTALS)}; ready-to-test portal configs: {portal_ready}; pending: {len(JOB_PORTALS)-portal_ready}")
    print(f"Company catalog: {len(COMPANY_CAREER_SOURCES)}; structured attempts available: {len(COMPANY_CAREER_SOURCES)}")
    print("This audit does not guarantee any source will return jobs or start a scrape.")

if __name__ == "__main__":
    main()
