# buildlog

A local continuity system for builders who ship with agents.

`buildlog` helps you never lose the thread of what you are building. It records daily build logs locally, then turns them into session-ready context you can paste into Cursor, Claude, or any other agent.

Git shows diffs, not intent. Chat history is messy and ephemeral. Notes apps store thoughts, not shipping history. `buildlog` sits in the middle: a local source of truth for what you built, why it mattered, and how to resume.

## What it does

- **Capture** — record projects, titles, summaries, and tags as JSONL
- **Review** — list, filter, inspect, and summarize your build history
- **Resume** — generate agent-ready handoff bundles from recent work

The goal is not another journal. The goal is continuity between you, your repos, and your agents.

## Requirements

- Python 3.9+

## Install

Install locally in editable mode:

```bash
pip install -e .
buildlog stats
```

You can also run without installing:

```bash
python -m buildlog stats
```

## Usage

Run commands from the repository root (or anywhere, after install):

```bash
buildlog add \
  --project myapp \
  --title "Setup CLI" \
  --summary "Scaffolded buildlog commands" \
  --tag python --tag cli

buildlog list
buildlog list --project myapp --limit 5
buildlog list --tag cli
buildlog list --project myapp --tag v3
buildlog export
buildlog export --format jsonl
buildlog stats
buildlog handoff
buildlog resume
buildlog show --id 5562be1f
buildlog add ... --capture-git
```

### List behavior

- `list` shows the 20 most recent entries by default.
- `list --tag` filters to entries containing at least one matching tag; repeat `--tag` to match any of several tags.
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

### Handoff behavior

- `handoff` is the core continuity command: a deterministic Markdown bundle for resuming work in a new session.
- Includes recent shipping, active projects, recurring themes, and a paste-ready resume prompt.
- `--limit` defaults to `5`; use `--limit 0` for all entries in recent shipping.
- `--project` filters entries before building the handoff.
- With no stored entries, all sections print `none` except the resume prompt, which suggests running `add`.

Typical workflow:

```bash
buildlog add --project myapp --title "Ship feature X" --summary "What changed and why" --capture-git
buildlog resume | pbcopy    # paste into your next agent session with git context
buildlog handoff | pbcopy   # log-only handoff without git delta
```

### Resume behavior

- `resume` is the git-aware continuity command: last logged session plus repo changes since that entry.
- Includes handoff-style sections (recent shipping, active projects, recurring themes) and an enhanced resume prompt.
- `--limit` defaults to `5`; use `--limit 0` for all entries in recent shipping.
- `--project` anchors on the latest entry for that project and filters the bundle.
- Run from the project repository when you want git context. Outside a git repo, git sections print `none`.
- Use `add --capture-git` to store branch, commit, and dirty state on an entry for more accurate deltas.

### Show behavior

- `show --id` prints one entry in a human-readable detail view, including the internal id.
- Accepts a full id or a unique id prefix. Prefixes that match multiple entries exit with code `1`.
- Entry ids are printed when you run `add` (`Added <id>`).
- The `Tags:` line is omitted when an entry has no tags.

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

- `buildlog` is a continuity system first: capture intent locally, resume agents quickly.
- Agent behavior is defined in `AGENTS.md`.
- Sensitive and generated paths are excluded via `.cursorignore`.
