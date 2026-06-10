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
            with open(log_path, "w", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(json.dumps(entry) + "\n")

            exit_code, stdout, _ = self.run_cli(
                ["list", "--project", "alpha", "--limit", "1"],
                log_path,
            )

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            self.assertIn("alpha", lines[0])
            self.assertIn("New", lines[0])

    def test_export_writes_jsonl_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entry = {
                "id": "abc123",
                "timestamp": "2026-06-09T12:00:00+00:00",
                "project": "demo",
                "title": "Export me",
                "summary": "For export",
                "tags": ["export"],
            }
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")

            exit_code, stdout, _ = self.run_cli(["export"], log_path)

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), entry)

    def test_module_invocation(self):
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


if __name__ == "__main__":
    unittest.main()
