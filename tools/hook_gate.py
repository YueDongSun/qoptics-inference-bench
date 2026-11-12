"""Shared decisions for git hooks and agent hooks.

``spec/`` and ``data/gold/`` are owner-only. See ``AGENTS.md``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

OWNER_PREFIXES: tuple[str, ...] = ("spec/", "data/gold/")

SCIENCE_DECISION_MESSAGE = (
    "spec/ and data/gold/ are owner-only. Do not edit them. "
    "Open a GitHub issue labelled needs-science-decision, quote the exact "
    "spec line, list the concrete options, and stop work on that piece."
)

_COMMIT_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
_COMMIT_SCOPES = (
    "task",
    "verify",
    "reference",
    "taskfmt",
    "tooling",
    "docs",
    "ci",
    "deps",
    "spec",
)

_HEADER = re.compile(
    "^(" + "|".join(_COMMIT_TYPES) + r")\((" + "|".join(_COMMIT_SCOPES) + r")\)(?:!)?: \S.*$"
)
_ATTRIBUTION = re.compile(
    r"^(?:Co-authored-by|Generated-by|Made-with)\s*:",
    re.IGNORECASE | re.MULTILINE,
)
_MADE_WITH = re.compile(r"^made with\b", re.IGNORECASE | re.MULTILINE)
_QUOTED = re.compile(r"""('([^'\\]|\\.)*'|"([^"\\]|\\.)*")""")
_SHARED_BRANCH = "main"


def repo_root() -> Path:
    """Return the repository root (the parent of ``tools/``)."""

    return Path(__file__).resolve().parents[1]


def relative_repo_path(path: str, root: Path | None = None) -> str:
    """Return a repo-relative posix path, or an absolute path outside the repo."""

    base = (root if root is not None else repo_root()).resolve()
    candidate = Path(path.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return resolved.as_posix()


def is_owner_only_path(path: str, root: Path | None = None) -> bool:
    """True when ``path`` is ``spec/`` or ``data/gold/``."""

    relative = relative_repo_path(path, root)
    if relative in {"spec", "data/gold"}:
        return True
    return relative.startswith(OWNER_PREFIXES)


def commit_message_error(message: str) -> str | None:
    """Return an error string, or None when the message matches the contract."""

    text = message.replace("\r\n", "\n")
    lines = text.split("\n")
    header = lines[0]
    if _HEADER.fullmatch(header) is None:
        return (
            "commit message must be Conventional Commits with a scope from "
            "task, verify, reference, taskfmt, tooling, docs, ci, deps, spec. "
            "Example: feat(task): add example_000_smoke"
        )
    if _ATTRIBUTION.search(text) or _MADE_WITH.search(text):
        return (
            "ordinary commits must not contain attribution trailers "
            "(Co-authored-by, Generated-by, Made-with)"
        )
    if len(lines) > 1 and lines[1] != "":
        return "commit body must start after a blank line"
    return None


def shell_denial(command: str, current_branch: str | None) -> str | None:
    """Return a denial reason, or None when the shell command is allowed."""

    if re.search(r"OWNER_SPEC_EDIT\s*=", command):
        return (
            "refusing OWNER_SPEC_EDIT=. Agents must never set that variable. "
            + SCIENCE_DECISION_MESSAGE
        )
    for segment in _segments(command):
        reason = _segment_denial(segment, current_branch)
        if reason is not None:
            return reason
    return None


def pushes_main(payload: str) -> bool:
    """True when git pre-push stdin updates ``refs/heads/main``."""

    for line in payload.splitlines():
        parts = line.split()
        remote_ref_index = 2
        if len(parts) > remote_ref_index and parts[remote_ref_index] == "refs/heads/main":
            return True
    return False


def git_current_branch(cwd: Path) -> str | None:
    """Return the current branch name, or None when git cannot resolve it."""

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    name = result.stdout.strip()
    if not name or name == "HEAD":
        return None
    return name


def _segments(command: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n|&&|\|\||;", command) if part.strip()]


def _segment_denial(segment: str, current_branch: str | None) -> str | None:
    bare = _QUOTED.sub(" ", segment)
    if _is_force_push(bare):
        return "refusing git push --force. Force-push is denied."
    if _is_push_to_main(bare):
        return "refusing git push to main. Open a pull request; do not push main."
    if _is_no_verify_commit(bare):
        return "refusing git commit --no-verify. Hooks are part of the contract."
    if _is_reset_hard(bare):
        return _reset_hard_denial(current_branch)
    if _is_pip_install(bare):
        return "refusing pip install. Add dependencies with uv add."
    return None


def _is_force_push(segment: str) -> bool:
    if re.search(r"\bgit\s+push\b", segment) is None:
        return False
    if re.search(r"--force\b", segment):
        return True
    return re.search(r"(?:^|\s)-f(?:\s|$)", segment) is not None


def _is_push_to_main(segment: str) -> bool:
    if re.search(r"\bgit\s+push\b", segment) is None:
        return False
    destination = r"(?:^|\s)(?:[\w./+-]+:)?(?:refs/heads/)?main(?:\s|$)"
    return re.search(destination, segment) is not None


def _is_no_verify_commit(segment: str) -> bool:
    if re.search(r"\bgit\s+commit\b", segment) is None:
        return False
    if "--no-verify" in segment:
        return True
    return re.search(r"(?:^|\s)-n(?:\s|$)", segment) is not None


def _is_reset_hard(segment: str) -> bool:
    return re.search(r"\bgit\s+reset\b", segment) is not None and "--hard" in segment.split()


def _reset_hard_denial(current_branch: str | None) -> str | None:
    if current_branch is None:
        return (
            "refusing git reset --hard because the current branch could not be resolved. "
            f"Hard reset on the shared branch {_SHARED_BRANCH} is denied."
        )
    if current_branch == _SHARED_BRANCH:
        return f"refusing git reset --hard on shared branch {_SHARED_BRANCH}."
    return None


def _is_pip_install(segment: str) -> bool:
    if re.search(r"\bpip3?\s+install\b", segment):
        return True
    return re.search(r"\bpython(?:3(?:\.\d+)?)?\s+-m\s+pip\s+install\b", segment) is not None
