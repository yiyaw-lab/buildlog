import uuid
from datetime import datetime, timezone

DECISION_KIND = "decision"


def is_decision(record):
    return isinstance(record, dict) and record.get("kind") == DECISION_KIND


def normalize_tags(tags):
    seen = set()
    normalized = []
    for tag in tags:
        cleaned = tag.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def make_entry(project, title, summary, tags=None, git=None):
    project = project.strip()
    title = title.strip()
    summary = summary.strip()

    if not project:
        raise ValueError("project must not be empty")
    if not title:
        raise ValueError("title must not be empty")
    if not summary:
        raise ValueError("summary must not be empty")

    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "title": title,
        "summary": summary,
        "tags": normalize_tags(tags or []),
    }
    if git is not None:
        entry["git"] = git
    return entry


def make_decision(project, choice, rationale, tags=None, git=None):
    project = project.strip()
    choice = choice.strip()
    rationale = rationale.strip()

    if not project:
        raise ValueError("project must not be empty")
    if not choice:
        raise ValueError("choice must not be empty")
    if not rationale:
        raise ValueError("rationale must not be empty")

    decision = {
        "kind": DECISION_KIND,
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "choice": choice,
        "rationale": rationale,
        "tags": normalize_tags(tags or []),
    }
    if git is not None:
        decision["git"] = git
    return decision
