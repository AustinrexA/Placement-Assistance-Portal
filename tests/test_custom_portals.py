import unittest
from bs4 import BeautifulSoup
from collectors.custom_portals import _jsonld_jobs, _job_from_jsonld, _fallback, _embedded_job_records, CustomPortalCollector, PORTALS

class CustomPortalParserTests(unittest.TestCase):
    def test_jsonld_jobposting_extracts(self):
        soup=BeautifulSoup("""<script type='application/ld+json'>{"@context":"https://schema.org","@type":"JobPosting","title":"Python Developer","datePosted":"2026-11-01","hiringOrganization":{"@type":"Organization","name":"Example"},"jobLocation":{"address":{"addressLocality":"Chennai","addressRegion":"Tamil Nadu"}},"url":"https://www.hirist.tech/j/python-developer-123"}</script>""","html.parser")
        records=_jsonld_jobs(soup); self.assertEqual(len(records),1)
        raw=_job_from_jsonld(records[0],"hirist")
        self.assertEqual(raw["title"],"Python Developer"); self.assertEqual(raw["company"],"Example")
        self.assertEqual(raw["location"],"Chennai, Tamil Nadu"); self.assertTrue(raw["job_url"].startswith("https://"))
    def test_navigation_links_are_rejected(self):
        soup=BeautifulSoup('<a href="/c/ai-ml-jobs">AI/ML</a><a href="/j/python-engineer-123">Python Engineer</a>',"html.parser")
        rows=_fallback(soup,"hirist")
        self.assertEqual([x["title"] for x in rows],["Python Engineer"])
    def test_embedded_json_job_objects_are_extracted(self):
        soup=BeautifulSoup('<script type="application/json">{"jobs":[{"id":123,"title":"QA Engineer","url":"/job-123-qa-engineer","companyName":"Acme","location":"Chennai"}]}</script>',"html.parser")
        rows=_embedded_job_records(soup,"instahyre")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["company"],"Acme")
    def test_freshersworld_real_job_detail_url_is_recognized(self):
        from collectors.custom_portals import JOB_PATHS
        self.assertRegex("https://www.freshersworld.com/jobs/trainee-software-engineer-3821904",
                         JOB_PATHS["freshersworld"])
    def test_all_portals_have_search_url(self):
        for portal in PORTALS:
            c=CustomPortalCollector(portal,"Python Developer","Chennai",10)
            self.assertIn("https://",c.search_url())
        self.assertIn("freshers",CustomPortalCollector("freshersworld","Python Developer","Chennai").search_url())
if __name__=="__main__": unittest.main()
