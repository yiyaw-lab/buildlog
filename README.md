# buildlog

A local continuity system for builders who ship with agents.

**Repository:** [github.com/yiyaw-lab/buildlog](https://github.com/yiyaw-lab/buildlog)

`buildlog` helps you never lose the thread of what you are building. It records what you ship and why you chose it, then turns that history into session-ready context for Cursor, Claude, or any other agent.

Git shows diffs, not intent. Chat history is messy and ephemeral. Notes apps store thoughts, not shipping history. `buildlog` sits in the middle: a local source of truth for what you built, why it mattered, and how to resume.

## What it does

- **Capture** — `add` records what you shipped; `decide` records why you chose it
- **Review** — `list`, `show`, `stats`, and `export` summarize local JSONL history
- **Resume** — `handoff` and `resume` generate agent-ready continuity bundles

The goal is not another journal. The goal is continuity between you, your repos, and your agents.

## Continuity loop

```text
session start  →  read resume context  →  work with agent  →  log what shipped  →  next session
```

In this repo, that loop is mostly automatic:

1. **Session start** — a Cursor hook writes `buildlog resume` to `.buildlog/latest-resume.md`; the agent reads it via `.cursor/rules/buildlog-continuity.mdc`
2. **During work** — use `add` for shipping notes and `decide` for ADR-lite reasoning
3. **Session end** — a Cursor `stop` hook nudges you to run `buildlog add ... --capture-git`

Manual fallback anytime:

```bash
buildlog resume -o .buildlog/latest-resume.md
buildlog resume | pbcopy
```

## Requirements

- Python 3.9+
- Stdlib only (no external dependencies)

## Install

From a clone of the public repository:

```bash
git clone https://github.com/yiyaw-lab/buildlog.git
cd buildlog
pip install -e .
buildlog stats
```

In an existing checkout:

```bash
pip install -e .
buildlog stats
```

Without installing:

```bash
python -m buildlog stats
```

## Commands

| Command | Purpose |
|---------|---------|
| `add` | Record what you shipped |
| `decide` | Record a builder decision (choice + rationale) |
| `list` | Show recent entries and decisions |
| `show` | Inspect one record by id |
| `stats` | Summary counts and top tags |
| `export` | Export full log as Markdown or JSONL |
| `handoff` | Agent bundle without git delta |
| `resume` | Agent bundle with git changes since last log |

Shared flags on several commands:

- `--project` — filter or scope to one project
- `--tag` — filter `list` by tag (repeatable)
- `--limit` — cap results (`list` default 20; `handoff`/`resume` default 5; `0` = all)
- `--capture-git` — attach branch, commit, and dirty state (`add`, `decide`)
- `-o <path>` — write output to a file (`export`, `handoff`, `resume`)

## Usage

```bash
# Record shipping work
buildlog add \
  --project myapp \
  --title "Setup CLI" \
  --summary "Scaffolded buildlog commands" \
  --tag python --tag cli \
  --capture-git

# Record a decision
buildlog decide \
  --project myapp \
  --choice "Use JSONL storage" \
  --rationale "Keeps one local file and reuses resume/handoff without a database." \
  --tag adr

# Review
buildlog list
buildlog list --project myapp --limit 5
buildlog list --tag cli
buildlog show --id 5562be1f
buildlog stats

# Export
buildlog export
buildlog export --format jsonl
buildlog export -o buildlog.md

# Resume work in a new agent session
buildlog handoff
buildlog handoff -o handoff.md
buildlog resume
buildlog resume -o .buildlog/latest-resume.md
```

## Storage

Entries are stored as JSONL at `.buildlog/entries.jsonl` by default.

Override for tests or custom setups:

```bash
BUILDLOG_PATH=/tmp/buildlog.jsonl python -m buildlog list
```

### Record shapes

**Shipping entry** (default — no `kind` field):

```json
{
  "id": "...",
  "timestamp": "2026-06-12T12:00:00+00:00",
  "project": "myapp",
  "title": "Setup CLI",
  "summary": "Scaffolded commands",
  "tags": ["cli"],
  "git": { "branch": "main", "commit": "...", "dirty": false }
}
```

**Decision** (`kind: "decision"`):

```json
{
  "kind": "decision",
  "id": "...",
  "timestamp": "2026-06-12T12:00:00+00:00",
  "project": "myapp",
  "choice": "Use JSONL storage",
  "rationale": "One file, no database",
  "tags": ["adr"]
}
```

Malformed JSONL lines are skipped with a stderr warning.

## Command reference

### `add`

- Required: `--project`, `--title`, `--summary`
- Optional: `--tag` (repeatable), `--capture-git`
- Prints `Added <id>` on success

### `decide`

- Required: `--project`, `--choice`, `--rationale`
- Optional: `--tag` (repeatable), `--capture-git`
- Stored with `kind: "decision"` in the same JSONL file
- `list` shows `[decision]` before the choice text
- `handoff` and `resume` include a `## Recent decisions` section
- When decisions are present, the resume prompt warns agents not to contradict them without approval

### `list`

- Default limit: 20 (newest first)
- `--limit 0` shows all; `--limit -1` exits with code `1`
- Filters: `--project`, `--tag` (any match when repeated)
- Empty storage prints empty stdout

### `show`

- `--id` accepts a full id or unique prefix
- Shipping entries show `Title` and `Summary`
- Decisions show `Kind: decision`, `Choice`, and `Rationale`
- Ambiguous prefixes exit with code `1`

### `stats`

- Prints total entries, project count, top tags (up to 5), and latest entry
- Top tags: frequency descending, then alphabetical for ties
- Decisions count toward totals; latest entry may be a decision (`choice` shown instead of `title`)

### `export`

- Default: Markdown to stdout
- `--format jsonl` — raw JSONL, oldest first
- `-o <path>` — write to file (creates parent directories)
- Empty storage: empty stdout, or empty file with `-o`

Markdown shipping entry:

```markdown
## YYYY-MM-DD — project

### title

summary

Tags: tag1, tag2
```

Markdown decision:

```markdown
## YYYY-MM-DD — project

### Decision: choice

rationale

Tags: tag1, tag2
```

Internal ids are omitted from Markdown export. The `Tags:` line is omitted when there are no tags.

### `handoff`

- Markdown bundle: recent shipping, active projects, recurring themes, recent decisions, resume prompt
- No git delta — use when you only need log context
- `--project`, `--limit`, `-o` supported
- Empty storage: sections print `none` except the resume prompt (suggests running `add`)

### `resume`

- Markdown bundle like `handoff`, plus:
  - **Last logged session** — anchor entry with optional git snapshot
  - **Since that entry** — commits and working tree changes since that log
- Run from a git repo for delta context; outside a repo, git sections print `none`
- `--project`, `--limit`, `-o` supported
- Use `add --capture-git` / `decide --capture-git` for more accurate deltas

Typical handoff:

```bash
buildlog add --project myapp --title "Ship feature X" --summary "What changed and why" --capture-git
buildlog resume | pbcopy          # git-aware — preferred
buildlog handoff | pbcopy         # log-only, no git delta
buildlog resume -o .buildlog/latest-resume.md
```

## Cursor hooks

This repo includes project hooks for automatic continuity.

### Session start (resume)

| File | Role |
|------|------|
| `.cursor/hooks.json` | Registers hooks |
| `.cursor/hooks/session-resume.sh` | Runs `buildlog resume` on `sessionStart` |
| `.cursor/rules/buildlog-continuity.mdc` | Tells the agent to read `.buildlog/latest-resume.md` |

Behavior:

- Writes resume output to `.buildlog/latest-resume.md`
- Also returns `additional_context` when Cursor supports it
- Skips background agents and Ask mode
- Fails open on errors

Setup:

```bash
pip install -e .
chmod +x .cursor/hooks/session-resume.sh
```

Verify:

```bash
echo '{"is_background_agent": false, "composer_mode": "agent"}' | .cursor/hooks/session-resume.sh | python3 -c "import json,sys; print('ok' if json.load(sys.stdin).get('additional_context') else 'missing')"
head -20 .buildlog/latest-resume.md
```

**Known limitation:** Some Cursor versions drop `sessionStart` `additional_context` due to a timing bug. The file + rule fallback is the supported path. Manual fallback: `buildlog resume | pbcopy` or `buildlog resume -o .buildlog/latest-resume.md`.

### Session end (capture)

| File | Role |
|------|------|
| `.cursor/hooks/session-capture.sh` | Prompts logging on `stop` |

Behavior:

- Fires when the agent loop ends with `status: completed`
- Returns a one-time `followup_message` to run `buildlog add ... --capture-git`
- `loop_limit: 1` per conversation
- Skips aborted/error sessions; fails open

Verify:

```bash
echo '{"status": "completed", "loop_count": 0}' | .cursor/hooks/session-capture.sh | python3 -c "import json,sys; print('ok' if json.load(sys.stdin).get('followup_message') else 'missing')"
```

## Tests

```bash
python -m unittest
```

## Project notes

- `buildlog` is a continuity system first: capture intent locally, resume agents quickly.
- Agent behavior is defined in `AGENTS.md`.
- Sensitive and generated paths are excluded via `.cursorignore`.
- `.buildlog/` is gitignored; hooks refresh `.buildlog/latest-resume.md` locally.
