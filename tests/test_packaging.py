import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from buildlog.cli import run


class PackagingTests(unittest.TestCase):
    def test_run_exits_with_main_status(self):
        with patch("buildlog.cli.main", return_value=0) as main:
            with self.assertRaises(SystemExit) as ctx:
                run()
            self.assertEqual(ctx.exception.code, 0)
            main.assert_called_once()

    def test_console_script_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = os.path.join(tmp, "venv")
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            pip = os.path.join(venv_dir, "bin", "pip")
            buildlog = os.path.join(venv_dir, "bin", "buildlog")
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            subprocess.run([pip, "install", "-e", repo_root], check=True, capture_output=True)
            result = subprocess.run(
                [buildlog, "stats"],
                capture_output=True,
                text=True,
                env={**os.environ, "BUILDLOG_PATH": os.path.join(tmp, "missing.jsonl")},
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Total entries: 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
