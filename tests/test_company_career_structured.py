import json
from types import SimpleNamespace

import pytest

from collectors.company_career_catalog import COMPANY_CAREER_BY_KEY

TEST_TCS_SOURCE = {"name": "TCS Careers", "company": "TCS", "base_url": "https://www.tcs.com/careers/india", "key": "TCS", "allowed_hosts": ["www.tcs.com"], "discovery_urls": ["https://www.tcs.com/careers/india/entry-level", "https://www.tcs.com/careers/india/tcs-all-india-nqt-hiring", "https://www.tcs.com/careers/india/tcs-bsc-ignite-and-smart-hiring"]}
from collectors.company_career_structured import (
    PageParser,
    _walk_jsonld,
    collect_structured_jobs,
    map_job_posting,
    validate_company_vacancy_record,
)


def posting(**overrides):
    value = {
        "@type": "JobPosting",
        "title": "Software Engineer",
        "url": "https://www.tcs.com/careers/jobs/software-engineer-123",
        "identifier": {"value": "123"},
        "datePosted": "2026-10-01",
        "hiringOrganization": {"@type": "Organization", "name": "TCS"},
        "jobLocation": [{"@type": "Place", "address": {
            "addressLocality": "Chennai", "addressRegion": "Tamil Nadu", "addressCountry": "India"
        }}],
        "description": "Build software for enterprise customers.",
    }
    value.update(overrides)
    return value


def test_jsonld_parser_extracts_jobposting_not_program_text():
    parser = PageParser()
    parser.feed('<html><title>TCS Ignite Program</title><script type="application/ld+json">' +
                json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": "Program"}) +
                '</script></html>')
    found = [item for block in parser.jsonld for item in _walk_jsonld(block)]
    assert found == []


def test_maps_real_india_jobposting():
    source = TEST_TCS_SOURCE
    result = map_job_posting(posting(), source["base_url"], source)
    assert result["title"] == "Software Engineer"
    assert result["company"] == "TCS"
    assert "India" in result["location"]
    assert result["external_id"] == "123"
    assert result["status"] == "active"


def test_rejects_non_india_jobposting():
    source = TEST_TCS_SOURCE
    foreign = posting(jobLocation=[{"address": {"addressLocality": "Austin", "addressRegion": "Texas", "addressCountry": "USA"}}])
    with pytest.raises(ValueError, match="India location"):
        map_job_posting(foreign, source["base_url"], source)


def test_rejects_mismatched_employer():
    source = TEST_TCS_SOURCE
    with pytest.raises(ValueError, match="does not match"):
        map_job_posting(posting(hiringOrganization={"name": "Unrelated Corp"}), source["base_url"], source)


def test_rejects_program_page_without_jobposting():
    source = TEST_TCS_SOURCE
    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        is_redirect = False
        is_permanent_redirect = False
        text = '<html><title>TCS NQT Hiring</title><body>Program registration and eligibility</body></html>'
    class FakeSession:
        def get(self, url, **kwargs):
            return FakeResponse()
    jobs, stats = collect_structured_jobs(source, max_results=10, max_pages=5, session=FakeSession())
    assert jobs == []
    assert stats["pages_checked"] >= 1
    assert stats["jobs_found"] == 0


def test_rejects_job_url_outside_company_host_during_collection(monkeypatch):
    source = TEST_TCS_SOURCE
    # Exercise the mapping-level URL check contract separately: mapping itself
    # may parse an external URL, but the collector's host allowlist rejects it.
    from collectors.company_career_structured import _is_allowed_url, _allowed_hosts
    external = posting(url="https://jobs-unrelated.example/job/1")
    mapped = map_job_posting(external, source["base_url"], source)
    assert not _is_allowed_url(mapped["job_url"], _allowed_hosts(source))


def test_accepts_india_country_code_in_structured_address():
    source = TEST_TCS_SOURCE
    india_code = posting(jobLocation=[{"address": {
        "addressLocality": "Pune", "addressRegion": "Maharashtra", "addressCountry": "IN"
    }}])
    result = map_job_posting(india_code, source["base_url"], source)
    assert "India" in result["location"]


def test_apify_company_runner_rejects_program_landing_pages():
    source = TEST_TCS_SOURCE
    with pytest.raises(ValueError, match="landing page"):
        validate_company_vacancy_record({"title": "NQT Hiring", "job_url": "https://www.tcs.com/careers/india/tcs-all-india-nqt-hiring", "company": "TCS"}, source)


def test_apify_company_runner_rejects_external_unconfigured_job_urls():
    source = TEST_TCS_SOURCE
    with pytest.raises(ValueError, match="outside the configured official"):
        validate_company_vacancy_record({"title": "Software Engineer", "job_url": "https://unrelated.example/jobs/123", "company": "TCS"}, source)


