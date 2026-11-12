"""Shared decisions for git hooks and agent hooks.

``spec/`` and ``data/gold/`` are owner-only. See ``AGENTS.md``.
"""

from __future__ import annotations

import re
import shlex
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
_SHARED_BRANCH = "main"
_GIT_OPTIONS_WITH_VALUE = {"-C", "-c"}


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
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        return f"refusing unparseable shell command: {segment}"
    reasons = (
        "refusing git push --force. Force-push is denied." if _is_force_push(tokens) else None,
        "refusing git push to main. Open a pull request; do not push main."
        if _is_push_to_main(tokens)
        else None,
        "refusing git commit --no-verify. Hooks are part of the contract."
        if _is_no_verify_commit(tokens)
        else None,
        _reset_hard_denial(current_branch) if _is_reset_hard(tokens) else None,
        "refusing pip install. Add dependencies with uv add." if _is_pip_install(tokens) else None,
    )
    for reason in reasons:
        if reason is not None:
            return reason
    return None


def _git_args(tokens: list[str], subcommand: str) -> list[str] | None:
    """Return arguments after ``git <subcommand>``, skipping global git options."""

    idx = 0
    while idx < len(tokens) and _is_assignment(tokens[idx]):
        idx += 1
    if idx < len(tokens) and tokens[idx] == "command":
        idx += 1
    if idx >= len(tokens) or Path(tokens[idx]).name not in {"git", "git.exe"}:
        return None
    idx += 1
    while idx < len(tokens) and tokens[idx] != subcommand:
        tok = tokens[idx]
        if tok in _GIT_OPTIONS_WITH_VALUE:
            idx += 2
            continue
        if tok.startswith("-"):
            idx += 1
            continue
        return None
    if idx >= len(tokens):
        return None
    return tokens[idx + 1 :]


def _is_assignment(token: str) -> bool:
    name, sep, _value = token.partition("=")
    return sep == "=" and name != "" and not name.startswith("-")


def _is_force_push(tokens: list[str]) -> bool:
    args = _git_args(tokens, "push")
    if args is None:
        return False
    return any(tok == "-f" or tok.startswith("--force") for tok in args)


def _is_push_to_main(tokens: list[str]) -> bool:
    args = _git_args(tokens, "push")
    if args is None:
        return False
    for tok in args:
        if tok.startswith("-"):
            continue
        destination = tok.split(":")[-1]
        if destination in {"main", "refs/heads/main"}:
            return True
    return False


def _is_no_verify_commit(tokens: list[str]) -> bool:
    args = _git_args(tokens, "commit")
    if args is None:
        return False
    for tok in args:
        if tok == "--no-verify" or tok.startswith("--no-verify="):
            return True
        if tok.startswith("-") and not tok.startswith("--") and "n" in tok[1:]:
            return True
    return False


def _is_reset_hard(tokens: list[str]) -> bool:
    args = _git_args(tokens, "reset")
    if args is None:
        return False
    return "--hard" in args


def _reset_hard_denial(current_branch: str | None) -> str | None:
    if current_branch is None:
        return (
            "refusing git reset --hard because the current branch could not be resolved. "
            f"Hard reset on the shared branch {_SHARED_BRANCH} is denied."
        )
    if current_branch == _SHARED_BRANCH:
        return f"refusing git reset --hard on shared branch {_SHARED_BRANCH}."
    return None


def _is_pip_install(tokens: list[str]) -> bool:
    for idx, tok in enumerate(tokens):
        if tok in {"pip", "pip3"} and idx + 1 < len(tokens) and tokens[idx + 1] == "install":
            return True
        if tok in {"python", "python3"} or tok.startswith("python3."):
            window = tokens[idx : idx + 4]
            if window[1:] == ["-m", "pip", "install"]:
                return True
    return False
