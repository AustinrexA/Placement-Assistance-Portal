
import argparse
import hashlib
import logging
import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit

from apify_client import ApifyClient
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from collectors.normalization import normalize_job
from collectors.repository import save_jobs

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# IT job categories. Add or remove roles as needed.
DEFAULT_IT_ROLES = [
    "Software Engineer",
    "Full Stack Developer",
    "Frontend Developer",
    "Backend Developer",
    "Java Developer",
    "Python Developer",
    "Mobile App Developer",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "AI Engineer",
    "Cloud Engineer",
    "AWS Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Cyber Security Analyst",
    "Information Security Engineer",
    "Network Engineer",
    "System Administrator",
    "IT Support Engineer",
    "Service Desk Analyst",
    "Desktop Support Engineer",
    "Application Support Engineer",
    "Database Administrator",
    "SQL Developer",
    "QA Engineer",
    "Software Tester",
    "Automation Test Engineer",
    "Business Analyst IT",
    "IT Project Manager",
    "IT Infrastructure Engineer",
    "Technical Support Engineer",
    "ERP Consultant",
    "SAP Consultant",
]

DEFAULT_LOCATIONS = [
    "Bengaluru",
    "Chennai",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Delhi NCR",
    "Kolkata",
    "Ahmedabad",
    "Kochi",
    "Coimbatore",
]


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().casefold())


def location_text(value):
    if isinstance(value, dict):
        return (
            value.get("raw")
            or value.get("city")
            or value.get("name")
            or value.get("label")
            or ""
        )

    if isinstance(value, list):
        return ", ".join(
            str(item).strip() for item in value if item
        )

    return str(value).strip() if value else ""


def extract_job_url(item):
    fields = (
        "platform_url", "job_url", "jobUrl", "job_link",
        "jobLink", "job_url_link", "url", "link",
        "apply_url", "applyUrl", "official_url", "jobDetailsUrl",
    )

    value = next(
        (item.get(field) for field in fields if item.get(field)),
        None,
    )

    if isinstance(value, dict):
        value = value.get("url") or value.get("href") or value.get("link")

    return value.strip() if isinstance(value, str) and value.strip() else None


def map_actor_item(item):
    if not isinstance(item, dict):
        raise ValueError("Dataset item must be a JSON object")

    return {
        "external_id": (
            item.get("id") or item.get("job_id")
            or item.get("jobId") or item.get("jobID")
        ),
        "title": (
            item.get("title") or item.get("job_title")
            or item.get("jobTitle")
        ),
        "company": (
            item.get("company_name") or item.get("company")
            or item.get("companyName")
        ),
        "location": location_text(item.get("location")),
        "experience": (
            item.get("experience_range") or item.get("experience")
            or item.get("experienceRange") or item.get("experienceText")
            or item.get("job_level") or item.get("jobLevel")
        ),
        "skills": (
            item.get("skills") or item.get("key_skills")
            or item.get("keySkills")
        ),
        "description": (
            item.get("description") or item.get("job_description")
            or item.get("jobDescription")
        ),
        "job_url": extract_job_url(item),
        "posted_at": (
            item.get("posted_date") or item.get("postedAt")
            or item.get("posted_at") or item.get("postedDate")
            or item.get("published_at") or item.get("created_at")
        ),
        "status": item.get("status") or "active",
    }


def canonical_url(value):
    """Remove URL tracking parameters for duplicate comparison."""
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parts = urlsplit(value.strip())

        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            return None

        host = parts.hostname.lower()
        if host.startswith("www."):
            host = host[4:]

        port = parts.port
        if port and not (
            (parts.scheme.lower() == "https" and port == 443)
            or (parts.scheme.lower() == "http" and port == 80)
        ):
            host = f"{host}:{port}"

        return urlunsplit((
            parts.scheme.lower(),
            host,
            parts.path.rstrip("/") or "/",
            "",
            "",
        ))
    except (ValueError, TypeError):
        return None


def dedup_key(job):
    url = canonical_url(job.get("job_url"))
    if url:
        return ("url", url)

    external_id = job.get("external_id")
    if external_id is not None and str(external_id).strip():
        return ("id", str(external_id).strip().casefold())

    title = normalize_text(job.get("title"))
    company = normalize_text(job.get("company"))
    location = normalize_text(job.get("location"))

    if title and company:
        return ("details", title, company, location)

    # Last-resort fingerprint for records with limited fields.
    import json
    payload = json.dumps(job, sort_keys=True, default=str)
    return ("hash", hashlib.sha256(payload.encode()).hexdigest())


def unique_values(values):
    result = []
    seen = set()

    for value in values:
        value = value.strip()
        key = normalize_text(value)

        if value and key not in seen:
            seen.add(key)
            result.append(value)

    return result


def collect_search(client, actor_id, keyword, location, max_results):
    """Run one Actor search for one role and one location."""
    run_input = {
        "keyword": keyword,
        "location": location,
        "maxJobs": max_results,
        "experienceMin": 0,
    }

    logger.info(
        "Searching role=%r location=%r limit=%s",
        keyword, location, max_results,
    )

    run = client.actor(actor_id).call(run_input=run_input)

    if not run:
        raise RuntimeError("Apify returned no run information")

    if run.get("status") != "SUCCEEDED":
        raise RuntimeError(
            f"Apify Actor status: {run.get('status')}"
        )

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise RuntimeError("Apify run has no default dataset ID")

    items = client.dataset(dataset_id).list_items(
        limit=max_results
    ).items

    valid_jobs = []
    skipped = 0

    for index, item in enumerate(items, start=1):
        try:
            job = normalize_job(map_actor_item(item))

            if not isinstance(job, dict) or not job:
                skipped += 1
                continue

            valid_jobs.append(job)

        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            skipped += 1
            logger.warning(
                "Skipping record %s for %s / %s: %s",
                index, keyword, location, exc,
            )

    logger.info(
        "Finished %s / %s: retrieved=%s valid=%s skipped=%s",
        keyword, location, len(items), len(valid_jobs), skipped,
    )

    return valid_jobs, len(items), skipped, run.get("id")


