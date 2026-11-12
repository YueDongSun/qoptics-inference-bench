#!/usr/bin/env python3
"""Reject staged edits under spec/ or data/gold/ unless OWNER_SPEC_EDIT=1.

Agents must never set OWNER_SPEC_EDIT. See AGENTS.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_gate import SCIENCE_DECISION_MESSAGE, is_owner_only_path


def staged_paths() -> list[str]:
    """Return paths staged for the next commit."""

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> None:
    """Exit 1 when the index contains an owner-only path."""

    if os.environ.get("OWNER_SPEC_EDIT") == "1":
        return
    bad = [path for path in staged_paths() if is_owner_only_path(path)]
    if not bad:
        return
    print(SCIENCE_DECISION_MESSAGE, file=sys.stderr)
    for path in bad:
        print(path, file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
