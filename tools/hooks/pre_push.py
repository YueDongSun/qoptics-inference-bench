#!/usr/bin/env python3
"""pre-push hook: refuse main, then run make check."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hook_gate import git_current_branch, pushes_main, repo_root

_MAIN_REFS = frozenset({"main", "refs/heads/main"})


def _env_destination_is_main() -> bool:
    """True when pre-commit recorded a push whose remote ref is ``main``.

    pre-commit consumes git's pre-push stdin and passes the destination in
    ``PRE_COMMIT_REMOTE_BRANCH``. The hook process then sees an empty stdin.
    """

    remote = os.environ.get("PRE_COMMIT_REMOTE_BRANCH", "").strip()
    return remote in _MAIN_REFS


def main() -> None:
    """Refuse a push of ``main``, then require ``make check`` to pass."""

    payload = sys.stdin.read()
    branch = git_current_branch(Path.cwd())
    if branch == "main" or pushes_main(payload) or _env_destination_is_main():
        print("refusing push to main. Open a pull request.", file=sys.stderr)
        raise SystemExit(1)
    result = subprocess.run(["make", "check"], cwd=repo_root(), check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
