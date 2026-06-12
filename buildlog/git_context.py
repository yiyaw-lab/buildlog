import subprocess
import sys


def run_git(args, cwd=None):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None, "git not found"

    if result.returncode != 0:
        message = result.stderr.strip() or f"git {' '.join(args)} failed"
        return None, message

    return result.stdout.strip(), None


def is_inside_git_repo(cwd=None):
    stdout, _ = run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return stdout == "true"


def capture_git_context(cwd=None):
    if not is_inside_git_repo(cwd):
        return None, "not inside a git repository"

    branch, error = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if error:
        return None, error

    commit, error = run_git(["rev-parse", "HEAD"], cwd=cwd)
    if error:
        return None, error

    status, error = run_git(["status", "--porcelain"], cwd=cwd)
    if error:
        return None, error

    return {
        "branch": branch,
        "commit": commit,
        "dirty": bool(status.strip()),
    }, None


def _commits_since_anchor(anchor, cwd=None):
    git_info = anchor.get("git")
    if isinstance(git_info, dict) and git_info.get("commit"):
        commit = git_info["commit"]
        _, verify_error = run_git(["cat-file", "-e", f"{commit}^{{commit}}"], cwd=cwd)
        if not verify_error:
            log_output, log_error = run_git(["log", f"{commit}..HEAD", "--oneline"], cwd=cwd)
            if not log_error:
                if log_output:
                    return log_output.splitlines()
                return []

    log_output, log_error = run_git(
        ["log", f"--since={anchor['timestamp']}", "--oneline"],
        cwd=cwd,
    )
    if log_error or not log_output:
        return []
    return log_output.splitlines()


def format_git_delta_since(anchor, cwd=None):
    if not is_inside_git_repo(cwd):
        return {
            "available": False,
            "text": "none",
            "branch": None,
            "commit_count": 0,
            "working_tree": None,
        }

    branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    commit_lines = _commits_since_anchor(anchor, cwd=cwd)
    status, _ = run_git(["status", "--porcelain"], cwd=cwd)
    dirty = bool(status and status.strip())
    working_tree = "dirty" if dirty else "clean"

    lines = []
    if branch:
        lines.append(f"Branch: {branch}")
    lines.append(f"Commits: {len(commit_lines)}")
    if commit_lines:
        lines.extend(f"- {line}" for line in commit_lines)
    else:
        lines.append("- No commits since last logged entry.")
    lines.append("")
    lines.append("Working tree:")
    if dirty:
        lines.extend(f"- {line}" for line in status.splitlines())
    else:
        lines.append("- clean")

    return {
        "available": True,
        "text": "\n".join(lines),
        "branch": branch,
        "commit_count": len(commit_lines),
        "working_tree": working_tree,
    }


def warn(message):
    print(f"warning: {message}", file=sys.stderr)
