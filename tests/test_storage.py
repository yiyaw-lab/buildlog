import json
import os
import tempfile
import unittest
from unittest.mock import patch

from buildlog import storage


class StorageTests(unittest.TestCase):
    def test_get_log_path_default(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BUILDLOG_PATH", None)
            self.assertEqual(storage.get_log_path(), ".buildlog/entries.jsonl")

    def test_get_log_path_override(self):
        with patch.dict(os.environ, {"BUILDLOG_PATH": "/tmp/custom.jsonl"}):
            self.assertEqual(storage.get_log_path(), "/tmp/custom.jsonl")

    def test_append_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entry = {
                "id": "abc123",
                "timestamp": "2026-06-09T12:00:00+00:00",
                "project": "demo",
                "title": "Test",
                "summary": "Roundtrip",
                "tags": ["test"],
            }
            with patch.dict(os.environ, {"BUILDLOG_PATH": log_path}):
                storage.append_entry(entry)
                loaded = storage.load_entries()

            self.assertEqual(loaded, [entry])

    def test_load_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "missing.jsonl")
            with patch.dict(os.environ, {"BUILDLOG_PATH": log_path}):
                self.assertEqual(storage.load_entries(), [])

    def test_invalid_json_line_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            valid = {
                "id": "abc123",
                "timestamp": "2026-06-09T12:00:00+00:00",
                "project": "demo",
                "title": "Test",
                "summary": "Valid",
                "tags": [],
            }
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write("not json\n")
                handle.write(json.dumps(valid) + "\n")

            with patch.dict(os.environ, {"BUILDLOG_PATH": log_path}):
                with patch("sys.stderr") as stderr:
                    loaded = storage.load_entries()

            self.assertEqual(loaded, [valid])
            stderr.write.assert_called()

    def test_malformed_valid_json_entry_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            valid = {
                "id": "abc123",
                "timestamp": "2026-06-09T12:00:00+00:00",
                "project": "demo",
                "title": "Test",
                "summary": "Valid",
                "tags": [],
            }
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"project": "demo", "title": "Missing fields"}) + "\n")
                handle.write(json.dumps(valid) + "\n")

            with patch.dict(os.environ, {"BUILDLOG_PATH": log_path}):
                with patch("sys.stderr") as stderr:
                    loaded = storage.load_entries()

            self.assertEqual(loaded, [valid])
            stderr.write.assert_called()

    def test_invalid_git_field_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            valid = {
                "id": "abc123",
                "timestamp": "2026-06-09T12:00:00+00:00",
                "project": "demo",
                "title": "Test",
                "summary": "Valid",
                "tags": [],
            }
            invalid_git = dict(valid)
            invalid_git["id"] = "badgit"
            invalid_git["git"] = {"branch": "main", "commit": "abc", "dirty": "no"}
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(invalid_git) + "\n")
                handle.write(json.dumps(valid) + "\n")

            with patch.dict(os.environ, {"BUILDLOG_PATH": log_path}):
                with patch("sys.stderr") as stderr:
                    loaded = storage.load_entries()

            self.assertEqual(loaded, [valid])
            stderr.write.assert_called()


if __name__ == "__main__":
    unittest.main()
