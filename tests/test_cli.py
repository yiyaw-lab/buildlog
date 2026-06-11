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


EMPTY_STATS_OUTPUT = "\n".join(
    [
        "Total entries: 0",
        "Projects: 0",
        "Top tags: none",
        "Latest entry: none",
    ]
)


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

    def test_stats_empty_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "missing.jsonl")
            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.strip(), EMPTY_STATS_OUTPUT)

    def test_stats_basic_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "alpha",
                    "title": "First",
                    "summary": "One",
                    "tags": ["infra"],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-10T12:00:00+00:00",
                    "project": "beta",
                    "title": "Second",
                    "summary": "Two",
                    "tags": ["cli", "infra"],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Total entries: 2", stdout)
            self.assertIn("Projects: 2", stdout)
            self.assertIn("Top tags: infra, cli", stdout)
            self.assertIn("Latest entry: 2026-06-10 — beta — Second", stdout)

    def test_stats_top_tags_by_frequency(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "alpha",
                    "title": "One",
                    "summary": "First",
                    "tags": ["cursor", "cli"],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-09T11:00:00+00:00",
                    "project": "alpha",
                    "title": "Two",
                    "summary": "Second",
                    "tags": ["cursor", "testing"],
                },
                {
                    "id": "3",
                    "timestamp": "2026-06-09T12:00:00+00:00",
                    "project": "beta",
                    "title": "Three",
                    "summary": "Third",
                    "tags": ["cursor"],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Top tags: cursor, cli, testing", stdout)

    def test_stats_top_tags_alphabetical_tie_break(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "alpha",
                    "title": "One",
                    "summary": "First",
                    "tags": ["zebra"],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-09T11:00:00+00:00",
                    "project": "alpha",
                    "title": "Two",
                    "summary": "Second",
                    "tags": ["alpha"],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Top tags: alpha, zebra", stdout)

    def test_stats_top_tags_limited_to_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": str(index),
                    "timestamp": f"2026-06-09T{index:02d}:00:00+00:00",
                    "project": "alpha",
                    "title": f"Entry {index}",
                    "summary": "Summary",
                    "tags": [f"tag{index}"],
                }
                for index in range(1, 7)
            ]
            entries.append(
                {
                    "id": "7",
                    "timestamp": "2026-06-09T07:00:00+00:00",
                    "project": "alpha",
                    "title": "Extra",
                    "summary": "Summary",
                    "tags": ["common"],
                }
            )
            entries.append(
                {
                    "id": "8",
                    "timestamp": "2026-06-09T08:00:00+00:00",
                    "project": "alpha",
                    "title": "Extra 2",
                    "summary": "Summary",
                    "tags": ["common"],
                }
            )
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Top tags: common, tag1, tag2, tag3, tag4", stdout)
            self.assertNotIn("tag5", stdout)

    def test_stats_no_tags_shows_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entry = {
                "id": "1",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "Untagged",
                "summary": "No tags here",
                "tags": [],
            }
            self.write_entries(log_path, [entry])

            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Top tags: none", stdout)

    def test_stats_latest_entry_by_timestamp_not_file_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-10T12:00:00+00:00",
                    "project": "newer",
                    "title": "Newest",
                    "summary": "Latest by timestamp",
                    "tags": [],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "older",
                    "title": "Older",
                    "summary": "Earlier",
                    "tags": [],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Latest entry: 2026-06-10 — newer — Newest", stdout)

    def test_stats_skips_malformed_entry_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            valid = {
                "id": "1",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "Valid",
                "summary": "Only valid entry",
                "tags": ["infra"],
            }
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"project": "alpha", "title": "Missing fields"}) + "\n")
                handle.write(json.dumps(valid) + "\n")

            exit_code, stdout, stderr = self.run_cli(["stats"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Total entries: 1", stdout)
            self.assertIn("Latest entry: 2026-06-09 — alpha — Valid", stdout)
            self.assertIn("warning:", stderr)

    def test_module_invocation_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            self.write_entries(log_path, self.sample_entries())
            env = os.environ.copy()
            env["BUILDLOG_PATH"] = log_path
            result = subprocess.run(
                [sys.executable, "-m", "buildlog", "stats"],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Total entries: 2", result.stdout)

    def test_handoff_empty_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "missing.jsonl")
            exit_code, stdout, _ = self.run_cli(["handoff"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("# Buildlog Handoff", stdout)
            self.assertIn("## Recent shipping", stdout)
            self.assertIn("## Active projects", stdout)
            self.assertIn("## Recurring themes", stdout)
            self.assertIn("## Resume prompt", stdout)
            self.assertIn("none", stdout)
            self.assertIn("python -m buildlog add", stdout)

    def test_handoff_basic_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "alpha",
                    "title": "First",
                    "summary": "Initial work",
                    "tags": ["infra"],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-10T12:00:00+00:00",
                    "project": "beta",
                    "title": "Second",
                    "summary": "Latest work",
                    "tags": ["cli"],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["handoff"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("- 2026-06-10 — beta — Second", stdout)
            self.assertIn("  Latest work", stdout)
            self.assertIn("- beta (1 entries, latest: 2026-06-10)", stdout)
            self.assertIn("- alpha (1 entries, latest: 2026-06-09)", stdout)
            self.assertIn("Top tags: cli, infra", stdout)
            self.assertIn("You are resuming work on this builder project.", stdout)

    def test_handoff_respects_limit_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": str(index),
                    "timestamp": f"2026-06-0{index}T10:00:00+00:00",
                    "project": "alpha",
                    "title": f"Entry {index}",
                    "summary": f"Summary {index}",
                    "tags": [],
                }
                for index in range(1, 7)
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["handoff"], log_path)

            self.assertEqual(exit_code, 0)
            shipping_section = stdout.split("## Active projects")[0]
            self.assertEqual(shipping_section.count("- 2026-06-"), 5)

    def test_handoff_limit_zero_shows_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            self.write_entries(log_path, self.sample_entries())

            exit_code, stdout, _ = self.run_cli(["handoff", "--limit", "0"], log_path)

            self.assertEqual(exit_code, 0)
            shipping_section = stdout.split("## Active projects")[0]
            self.assertEqual(shipping_section.count("- 2026-06-"), 2)

    def test_handoff_limit_negative_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            exit_code, stdout, stderr = self.run_cli(["handoff", "--limit", "-1"], log_path)

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("error:", stderr)

    def test_handoff_filters_by_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "alpha",
                    "title": "Alpha entry",
                    "summary": "Alpha work",
                    "tags": ["alpha-tag"],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-10T12:00:00+00:00",
                    "project": "beta",
                    "title": "Beta entry",
                    "summary": "Beta work",
                    "tags": ["beta-tag"],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["handoff", "--project", "alpha"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Alpha entry", stdout)
            self.assertNotIn("Beta entry", stdout)
            self.assertIn("- alpha (1 entries, latest: 2026-06-09)", stdout)
            self.assertNotIn("- beta", stdout)

    def test_handoff_recent_shipping_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entries = [
                {
                    "id": "1",
                    "timestamp": "2026-06-10T12:00:00+00:00",
                    "project": "newer",
                    "title": "Newest",
                    "summary": "Latest by timestamp",
                    "tags": [],
                },
                {
                    "id": "2",
                    "timestamp": "2026-06-09T10:00:00+00:00",
                    "project": "older",
                    "title": "Older",
                    "summary": "Earlier",
                    "tags": [],
                },
            ]
            self.write_entries(log_path, entries)

            exit_code, stdout, _ = self.run_cli(["handoff"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertLess(stdout.index("Newest"), stdout.index("Older"))

    def test_handoff_omits_entry_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            entry = {
                "id": "deadbeefdeadbeefdeadbeefdeadbeef",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "Visible title",
                "summary": "Visible summary",
                "tags": [],
            }
            self.write_entries(log_path, [entry])

            exit_code, stdout, _ = self.run_cli(["handoff"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertNotIn("deadbeef", stdout)
            self.assertIn("Visible title", stdout)

    def test_handoff_skips_malformed_entry_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            valid = {
                "id": "1",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "project": "alpha",
                "title": "Valid",
                "summary": "Only valid entry",
                "tags": ["infra"],
            }
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"project": "alpha", "title": "Missing fields"}) + "\n")
                handle.write(json.dumps(valid) + "\n")

            exit_code, stdout, stderr = self.run_cli(["handoff"], log_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("Valid", stdout)
            self.assertNotIn("Missing fields", stdout)
            self.assertIn("warning:", stderr)

    def test_module_invocation_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "entries.jsonl")
            self.write_entries(log_path, self.sample_entries())
            env = os.environ.copy()
            env["BUILDLOG_PATH"] = log_path
            result = subprocess.run(
                [sys.executable, "-m", "buildlog", "handoff"],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("# Buildlog Handoff", result.stdout)


if __name__ == "__main__":
    unittest.main()
