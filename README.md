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
```

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
