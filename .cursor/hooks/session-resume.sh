#!/usr/bin/env bash
set -euo pipefail

export HOOK_INPUT="$(cat)"

python3 <<'PY'
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RESUME_FILE = Path(".buildlog/latest-resume.md")

try:
    payload = json.loads(os.environ.get("HOOK_INPUT") or "{}")
except json.JSONDecodeError:
    payload = {}

if payload.get("is_background_agent"):
    print(json.dumps({"additional_context": ""}))
    sys.exit(0)

if payload.get("composer_mode") == "ask":
    print(json.dumps({"additional_context": ""}))
    sys.exit(0)


def run_resume():
    commands = []
    if shutil.which("buildlog"):
        commands.append(["buildlog", "resume"])
    commands.append([sys.executable, "-m", "buildlog", "resume"])

    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue
        if result.returncode == 0:
            return result.stdout.strip()
    return ""


resume = run_resume()
if not resume:
    resume = (
        "No build log context available yet. "
        "Run `buildlog add ...` to start recording what you ship."
    )

context = (
    "## Buildlog continuity context (auto-injected at session start)\n\n"
    f"{resume}\n\n"
    "Use this as prior builder context. Ask what changed since the last logged entry "
    "before making multi-file edits."
)

max_len = 8192
if len(context) > max_len:
    context = context[:max_len] + "\n\n...(truncated)"

RESUME_FILE.parent.mkdir(parents=True, exist_ok=True)
RESUME_FILE.write_text(context + "\n", encoding="utf-8")

print(json.dumps({"additional_context": context}))
PY
