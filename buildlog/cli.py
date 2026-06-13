import argparse
import json
import sys
from pathlib import Path

from buildlog import entries, git_context, storage

DEFAULT_LIST_LIMIT = 20
DEFAULT_HANDOFF_LIMIT = 5


def build_parser():
    parser = argparse.ArgumentParser(prog="buildlog", description="Record daily build logs locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a build log entry.")
    add_parser.add_argument("--project", required=True)
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--tag", action="append", default=[], dest="tags")
    add_parser.add_argument(
        "--capture-git",
        action="store_true",
        help="Attach current git branch, commit, and dirty state to the entry.",
    )

    list_parser = subparsers.add_parser("list", help="List recent build log entries.")
    list_parser.add_argument("--project")
    list_parser.add_argument("--tag", action="append", default=[], dest="tags")
    list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIST_LIMIT,
        help=f"Maximum entries to show (default: {DEFAULT_LIST_LIMIT}). Use 0 for all.",
    )

    export_parser = subparsers.add_parser("export", help="Export all entries to stdout.")
    export_parser.add_argument(
        "--format",
        choices=("markdown", "jsonl"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    export_parser.add_argument(
        "-o",
        "--output",
        help="Write export output to a file instead of stdout.",
    )

    subparsers.add_parser("stats", help="Show a summary of stored build log entries.")

    handoff_parser = subparsers.add_parser(
        "handoff",
        help="Generate an agent-ready session resume bundle.",
    )
    handoff_parser.add_argument("--project")
    handoff_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_HANDOFF_LIMIT,
        help=f"Maximum recent entries to include (default: {DEFAULT_HANDOFF_LIMIT}). Use 0 for all.",
    )
    handoff_parser.add_argument(
        "-o",
        "--output",
        help="Write handoff output to a file instead of stdout.",
    )

    show_parser = subparsers.add_parser("show", help="Show a single build log entry by id.")
    show_parser.add_argument("--id", required=True, help="Entry id or unique id prefix.")

    resume_parser = subparsers.add_parser(
        "resume",
        help="Generate a continuity bundle with git changes since the last entry.",
    )
    resume_parser.add_argument("--project")
    resume_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_HANDOFF_LIMIT,
        help=f"Maximum recent entries to include (default: {DEFAULT_HANDOFF_LIMIT}). Use 0 for all.",
    )
    resume_parser.add_argument(
        "-o",
        "--output",
        help="Write resume output to a file instead of stdout.",
    )

    decide_parser = subparsers.add_parser("decide", help="Record a builder decision.")
    decide_parser.add_argument("--project", required=True)
    decide_parser.add_argument("--choice", required=True)
    decide_parser.add_argument("--rationale", required=True)
    decide_parser.add_argument("--tag", action="append", default=[], dest="tags")
    decide_parser.add_argument(
        "--capture-git",
        action="store_true",
        help="Attach current git branch, commit, and dirty state to the decision.",
    )

    return parser


