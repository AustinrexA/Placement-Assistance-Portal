import unittest
from urllib.parse import urlparse

from collectors.source_catalog import JOB_PORTALS, PORTAL_BY_KEY, UI_PORTAL_KEYS


class SourceCatalogTests(unittest.TestCase):
    def test_catalog_contains_all_25_scoped_portals_with_unique_keys(self):
        expected = {
            "Naukri", "LinkedIn Jobs", "Indeed", "Foundit", "Internshala",
            "TimesJobs", "Freshersworld", "Cutshort", "Instahyre", "Hirist",
            "Apna", "Shine.com", "Wellfound", "National Career Service (NCS)",
            "iimjobs", "HerKey", "WorkIndia", "Hirect", "Jooble", "QuikrJobs",
            "Jobsora", "Jora", "PlacementIndia", "LetsIntern", "Glassdoor",
        }
        self.assertEqual(len(JOB_PORTALS), 25)
        self.assertEqual({portal["name"] for portal in JOB_PORTALS}, expected)
        self.assertEqual(len({portal["key"] for portal in JOB_PORTALS}), 25)
        self.assertEqual(len({portal["name"].lower() for portal in JOB_PORTALS}), 25)


    def test_ui_allowlist_excludes_jora_after_http_403_and_zero_saved_jobs(self):
        self.assertEqual(UI_PORTAL_KEYS, {
            "NAUKRI", "INDEED", "FOUNDIT", "TIMESJOBS", "INTERNSHALA", "LINKEDIN_JOBS",
            "FRESHERSWORLD", "CUTSHORT", "HIRIST", "SHINE_COM", "WELLFOUND",
            "NATIONAL_CAREER_SERVICE_NCS", "IIMJOBS", "JOOBLE", "QUIKRJOBS",
            "PLACEMENTINDIA", "GLASSDOOR",
        })

    def test_all_portals_have_valid_https_homepages_and_keys(self):
        for portal in JOB_PORTALS:
            with self.subTest(portal=portal["name"]):
                parsed = urlparse(portal["base_url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)
                self.assertIn(portal["key"].lower(), PORTAL_BY_KEY)

    def test_popular_portals_are_ordered_first(self):
        self.assertEqual(
            [portal["name"] for portal in JOB_PORTALS[:4]],
            ["Naukri", "Indeed", "Foundit", "TimesJobs"],
        )
        self.assertTrue(all(portal["popular"] for portal in JOB_PORTALS[:4]))
        self.assertFalse(any(portal["popular"] for portal in JOB_PORTALS[4:]))


if __name__ == "__main__":
    unittest.main()
