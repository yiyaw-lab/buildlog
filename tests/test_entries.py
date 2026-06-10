import unittest

from buildlog.entries import make_entry, normalize_tags


class EntryTests(unittest.TestCase):
    def test_make_entry_has_required_fields(self):
        entry = make_entry("myapp", "Setup", "Initial work", ["infra"])

        self.assertIn("id", entry)
        self.assertIn("timestamp", entry)
        self.assertEqual(entry["project"], "myapp")
        self.assertEqual(entry["title"], "Setup")
        self.assertEqual(entry["summary"], "Initial work")
        self.assertEqual(entry["tags"], ["infra"])

    def test_make_entry_normalizes_tags(self):
        entry = make_entry(
            "myapp",
            "Setup",
            "Initial work",
            [" infra ", "python", "", "python", "  "],
        )

        self.assertEqual(entry["tags"], ["infra", "python"])

    def test_make_entry_rejects_empty_required_fields(self):
        with self.assertRaises(ValueError):
            make_entry("", "title", "summary")
        with self.assertRaises(ValueError):
            make_entry("project", "", "summary")
        with self.assertRaises(ValueError):
            make_entry("project", "title", "")

    def test_normalize_tags_deduplicates(self):
        self.assertEqual(normalize_tags(["a", "a", "b"]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
