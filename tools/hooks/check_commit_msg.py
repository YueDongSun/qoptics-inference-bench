#!/usr/bin/env python3
"""commit-msg hook: Conventional Commits with a required scope."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hook_gate import commit_message_error

_ARGC = 2


def main() -> None:
    """Exit 1 when the commit message file violates the contract."""

    if len(sys.argv) != _ARGC:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} <message-file>")
    message = Path(sys.argv[1]).read_text(encoding="utf-8")
    error = commit_message_error(message)
    if error is None:
        return
    print(error, file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
