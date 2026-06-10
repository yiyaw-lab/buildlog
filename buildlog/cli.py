import argparse
import json
import sys

from buildlog import entries, storage

DEFAULT_LIST_LIMIT = 20


def build_parser():
    parser = argparse.ArgumentParser(prog="buildlog", description="Record daily build logs locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a build log entry.")
    add_parser.add_argument("--project", required=True)
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--tag", action="append", default=[], dest="tags")

    list_parser = subparsers.add_parser("list", help="List recent build log entries.")
    list_parser.add_argument("--project")
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

    return parser


def cmd_add(args):
    try:
        entry = entries.make_entry(args.project, args.title, args.summary, args.tags)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    storage.append_entry(entry)
    print(f"Added {entry['id']}")
    return 0


def cmd_list(args):
    if args.limit is not None and args.limit < 0:
        print("error: limit must be zero or greater", file=sys.stderr)
        return 1

    loaded = storage.load_entries()
    if args.project:
        loaded = [entry for entry in loaded if entry["project"] == args.project]

    loaded.sort(key=lambda entry: entry["timestamp"], reverse=True)

    if args.limit == 0:
        selected = loaded
    else:
        selected = loaded[: args.limit]

    for entry in selected:
        tags = entry["tags"]
        tag_text = ", ".join(tags)
        tag_suffix = f"  [{tag_text}]" if tag_text else ""
        print(
            f"{entry['timestamp']}  "
            f"{entry['project']}  "
            f"{entry['title']}  "
            f"{entry['summary']}{tag_suffix}"
        )
    return 0


def format_entry_markdown(entry):
    date = entry["timestamp"][:10]
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


def export_entries(entries, fmt):
    if fmt == "jsonl":
        for entry in entries:
            print(json.dumps(entry, ensure_ascii=False))
        return

    if not entries:
        return

    print("# Build Log")
    print()
    for index, entry in enumerate(entries):
        print(format_entry_markdown(entry))
        if index < len(entries) - 1:
            print()


def cmd_export(args):
    loaded = storage.load_entries()
    loaded.sort(key=lambda entry: entry["timestamp"])
    export_entries(loaded, args.format)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        return cmd_add(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "export":
        return cmd_export(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
