import unittest
from unittest.mock import patch

from app import app

SAMPLE_JOBS = [
    {"id": 1, "title": "Python Developer", "company": "Infosys", "location": "Chennai", "job_url": "https://example.com/job/1"},
    {"id": 2, "title": "Java Developer", "company": "Example Tech", "location": "Bengaluru", "job_url": "https://example.com/job/2"},
]


class JobPortalAPITests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["authenticated"] = True
            session["username"] = "test-user"

    def test_home_renders_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"V4Career", response.data)

    @patch("app.fetch_all", side_effect=[[{"source_name": "Naukri", "job_count": 10}], [{"source_name": "Naukri", "status": "succeeded", "records_found": 5, "records_inserted": 3}]])
    @patch("app.fetch_one", side_effect=[{"total_jobs": 10, "jobs_added_today": 2, "jobs_added_this_week": 5, "jobs_added_this_month": 8, "jobs_with_salary": 4}, {"scraper_found_today": 5, "scraper_found_this_week": 9, "scraper_found_this_month": 10, "scraper_inserted_today": 3, "failed_runs_today": 0}, {"total_sources": 25, "enabled_sources": 6}])
    def test_dashboard_stats_api(self, mock_fetch_one, mock_fetch_all):
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["metrics"]["total_jobs"], 10)
        self.assertEqual(data["metrics"]["scraper_found_today"], 5)
        self.assertEqual(len(data["top_sources"]), 1)
        self.assertEqual(len(data["recent_runs"]), 1)

    def test_dashboard_redirects_when_not_authenticated(self):
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_invalid_page_parameter(self):
        self.assertEqual(self.client.get("/api/jobs?page=abc").status_code, 400)

    def test_invalid_per_page_parameter(self):
        self.assertEqual(self.client.get("/api/jobs?per_page=500").status_code, 400)

    def test_invalid_source_id(self):
        self.assertEqual(self.client.get("/api/jobs?source_id=abc").status_code, 400)

    def test_invalid_collection_limit(self):
        self.assertEqual(self.client.get("/api/collection-runs?limit=500").status_code, 400)

    def test_unknown_job_returns_404(self):
        with patch("app.fetch_one", return_value=None):
            response = self.client.get("/api/jobs/999999999")
        self.assertEqual(response.status_code, 404)

    def test_unknown_endpoint_returns_404(self):
        self.assertEqual(self.client.get("/api/does-not-exist").status_code, 404)

    @patch("app.fetch_all", return_value=[])
    @patch("app.fetch_one", return_value={"total": 0})
    def test_jobs_report_accepts_company_career_source_type(self, mock_fetch_one, mock_fetch_all):
        response = self.client.get("/api/reports/jobs?source_type=career_site")
        self.assertEqual(response.status_code, 200)
        self.assertIn("LEFT JOIN sources", mock_fetch_one.call_args[0][0])
        self.assertIn("company_career", mock_fetch_one.call_args[0][1])
        self.assertEqual(response.get_json()["pagination"]["total"], 0)

    def test_jobs_report_rejects_unknown_source_type(self):
        response = self.client.get("/api/reports/jobs?source_type=made-up")
        self.assertEqual(response.status_code, 400)

    @patch("app.fetch_all", return_value=[])
    @patch("app.fetch_one", return_value={"total": 0})
    def test_jobs_report_supports_safe_sort_options(self, mock_fetch_one, mock_fetch_all):
        response = self.client.get("/api/reports/jobs?sort=company_asc")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ORDER BY j.company ASC", mock_fetch_all.call_args[0][0])

    @patch("app.fetch_all")
    @patch("app.fetch_one")
    def test_job_listing_returns_data(self, mock_fetch_one, mock_fetch_all):
        mock_fetch_one.return_value = {"total": 2}
        mock_fetch_all.return_value = SAMPLE_JOBS
        response = self.client.get("/api/jobs")
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["data"]), 2)
        self.assertEqual(data["pagination"]["total"], 2)

    @patch("app.fetch_all")
    @patch("app.fetch_one")
    def test_search_is_parameterized(self, mock_fetch_one, mock_fetch_all):
        mock_fetch_one.return_value = {"total": 1}
        mock_fetch_all.return_value = [SAMPLE_JOBS[0]]
        response = self.client.get("/api/jobs?search=Python")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_fetch_one.call_args[0][1], ("%Python%", "%Python%", "%Python%"))

    @patch("app.fetch_all")
    @patch("app.fetch_one")
    def test_pagination_parameters(self, mock_fetch_one, mock_fetch_all):
        mock_fetch_one.return_value = {"total": 25}
        mock_fetch_all.return_value = SAMPLE_JOBS[:1]
        response = self.client.get("/api/jobs?page=2&per_page=10")
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["total_pages"], 3)
        self.assertEqual(mock_fetch_all.call_args[0][1][-2:], (10, 10))

    @patch("app.fetch_all", side_effect=[[{"value": "Python Developer"}], [{"value": "0-2 years"}], [{"value": "Chennai"}]])
    def test_filter_options_return_dependent_facets(self, mock_fetch_all):
        response = self.client.get("/api/filter-options?location=Chennai&source_ids=1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Python Developer", data["roles"])
        self.assertIn("0-2 years", data["experiences"])
        self.assertIn("Chennai", data["locations"])
        self.assertEqual(mock_fetch_all.call_count, 3)


if __name__ == "__main__":
    unittest.main()
