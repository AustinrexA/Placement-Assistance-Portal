
import pytest

from collectors.normalization import (
    normalize_url,
    normalize_job,
    parse_skills,
    parse_datetime,
    url_hash,
    parse_salary,
)


def test_normalize_url_removes_tracking_parameters():
    result = normalize_url(
        "https://Example.com/jobs/123?utm_source=test&ref=direct#section"
    )

    assert result == "https://example.com/jobs/123?ref=direct"


def test_normalize_url_rejects_missing_url():
    with pytest.raises(ValueError):
        normalize_url("")


def test_normalize_url_rejects_invalid_hostname():
    with pytest.raises(ValueError):
        normalize_url("https:///jobs/123")


def test_url_hash_is_deterministic():
    url = "https://example.com/jobs/123"

    assert url_hash(url) == url_hash(url)


def test_parse_skills_from_list():
    assert parse_skills(["Python", " SQL "]) == '["Python", "SQL"]'


def test_parse_skills_from_semicolon_string():
    assert parse_skills("Python; SQL") == '["Python", "SQL"]'


def test_parse_datetime_iso_timestamp():
    result = parse_datetime("2026-10-05T17:33:48Z")

    assert result == "2026-10-05 17:33:48"


def test_normalize_job_valid_record():
    job = normalize_job({
        "title": "Backend Developer",
        "job_url": "https://example.com/jobs/123?utm_source=test",
        "company": "Example Ltd",
        "skills": ["Python", "MySQL"],
        "status": "active",
    })

    assert job["title"] == "Backend Developer"
    assert job["job_url"] == "https://example.com/jobs/123"
    assert job["company"] == "Example Ltd"
    assert job["status"] == "active"
    assert len(job["url_hash"]) == 64


def test_normalize_job_rejects_missing_title():
    with pytest.raises(ValueError, match="Job title is required"):
        normalize_job({
            "title": "",
            "job_url": "https://example.com/jobs/123",
        })


def test_normalize_job_rejects_invalid_url():
    with pytest.raises(ValueError):
        normalize_job({
            "title": "Backend Developer",
            "job_url": "not-a-valid-url",
        })


def test_salary_numeric_fields_are_normalized():
    salary = parse_salary({"salary_min": "300000", "salary_max": "900000", "salaryCurrency": "INR", "salaryPeriod": "annual"})
    assert salary == {"salary_min": 300000.0, "salary_max": 900000.0, "salary_currency": "INR", "salary_period": "year"}


def test_salary_range_text_detects_currency_and_range():
    salary = parse_salary({"salary": "$80,000 - $120,000 per year"})
    assert salary["salary_min"] == 80000.0
    assert salary["salary_max"] == 120000.0
    assert salary["salary_currency"] == "USD"
    assert salary["salary_period"] == "year"


def test_normalize_job_includes_nullable_salary_fields():
    job = normalize_job({"title": "Backend Developer", "job_url": "https://example.com/jobs/123"})
    assert job["salary_min"] is None
    assert job["salary_max"] is None
    assert job["salary_currency"] == "INR"
    assert job["salary_period"] == "year"
