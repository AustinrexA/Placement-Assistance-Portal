
import logging
import os

import requests
from dotenv import load_dotenv

from collectors.base import BaseCollector
from collectors.normalization import normalize_job

load_dotenv()

logger = logging.getLogger(__name__)


class NaukriAuthorizedFeedCollector(BaseCollector):
    """
    Adapter for a company-approved Naukri API/feed.

    This collector does not scrape Naukri webpages.
    It makes no request unless explicit authorization and a feed URL
    are configured.
    """

    source_name = "Naukri"
    base_url = "https://www.naukri.com"
    source_type = "job_website"

    def fetch_jobs(self) -> list[dict]:
        approved = (
            os.getenv("NAUKRI_ACCESS_APPROVED", "false").lower()
            == "true"
        )
        feed_url = os.getenv("NAUKRI_FEED_URL", "").strip()
        token = os.getenv("NAUKRI_API_TOKEN", "").strip()

        if not approved:
            raise RuntimeError(
                "Naukri collection is disabled. Confirm written authorization "
                "and configure NAUKRI_ACCESS_APPROVED=true first."
            )

        if not feed_url:
            raise RuntimeError(
                "NAUKRI_FEED_URL is missing. Configure the approved feed/API endpoint."
            )

        headers = {"Accept": "application/json"}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.get(
                feed_url,
                headers=headers,
                timeout=(5, 30),
            )
            response.raise_for_status()
            payload = response.json()

        except requests.RequestException as exc:
            logger.exception("Naukri feed request failed")
            raise RuntimeError("Unable to retrieve jobs from the approved feed") from exc

        except ValueError as exc:
            logger.exception("Naukri feed returned invalid JSON")
            raise RuntimeError("The approved feed returned invalid JSON") from exc

        if isinstance(payload, list):
            items = payload
        elif (
            isinstance(payload, dict)
            and isinstance(payload.get("jobs"), list)
        ):
            items = payload["jobs"]
        else:
            raise ValueError(
                "Unsupported feed response. Expected a JSON list or {'jobs': [...]}."
            )

        jobs = []
        skipped = 0

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                skipped += 1
                logger.warning(
                    "Skipping Naukri record %s: expected a JSON object",
                    index,
                )
                continue

            raw_job = {
                "external_id": item.get("id") or item.get("jobId"),
                "title": item.get("title") or item.get("jobTitle"),
                "company": item.get("company") or item.get("companyName"),
                "location": item.get("location") or item.get("jobLocation"),
                "experience": (
                    item.get("experience")
                    or item.get("experienceLevel")
                    or item.get("experienceText")
                ),
                "skills": item.get("skills"),
                "description": (
                    item.get("description")
                    or item.get("jobDescription")
                ),
                "job_url": item.get("url") or item.get("jobUrl"),
                "posted_at": (
                    item.get("posted_at")
                    or item.get("postedDate")
                ),
                "status": item.get("status") or "unknown",
            }

            try:
                job = normalize_job(raw_job)
                jobs.append(job)

            except (ValueError, TypeError, AttributeError) as exc:
                skipped += 1
                logger.warning(
                    "Skipping invalid Naukri record %s: %s",
                    index,
                    exc,
                )

        logger.info(
            "Naukri feed processing complete: received=%s valid=%s skipped=%s",
            len(items),
            len(jobs),
            skipped,
        )

        return jobs
