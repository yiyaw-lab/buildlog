#!/usr/bin/env bash
set -euo pipefail

export HOOK_INPUT="$(cat)"

python3 <<'PY'
import json
import os
import sys

try:
    payload = json.loads(os.environ.get("HOOK_INPUT") or "{}")
except json.JSONDecodeError:
    payload = {}

if payload.get("loop_count", 0) >= 1:
    print("{}")
    sys.exit(0)

status = payload.get("status", "")
if status != "completed":
    print("{}")
    sys.exit(0)

followup = (
    "Before we wrap up: summarize what we shipped this session, then run "
    "`buildlog add --project <project> --title \"...\" --summary \"...\" "
    "--capture-git` to record it. Ask me for project and title if unclear."
)

print(json.dumps({"followup_message": followup}))
PY
