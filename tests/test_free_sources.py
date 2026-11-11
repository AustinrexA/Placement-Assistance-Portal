import unittest

from scripts.run_free_sources import job_is_india, normalize_record


class FreeSourceTests(unittest.TestCase):
    def test_indian_city_is_accepted(self):
        self.assertTrue(job_is_india({"location": "Chennai, Tamil Nadu"}))

    def test_india_is_accepted(self):
        self.assertTrue(job_is_india({"jobGeo": "India"}))

    def test_worldwide_remote_is_not_assumed_india(self):
        self.assertFalse(job_is_india({"location": "Worldwide"}))

    def test_missing_location_is_not_assumed_india(self):
        self.assertFalse(job_is_india({"location": ""}))

    def test_normalization_maps_lever_style_fields(self):
        job = normalize_record({
            "id": "123",
            "text": "Software Engineer",
            "title": "Software Engineer",
            "company": "Example Co",
            "location": "Bengaluru, India",
            "url": "https://jobs.example.com/123",
            "descriptionPlain": "Build software",
        }, "lever")
        self.assertEqual(job["title"], "Software Engineer")
        self.assertEqual(job["company"], "Example Co")
        self.assertEqual(job["location"], "Bengaluru, India")
        self.assertEqual(job["external_id"], "123")
        self.assertEqual(job["status"], "active")
        self.assertEqual(len(job["url_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
