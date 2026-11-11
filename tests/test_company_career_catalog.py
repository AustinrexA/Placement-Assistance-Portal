import unittest
from urllib.parse import urlparse

from collectors.company_career_catalog import COMPANY_CAREER_SOURCES, COMPANY_CAREER_BY_KEY


class CompanyCareerCatalogTests(unittest.TestCase):
    def test_catalog_contains_all_25_scoped_companies(self):
        expected = {
            "TCS", "INFOSYS", "ACCENTURE", "COGNIZANT", "HCLTECH", "WIPRO",
            "CAPGEMINI", "AMAZON", "DELOITTE", "TECH_MAHINDRA", "LTIMINDTREE",
            "IBM", "ORACLE", "ZOHO", "MPHASIS", "HEXAWARE", "PERSISTENT_SYSTEMS",
            "MICROSOFT", "GOOGLE", "CGI", "FRESHWORKS", "CISCO", "ADOBE",
            "QUALCOMM", "NVIDIA",
        }
        self.assertEqual({s["key"] for s in COMPANY_CAREER_SOURCES}, expected)
        self.assertEqual(len(COMPANY_CAREER_SOURCES), 25)
        self.assertEqual(len(COMPANY_CAREER_SOURCES), len(COMPANY_CAREER_BY_KEY))
        for key in ("INFOSYS", "AMAZON", "DELOITTE", "WIPRO", "ACCENTURE"):
            self.assertTrue(COMPANY_CAREER_BY_KEY[key]["verified_collector"])

    def test_company_sources_have_https_urls_and_required_fields(self):
        for source in COMPANY_CAREER_SOURCES:
            with self.subTest(source=source["key"]):
                self.assertTrue(source["key"])
                self.assertTrue(source["company"])
                self.assertTrue(source["allowed_hosts"])
                parsed = urlparse(source["base_url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)


if __name__ == "__main__":
    unittest.main()
