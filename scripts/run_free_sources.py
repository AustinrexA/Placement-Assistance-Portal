"""Collect jobs from permitted free/public APIs without Apify.

Safe by default: fetches and reports only. Pass --save only after reviewing
output and configuring DATABASE_URL for the existing V4Career repository.
India filtering is intentionally conservative; this is not a 5,000-job guarantee.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from collectors.normalization import normalize_job
from collectors.repository import save_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("v4career.free_sources")
USER_AGENT = "V4CareerFreeCollector/1.0 (job discovery; respects source terms)"
INDIA_RE = re.compile(
    r"\b(india|bengaluru|bangalore|chennai|hyderabad|pune|mumbai|gurugram|gurgaon|"
    r"noida|new delhi|delhi|kolkata|kochi|cochin|thiruvananthapuram|trivandrum|"
    r"ahmedabad|jaipur|lucknow|indore|coimbatore|mysuru|mysore|vadodara|"
    r"visakhapatnam|vizag|bhubaneswar|chandigarh)\b", re.I
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


def get_json(url, params=None, timeout=20):
    response = SESSION.get(url, params=params, timeout=timeout)
    if response.status_code in (401, 403, 429):
        raise RuntimeError(f"Source refused or rate-limited request (HTTP {response.status_code})")
    response.raise_for_status()
    return response.json()


def job_is_india(raw):
    loc = " ".join(str(raw.get(k) or "") for k in (
        "location", "jobGeo", "job_location", "jobLocation", "locations",
        "country", "countryCode", "applicantLocationRequirements"
    ))
    # Strict: global remote listings are not assumed eligible in India.
    return bool(INDIA_RE.search(loc))


def normalize_record(raw, source, company_fallback=None):
    """Map a source record to V4Career's existing normalized job schema."""
    title = raw.get("title") or raw.get("position") or raw.get("jobTitle") or raw.get("name")
    url = raw.get("job_url") or raw.get("url") or raw.get("apply_url") or raw.get("jobUrl")
    company = raw.get("company") or raw.get("companyName") or raw.get("employer") or company_fallback
    location = raw.get("location") or raw.get("jobGeo") or raw.get("job_location") or raw.get("jobLocation")
    if isinstance(location, list):
        location = ", ".join(str(x) for x in location)
    if isinstance(location, dict):
        location = ", ".join(str(v) for v in location.values() if v)
    description = raw.get("description") or raw.get("jobDescription") or raw.get("content") or raw.get("summary")
    posted = raw.get("posted_at") or raw.get("date") or raw.get("pubDate") or raw.get("createdAt") or raw.get("created_at")
    external_id = raw.get("id") or raw.get("job_id") or raw.get("jobId") or raw.get("requisitionId")
    skills = raw.get("tags") or raw.get("jobIndustry") or raw.get("skills")
    if isinstance(skills, str):
        skills = [skills]
    mapped = {
        "external_id": external_id,
        "title": title,
        "company": company,
        "location": location,
        "experience": raw.get("experience") or raw.get("jobLevel") or raw.get("seniority"),
        "salary_min": raw.get("salary_min") or raw.get("salaryMin"),
        "salary_max": raw.get("salary_max") or raw.get("salaryMax"),
        "salary_currency": raw.get("salary_currency") or raw.get("salaryCurrency") or "INR",
        "salary_period": raw.get("salary_period") or raw.get("salaryPeriod") or "year",
        "salary": raw.get("salary") or raw.get("salaryDescription"),
        "skills": skills,
        "description": description,
        "job_url": url,
        "posted_at": posted,
        "status": "active",
    }
    return normalize_job(mapped)


def configured_boards(config, provider):
    boards = config.get(provider, [])
    if not isinstance(boards, list):
        raise ValueError(f"config[{provider!r}] must be a list")
    clean = []
    for item in boards:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or "").strip()
        company = str(item.get("company") or "").strip()
        if slug and company:
            clean.append({"slug": slug, "company": company})
    return clean


def fetch_greenhouse(config, limit):
    results = []
    for board in configured_boards(config, "greenhouse"):
        url = f"https://boards-api.greenhouse.io/v1/boards/{board['slug']}/jobs"
        payload = get_json(url, params={"content": "true"})
        for item in payload.get("jobs", [])[:limit]:
            location = (item.get("location") or {}).get("name", "")
            raw = {
                "id": item.get("id"),
                "title": item.get("title"),
                "company": board["company"],
                "location": location,
                "url": item.get("absolute_url"),
                "posted_at": item.get("updated_at"),
                "description": item.get("content"),
            }
            if job_is_india(raw):
                results.append((board["company"], raw))
        time.sleep(0.25)
    return results