def test_all_403_pages_are_reported_as_blocked_not_successful_fetches():
    source = TEST_TCS_SOURCE
    class ForbiddenResponse:
        status_code = 403
        headers = {"Content-Type": "text/html; charset=utf-8"}
        is_redirect = False
        is_permanent_redirect = False
        text = "Forbidden"
    class ForbiddenSession:
        def get(self, url, **kwargs):
            return ForbiddenResponse()
    jobs, stats = collect_structured_jobs(source, max_results=10, max_pages=5, session=ForbiddenSession())
    assert jobs == []
    assert stats["pages_attempted"] == 4
    assert stats["pages_fetched"] == 0
    assert stats["pages_blocked"] == 4
    assert stats["jobs_found"] == 0


class InfosysApiIntegrationTests:
    def test_infosys_api_maps_and_deduplicates_records_without_network(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["INFOSYS"]

        class Response:
            def __init__(self, payload, status=200):
                self._payload = payload
                self.status_code = status
            def json(self):
                return self._payload

        class FakeSession:
            def __init__(self):
                self.calls = []
            def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                if url.endswith("environment.json"):
                    return Response({"JobsUnAuthUrl": "https://intapgateway.infosysapps.com/careersci/search/intapjbsrch/"})
                return Response({"data": [
                    {"jobReferenceCode": "INFSYS-EXTERNAL-1", "jobTitle": "Software Engineer", "location": "CHENNAI", "description": "Build software", "postedDate": "2026-10-19"},
                    {"jobReferenceCode": "INFSYS-EXTERNAL-1", "jobTitle": "Software Engineer", "location": "CHENNAI"},
                    {"jobReferenceCode": "INFSYS-EXTERNAL-2", "jobTitle": "Data Engineer", "location": "BANGALORE"},
                ]})

        session = FakeSession()
        jobs, stats = collect_structured_jobs(source, max_results=10, timeout=5, session=session)
        assert len(jobs) == 2
        assert len({job["external_id"] for job in jobs}) == 2
        assert jobs[0]["company"] == "Infosys"
        assert jobs[0]["job_url"] == "https://career.infosys.com/jobdesc?jobReferenceCode=INFSYS-EXTERNAL-1"
        assert jobs[0]["location"] == "CHENNAI"
        assert stats["method"] == "infosys_public_search_api"
        assert stats["api_records_received"] == 3
        assert stats["jobs_found"] == 2
        assert session.calls[1][1]["params"] == {"sourceId": "1,21", "searchText": "ALL"}

    def test_infosys_api_rejects_unexpected_api_host(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["INFOSYS"]
        class Response:
            status_code = 200
            def json(self):
                return {"JobsUnAuthUrl": "https://attacker.example/api/"}
        class FakeSession:
            def get(self, url, **kwargs):
                return Response()
        import pytest
        with pytest.raises(RuntimeError, match="expected official public API host"):
            collect_structured_jobs(source, session=FakeSession())


def test_wipro_official_rss_collector_maps_individual_vacancies():
    from collectors.company_career_structured import collect_structured_jobs
    source = COMPANY_CAREER_BY_KEY["WIPRO"]
    class Response:
        status_code = 200
        is_redirect = False
        is_permanent_redirect = False
        headers = {"Content-Type": "application/rss+xml"}
        text = '''<?xml version="1.0"?><rss version="2.0"><channel>
          <item><title>Software Engineer</title><link>https://careers.wipro.com/job/Software-Engineer/123-en_US</link>
          <guid>WIPRO-123</guid><description><![CDATA[<p>Location: Bengaluru, India</p><p>Build software systems.</p>]]></description>
          <pubDate>Tue, 20 Oct 2026 10:00:00 GMT</pubDate></item>
          <item><title>Data Analyst</title><link>https://careers.wipro.com/job/Data-Analyst/456-en_US</link>
          <guid>WIPRO-456</guid><description>India vacancy</description></item>
        </channel></rss>'''
    class FakeSession:
        def get(self, url, **kwargs):
            assert url == "https://careers.wipro.com/services/rss/category/?catid=9649255"
            return Response()
    jobs, stats = collect_structured_jobs(source, max_results=10, timeout=5, session=FakeSession())
    assert len(jobs) == 2
    assert jobs[0]["title"] == "Software Engineer"
    assert jobs[0]["external_id"] == "WIPRO-123"
    assert jobs[0]["company"] == "Wipro"
    assert jobs[0]["location"] == "Bengaluru, India"
    assert stats["method"] == "official_wipro_india_rss"
    assert stats["feed_items_received"] == 2
    assert stats["jobs_found"] == 2

class AmazonOfficialCollectorTests:
    def test_amazon_search_html_extracts_job_cards(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["AMAZON"]
        class Response:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            is_redirect = False
            is_permanent_redirect = False
            text = '<html><a href="/en/jobs/10570423/applied-scientist">Applied Scientist II, Last Mile Science</a><a href="/en/jobs/10555861/program-manager">Program Manager - Control Tower</a></html>'
        class FakeSession:
            def get(self, url, **kwargs):
                assert "amazon.jobs" in url and "country=IND" in url
                return Response()
        jobs, stats = collect_structured_jobs(source, max_results=10, session=FakeSession())
        assert len(jobs) == 2
        assert jobs[0]["external_id"] == "10570423"
        assert jobs[0]["company"] == "Amazon"
        assert stats["method"] == "official_amazon_jobs_search_html"

    def test_amazon_search_json_extracts_job_records(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["AMAZON"]
        class Response:
            status_code = 200
            headers = {"Content-Type": "application/json"}
            is_redirect = False
            is_permanent_redirect = False
            url = "https://www.amazon.jobs/en/search.json?country=IND"
            text = '{"jobs":[{"id": "10570423", "title": "Software Development Engineer", "job_path": "/en/jobs/10570423/software-development-engineer", "location": "Bengaluru, India"}]}'
            def json(self):
                import json
                return json.loads(self.text)
        class FakeSession:
            def get(self, url, **kwargs):
                assert url.endswith("/en/search.json")
                assert kwargs["params"]["country"] == "IND"
                return Response()
        jobs, stats = collect_structured_jobs(source, max_results=10, session=FakeSession())
        assert len(jobs) == 1
        assert jobs[0]["external_id"] == "10570423"
        assert jobs[0]["location"] == "Bengaluru, India"
        assert stats["method"] == "official_amazon_jobs_search_json"

    def test_amazon_rejects_placeholder(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["AMAZON"]
        class Response:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            is_redirect = False
            is_permanent_redirect = False
            text = '<html><a href="/en/jobs/12345678/no-jobs">No jobs currently available</a></html>'
        class FakeSession:
            def get(self, url, **kwargs): return Response()
        jobs, stats = collect_structured_jobs(source, session=FakeSession())
        assert jobs == []
        assert stats["jobs_found"] == 0

class AccentureOfficialCollectorTests:
    def test_accenture_search_extracts_real_jobdetail_links(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["ACCENTURE"]
        class Response:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            is_redirect = False
            is_permanent_redirect = False
            text = '''<html><body>
              <a href="/in-en/careers/jobdetails?id=R00339489_en">SAP S/4HANA Finance Consultant</a>
              <a href="/in-en/careers/jobdetails?id=R00325334_en">Enterprise AI Value Strategy Senior Manager</a>
              <a href="/in-en/careers/jobdetails?id=R00325334_en">Duplicate card</a>
              <a href="/in-en/careers">Search jobs</a>
            </body></html>'''
        class FakeSession:
            def get(self, url, **kwargs):
                assert "accenture.com/in-en/careers" in url
                return Response()
        jobs, stats = collect_structured_jobs(source, max_results=10, max_pages=1, session=FakeSession())
        assert len(jobs) == 2
        assert jobs[0]["external_id"] == "R00339489_en"
        assert jobs[0]["title"] == "SAP S/4HANA Finance Consultant"
        assert jobs[0]["job_url"].startswith("https://www.accenture.com/in-en/careers/jobdetails?id=")
        assert stats["method"] == "official_accenture_search_listing_html"

    def test_accenture_ignores_non_job_links(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["ACCENTURE"]
        class Response:
            status_code = 200
            headers = {"Content-Type": "text/html"}
            is_redirect = False
            is_permanent_redirect = False
            text = '<a href="/in-en/careers">Search jobs</a><a href="/in-en/careers/jobdetails?id=R123_en">Apply Now</a>'
        class FakeSession:
            def get(self, url, **kwargs): return Response()
        jobs, stats = collect_structured_jobs(source, max_results=10, max_pages=1, session=FakeSession())
        assert jobs == []


class TestDeloitteOfficialCollector:
    def test_deloitte_successfactors_listing_extracts_job_links(self):
        from collectors.company_career_structured import collect_structured_jobs
        source = COMPANY_CAREER_BY_KEY["DELOITTE"]
        class Response:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            is_redirect = False
            is_permanent_redirect = False
            url = "https://southasiacareers.deloitte.com/go/Deloitte-India/718244/"
            text = """<html><body>
              <a href="/job/Bengaluru-Manager-GBS-Strategy-Ops-Functional-Bengaluru-Finance-Transformation/55097544/">Manager | GBS Strategy &amp; Ops: Functional | Bengaluru | Finance Transformation</a>
              <a href="/job/Hyderabad-Lead-Senior-Associate-Engineering/55097545/">Lead Senior Associate | Engineering | Hyderabad</a>
              <a href="/go/Deloitte-India/718244/">Deloitte India</a>
            </body></html>"""
        class FakeSession:
            def get(self, url, **kwargs):
                return Response()
        jobs, stats = collect_structured_jobs(source, max_results=10, max_pages=1, session=FakeSession())
        assert len(jobs) == 2
        assert jobs[0]["external_id"] == "55097544"
        assert "Manager" in jobs[0]["title"]
        assert jobs[0]["job_url"].startswith("https://southasiacareers.deloitte.com/job/")
        assert stats["method"] == "official_deloitte_successfactors_search_html"
