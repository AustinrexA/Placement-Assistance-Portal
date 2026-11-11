import unittest
from types import SimpleNamespace

from collectors.db import column_names


class DatabaseCompatibilityHelperTests(unittest.TestCase):
    def test_column_names_support_psycopg_metadata(self):
        cursor = SimpleNamespace(description=[SimpleNamespace(name="id"), SimpleNamespace(name="title")])
        self.assertEqual(column_names(cursor), ["id", "title"])

    def test_column_names_support_mysql_metadata(self):
        cursor = SimpleNamespace(description=[("id",), ("title",)])
        self.assertEqual(column_names(cursor), ["id", "title"])

    def test_column_names_support_empty_description(self):
        cursor = SimpleNamespace(description=None)
        self.assertEqual(column_names(cursor), [])


if __name__ == "__main__":
    unittest.main()
