import unittest

from buildlog.entries import is_decision, make_decision, make_entry, normalize_tags


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

    def test_make_decision_has_required_fields(self):
        decision = make_decision("myapp", "Use JSONL", "Keeps one storage path")

        self.assertTrue(is_decision(decision))
        self.assertIn("id", decision)
        self.assertIn("timestamp", decision)
        self.assertEqual(decision["project"], "myapp")
        self.assertEqual(decision["choice"], "Use JSONL")
        self.assertEqual(decision["rationale"], "Keeps one storage path")
        self.assertEqual(decision["tags"], [])

    def test_make_decision_rejects_empty_required_fields(self):
        with self.assertRaises(ValueError):
            make_decision("", "choice", "rationale")
        with self.assertRaises(ValueError):
            make_decision("project", "", "rationale")
        with self.assertRaises(ValueError):
            make_decision("project", "choice", "")


if __name__ == "__main__":
    unittest.main()
