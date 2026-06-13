import json
import os
import sys
from pathlib import Path

DEFAULT_LOG_PATH = ".buildlog/entries.jsonl"
REQUIRED_STRING_FIELDS = ("id", "timestamp", "project", "title", "summary")
DECISION_STRING_FIELDS = ("id", "timestamp", "project", "choice", "rationale")


def is_valid_git(git):
    if not isinstance(git, dict):
        return False
    for field in ("branch", "commit"):
        if field not in git or not isinstance(git[field], str):
            return False
    if "dirty" not in git or not isinstance(git["dirty"], bool):
        return False
    return True


def is_valid_entry(entry):
    if not isinstance(entry, dict):
        return False

    for field in REQUIRED_STRING_FIELDS:
        if field not in entry or not isinstance(entry[field], str):
            return False

    tags = entry.get("tags")
    if not isinstance(tags, list):
        return False
    if not all(isinstance(tag, str) for tag in tags):
        return False

    git = entry.get("git")
    if git is not None and not is_valid_git(git):
        return False

    return True


def is_valid_decision(entry):
    if not isinstance(entry, dict):
        return False
    if entry.get("kind") != "decision":
        return False

    for field in DECISION_STRING_FIELDS:
        if field not in entry or not isinstance(entry[field], str):
            return False

    tags = entry.get("tags")
    if not isinstance(tags, list):
        return False
    if not all(isinstance(tag, str) for tag in tags):
        return False

    git = entry.get("git")
    if git is not None and not is_valid_git(git):
        return False

    return True


def is_valid_record(entry):
    if not isinstance(entry, dict):
        return False

    kind = entry.get("kind")
    if kind == "decision":
        return is_valid_decision(entry)
    if kind is not None:
        return False

    return is_valid_entry(entry)


def get_log_path():
    return os.environ.get("BUILDLOG_PATH", DEFAULT_LOG_PATH)


def append_entry(entry):
    path = Path(get_log_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_entries():
    path = Path(get_log_path())
    if not path.exists():
        return []

    entries = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                print(
                    f"warning: skipping invalid JSON on line {line_number}",
                    file=sys.stderr,
                )
                continue

            if not is_valid_record(parsed):
                print(
                    f"warning: skipping malformed entry on line {line_number}",
                    file=sys.stderr,
                )
                continue

            entries.append(parsed)
    return entries