def cmd_add(args):
    try:
        git_info = None
        if args.capture_git:
            git_info, warning = git_context.capture_git_context()
            if warning:
                git_context.warn(warning)

        entry = entries.make_entry(
            args.project,
            args.title,
            args.summary,
            args.tags,
            git=git_info,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    storage.append_entry(entry)
    print(f"Added {entry['id']}")
    return 0


def cmd_decide(args):
    try:
        git_info = None
        if args.capture_git:
            git_info, warning = git_context.capture_git_context()
            if warning:
                git_context.warn(warning)

        decision = entries.make_decision(
            args.project,
            args.choice,
            args.rationale,
            args.tags,
            git=git_info,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    storage.append_entry(decision)
    print(f"Added {decision['id']}")
    return 0


def cmd_list(args):
    if args.limit is not None and args.limit < 0:
        print("error: limit must be zero or greater", file=sys.stderr)
        return 1

    loaded = storage.load_entries()
    if args.project:
        loaded = [entry for entry in loaded if entry["project"] == args.project]
    if args.tags:
        required_tags = set(args.tags)
        loaded = [entry for entry in loaded if required_tags.intersection(entry["tags"])]

    loaded.sort(key=lambda entry: entry["timestamp"], reverse=True)

    if args.limit == 0:
        selected = loaded
    else:
        selected = loaded[: args.limit]

    for entry in selected:
        tags = entry["tags"]
        tag_text = ", ".join(tags)
        tag_suffix = f"  [{tag_text}]" if tag_text else ""
        if entries.is_decision(entry):
            print(
                f"{entry['timestamp']}  "
                f"{entry['project']}  "
                f"[decision]  "
                f"{entry['choice']}  "
                f"{entry['rationale']}{tag_suffix}"
            )
        else:
            print(
                f"{entry['timestamp']}  "
                f"{entry['project']}  "
                f"{entry['title']}  "
                f"{entry['summary']}{tag_suffix}"
            )
    return 0


def format_entry_markdown(entry):
    date = entry["timestamp"][:10]
    if entries.is_decision(entry):
        lines = [
            f"## {date} — {entry['project']}",
            "",
            f"### Decision: {entry['choice']}",
            "",
            entry["rationale"],
        ]
    else:
        lines = [
            f"## {date} — {entry['project']}",
            "",
            f"### {entry['title']}",
            "",
            entry["summary"],
        ]
    if entry["tags"]:
        lines.extend(["", f"Tags: {', '.join(entry['tags'])}"])
    return "\n".join(lines)


def emit_output(content, output_path):
    if output_path:
        path = Path(output_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if content and not content.endswith("\n"):
                content = content + "\n"
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    if not content:
        return 0

    sys.stdout.write(content if content.endswith("\n") else content + "\n")
    return 0


def format_export(records, fmt):
    if fmt == "jsonl":
        if not records:
            return ""
        return "\n".join(json.dumps(entry, ensure_ascii=False) for entry in records) + "\n"

    if not records:
        return ""

    lines = ["# Build Log", ""]
    for index, entry in enumerate(records):
        lines.append(format_entry_markdown(entry))
        if index < len(records) - 1:
            lines.append("")
    return "\n".join(lines) + "\n"


def export_entries(records, fmt):
    sys.stdout.write(format_export(records, fmt))


def cmd_export(args):
    loaded = storage.load_entries()
    loaded.sort(key=lambda entry: entry["timestamp"])
    return emit_output(format_export(loaded, args.format), args.output)


def _top_tags(entries, limit=5):
    tag_counts = {}
    for entry in entries:
        for tag in entry["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if not tag_counts:
        return []

    ranked_tags = sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [tag for tag, _ in ranked_tags]


def format_stats(records):
    top_tags = _top_tags(records)
    top_tags_text = ", ".join(top_tags) if top_tags else "none"

    if records:
        latest = max(records, key=lambda entry: entry["timestamp"])
        if entries.is_decision(latest):
            latest_text = f"{latest['timestamp'][:10]} — {latest['project']} — {latest['choice']}"
        else:
            latest_text = f"{latest['timestamp'][:10]} — {latest['project']} — {latest['title']}"
    else:
        latest_text = "none"

    return "\n".join(
        [
            f"Total entries: {len(records)}",
            f"Projects: {len({entry['project'] for entry in records})}",
            f"Top tags: {top_tags_text}",
            f"Latest entry: {latest_text}",
        ]
    )


def _format_handoff_shipping_entry(entry):
    date = entry["timestamp"][:10]
    lines = [
        f"- {date} — {entry['project']} — {entry['title']}",
        f"  {entry['summary']}",
    ]
    if entry["tags"]:
        lines.append(f"  Tags: {', '.join(entry['tags'])}")
    return "\n".join(lines)


def _format_handoff_decision_entry(entry):
    date = entry["timestamp"][:10]
    lines = [
        f"- {date} — {entry['project']} — {entry['choice']}",
        f"  {entry['rationale']}",
    ]
    if entry["tags"]:
        lines.append(f"  Tags: {', '.join(entry['tags'])}")
    return "\n".join(lines)


def _recent_records(records, limit, predicate):
    filtered = [record for record in records if predicate(record)]
    if limit == 0:
        return filtered
    return filtered[:limit]


def _format_active_projects(entries):
    if not entries:
        return "none"

    by_project = {}
    for entry in entries:
        project = entry["project"]
        date = entry["timestamp"][:10]
        if project not in by_project:
            by_project[project] = {"count": 0, "latest": date}
        by_project[project]["count"] += 1
        if date > by_project[project]["latest"]:
            by_project[project]["latest"] = date

    lines = []
    for project, info in sorted(by_project.items(), key=lambda item: item[1]["latest"], reverse=True):
        lines.append(f"- {project} ({info['count']} entries, latest: {info['latest']})")
    return "\n".join(lines)


def _format_resume_prompt(entries, selected, decisions):
    if not entries:
        return (
            "No build log entries yet. Start by running "
            "`python -m buildlog add ...` to record what you ship."
        )

    recent_lines = []
    for entry in selected:
        date = entry["timestamp"][:10]
        recent_lines.append(
            f"- [{date}] {entry['project']} — {entry['title']}: {entry['summary']}"
        )

    project_names = sorted({entry["project"] for entry in entries})
    tag_text = ", ".join(_top_tags(entries)) or "none"

    lines = [
        "You are resuming work on this builder project.",
        "",
        "Recent context:",
        *recent_lines,
        "",
        f"Active projects: {', '.join(project_names)}",
        f"Recurring themes: {tag_text}",
    ]
    if decisions:
        lines.extend(
            [
                "",
                "Recent decisions are listed above; do not contradict them without explicit user approval.",
            ]
        )
    lines.extend(
        [
            "",
            "Pick up from the latest entry unless instructed otherwise. "
            "Ask what changed since the last session before making multi-file edits.",
        ]
    )
    return "\n".join(lines)


def format_handoff(entries, selected, decisions):
    top_tags = _top_tags(entries)
    themes = f"Top tags: {', '.join(top_tags)}" if top_tags else "none"

    if selected:
        shipping = "\n".join(_format_handoff_shipping_entry(entry) for entry in selected)
    else:
        shipping = "none"

    if decisions:
        decision_text = "\n".join(_format_handoff_decision_entry(entry) for entry in decisions)
    else:
        decision_text = "none"

    return "\n".join(
        [
            "# Buildlog Handoff",
            "",
            "## Recent shipping",
            shipping,
            "",
            "## Active projects",
            _format_active_projects(entries),
            "",
            "## Recurring themes",
            themes,
            "",
            "## Recent decisions",
            decision_text,
            "",
            "## Resume prompt",
            _format_resume_prompt(entries, selected, decisions),
        ]
    )


def _format_last_logged_session(anchor):
    date = anchor["timestamp"][:10]
    if entries.is_decision(anchor):
        lines = [
            f"{date} — {anchor['project']} — {anchor['choice']}",
            anchor["rationale"],
        ]
    else:
        lines = [
            f"{date} — {anchor['project']} — {anchor['title']}",
            anchor["summary"],
        ]
    if anchor["tags"]:
        lines.append(f"Tags: {', '.join(anchor['tags'])}")

    git_info = anchor.get("git")
    if isinstance(git_info, dict):
        short_commit = git_info["commit"][:7]
        state = "dirty" if git_info["dirty"] else "clean"
        lines.append(f"Recorded at commit: {short_commit} ({git_info['branch']}, {state})")

    return "\n".join(lines)


def _format_resume_prompt_with_git(records, selected, anchor, git_delta, decisions):
    if not records:
        return (
            "No build log entries yet. Start by running "
            "`python -m buildlog add ...` to record what you ship."
        )

    recent_lines = []
    for entry in selected:
        date = entry["timestamp"][:10]
        recent_lines.append(
            f"- [{date}] {entry['project']} — {entry['title']}: {entry['summary']}"
        )

    project_names = sorted({entry["project"] for entry in records})
    tag_text = ", ".join(_top_tags(records)) or "none"
    anchor_date = anchor["timestamp"][:10]
    if entries.is_decision(anchor):
        anchor_line = (
            f"- [{anchor_date}] {anchor['project']} — {anchor['choice']}: {anchor['rationale']}"
        )
    else:
        anchor_line = (
            f"- [{anchor_date}] {anchor['project']} — {anchor['title']}: {anchor['summary']}"
        )

    git_lines = []
    if git_delta["available"]:
        git_lines.append(
            f"- {git_delta['commit_count']} commit(s) on {git_delta['branch']} since last log"
        )
        git_lines.append(f"- Working tree: {git_delta['working_tree']}")
    else:
        git_lines.append("- Git context unavailable")

    lines = [
        f"You are resuming work on {anchor['project']}.",
        "",
        "Last recorded intent:",
        anchor_line,
        "",
        "Recent context:",
        *recent_lines,
        "",
        "Code changes since then:",
        *git_lines,
        "",
        f"Active projects: {', '.join(project_names)}",
        f"Recurring themes: {tag_text}",
    ]
    if decisions:
        lines.extend(
            [
                "",
                "Recent decisions are listed above; do not contradict them without explicit user approval.",
            ]
        )
    lines.extend(
        [
            "",
            "Pick up from the latest entry unless instructed otherwise. "
            "Ask what changed since the last session before making multi-file edits.",
        ]
    )
    return "\n".join(lines)


def format_resume(anchor, entries, selected, git_delta, decisions):
    if not entries:
        return "\n".join(
            [
                "# Buildlog Resume",
                "",
                "## Last logged session",
                "none",
                "",
                "## Since that entry",
                "none",
                "",
                "## Recent shipping",
                "none",
                "",
                "## Active projects",
                "none",
                "",
                "## Recurring themes",
                "none",
                "",
                "## Recent decisions",
                "none",
                "",
                "## Resume prompt",
                _format_resume_prompt_with_git(entries, selected, anchor, git_delta, decisions),
            ]
        )

    top_tags = _top_tags(entries)
    themes = f"Top tags: {', '.join(top_tags)}" if top_tags else "none"
    shipping = "\n".join(_format_handoff_shipping_entry(entry) for entry in selected)
    if decisions:
        decision_text = "\n".join(_format_handoff_decision_entry(entry) for entry in decisions)
    else:
        decision_text = "none"

    return "\n".join(
        [
            "# Buildlog Resume",
            "",
            "## Last logged session",
            _format_last_logged_session(anchor),
            "",
            "## Since that entry",
            git_delta["text"],
            "",
            "## Recent shipping",
            shipping or "none",
            "",
            "## Active projects",
            _format_active_projects(entries),
            "",
            "## Recurring themes",
            themes,
            "",
            "## Recent decisions",
            decision_text,
            "",
            "## Resume prompt",
            _format_resume_prompt_with_git(entries, selected, anchor, git_delta, decisions),
        ]
    )


def cmd_stats():
    loaded = storage.load_entries()
    print(format_stats(loaded))
    return 0


def cmd_handoff(args):
    if args.limit is not None and args.limit < 0:
        print("error: limit must be zero or greater", file=sys.stderr)
        return 1

    loaded = storage.load_entries()
    if args.project:
        loaded = [entry for entry in loaded if entry["project"] == args.project]

    loaded.sort(key=lambda entry: entry["timestamp"], reverse=True)

    shipping_selected = _recent_records(
        loaded,
        args.limit,
        lambda record: not entries.is_decision(record),
    )
    decisions_selected = _recent_records(
        loaded,
        args.limit,
        entries.is_decision,
    )

    handoff_text = format_handoff(loaded, shipping_selected, decisions_selected)
    return emit_output(handoff_text, args.output)


def cmd_resume(args):
    if args.limit is not None and args.limit < 0:
        print("error: limit must be zero or greater", file=sys.stderr)
        return 1

    loaded = storage.load_entries()
    if args.project:
        loaded = [entry for entry in loaded if entry["project"] == args.project]

    loaded.sort(key=lambda entry: entry["timestamp"], reverse=True)

    shipping_selected = _recent_records(
        loaded,
        args.limit,
        lambda record: not entries.is_decision(record),
    )
    decisions_selected = _recent_records(
        loaded,
        args.limit,
        entries.is_decision,
    )

    anchor = loaded[0] if loaded else None
    git_delta = (
        git_context.format_git_delta_since(anchor)
        if anchor
        else {"available": False, "text": "none", "branch": None, "commit_count": 0, "working_tree": None}
    )
    resume_text = format_resume(anchor, loaded, shipping_selected, git_delta, decisions_selected)
    return emit_output(resume_text, args.output)


def find_entry_by_id(entries, id_query):
    id_query = id_query.strip().lower()
    exact_matches = [entry for entry in entries if entry["id"] == id_query]
    if len(exact_matches) == 1:
        return exact_matches[0]

    prefix_matches = [entry for entry in entries if entry["id"].startswith(id_query)]
    if not prefix_matches:
        return None
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    return "ambiguous"


def format_entry_show(entry):
    lines = [
        f"ID: {entry['id']}",
        f"Timestamp: {entry['timestamp']}",
        f"Project: {entry['project']}",
    ]
    if entries.is_decision(entry):
        lines.extend(
            [
                "Kind: decision",
                f"Choice: {entry['choice']}",
                f"Rationale: {entry['rationale']}",
            ]
        )
    else:
        lines.extend(
            [
                f"Title: {entry['title']}",
                f"Summary: {entry['summary']}",
            ]
        )
    if entry["tags"]:
        lines.append(f"Tags: {', '.join(entry['tags'])}")
    return "\n".join(lines)


def cmd_show(args):
    id_query = args.id.strip()
    if not id_query:
        print("error: id must not be empty", file=sys.stderr)
        return 1

    loaded = storage.load_entries()
    match = find_entry_by_id(loaded, id_query)
    if match == "ambiguous":
        print(f"error: ambiguous id prefix {id_query!r}", file=sys.stderr)
        return 1
    if match is None:
        print(f"error: no entry found for id {id_query!r}", file=sys.stderr)
        return 1

    print(format_entry_show(match))
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        return cmd_add(args)
    if args.command == "decide":
        return cmd_decide(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "export":
        return cmd_export(args)
    if args.command == "stats":
        return cmd_stats()
    if args.command == "handoff":
        return cmd_handoff(args)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "resume":
        return cmd_resume(args)

    parser.print_help()
    return 1


def run():
    raise SystemExit(main())


if __name__ == "__main__":
    run()
