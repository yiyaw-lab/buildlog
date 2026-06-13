# buildlog

A local continuity system for builders who ship with agents.

`buildlog` helps you never lose the thread of what you are building. It records daily build logs locally, then turns them into session-ready context you can paste into Cursor, Claude, or any other agent.

Git shows diffs, not intent. Chat history is messy and ephemeral. Notes apps store thoughts, not shipping history. `buildlog` sits in the middle: a local source of truth for what you built, why it mattered, and how to resume.

## What it does

- **Capture** — record projects, titles, summaries, tags, and decisions as JSONL
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

buildlog decide \
  --project myapp \
  --choice "Use JSONL storage" \
  --rationale "Keeps one local file and reuses resume/handoff without a database." \
  --tag adr

buildlog list
buildlog list --project myapp --limit 5
buildlog list --tag cli
buildlog list --project myapp --tag v3
buildlog export
buildlog export --format jsonl
buildlog export -o buildlog.md
buildlog stats
buildlog handoff
buildlog handoff -o handoff.md
buildlog resume
buildlog resume -o .buildlog/latest-resume.md
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
- `export -o <path>` writes export output to a file instead of stdout.
- With no stored entries, `export` prints empty stdout (or writes an empty file with `-o`).

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
- `-o <path>` writes handoff output to a file instead of stdout.
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
- `-o <path>` writes resume output to a file instead of stdout.
- Run from the project repository when you want git context. Outside a git repo, git sections print `none`.
- Use `add --capture-git` to store branch, commit, and dirty state on an entry for more accurate deltas.

### Cursor hook (automatic resume)

This repository includes a project hook that refreshes `buildlog resume` at agent session start.

Files:

- `.cursor/hooks.json`
- `.cursor/hooks/session-resume.sh`
- `.cursor/rules/buildlog-continuity.mdc`

Behavior:

- Runs on `sessionStart` for agent sessions in this repo.
- Writes resume output to `.buildlog/latest-resume.md` (reliable fallback).
- Also returns `additional_context` for Cursor injection when supported.
- The `buildlog-continuity` rule tells the agent to read `.buildlog/latest-resume.md` first.
- Skips background agents and Ask mode.
- Fails open: if `buildlog resume` fails, the session still starts with a short fallback message.

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

Then open a new Agent conversation and check the **Hooks** output channel for errors.

Note: Some Cursor versions do not inject `sessionStart` `additional_context` reliably due to a known timing issue. The file + rule fallback is the supported path: the hook writes `.buildlog/latest-resume.md`, and the agent reads it per `.cursor/rules/buildlog-continuity.mdc`. Manual fallback: `buildlog resume | pbcopy`.

### Cursor hook (capture at session end)

A `stop` hook prompts you to log what shipped when an agent run completes.

Files:

- `.cursor/hooks/session-capture.sh`

Behavior:

- Runs when the agent loop ends with `status: completed`.
- Returns a one-time `followup_message` asking the agent to run `buildlog add ... --capture-git`.
- `loop_limit: 1` — at most one capture prompt per conversation.
- Skips aborted or error sessions.
- Fails open: hook errors produce no follow-up.

Verify:

```bash
echo '{"status": "completed", "loop_count": 0}' | .cursor/hooks/session-capture.sh | python3 -c "import json,sys; print('ok' if json.load(sys.stdin).get('followup_message') else 'missing')"
echo '{"status": "completed", "loop_count": 1}' | .cursor/hooks/session-capture.sh | python3 -c "import json,sys; print('skip' if json.load(sys.stdin) == {} else 'unexpected')"
```

### Show behavior

- `show --id` prints one record in a human-readable detail view, including the internal id.
- Shipping entries show `Title` and `Summary`. Decisions show `Kind: decision`, `Choice`, and `Rationale`.
- Accepts a full id or a unique id prefix. Prefixes that match multiple entries exit with code `1`.
- Entry ids are printed when you run `add` or `decide` (`Added <id>`).
- The `Tags:` line is omitted when an entry has no tags.

### Decide behavior

- `decide` records ADR-lite builder decisions in the same JSONL file with `kind: "decision"`.
- Required fields: `--project`, `--choice`, `--rationale`.
- Optional: `--tag` (repeatable), `--capture-git`.
- `list` marks decisions with `[decision]` before the choice text.
- `export` renders decisions as `### Decision: <choice>` in Markdown.
- `handoff` and `resume` include a `## Recent decisions` section (up to `--limit`, default 5).
- When decisions are present, the resume prompt reminds the agent not to contradict them without approval.
- Legacy shipping entries without `kind` continue to load unchanged.

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
