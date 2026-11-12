"""Run every task solution and the required empty-solution failure."""

from __future__ import annotations

from pathlib import Path

from qoinfer.taskfmt.runner import repo_root_from, validate_all


def test_every_task_solution_and_empty_run() -> None:
    validate_all(repo_root_from(Path(__file__).resolve()))
