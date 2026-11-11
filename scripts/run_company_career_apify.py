"""Collect jobs from one configured company career-site Apify Actor.

Required per source:
  APIFY_ACTOR_COMPANY_<KEY>=owner~actor-name
  APIFY_ACCESS_APPROVED_COMPANY_<KEY>=true
  APIFY_INPUT_COMPANY_<KEY>={...}  # valid JSON for that Actor's current input schema

JSON input supports {keyword}, {location}, {max_results}, and {start_url}.
The actor's dataset should contain job title and job URL fields. This runner
uses the existing V4Career normalization, database repository, run history,
and URL-based deduplication. It does not bypass site access controls.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import sys

from apify_client import ApifyClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from collectors.company_career_catalog import COMPANY_CAREER_SOURCES, COMPANY_CAREER_BY_KEY, COMPANY_CAREER_BY_NAME
from collectors.normalization import normalize_job
from collectors.repository import save_jobs
from collectors.company_career_structured import validate_company_vacancy_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("v4career.company_careers")


def first(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def flatten(value):
    if isinstance(value, dict):
        return str(first(value, "name", "label", "city", "raw", "value") or "").strip()
    if isinstance(value, list):
        return ", ".join(part for part in (flatten(v) for v in value) if part)
    return str(value).strip() if value is not None else ""


def replace_placeholders(value, source, keyword, location, max_results):
    replacements = {
        "{keyword}": keyword,
        "{location}": location,
        "{max_results}": max_results,
        "{start_url}": source["base_url"],
    }
    if isinstance(value, str):
        if value in replacements:
            return replacements[value]
        for token, replacement in replacements.items():
            value = value.replace(token, str(replacement))
        return value
    if isinstance(value, list):
        return [replace_placeholders(item, source, keyword, location, max_results) for item in value]
    if isinstance(value, dict):
        return {key: replace_placeholders(item, source, keyword, location, max_results) for key, item in value.items()}
    return value


def map_job(item, source):
    if not isinstance(item, dict):
        raise ValueError("Actor dataset row is not a JSON object")
    url = first(item, "job_url", "jobUrl", "job_link", "jobLink", "url", "link", "apply_url", "applyUrl", "jobDetailsUrl", "absolute_url")
    if isinstance(url, dict):
        url = first(url, "url", "href", "link")
    company = first(item, "company", "company_name", "companyName", "employer", "organization", "organizationName") or source["company"]
    return {
        "external_id": first(item, "id", "job_id", "jobId", "external_id", "requisitionId", "jobReqId"),
        "title": first(item, "title", "job_title", "jobTitle", "position", "role", "name"),
        "company": flatten(company),
        "location": flatten(first(item, "location", "locations", "job_location", "jobLocation", "city", "country", "locationName")),
        "experience": first(item, "experience", "experience_range", "experienceRange", "level", "seniority"),
        "salary_min": first(item, "salary_min", "salaryMin", "minSalary"),
        "salary_max": first(item, "salary_max", "salaryMax", "maxSalary"),
        "salary_currency": first(item, "salary_currency", "salaryCurrency", "currency"),
        "salary_period": first(item, "salary_period", "salaryPeriod", "payPeriod"),
        "salary": first(item, "salary", "salaryRange", "compensation"),
        "skills": first(item, "skills", "keySkills", "technologies", "tags"),
        "description": first(item, "description", "jobDescription", "descriptionText", "summary"),
        "job_url": str(url).strip() if url else None,
        "posted_at": first(item, "posted_at", "postedAt", "posted_date", "postedDate", "datePosted", "datePublished"),
        "status": first(item, "status", "job_status") or "unknown",
    }


def validate_company_vacancy(job, source):
    return validate_company_vacancy_record(job, source)

def collect(source, keyword, location, max_results):
    key = source["key"]
    actor_id = os.getenv(f"APIFY_ACTOR_COMPANY_{key}", "").strip()
    approved = os.getenv(f"APIFY_ACCESS_APPROVED_COMPANY_{key}", "false").strip().lower() == "true"
    input_text = os.getenv(f"APIFY_INPUT_COMPANY_{key}", "").strip()
    if not actor_id:
        raise SystemExit(f"No Actor configured for {source['name']}. Set APIFY_ACTOR_COMPANY_{key} in .env.")
    if not approved:
        raise SystemExit(f"Collection disabled for {source['name']}. Review site terms and Actor permissions, then set APIFY_ACCESS_APPROVED_COMPANY_{key}=true.")
    if not input_text:
        raise SystemExit(f"Missing APIFY_INPUT_COMPANY_{key}. Add JSON matching the Actor's current input schema; do not guess the schema.")
    try:
        actor_input = json.loads(input_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"APIFY_INPUT_COMPANY_{key} must be valid JSON: {exc}")
    if not isinstance(actor_input, dict):
        raise SystemExit(f"APIFY_INPUT_COMPANY_{key} must be a JSON object.")
    actor_input = replace_placeholders(actor_input, source, keyword, location, max_results)
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("APIFY_API_TOKEN is missing from the local .env file.")

    logger.info("Starting company career Actor source=%s actor=%s", source["name"], actor_id)
    run = ApifyClient(token).actor(actor_id).call(run_input=actor_input)
    if not run or run.get("status") != "SUCCEEDED":
        raise SystemExit(f"Actor run did not succeed: {run.get('status') if run else 'no run result'}")
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise SystemExit("Actor succeeded but returned no dataset ID.")

    client = ApifyClient(token)
    normalized, skipped = [], 0
    for index, item in enumerate(client.dataset(dataset_id).iterate_items()):
        if len(normalized) >= max_results:
            break
        try:
            mapped = validate_company_vacancy(map_job(item, source), source)
            normalized.append(normalize_job(mapped))
        except (ValueError, TypeError, AttributeError) as exc:
            skipped += 1
            logger.warning("Skipping invalid %s result %s: %s", source["name"], index, exc)

    result = save_jobs(source["name"], source["base_url"], normalized, source_type="company_career")
    print(json.dumps({"source": source["name"], "actor": actor_id, "records_skipped": skipped, **result}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Collect jobs from one configured company career site")
    parser.add_argument("--source", required=True, help="Company key or name, e.g. TCS or 'TCS Careers'")
    parser.add_argument("--keyword", default="Software Engineer")
    parser.add_argument("--location", default="India")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.max_results <= 500:
        parser.error("--max-results must be between 1 and 500")
    source = COMPANY_CAREER_BY_KEY.get(args.source.strip().upper()) or COMPANY_CAREER_BY_NAME.get(args.source.strip().casefold())
    if not source:
        parser.error("Unknown company source. Use: " + ", ".join(s["key"] for s in COMPANY_CAREER_SOURCES))
    collect(source, args.keyword, args.location, args.max_results)


if __name__ == "__main__":
    main()