def main():
    parser = argparse.ArgumentParser(
        description="Collect IT jobs from Naukri across multiple Indian locations."
    )

    parser.add_argument(
        "--keyword",
        default=None,
        help="Search only one role, e.g. 'Python Developer'.",
    )
    parser.add_argument(
        "--roles",
        default=None,
        help="Custom comma-separated IT roles.",
    )
    parser.add_argument(
        "--location",
        default=None,
        help="Search only one location.",
    )
    parser.add_argument(
        "--locations",
        default=None,
        help="Custom comma-separated locations.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum dataset records per role/location search (1-100).",
    )

    args = parser.parse_args()

    if not 1 <= args.max_results <= 100:
        parser.error("--max-results must be between 1 and 100")

    if args.keyword and args.roles:
        parser.error("Use either --keyword or --roles, not both.")

    if args.location and args.locations:
        parser.error("Use either --location or --locations, not both.")

    # A single keyword preserves the previous command's behaviour.
    if args.keyword:
        roles = unique_values([args.keyword])
    elif args.roles:
        roles = unique_values(args.roles.split(","))
    else:
        roles = DEFAULT_IT_ROLES

    if args.location:
        locations = unique_values([args.location])
    elif args.locations:
        locations = unique_values(args.locations.split(","))
    else:
        locations = DEFAULT_LOCATIONS

    if not roles:
        parser.error("At least one IT role is required.")

    if not locations:
        parser.error("At least one location is required.")

    token = os.getenv("APIFY_API_TOKEN", "").strip()
    actor_id = os.getenv(
        "APIFY_NAUKRI_ACTOR_ID",
        "automation-lab~naukri-scraper",
    ).strip()

    if not token:
        parser.error("APIFY_API_TOKEN is missing from the project-root .env file.")

    if not actor_id:
        parser.error("APIFY_NAUKRI_ACTOR_ID cannot be empty.")
    if os.getenv("APIFY_ACCESS_APPROVED_NAUKRI", "false").lower() != "true":
        parser.error("Confirm the Actor's terms, pricing, and your permission to collect/reuse its data, then set APIFY_ACCESS_APPROVED_NAUKRI=true in .env.")

    total_searches = len(roles) * len(locations)

    logger.info("IT roles: %s", len(roles))
    logger.info("Locations: %s", len(locations))
    logger.info("Actor searches planned: %s", total_searches)
    logger.info("Max records per search: %s", args.max_results)
    logger.info(
        "Maximum requested records: %s",
        total_searches * args.max_results,
    )

    try:
        client = ApifyClient(token)
    except Exception:
        logger.exception("Could not initialize Apify client.")
        raise SystemExit(1)

    unique_jobs = {}
    failures = []
    run_ids = []
    total_retrieved = 0
    total_skipped = 0
    completed = 0

    # Search every role in every location.
    for role in roles:
        for location in locations:
            try:
                jobs, retrieved, skipped, run_id = collect_search(
                    client=client,
                    actor_id=actor_id,
                    keyword=role,
                    location=location,
                    max_results=args.max_results,
                )

                completed += 1
                total_retrieved += retrieved
                total_skipped += skipped

                if run_id:
                    run_ids.append(run_id)

                for job in jobs:
                    key = dedup_key(job)
                    if key not in unique_jobs:
                        unique_jobs[key] = job

                logger.info(
                    "Progress: %s/%s searches; unique jobs=%s",
                    completed, total_searches, len(unique_jobs),
                )

            except Exception as exc:
                failures.append({
                    "role": role,
                    "location": location,
                    "error": str(exc),
                })
                logger.exception(
                    "Search failed for role=%r location=%r; continuing.",
                    role, location,
                )

    jobs_to_save = list(unique_jobs.values())

    logger.info("All searches finished.")
    logger.info("Successful searches: %s", completed)
    logger.info("Failed searches: %s", len(failures))
    logger.info("Dataset records retrieved: %s", total_retrieved)
    logger.info("Invalid records skipped: %s", total_skipped)
    logger.info("Unique valid jobs to save: %s", len(jobs_to_save))

    if not jobs_to_save:
        print({
            "roles": roles,
            "locations": locations,
            "retrieved": total_retrieved,
            "unique_jobs": 0,
            "skipped": total_skipped,
            "failures": failures,
            "apify_run_ids": run_ids,
        })

        if completed == 0:
            raise SystemExit("Every Actor search failed.")
        return

    try:
        database_result = save_jobs(
            source_name="Naukri",
            base_url="https://www.naukri.com",
            jobs=jobs_to_save,
            source_type="job_website",
        )
    except Exception:
        logger.exception("Failed to save jobs to MySQL.")
        raise SystemExit(1)

    print("IT jobs import result:", {
        "roles_searched": len(roles),
        "locations_searched": len(locations),
        "searches_completed": completed,
        "searches_failed": len(failures),
        "records_retrieved": total_retrieved,
        "unique_jobs_validated": len(jobs_to_save),
        "invalid_records_skipped": total_skipped,
        "failures": failures,
        "apify_run_ids": run_ids,
        "database_result": database_result,
    })


if __name__ == "__main__":
    main()