def fetch_lever(config, limit):
    results = []
    for board in configured_boards(config, "lever"):
        url = f"https://api.lever.co/v0/postings/{board['slug']}"
        payload = get_json(url, params={"mode": "json"})
        if not isinstance(payload, list):
            LOG.warning("Lever response was not a list for board %s", board["slug"])
            continue
        for item in payload[:limit]:
            cats = item.get("categories") or {}
            location = cats.get("location") or cats.get("allLocations") or ""
            raw = {
                "id": item.get("id"),
                "title": item.get("text"),
                "company": board["company"],
                "location": location,
                "url": item.get("hostedUrl") or item.get("applyUrl"),
                "posted_at": item.get("createdAt"),
                "description": item.get("descriptionPlain") or item.get("description"),
                "jobLevel": cats.get("commitment"),
            }
            if job_is_india(raw):
                results.append((board["company"], raw))
        time.sleep(0.25)
    return results


def fetch_remoteok(limit):
    payload = get_json("https://remoteok.com/api")
    if not isinstance(payload, list):
        raise RuntimeError("Remote OK returned an unexpected response")
    # First record may be API metadata; normalizer/validation will discard it.
    results = []
    for item in payload:
        if not isinstance(item, dict) or not item.get("position") or not item.get("url"):
            continue
        if job_is_india(item):
            results.append(("Remote OK", item))
        if len(results) >= limit:
            break
    return results


def fetch_jobicy(limit):
    payload = get_json("https://jobicy.com/api/v2/remote-jobs", params={"count": min(limit, 50)})
    items = payload.get("jobs", []) if isinstance(payload, dict) else []
    results = []
    for item in items:
        if isinstance(item, dict) and job_is_india(item):
            results.append(("Jobicy", item))
    return results


def load_config(path):
    if not path.exists():
        return {"greenhouse": [], "lever": []}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Board config must be a JSON object")
    return data


def main():
    parser = argparse.ArgumentParser(description="Collect from free/public job feeds and configured company boards")
    parser.add_argument("--source", choices=("all", "greenhouse", "lever", "remoteok", "jobicy"), default="all")
    parser.add_argument("--limit-per-source", type=int, default=100)
    parser.add_argument("--config", default=str(ROOT / "config" / "free_sources.json"))
    parser.add_argument("--save", action="store_true", help="Persist validated jobs to the existing database (default is dry-run)")
    args = parser.parse_args()
    if not 1 <= args.limit_per_source <= 500:
        parser.error("--limit-per-source must be between 1 and 500")

    config = load_config(Path(args.config))
    fetchers = {
        "greenhouse": lambda: fetch_greenhouse(config, args.limit_per_source),
        "lever": lambda: fetch_lever(config, args.limit_per_source),
        "remoteok": lambda: fetch_remoteok(args.limit_per_source),
        "jobicy": lambda: fetch_jobicy(args.limit_per_source),
    }
    selected = list(fetchers) if args.source == "all" else [args.source]
    totals = {"fetched": 0, "valid": 0, "unique": 0, "inserted": 0, "updated": 0, "errors": []}
    seen = set()
    for source in selected:
        try:
            records = fetchers[source]()
            normalized = []
            for company, raw in records:
                totals["fetched"] += 1
                try:
                    if not job_is_india(raw):
                        continue
                    job = normalize_record(raw, source, company_fallback=company)
                    key = job["url_hash"]
                    if key in seen:
                        continue
                    seen.add(key)
                    normalized.append(job)
                except (ValueError, TypeError, AttributeError) as exc:
                    LOG.debug("Skipping invalid record from %s: %s", source, exc)
            totals["valid"] += len(normalized)
            totals["unique"] += len(normalized)
            LOG.info("%s: valid India jobs=%d", source, len(normalized))
            if args.save and normalized:
                base_urls = {
                    "greenhouse": "https://boards-api.greenhouse.io/",
                    "lever": "https://api.lever.co/v0/postings/",
                    "remoteok": "https://remoteok.com/",
                    "jobicy": "https://jobicy.com/api/jobs",
                }
                result = save_jobs(f"{source.title()} (Free API)", base_urls[source], normalized, source_type="free_api")
                totals["inserted"] += result.get("inserted", 0)
                totals["updated"] += result.get("updated", 0)
        except Exception as exc:
            LOG.error("%s failed: %s", source, exc)
            totals["errors"].append({"source": source, "error": str(exc)})
    print(json.dumps({"mode": "save" if args.save else "dry-run", **totals}, indent=2))
    if totals["errors"] and len(totals["errors"]) == len(selected):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
