import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from buildlog.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, args, log_path):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.dict(os.environ, {"BUILDLOG_PATH": log_path}):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def sample_entries(self):
        return [
            {
                "id": "1",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "Old",
                "summary": "First entry",
                "tags": ["infra"],
            },
            {
                "id": "2",
                "timestamp": "2026-06-09T12:00:00+00:00",
                "project": "demo",
                "title": "Export me",
                "summary": "For export",
                "tags": ["export"],
            },
        ]

    def write_entries(self, log_path, entries):
        with open(log_path, "w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry) + "\n")

    def test_add_command_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            exit_code, stdout, _ = self.run_cli(
                [
                    "add",
                    "--project",
                    "demo",
                    "--title",
                    "First entry",
                    "--summary",
                    "Added from test",
                    "--tag",
                    "test",
                ],
                log_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(stdout.startswith("Added "))
            with open(log_path, encoding="utf-8") as handle:
                lines = [line for line in handle if line.strip()]
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["project"], "demo")
            self.assertEqual(entry["tags"], ["test"])

    def test_list_empty_storage_prints_empty_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "missing.jsonl")
            exit_code, stdout, _ = self.run_cli(["list"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "")

    def test_list_filters_by_project_and_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "alpha",
                    "title": "Old",
                    "summary": "First",
                    "tags": [],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-09T11:00:00+00:00",
                    "project": "beta",
                    "title": "Middle",
                    "summary": "Second",
                    "tags": [],
                },
                {
                    "id": "3",
                    "timestamp": "2026-06-09T12:00:00+00:00",
                    "project": "alpha",
                    "title": "New",
                    "summary": "Third",
                    "tags": [],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(
                ["list", "--project", "alpha", "--limit", "1"],
                log_path,
            )

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            self.assertIn("alpha", lines[0])
            self.assertIn("New", lines[0])

    def test_list_limit_zero_returns_all_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            self.write_entries(log_path, self.sample_entries())

            exit_code, stdout, _ = self.run_cli(["list", "--limit", "0"], log_path)

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)

    def test_list_limit_negative_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            exit_code, stdout, stderr = self.run_cli(["list", "--limit", "-1"], log_path)

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("error:", stderr)

    def test_export_empty_storage_markdown_prints_empty_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "missing.jsonl")
            exit_code, stdout, _ = self.run_cli(["export"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "")

    def test_export_empty_storage_jsonl_prints_empty_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "missing.jsonl")
            exit_code, stdout, _ = self.run_cli(["export", "--format", "jsonl"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "")

    def test_export_writes_markdown_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = self.sample_entries()
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["export"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertTrue(stdout.startswith("# Build Log\n\n"))
            self.assertLess(stdout.index("Old"), stdout.index("Export me"))
            self.assertIn("## 2026-06-09 — alpha", stdout)
            self.assertIn("### Old", stdout)
            self.assertIn("First entry", stdout)
            self.assertIn("Tags: infra", stdout)

    def test_export_markdown_without_tags_omits_tags_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entry = {
                "id": "1",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "No tags",
                "summary": "Summary only",
                "tags": [],
            }
            self.write_entries(log_path, [entry])

            exit_code, stdout, _ = self.run_cli(["export"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertNotIn("Tags:", stdout)

    def test_export_markdown_single_entry_has_no_trailing_separator(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entry = {
                "id": "1",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "Only one",
                "summary": "Single entry",
                "tags": ["solo"],
            }
            self.write_entries(log_path, [entry])

            exit_code, stdout, _ = self.run_cli(["export"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertNotIn("---", stdout)
            self.assertFalse(stdout.endswith("\n\n\n"))

    def test_export_writes_jsonl_preserves_full_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = self.sample_entries()
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["export", "--format", "jsonl"], log_path)

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertEqual([json.loads(line) for line in lines], entries)

    def test_malformed_valid_json_entry_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            valid = self.sample_entries()[0]
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"project": "alpha", "title": "Missing fields"}) + "\n")
                handle.write(json.dumps(valid) + "\n")

            exit_code, stdout, stderr = self.run_cli(["export", "--format", "jsonl"], log_path)

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), valid)
            self.assertIn("warning:", stderr)

    def test_module_invocation_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            env = os.environ.copy()
            env["BUILDLOG_PATH"] = log_path
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "buildlog",
                    "add",
                    "--project",
                    "demo",
                    "--title",
                    "Module path",
                    "--summary",
                    "Works via python -m",
                ],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Added", result.stdout)

    def test_module_invocation_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            self.write_entries(log_path, self.sample_entries())
            env = os.environ.copy()
            env["BUILDLOG_PATH"] = log_path
            result = subprocess.run(
                [sys.executable, "-m", "buildlog", "export"],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("# Build Log", result.stdout)


if __name__ == "__main__":
    unittest.main()
