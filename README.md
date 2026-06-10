# Cursor sandbox

A tiny local Python CLI for recording daily build logs.

## Requirements

- Python 3.9+

## Usage

Run commands from the repository root:

```bash
python -m buildlog add \
  --project myapp \
  --title "Setup CLI" \
  --summary "Scaffolded buildlog commands" \
  --tag python --tag cli

python -m buildlog list
python -m buildlog list --project myapp --limit 5
python -m buildlog export
python -m buildlog export --format jsonl
python -m buildlog stats
```

### List behavior

- `list` shows the 20 most recent entries by default.
- `list --limit 0` shows all entries.
- `list --limit -1` exits with code `1`.
- With no stored entries, `list` prints empty stdout.

### Export behavior

- `export` prints human-readable Markdown by default.
- `export --format markdown` prints the same Markdown output.
- `export --format jsonl` prints full raw JSONL entries, oldest first.
- With no stored entries, `export` prints empty stdout.

Markdown format:

```markdown
# Build Log

## YYYY-MM-DD — project

### title

summary

Tags: tag1, tag2
```

Markdown export omits internal entry ids. The `Tags:` line is omitted when an entry has no tags.

### Stats behavior

- `stats` prints total entries, unique project count, top tags (up to 5), and the latest entry.
- Top tags are ordered by frequency descending, then alphabetically for ties.
- With no stored entries, `stats` prints zero counts and `none` for tags and latest entry.

Entries are stored as JSONL at `.buildlog/entries.jsonl` by default.

Override the storage path for tests or custom setups:

```bash
BUILDLOG_PATH=/tmp/buildlog.jsonl python -m buildlog list
```

## Tests

```bash
python -m unittest
```

## Project notes

- Agent behavior is defined in `AGENTS.md`.
- Sensitive and generated paths are excluded via `.cursorignore`.
