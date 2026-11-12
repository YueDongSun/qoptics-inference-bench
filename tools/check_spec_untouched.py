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
    """Return staged paths, including both sides of a rename and deletions."""

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z", "-M"],
        check=True,
        capture_output=True,
    )
    return paths_from_name_status_z(result.stdout)


def paths_from_name_status_z(payload: bytes) -> list[str]:
    """Parse ``git diff --name-status -z`` output into every path it names."""

    records = payload.split(b"\0")
    if records and records[-1] == b"":
        records.pop()
    paths: list[str] = []
    index = 0
    while index < len(records):
        status = records[index].decode("utf-8")
        index += 1
        path_count = 2 if status[:1] in {"R", "C"} else 1
        end = index + path_count
        if end > len(records):
            raise SystemExit(f"truncated git name-status record starting with {status!r}")
        for record in records[index:end]:
            paths.append(record.decode("utf-8"))
        index = end
    return paths


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
