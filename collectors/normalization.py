
import hashlib
import json
import re
from datetime import datetime
from urllib.parse import (
    urlsplit,
    urlunsplit,
    parse_qsl,
    urlencode,
)


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def normalize_url(raw_url: str) -> str:
    """Validate a job URL and remove common tracking parameters."""
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise ValueError("job_url is required")

    raw_url = raw_url.strip()

    try:
        parts = urlsplit(raw_url)
        hostname = parts.hostname

        # Accessing port also detects malformed port values.
        _ = parts.port
    except ValueError as exc:
        raise ValueError("Invalid job URL") from exc

    if (
        parts.scheme.lower() not in {"http", "https"}
        or not hostname
        or not parts.netloc
        or any(char.isspace() for char in raw_url)
    ):
        raise ValueError("A valid HTTP(S) job URL is required")

    # Preserve the original netloc apart from lowercasing it.
    # Remove fragments and common tracking query parameters.
    query = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key.lower() not in TRACKING_PARAMS
    ]

    path = parts.path.rstrip("/") or "/"

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(query, doseq=True),
            "",
        )
    )


def url_hash(normalized_url: str) -> str:
    """Generate a stable SHA-256 hash for a normalized URL."""
    return hashlib.sha256(
        normalized_url.encode("utf-8")
    ).hexdigest()


def parse_skills(value):
    """Convert skills into a JSON array string for MySQL."""
    if value is None or value == "":
        return None

    if isinstance(value, list):
        skills = value
    else:
        text = str(value).strip()

        if not text:
            return None

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                skills = parsed
            else:
                skills = [
                    part.strip()
                    for part in text.split(";")
                    if part.strip()
                ]
        except json.JSONDecodeError:
            skills = [
                part.strip()
                for part in text.split(";")
                if part.strip()
            ]

    cleaned = [
        str(skill).strip()
        for skill in skills
        if skill is not None and str(skill).strip()
    ]

    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


def parse_datetime(value):
    """Parse common date formats and ISO timestamps."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    value = str(value).strip()

    if not value:
        return None

    # Handle ISO timestamps ending in Z.
    iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value

    try:
        parsed = datetime.fromisoformat(iso_value)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(value[:19], fmt)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return None



def parse_salary(raw):
    """Normalize common salary fields without guessing units or currencies."""
    if not isinstance(raw, dict):
        return {"salary_min": None, "salary_max": None, "salary_currency": "INR", "salary_period": "year"}
    minimum = raw.get("salary_min", raw.get("salaryMin", raw.get("minSalary")))
    maximum = raw.get("salary_max", raw.get("salaryMax", raw.get("maxSalary")))
    currency = str(raw.get("salary_currency") or raw.get("salaryCurrency") or raw.get("currency") or "INR").strip().upper()
    period = str(raw.get("salary_period") or raw.get("salaryPeriod") or raw.get("salary_type") or raw.get("payPeriod") or "year").strip().lower()
    if period in {"annual", "annually", "yearly", "per year", "year"}: period = "year"
    elif period in {"monthly", "per month", "month"}: period = "month"
    elif period in {"hourly", "per hour", "hour"}: period = "hour"
    elif period in {"weekly", "per week", "week"}: period = "week"
    else: period = "year"
    def number(value):
        if value is None or value == "": return None
        if isinstance(value, (int, float)): return float(value) if value >= 0 else None
        cleaned = re.sub(r"[^0-9.]", "", str(value).replace(",", ""))
        try: return float(cleaned) if cleaned else None
        except ValueError: return None
    lo, hi = number(minimum), number(maximum)
    if lo is None and hi is None:
        text = " ".join(str(raw.get(key) or "") for key in ("salary", "salary_range", "salaryRange", "compensation", "pay"))
        if text:
            found = re.findall(r"(?:₹|INR|Rs\.?|\$|USD|EUR|€|£)?\s*([0-9][0-9,.]*)\s*([kKmM]?)", text)
            values = []
            for amount, suffix in found:
                val = number(amount)
                if val is not None:
                    if suffix.lower() == "k": val *= 1000
                    elif suffix.lower() == "m": val *= 1000000
                    values.append(val)
            upper = text.upper()
            if values and any(token in upper for token in ("LPA", "LAKH", "LAKHS")):
                values = [value * 100000 if value < 1000 else value for value in values]
            if values and any(token in upper for token in ("CRORE", "CRORES", "CR PA", "CR/YEAR")):
                values = [value * 10000000 if value < 1000 else value for value in values]
            if values:
                lo, hi = min(values), max(values)
            upper = text.upper()
            if "$" in text or "USD" in upper: currency = "USD"
            elif "€" in text or "EUR" in upper: currency = "EUR"
            elif "£" in text or "GBP" in upper: currency = "GBP"
            elif "₹" in text or "INR" in upper or "RS" in upper: currency = "INR"
            if any(word in upper for word in ("MONTH", "/MO", "PER MONTH")): period = "month"
            elif any(word in upper for word in ("HOUR", "/HR", "PER HOUR")): period = "hour"
            elif any(word in upper for word in ("WEEK", "/WK")): period = "week"
    if lo is not None and hi is not None and lo > hi: lo, hi = hi, lo
    if not re.fullmatch(r"[A-Z]{3}", currency): currency = "INR"
    return {"salary_min": lo, "salary_max": hi, "salary_currency": currency, "salary_period": period}


def normalize_job(raw: dict) -> dict:
    """Validate and normalize a raw job into the database format."""
    if not isinstance(raw, dict):
        raise ValueError("Job data must be a dictionary")

    title = str(raw.get("title") or "").strip()

    if not title:
        raise ValueError("Job title is required")

    raw_url = raw.get("job_url") or raw.get("url") or ""
    normalized_url = normalize_url(raw_url)

    status = str(raw.get("status") or "unknown").strip().lower()

    if status not in {"active", "closed", "expired", "unknown"}:
        status = "unknown"

    external_id = raw.get("external_id")
    if external_id is not None:
        external_id = str(external_id).strip() or None

    company = str(raw.get("company") or "").strip()[:255] or None
    location = str(raw.get("location") or "").strip()[:255] or None
    experience = str(raw.get("experience") or "").strip()[:255] or None
    description = str(raw.get("description") or "").strip() or None

    salary = parse_salary(raw)

    return {
        "external_id": external_id,
        "url_hash": url_hash(normalized_url),
        "title": title[:500],
        "company": company,
        "location": location,
        "experience": experience,
        **salary,
        "skills": parse_skills(raw.get("skills")),
        "description": description,
        "job_url": normalized_url,
        "posted_at": parse_datetime(raw.get("posted_at")),
        "status": status,
    }
