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
    list_parser.add_argument("--limit", type=int, default=DEFAULT_LIST_LIMIT)

    subparsers.add_parser("export", help="Export all entries as JSONL to stdout.")

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
        loaded = [entry for entry in loaded if entry.get("project") == args.project]

    loaded.sort(key=lambda entry: entry.get("timestamp", ""), reverse=True)

    if args.limit == 0:
        selected = loaded
    else:
        selected = loaded[: args.limit]

    for entry in selected:
        tags = entry.get("tags") or []
        tag_text = ", ".join(tags)
        tag_suffix = f"  [{tag_text}]" if tag_text else ""
        print(
            f"{entry.get('timestamp', '')}  "
            f"{entry.get('project', '')}  "
            f"{entry.get('title', '')}  "
            f"{entry.get('summary', '')}{tag_suffix}"
        )
    return 0


def cmd_export():
    loaded = storage.load_entries()
    loaded.sort(key=lambda entry: entry.get("timestamp", ""))
    for entry in loaded:
        print(json.dumps(entry, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        return cmd_add(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "export":
        return cmd_export()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
