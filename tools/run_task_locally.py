#!/usr/bin/env python3
"""Run task verifiers on this machine.

See docs/adr/0002-task-format.md. This does not build the task image.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qoinfer.taskfmt.runner import TaskRunError, run_empty_only, validate_all, validate_one


def main(argv: list[str] | None = None) -> None:
    """Validate every task, one task, or an empty solution."""

    parser = argparse.ArgumentParser(description="Run task verifiers on this machine.")
    parser.add_argument("--all", action="store_true", help="Validate every task directory.")
    parser.add_argument("--task", help="Task id under tasks/.")
    parser.add_argument(
        "--empty-only",
        action="store_true",
        help="Run the verifier without the solution and return pytest's exit code.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[1]
    if args.all and args.task:
        raise SystemExit("pass only one of --all and --task")
    try:
        if args.all:
            if args.empty_only:
                raise SystemExit("--empty-only requires --task")
            validate_all(root)
            print("validate: ok")
            return
        if not args.task:
            raise SystemExit("pass --all or --task <task_id>")
        task_dir = root / "tasks" / args.task
        if args.empty_only:
            raise SystemExit(run_empty_only(task_dir, root))
        validate_one(task_dir, root)
    except TaskRunError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print("validate: ok")


if __name__ == "__main__":
    main()
