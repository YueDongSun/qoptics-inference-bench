#!/usr/bin/env python3
"""Scaffold a Terminal-Bench style task directory.

Usage: python tools/new_task.py <task_id>
See docs/adr/0002-task-format.md and spec/TASKS.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

from qoinfer.taskfmt.validate import TaskFormatError, parse_task_id

_DOCKERFILE = """\
FROM python:3.12.3-slim-bookworm

# Format demo base. Pin every added package. Run tests with network disabled.
WORKDIR /task
"""

_SOLVE = """\
#!/bin/sh
echo "reference solution not written" >&2
exit 1
"""

_TEST = '''\
"""Replace this verifier.

Read numeric thresholds from spec/TOLERANCES.md by name.
Do not hard-code a tolerance. If the name is missing, stop and open a
needs-science-decision issue.
"""

from __future__ import annotations


def test_verifier_not_written() -> None:
    raise AssertionError("write tests/test_outputs.py for this task")
'''


def scaffold_task(task_id: str, tasks_root: Path) -> Path:
    """Create ``tasks_root/task_id`` and return that path."""

    family, _number, _slug = parse_task_id(task_id)
    dest = tasks_root / task_id
    if dest.exists():
        raise FileExistsError(dest)
    (dest / "environment").mkdir(parents=True)
    (dest / "solution").mkdir()
    (dest / "tests").mkdir()
    (dest / "task.toml").write_text(
        "\n".join(
            [
                f'id = "{task_id}"',
                f'family = "{family}"',
                'difficulty = "unspecified"',
                'spec_ref = "spec/TASKS.md#task-families"',
                "timeout_sec = 60",
                'author = "scaffold"',
                'status = "draft"',
                "format_demo = false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dest / "instruction.md").write_text(
        "\n".join(
            [
                "# TODO",
                "",
                "Replace this file with the agent-facing instructions.",
                "",
                "Do not include hidden-test details or answers.",
                "Do not invent tolerances. Name them from spec/TOLERANCES.md.",
                "If the spec does not state a value, open a needs-science-decision",
                "issue and stop.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dest / "environment" / "Dockerfile").write_text(_DOCKERFILE, encoding="utf-8")
    solve = dest / "solution" / "solve.sh"
    solve.write_text(_SOLVE, encoding="utf-8")
    solve.chmod(0o755)
    (dest / "tests" / "test_outputs.py").write_text(_TEST, encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> None:
    """Scaffold one task id under ``tasks/``."""

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: python tools/new_task.py <task_id>")
    root = Path(__file__).resolve().parents[1]
    try:
        dest = scaffold_task(args[0], root / "tasks")
    except TaskFormatError as exc:
        raise SystemExit(str(exc)) from exc
    except FileExistsError as exc:
        raise SystemExit(f"already exists: {exc}") from exc
    print(dest)


if __name__ == "__main__":
    main()
