"""Conservative collector for genuine official career-site vacancies.

Only schema.org JobPosting JSON-LD objects are accepted as vacancies. Ordinary
career copy, graduate-program descriptions, menus, and links are never saved
as jobs. The collector follows a bounded number of same-host job-like links;
additional official ATS hosts must be explicitly configured per company.
"""
from __future__ import annotations

import json
import logging
import os
import re
import socket
import html as html_lib
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urldefrag

import requests

from collectors.company_career_catalog import COMPANY_CAREER_BY_KEY
from collectors.normalization import normalize_job

logger = logging.getLogger(__name__)
USER_AGENT = "V4CareerCareerCollector/1.0 (+official public career listings; contact site owner for access questions)"
JOB_LINK_HINTS = re.compile(r"(?:job|jobs|career|careers|opening|openings|requisition|position|vacanc|opportunit|posting|role)", re.I)
INDIA_HINTS = re.compile(r"\b(india|bengaluru|bangalore|chennai|hyderabad|pune|mumbai|gurugram|gurgaon|noida|new delhi|delhi|kolkata|kochi|cochin|thiruvananthapuram|trivandrum|ahmedabad|jaipur|lucknow|indore|coimbatore|mysuru|mysore|vadodara|visakhapatnam|vizag|bhubaneswar|chandigarh)\b", re.I)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._script_jsonld = False
        self._script_chunks = []
        self.jsonld = []
        self._in_title = False
        self.title_chunks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "a" and attrs.get("href"):
            self.links.append(attrs["href"].strip())
        if tag.lower() == "script" and "ld+json" in (attrs.get("type") or "").lower():
            self._script_jsonld = True
            self._script_chunks = []
        if tag.lower() == "title":
            self._in_title = True

    def handle_data(self, data):
        if self._script_jsonld:
            self._script_chunks.append(data)
        if self._in_title:
            self.title_chunks.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._script_jsonld:
            raw = "".join(self._script_chunks).strip()
            if raw:
                try:
                    self.jsonld.append(json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Ignoring malformed JSON-LD block")
            self._script_jsonld = False
            self._script_chunks = []
        if tag.lower() == "title":
            self._in_title = False


def _host(url):
    return (urlsplit(url).hostname or "").lower().rstrip(".")


def _allowed_hosts(source):
    key = source["key"]
    configured = os.getenv(f"CAREER_ALLOWED_HOSTS_{key}", "")
    values = {_host(source["base_url"])}
    values.update(_host("https://" + host.strip()) for host in source.get("allowed_hosts", []) if host.strip())
    values.update(host.strip().lower().rstrip(".") for host in configured.split(",") if host.strip())
    return {host for host in values if host}


def _is_allowed_url(url, hosts):
    try:
        parts = urlsplit(url)
        host = _host(url)
        if parts.scheme.lower() != "https" or not host or parts.username or parts.password:
            return False
        if not any(host == allowed or host.endswith("." + allowed) for allowed in hosts):
            return False
        # Refuse literal IP hosts; only public DNS names from the allowlist are used.
        try:
            socket.inet_aton(host)
            return False
        except OSError:
            return True
    except ValueError:
        return False


def _fetch(url, hosts, session, timeout):
    """Fetch one allowlisted page and return (html, final_url, outcome)."""
    if not _is_allowed_url(url, hosts):
        return None, None, "invalid_url"
    try:
        response = session.get(url, timeout=timeout, allow_redirects=False, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    except requests.RequestException as exc:
        logger.warning("Career page fetch failed for %s: %s", url, exc)
        return None, None, "network_error"
    if response.is_redirect or response.is_permanent_redirect:
        target = urljoin(url, response.headers.get("Location", ""))
        if not _is_allowed_url(target, hosts):
            logger.warning("Ignoring redirect outside configured official hosts: %s", target)
            return None, None, "external_redirect"
        try:
            response = session.get(target, timeout=timeout, allow_redirects=False, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        except requests.RequestException as exc:
            logger.warning("Career redirect fetch failed for %s: %s", target, exc)
            return None, None, "network_error"
        url = target
    if response.status_code != 200:
        logger.info("Career page returned HTTP %s: %s", response.status_code, url)
        return None, None, "blocked" if response.status_code in (401, 403, 429) else "http_error"
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type and "json" not in content_type:
        return None, None, "unsupported_content_type"
    return response.text, url, "fetched"


def _walk_jsonld(value):
    if isinstance(value, list):
        for child in value:
            yield from _walk_jsonld(child)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(t).split(":")[-1].casefold() == "jobposting" for t in types):
            yield value
        for key, child in value.items():
            if key in {"@graph", "mainEntity", "itemListElement", "item"} or isinstance(child, (dict, list)):
                yield from _walk_jsonld(child)


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(part for part in (_text(v) for v in value) if part)
    if isinstance(value, dict):
        for key in ("name", "value", "streetAddress", "addressLocality", "addressRegion", "addressCountry", "text"):
            if value.get(key) not in (None, ""):
                if key == "addressCountry" and isinstance(value[key], dict):
                    return _text(value[key])
                return _text(value[key])
    return ""


def _locations(job):
    raw = job.get("jobLocation") or job.get("applicantLocationRequirements") or []
    if isinstance(raw, dict):
        raw = [raw]
    values = []
    for entry in raw if isinstance(raw, list) else []:
        address = entry.get("address", entry) if isinstance(entry, dict) else entry
        if isinstance(address, dict):
            parts = [address.get(k) for k in ("addressLocality", "addressRegion", "addressCountry")]
            cleaned = []
            for part in parts:
                text = _text(part)
                if isinstance(part, str) and part.strip().upper() == "IN":
                    text = "India"
                elif isinstance(part, dict) and str(part.get("name", "")).strip().upper() == "IN":
                    text = "India"
                if text:
                    cleaned.append(text)
            values.append(", ".join(cleaned))
        else:
            values.append(_text(address))
    return "; ".join(v for v in values if v)


def _india_vacancy(location, job):
    country = _text(job.get("jobLocation")).casefold()
    applicant = _text(job.get("applicantLocationRequirements")).casefold()
    combined = f"{location} {country} {applicant}"
    # Remote roles are included only if their declared eligible location is India.
    return bool(INDIA_HINTS.search(combined))


def _status(job):
    valid_through = _text(job.get("validThrough"))
    if valid_through:
        try:
            from datetime import datetime, timezone
            parsed = datetime.fromisoformat(valid_through.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < datetime.now(timezone.utc):
                return "expired"
        except ValueError:
            pass
    return "active"


def map_job_posting(job, page_url, source):
    title = _text(job.get("title"))
    url = job.get("url") or page_url
    if isinstance(url, dict):
        url = url.get("@id") or url.get("url")
    if not title or not url:
        raise ValueError("JobPosting is missing a title or job URL")
    org = job.get("hiringOrganization") or {}
    company = _text(org.get("name")) if isinstance(org, dict) else _text(org)
    if company and source["company"].casefold() not in company.casefold() and company.casefold() not in source["company"].casefold():
        # A job page from a career site must still identify the configured employer.
        raise ValueError(f"Hiring organization does not match {source['company']}")
    location = _locations(job)
    if not _india_vacancy(location, job):
        raise ValueError("JobPosting does not declare an India location")
    identifier = job.get("identifier")
    external_id = identifier.get("value") if isinstance(identifier, dict) else identifier
    description = _text(job.get("description"))
    employment = _text(job.get("employmentType"))
    return normalize_job({
        "external_id": external_id,
        "title": title,
        "company": source["company"],
        "location": location or "India",
        "experience": _text(job.get("experienceRequirements") or job.get("qualifications")) or None,
        "description": description or None,
        "job_url": urljoin(page_url, str(url)),
        "posted_at": job.get("datePosted"),
        "status": _status(job),
        "salary": job.get("baseSalary"),
    })



def validate_company_vacancy_record(job, source):
    """Validate a generic Actor result against the official company source."""
    title = str(job.get("title") or "").strip()
    url = str(job.get("job_url") or "").strip()
    if not title or not url:
        raise ValueError("Actor result must include both a job title and job URL")
    generic_titles = {
        "careers", "career", "jobs", "job search", "job openings", "career opportunities",
        "entry level", "graduate program", "graduate programs", "nqt hiring",
        "ignite", "ignite and smart hiring", "smart hiring", "tcs ignite and smart hiring",
    }
    if title.casefold().strip(" -|:") in generic_titles:
        raise ValueError("Result title is a career/program landing page, not an individual vacancy")
    lowered_title = title.casefold()
    if "program description" in lowered_title or "registration for" in lowered_title or "hiring program" in lowered_title:
        raise ValueError("Result appears to be a hiring-program description, not an individual vacancy")
    def landing_key(value):
        parts = urlsplit(value)
        return (parts.scheme.lower(), (parts.hostname or "").lower(), parts.path.rstrip("/") or "/")
    known_landing_pages = {landing_key(source["base_url"])}
    known_landing_pages.update(landing_key(item) for item in source.get("discovery_urls", []))
    if landing_key(url) in known_landing_pages:
        raise ValueError("Result URL is a known career/program landing page, not a vacancy")
    if not _is_allowed_url(url, _allowed_hosts(source)):
        raise ValueError("Job URL is outside the configured official company career hosts")
    reported_company = str(job.get("company") or "").strip()
    if reported_company and source["company"].casefold() not in reported_company.casefold() and reported_company.casefold() not in source["company"].casefold():
        raise ValueError(f"Actor result employer does not match {source['company']}")
    return job

def _infosys_records(payload):
    """Extract job records from the public Infosys search API response shapes."""
    if isinstance(payload, list):
        if payload and any(isinstance(item, dict) and any(k in item for k in ("jobTitle", "title", "jobReferenceCode", "referenceCode")) for item in payload):
            return payload
        records = []
        for item in payload:
            records.extend(_infosys_records(item))
        return records
    if not isinstance(payload, dict):
        return []
    # Prefer known collection keys, but tolerate harmless API envelope changes.
    for key in ("jobs", "jobList", "jobResults", "results", "data", "response", "careerSearchJobs", "content"):
        value = payload.get(key)
        if isinstance(value, (dict, list)):
            records = _infosys_records(value)
            if records:
                return records
    if any(k in payload for k in ("jobTitle", "title", "jobReferenceCode", "referenceCode")):
        return [payload]
    records = []
    for value in payload.values():
        if isinstance(value, (dict, list)):
            records.extend(_infosys_records(value))
    return records


def _infosys_field(record, *names):
    for name in names:
        value = record.get(name)
        if value not in (None, ""):
            return value
    return None


def _collect_infosys_api_jobs(source, max_results=100, timeout=15, session=None):
    """Collect India job records from Infosys' public careers search API."""
    session = session or requests.Session()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; V4Career/1.0)", "Accept": "application/json, text/plain, */*"}
    stats = {
        "pages_checked": 0, "pages_attempted": 0, "pages_fetched": 0,
        "pages_blocked": 0, "pages_network_errors": 0, "pages_http_errors": 0,
        "pages_external_redirects": 0, "pages_unsupported_content_type": 0,
        "jobs_found": 0, "pages_queued_remaining": 0,
        "method": "infosys_public_search_api", "api_records_received": 0,
    }
    try:
        stats["pages_attempted"] += 1
        config_response = session.get(
            "https://career.infosys.com/assets/environments/environment.json",
            timeout=timeout, headers=headers,
        )
        stats["pages_checked"] += 1
        if config_response.status_code != 200:
            stats["pages_http_errors"] += 1
            raise RuntimeError(f"Infosys environment config returned HTTP {config_response.status_code}")
        config = config_response.json()
        api_base = str(config.get("JobsUnAuthUrl") or "").strip()
        parsed_base = urlsplit(api_base)
        if parsed_base.scheme != "https" or parsed_base.hostname != "intapgateway.infosysapps.com":
            raise RuntimeError("Infosys config did not provide the expected official public API host")
        endpoint = urljoin(api_base.rstrip("/") + "/", "getCareerSearchJobs")
        stats["pages_attempted"] += 1
        response = session.get(
            endpoint, params={"sourceId": "1,21", "searchText": "ALL"},
            timeout=timeout, headers=headers,
        )
        stats["pages_checked"] += 1
        if response.status_code in (401, 403, 429):
            stats["pages_blocked"] += 1
            raise RuntimeError(f"Infosys public search API returned HTTP {response.status_code}")
        if response.status_code != 200:
            stats["pages_http_errors"] += 1
            raise RuntimeError(f"Infosys public search API returned HTTP {response.status_code}")
        payload = response.json()
        stats["pages_fetched"] = 2
        records = _infosys_records(payload)
        stats["api_records_received"] = len(records)
    except requests.RequestException as exc:
        stats["pages_network_errors"] += 1
        raise RuntimeError(f"Could not fetch Infosys public job API: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"Infosys API returned invalid JSON or an unexpected payload: {exc}") from exc

    jobs, seen = [], set()
    for record in records:
        if not isinstance(record, dict):
            continue
        external_id = _infosys_field(record, "jobReferenceCode", "referenceCode", "jobId", "id", "requisitionId")
        title = _infosys_field(record, "postingTitle", "jobTitle", "title", "positionTitle", "designation")
        if not external_id or not title:
            continue
        external_id = str(external_id).strip()
        if external_id in seen:
            continue
        url = "https://career.infosys.com/jobdesc?jobReferenceCode=" + requests.utils.quote(external_id, safe="")
        location = _infosys_field(record, "location", "jobLocation", "city", "primaryLocation", "locationName")
        if isinstance(location, dict):
            location = _text(location)
        experience = _infosys_field(record, "experience", "experienceRange", "experienceRequired", "workExperience")
        if not experience:
            min_exp = _infosys_field(record, "minExperienceLevel")
            max_exp = _infosys_field(record, "maxExperienceLevel")
            if min_exp is not None and max_exp is not None:
                experience = f"{_text(min_exp)}-{_text(max_exp)} years"
            elif min_exp is not None:
                experience = f"{_text(min_exp)}+ years"
            elif max_exp is not None:
                experience = f"Up to {_text(max_exp)} years"
        if isinstance(experience, dict):
            experience = _text(experience)
        description_parts = []
        for key in ("postingDescription", "technicalRequirement", "additionalResponsibility", "rolesResponsibilities", "jobDescription", "description", "rolesAndResponsibilities", "responsibilities", "technicalRequirements", "requiredSkills", "educationalRequirement", "education", "preferredSkills", "genericSkills"):
            value = record.get(key)
            if value:
                text_value = _text(value)
                if text_value and text_value not in description_parts:
                    description_parts.append(text_value)
        posted_at = _infosys_field(record, "createdOn", "postedDate", "datePosted", "postingDate", "createdDate", "publishedDate")
        try:
            job = normalize_job({
                "external_id": external_id,
                "title": _text(title),
                "company": source["company"],
                "location": _text(location) or "India",
                "experience": _text(experience) or None,
                "description": "\n\n".join(description_parts) or None,
                "job_url": url,
                "posted_at": posted_at,
                "status": "active",
                "salary": None,
            })
        except (ValueError, TypeError):
            continue
        seen.add(external_id)
        jobs.append(job)
        if len(jobs) >= max_results:
            break
    stats["jobs_found"] = len(jobs)
    return jobs, stats


class _WiproListingParser(HTMLParser):
    """Extract individual vacancy links from Wipro's official SuccessFactors search HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        href = html_lib.unescape((attrs.get("href") or "").strip())
        if tag.lower() == "a" and re.search(r"/job/[^/?#]+/[^/?#]+", href, re.I):
            self._anchor = {"href": href, "chunks": []}

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor["chunks"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._anchor is not None:
            item = self._anchor
            title = re.sub(r"\s+", " ", " ".join(item["chunks"])).strip()
            if title:
                self.links.append((item["href"], title))
            self._anchor = None


def _collect_wipro_search_jobs(source, max_results=100, timeout=15, session=None):
    """Collect individual India vacancies from Wipro's official SuccessFactors job search."""
    session = session or requests.Session()
    base_url = "https://careers.wipro.com/search/?q=&locationsearch=India"
    hosts = _allowed_hosts(source)
    stats = {"method": "official_wipro_successfactors_search_html", "pages_checked": 0,
             "pages_attempted": 0, "pages_fetched": 0, "pages_blocked": 0,
             "pages_network_errors": 0, "pages_http_errors": 0,
             "pages_external_redirects": 0, "pages_unsupported_content_type": 0,
             "jobs_found": 0, "pages_queued_remaining": 0, "listing_links_received": 0}
    try:
        response = session.get(base_url, timeout=timeout, allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; V4Career/1.0)",
                     "Accept": "text/html,application/xhtml+xml"})
    except requests.RequestException as exc:
        stats["pages_attempted"] = stats["pages_checked"] = stats["pages_network_errors"] = 1
        logger.warning("Wipro official job-search fetch failed: %s", exc)
        return [], stats
    stats["pages_attempted"] = stats["pages_checked"] = 1
    if response.status_code != 200:
        if response.status_code in (401, 403, 429): stats["pages_blocked"] = 1
        else: stats["pages_http_errors"] = 1
        return [], stats
    final_url = response.url or base_url
    if not _is_allowed_url(final_url, hosts):
        stats["pages_external_redirects"] = 1
        return [], stats
    if "html" not in response.headers.get("Content-Type", "text/html").lower():
        stats["pages_unsupported_content_type"] = 1
        return [], stats
    stats["pages_fetched"] = 1
    parser = _WiproListingParser()
    parser.feed(response.text)
    stats["listing_links_received"] = len(parser.links)
    jobs, seen = [], set()
    for href, title in parser.links:
        job_url = urljoin(final_url, href)
        if not _is_allowed_url(job_url, hosts) or re.search(r"no jobs|no vacancies|career opportunities", title, re.I):
            continue
        path_parts = [part for part in urlsplit(job_url).path.rstrip("/").split("/") if part]
        external_id = path_parts[-1] if path_parts else ""
        external_id = re.sub(r"-en_[A-Za-z]{2}$", "", external_id)
        if not external_id or external_id in seen or len(title) < 4:
            continue
        try:
            job = normalize_job({"external_id": external_id, "title": title, "company": source["company"],
                "location": "India", "job_url": job_url, "status": "active", "salary": None})
        except (ValueError, TypeError):
            continue
        seen.add(external_id); jobs.append(job)
        if len(jobs) >= max_results: break
    stats["jobs_found"] = len(jobs)
    return jobs, stats


def _collect_wipro_rss_jobs(source, max_results=100, timeout=15, session=None):
    """Collect Wipro India vacancies from the official SuccessFactors RSS feed.

    Wipro's official India category page advertises this RSS endpoint. Unlike
    the generic HTML walker, this parses the feed's individual vacancy items.
    Only item URLs on the configured official careers host are accepted.
    """
    session = session or requests.Session()
    feed_url = "https://careers.wipro.com/services/rss/category/?catid=9649255"
    hosts = _allowed_hosts(source)
    stats = {
        "method": "official_wipro_india_rss",
        "pages_checked": 1,
        "pages_attempted": 1,
        "pages_fetched": 0,
        "pages_blocked": 0,
        "pages_network_errors": 0,
        "pages_http_errors": 0,
        "pages_external_redirects": 0,
        "pages_unsupported_content_type": 0,
        "jobs_found": 0,
        "pages_queued_remaining": 0,
        "feed_items_received": 0,
    }
    if not _is_allowed_url(feed_url, hosts):
        raise RuntimeError("Configured Wipro RSS feed is outside the official host allowlist")
    try:
        response = session.get(feed_url, timeout=timeout, allow_redirects=False,
                               headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    except requests.RequestException as exc:
        stats["pages_network_errors"] = 1
        return [], stats
    if response.is_redirect or response.is_permanent_redirect:
        target = urljoin(feed_url, response.headers.get("Location", ""))
        if not _is_allowed_url(target, hosts):
            stats["pages_external_redirects"] = 1
            return [], stats
        try:
            response = session.get(target, timeout=timeout, allow_redirects=False,
                                   headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
        except requests.RequestException:
            stats["pages_network_errors"] = 1
            return [], stats
    if response.status_code != 200:
        if response.status_code in (401, 403, 429):
            stats["pages_blocked"] = 1
        else:
            stats["pages_http_errors"] = 1
        return [], stats
    stats["pages_fetched"] = 1
    try:
        root = ET.fromstring(response.text)
    except (ET.ParseError, TypeError) as exc:
        logger.warning("Wipro official RSS feed was not valid XML: %s", exc)
        stats["pages_unsupported_content_type"] = 1
        return [], stats

    def child_text(item, names):
        for name in names:
            found = item.find(name)
            if found is not None and found.text:
                return html_lib.unescape(found.text).strip()
        return ""

    jobs, seen = [], set()
    items = root.findall(".//item")
    stats["feed_items_received"] = len(items)
    for item in items:
        title = child_text(item, ("title",))
        url = child_text(item, ("link",))
        guid = child_text(item, ("guid",))
        description = child_text(item, ("description",))
        posted = child_text(item, ("pubDate", "{http://purl.org/dc/elements/1.1/}date"))
        if (not title or re.search(r"no jobs currently available|check out our other opportunities|no vacancies", title, re.I)
                or not url or not _is_allowed_url(urljoin(feed_url, url), hosts)):
            continue
        url = urljoin(feed_url, url)
        # RSS is the official India category, so country is grounded in the
        # feed scope. Use any explicit city/location text when present.
        plain_with_lines = re.sub(r"<[^>]+>", "\n", description)
        location = "India"
        location_match = re.search(r"(?:location|job location)\s*[:\-]\s*([^|;\n<]{2,100})", html_lib.unescape(plain_with_lines), re.I)
        plain_description = re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", description))).strip()
        if location_match:
            candidate = location_match.group(1).strip()
            if INDIA_HINTS.search(candidate):
                location = candidate[:255]
        external_id = guid or urlsplit(url).path.rstrip("/").split("/")[-1]
        if not external_id or url in seen:
            continue
        try:
            normalized = normalize_job({
                "external_id": external_id,
                "title": title,
                "company": source["company"],
                "location": location,
                "description": plain_description or None,
                "job_url": url,
                "posted_at": posted or None,
                "status": "active",
                "salary": None,
            })
        except (ValueError, TypeError):
            continue
        seen.add(url)
        jobs.append(normalized)
        if len(jobs) >= max_results:
            break
    stats["jobs_found"] = len(jobs)
    # Some SuccessFactors category RSS feeds contain only a generic placeholder.
    # Fall back to the employer's official search page in that case.
    if not jobs:
        fallback_jobs, fallback_stats = _collect_wipro_search_jobs(
            source, max_results=max_results, timeout=timeout, session=session
        )
        fallback_stats["rss_feed_items_received"] = stats["feed_items_received"]
        fallback_stats["rss_pages_fetched"] = stats["pages_fetched"]
        return fallback_jobs, fallback_stats
    return jobs, stats



class _AmazonListingParser(HTMLParser):
    """Read visible job-card anchors from Amazon's official search results HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "a" and attrs.get("href"):
            href = attrs["href"].strip()
            if re.search(r"/en/jobs/\d+", href):
                self._current = {"href": href, "chunks": []}

    def handle_data(self, data):
        if self._current is not None:
            self._current["chunks"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._current is not None:
            item = self._current
            title = re.sub(r"\s+", " ", " ".join(item["chunks"])).strip()
            if title:
                self.links.append((item["href"], title))
            self._current = None


def _amazon_records(value):
    """Find Amazon job records in public search JSON response envelopes."""
    if isinstance(value, list):
        records = []
        for item in value:
            if isinstance(item, dict) and any(k in item for k in ("id", "jobId", "job_id", "title", "job_title")):
                records.append(item)
            else:
                records.extend(_amazon_records(item))
        return records
    if isinstance(value, dict):
        for key in ("jobs", "jobResults", "results", "jobPostings", "searchResults", "data"):
            if isinstance(value.get(key), (list, dict)):
                found = _amazon_records(value[key])
                if found: return found
        if any(k in value for k in ("id", "jobId", "job_id", "title", "job_title")):
            return [value]
        records = []
        for child in value.values():
            if isinstance(child, (dict, list)): records.extend(_amazon_records(child))
        return records
    return []


def _collect_amazon_jobs(source, max_results=100, timeout=15, session=None):
    """Collect India vacancies from Amazon's official JSON search endpoint, with HTML fallback."""
    session = session or requests.Session()
    url = "https://www.amazon.jobs/en/search.json"
    hosts = _allowed_hosts(source)
    stats = {"method": "official_amazon_jobs_search_json", "pages_checked": 0,
             "pages_attempted": 0, "pages_fetched": 0, "pages_blocked": 0,
             "pages_network_errors": 0, "pages_http_errors": 0,
             "pages_external_redirects": 0, "pages_unsupported_content_type": 0,
             "jobs_found": 0, "pages_queued_remaining": 0, "listing_links_received": 0,
             "api_records_received": 0}
    response = None
    try:
        stats["pages_attempted"] += 1
        response = session.get(url, params={"country": "IND", "loc_query": "India", "result_limit": min(max_results, 100), "offset": 0},
            timeout=timeout, allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; V4Career/1.0)", "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    except requests.RequestException as exc:
        stats["pages_network_errors"] += 1
        logger.warning("Amazon official search request failed: %s", exc)
        return [], stats
    stats["pages_checked"] += 1
    if response.status_code != 200:
        if response.status_code in (401, 403, 429): stats["pages_blocked"] += 1
        else: stats["pages_http_errors"] += 1
        return [], stats
    final_url = response.url or url
    if not _is_allowed_url(final_url, hosts):
        stats["pages_external_redirects"] += 1
        return [], stats
    stats["pages_fetched"] += 1
    records = []
    content_type = response.headers.get("Content-Type", "").lower()
    if "json" in content_type or response.text.lstrip().startswith(("{", "[")):
        try: records = _amazon_records(response.json())
        except (ValueError, TypeError): records = []
        stats["api_records_received"] = len(records)
    jobs, seen = [], set()
    for record in records:
        title = _text(record.get("title") or record.get("jobTitle") or record.get("job_title") or record.get("name"))
        raw_id = record.get("id") or record.get("jobId") or record.get("job_id") or record.get("jobPostingId")
        path = record.get("job_path") or record.get("jobPath") or record.get("url") or record.get("job_url") or record.get("jobUrl")
        if isinstance(path, dict): path = path.get("url") or path.get("href")
        match = re.search(r"(?:/en)?/jobs/(\d+)", str(path or "")) or re.search(r"\d+", str(raw_id or ""))
        if not title or not match: continue
        external_id = match.group(1) if match.lastindex else match.group(0)
        if external_id in seen or re.search(r"no jobs|no results|search results", title, re.I): continue
        job_url = urljoin("https://www.amazon.jobs", str(path)) if path else f"https://www.amazon.jobs/en/jobs/{external_id}"
        if not _is_allowed_url(job_url, hosts): continue
        location = _text(record.get("location") or record.get("locations") or record.get("normalizedLocation")) or "India"
        if not INDIA_HINTS.search(location) and not re.search(r"country=IND", final_url): continue
        try:
            job = normalize_job({"external_id": external_id, "title": title, "company": source["company"],
                "location": location, "description": _text(record.get("description")) or None,
                "job_url": job_url, "posted_at": record.get("posted_date") or record.get("postedDate") or record.get("posted_at"),
                "status": "active", "salary": None})
        except (ValueError, TypeError): continue
        seen.add(external_id); jobs.append(job)
        if len(jobs) >= max_results: break
    if not jobs and "html" in content_type:
        parser = _AmazonListingParser(); parser.feed(response.text)
        stats["method"] = "official_amazon_jobs_search_html_fallback"
        stats["listing_links_received"] = len(parser.links)
        for href, title in parser.links:
            full_url = urljoin(final_url, href)
            if not _is_allowed_url(full_url, hosts) or re.search(r"no jobs|no results|currently unavailable|search results", title, re.I): continue
            match = re.search(r"/en/jobs/(\d+)", urlsplit(full_url).path)
            if not match or match.group(1) in seen or len(title) < 4: continue
            try:
                job = normalize_job({"external_id": match.group(1), "title": title, "company": source["company"],
                    "location": "India", "job_url": full_url, "status": "active", "salary": None})
            except (ValueError, TypeError): continue
            seen.add(match.group(1)); jobs.append(job)
            if len(jobs) >= max_results: break
    stats["jobs_found"] = len(jobs)
    return jobs, stats



class _AccentureListingParser(HTMLParser):
    """Extract job-detail links from Accenture's server-rendered search results."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "a" and attrs.get("href"):
            href = html_lib.unescape(attrs["href"].strip())
            is_detail = ("jobdetails" in href.lower() and re.search(r"(?:\?|&)id=", href, re.I))
            is_job_path = bool(re.search(r"/careers/(?:job/|jobs/|jobdetails/)", href, re.I))
            if is_detail or is_job_path:
                self._anchor = {"href": href, "chunks": []}

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor["chunks"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._anchor is not None:
            item = self._anchor
            title = re.sub(r"\s+", " ", " ".join(item["chunks"])).strip()
            if title:
                self.links.append((item["href"], title))
            self._anchor = None


def _collect_accenture_jobs(source, max_results=100, max_pages=10, timeout=15, session=None):
    """Collect job cards from Accenture's official India search page.

    Accenture redirects legacy job-detail URLs to the official jobsearch route.
    Start at that route and extract only official jobdetails links with explicit
    requisition IDs; this is intentionally separate from JSON-LD.
    """
    session = session or requests.Session()
    base_url = "https://www.accenture.com/in-en/careers/jobsearch"
    hosts = _allowed_hosts(source)
    stats = {
        "method": "official_accenture_search_listing_html", "pages_checked": 0,
        "pages_attempted": 0, "pages_fetched": 0, "pages_blocked": 0,
        "pages_network_errors": 0, "pages_http_errors": 0,
        "pages_external_redirects": 0, "pages_unsupported_content_type": 0,
        "jobs_found": 0, "pages_queued_remaining": 0,
        "listing_links_received": 0,
    }
    jobs, seen_ids = [], set()
    # Use the canonical official search route, rather than the general careers
    # landing page or an unrelated job-detail URL.
    urls = ["https://www.accenture.com/in-en/careers/jobsearch"]
    for page_num in range(2, max_pages + 1):
        urls.append(f"https://www.accenture.com/in-en/careers/jobsearch?page={page_num}")
    for url in urls:
        if len(jobs) >= max_results:
            break
        if not _is_allowed_url(url, hosts):
            continue
        stats["pages_attempted"] += 1
        try:
            response = session.get(url, timeout=timeout, allow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0 (compatible; V4Career/1.0)",
                         "Accept": "text/html,application/xhtml+xml"})
        except requests.RequestException:
            stats["pages_network_errors"] += 1
            continue
        if response.is_redirect or response.is_permanent_redirect:
            target = urljoin(url, response.headers.get("Location", ""))
            if not _is_allowed_url(target, hosts):
                stats["pages_external_redirects"] += 1
                continue
            try:
                response = session.get(target, timeout=timeout, allow_redirects=False,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; V4Career/1.0)",
                             "Accept": "text/html,application/xhtml+xml"})
            except requests.RequestException:
                stats["pages_network_errors"] += 1
                continue
        stats["pages_checked"] += 1
        if response.status_code != 200:
            if response.status_code in (401, 403, 429): stats["pages_blocked"] += 1
            else: stats["pages_http_errors"] += 1
            continue
        content_type = response.headers.get("Content-Type", "text/html").lower()
        if content_type and "html" not in content_type:
            stats["pages_unsupported_content_type"] += 1
            continue
        stats["pages_fetched"] += 1
        parser = _AccentureListingParser()
        try:
            parser.feed(response.text)
        except Exception:
            continue
        stats["listing_links_received"] += len(parser.links)
        for href, title in parser.links:
            full_url = urljoin(url, href)
            if not _is_allowed_url(full_url, hosts):
                continue
            query = dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(urlsplit(full_url).query))
            job_id = (query.get("id") or "").strip()
            if not job_id:
                path_match = re.search(r"/(?:jobs?|jobdetails)/([^/?#]+)", urlsplit(full_url).path, re.I)
                job_id = path_match.group(1) if path_match else ""
            if not job_id or job_id in seen_ids:
                continue
            if len(title) < 4 or re.search(r"^(search jobs|job search|view job|apply now|read more)$", title, re.I):
                continue
            # Accenture's India careers search can include globally located
            # roles; only keep links whose visible card title/page is clearly
            # on the India job-search page. Location enrichment can be added
            # from detail pages once a stable public endpoint is confirmed.
            try:
                job = normalize_job({
                    "external_id": job_id,
                    "title": title,
                    "company": source["company"],
                    "location": "India",
                    "job_url": full_url,
                    "status": "active",
                    "salary": None,
                })
            except (ValueError, TypeError):
                continue
            seen_ids.add(job_id)
            jobs.append(job)
            if len(jobs) >= max_results:
                break
    stats["jobs_found"] = len(jobs)
    return jobs, stats



class _DeloitteListingParser(HTMLParser):
    """Extract real job links from Deloitte India's official SuccessFactors listing."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        href = html_lib.unescape((attrs.get("href") or "").strip())
        # Deloitte SuccessFactors detail URLs look like /job/Bengaluru-.../55097544/
        if tag.lower() == "a" and href and re.search(r"/job/[^?#]+/\d+/?(?:[?#].*)?$", href, re.I):
            self._anchor = {"href": href, "chunks": []}

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor["chunks"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._anchor is not None:
            item = self._anchor
            title = re.sub(r"\s+", " ", " ".join(item["chunks"])).strip()
            if title:
                self.links.append((item["href"], title))
            self._anchor = None


def _collect_deloitte_jobs(source, max_results=100, max_pages=10, timeout=15, session=None):
    """Collect India vacancy cards from Deloitte India's official SuccessFactors portal."""
    session = session or requests.Session()
    base_url = "https://southasiacareers.deloitte.com/go/Deloitte-India/718244/"
    hosts = _allowed_hosts(source)
    stats = {"method": "official_deloitte_successfactors_search_html",
             "pages_checked": 0, "pages_attempted": 0, "pages_fetched": 0,
             "pages_blocked": 0, "pages_network_errors": 0, "pages_http_errors": 0,
             "pages_external_redirects": 0, "pages_unsupported_content_type": 0,
             "jobs_found": 0, "pages_queued_remaining": 0, "listing_links_received": 0}
    jobs, seen = [], set()
    # SAP SuccessFactors uses startrow pagination; each page contains up to 25 cards.
    for page in range(max_pages):
        if len(jobs) >= max_results:
            break
        url = base_url if page == 0 else f"{base_url}?q=&sortColumn=referencedate&sortDirection=desc&startrow={page * 25}"
        if not _is_allowed_url(url, hosts):
            continue
        stats["pages_attempted"] += 1
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; V4Career/1.0)",
                         "Accept": "text/html,application/xhtml+xml"})
        except requests.RequestException as exc:
            stats["pages_network_errors"] += 1
            logger.warning("Deloitte official job search request failed: %s", exc)
            continue
        stats["pages_checked"] += 1
        if response.status_code != 200:
            if response.status_code in (401, 403, 429): stats["pages_blocked"] += 1
            else: stats["pages_http_errors"] += 1
            continue
        final_url = response.url or url
        if not _is_allowed_url(final_url, hosts):
            stats["pages_external_redirects"] += 1
            continue
        if "html" not in response.headers.get("Content-Type", "text/html").lower():
            stats["pages_unsupported_content_type"] += 1
            continue
        stats["pages_fetched"] += 1
        parser = _DeloitteListingParser()
        try:
            parser.feed(response.text)
        except Exception as exc:
            logger.debug("Deloitte listing HTML parse failed: %s", exc)
            continue
        stats["listing_links_received"] += len(parser.links)
        for href, title in parser.links:
            job_url = urljoin(final_url, href)
            if not _is_allowed_url(job_url, hosts):
                continue
            match = re.search(r"/job/[^/?#]+/(\d+)/?", urlsplit(job_url).path, re.I)
            if not match:
                continue
            external_id = match.group(1)
            if external_id in seen or len(title) < 4:
                continue
            if re.search(r"^(title|location|date|view job|apply now|read more)$", title, re.I):
                continue
            # SAP card text often includes title + city; keep it as the official card title.
            title = re.sub(r"\s+", " ", title).strip(" |")
            try:
                job = normalize_job({"external_id": external_id, "title": title,
                    "company": source["company"], "location": "India", "job_url": job_url,
                    "status": "active", "salary": None})
            except (ValueError, TypeError):
                continue
            seen.add(external_id)
            jobs.append(job)
            if len(jobs) >= max_results:
                break
    stats["jobs_found"] = len(jobs)
    return jobs, stats


def collect_structured_jobs(source, max_results=100, timeout=15, max_pages=60, session=None):
    """Return normalized India JobPosting records from one configured official site."""
    if max_results < 1 or max_results > 500:
        raise ValueError("max_results must be between 1 and 500")
    if max_pages < 1 or max_pages > 200:
        raise ValueError("max_pages must be between 1 and 200")
    if source.get("key") == "INFOSYS":
        return _collect_infosys_api_jobs(source, max_results=max_results, timeout=timeout, session=session)
    if source.get("key") == "WIPRO":
        return _collect_wipro_rss_jobs(source, max_results=max_results, timeout=timeout, session=session)
    if source.get("key") == "AMAZON":
        return _collect_amazon_jobs(source, max_results=max_results, timeout=timeout, session=session)
    if source.get("key") == "ACCENTURE":
        return _collect_accenture_jobs(source, max_results=max_results, max_pages=max_pages, timeout=timeout, session=session)
    if source.get("key") == "DELOITTE":
        return _collect_deloitte_jobs(source, max_results=max_results, max_pages=max_pages, timeout=timeout, session=session)
    hosts = _allowed_hosts(source)
    session = session or requests.Session()
    queue = list(source.get("discovery_urls") or []) + [source["base_url"]]
    seen_pages, seen_jobs = set(), set()
    jobs = []
    outcomes = {"fetched": 0, "blocked": 0, "network_error": 0, "http_error": 0,
                "external_redirect": 0, "unsupported_content_type": 0, "invalid_url": 0}
    while queue and len(seen_pages) < max_pages and len(jobs) < max_results:
        page_url = urldefrag(queue.pop(0))[0]
        if page_url in seen_pages or not _is_allowed_url(page_url, hosts):
            continue
        seen_pages.add(page_url)
        html, final_url, outcome = _fetch(page_url, hosts, session, timeout)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if not html or not final_url:
            continue
        parser = PageParser()
        try:
            parser.feed(html)
        except Exception as exc:
            logger.debug("Unable to parse career page %s: %s", page_url, exc)
            continue
        for block in parser.jsonld:
            for posting in _walk_jsonld(block):
                try:
                    mapped = map_job_posting(posting, final_url, source)
                    if not _is_allowed_url(mapped["job_url"], hosts):
                        raise ValueError("Job URL is outside the configured official career hosts")
                    if mapped["url_hash"] not in seen_jobs:
                        seen_jobs.add(mapped["url_hash"])
                        jobs.append(mapped)
                        if len(jobs) >= max_results:
                            break
                except (ValueError, TypeError, AttributeError) as exc:
                    logger.debug("Rejecting non-vacancy/invalid posting on %s: %s", final_url, exc)
            if len(jobs) >= max_results:
                break
        # Only crawl links that look like listing/detail pages. All remain on
        # the configured official host(s), and only JobPosting JSON-LD is saved.
        for href in parser.links:
            if len(seen_pages) + len(queue) >= max_pages * 2:
                break
            target = urldefrag(urljoin(final_url, href))[0]
            if target not in seen_pages and _is_allowed_url(target, hosts) and JOB_LINK_HINTS.search(urlsplit(target).path):
                queue.append(target)
    return jobs, {
        "pages_checked": len(seen_pages),  # compatibility: pages attempted
        "pages_attempted": len(seen_pages),
        "pages_fetched": outcomes["fetched"],
        "pages_blocked": outcomes["blocked"],
        "pages_network_errors": outcomes["network_error"],
        "pages_http_errors": outcomes["http_error"],
        "pages_external_redirects": outcomes["external_redirect"],
        "pages_unsupported_content_type": outcomes["unsupported_content_type"],
        "jobs_found": len(jobs),
        "pages_queued_remaining": len(queue),
    }
