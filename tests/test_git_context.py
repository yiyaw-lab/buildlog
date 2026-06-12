import os
import subprocess
import unittest
from pathlib import Path

from buildlog import git_context


class GitContextTests(unittest.TestCase):
    def init_repo(self, tmp, filename="file.txt", content="hello", message="initial"):
        subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp,
            check=True,
            capture_output=True,
        )
        file_path = Path(tmp) / filename
        file_path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", str(file_path.name)], cwd=tmp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=tmp, check=True, capture_output=True)

    def test_capture_git_context_in_repo(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.init_repo(tmp)
            context, warning = git_context.capture_git_context(cwd=tmp)

            self.assertIsNone(warning)
            self.assertTrue(context["branch"])
            self.assertEqual(len(context["commit"]), 40)
            self.assertFalse(context["dirty"])

    def test_capture_git_context_dirty_tree(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.init_repo(tmp)
            Path(tmp, "dirty.txt").write_text("change", encoding="utf-8")
            context, warning = git_context.capture_git_context(cwd=tmp)

            self.assertIsNone(warning)
            self.assertTrue(context["dirty"])

    def test_capture_git_context_outside_repo(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            context, warning = git_context.capture_git_context(cwd=tmp)

            self.assertIsNone(context)
            self.assertEqual(warning, "not inside a git repository")

    def test_git_delta_since_by_commit(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.init_repo(tmp, message="first")
            first_context, _ = git_context.capture_git_context(cwd=tmp)
            Path(tmp, "second.txt").write_text("more", encoding="utf-8")
            subprocess.run(["git", "add", "second.txt"], cwd=tmp, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "second"], cwd=tmp, check=True, capture_output=True)

            anchor = {
                "timestamp": "2026-06-09T10:00:00+00:00",
                "git": first_context,
            }
            delta = git_context.format_git_delta_since(anchor, cwd=tmp)

            self.assertTrue(delta["available"])
            self.assertEqual(delta["commit_count"], 1)
            self.assertIn("second", delta["text"])

    def test_git_delta_since_fallback_timestamp(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.init_repo(tmp, message="first")
            anchor = {
                "timestamp": "1970-01-01T00:00:00+00:00",
            }
            delta = git_context.format_git_delta_since(anchor, cwd=tmp)

            self.assertTrue(delta["available"])
            self.assertGreaterEqual(delta["commit_count"], 1)

    def test_git_delta_since_missing_commit(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.init_repo(tmp)
            anchor = {
                "timestamp": "1970-01-01T00:00:00+00:00",
                "git": {
                    "branch": "main",
                    "commit": "0" * 40,
                    "dirty": False,
                },
            }
            delta = git_context.format_git_delta_since(anchor, cwd=tmp)

            self.assertTrue(delta["available"])
            self.assertGreaterEqual(delta["commit_count"], 1)


if __name__ == "__main__":
    unittest.main()
