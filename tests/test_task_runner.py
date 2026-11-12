"""Vacuity check: a verifier that passes with no solution is rejected."""

from __future__ import annotations

from pathlib import Path

import pytest

from qoinfer.taskfmt.runner import TaskRunError, validate_one

ROOT = Path(__file__).resolve().parents[1]


def test_vacuous_verifier_fails_validation(tmp_path: Path) -> None:
    task = tmp_path / "example_002_vacuous"
    (task / "environment").mkdir(parents=True)
    (task / "solution").mkdir()
    (task / "tests").mkdir()
    (task / "task.toml").write_text(
        "\n".join(
            [
                'id = "example_002_vacuous"',
                'family = "example"',
                'difficulty = "trivial"',
                'spec_ref = "spec/TASKS.md#task-families"',
                "timeout_sec = 30",
                'author = "scaffold"',
                'status = "draft"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (task / "instruction.md").write_text("Format demo placeholder.\n", encoding="utf-8")
    (task / "environment" / "Dockerfile").write_text(
        "FROM python:3.12.3-slim-bookworm\n",
        encoding="utf-8",
    )
    (task / "solution" / "solve.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (task / "tests" / "test_outputs.py").write_text(
        "def test_always() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    with pytest.raises(TaskRunError, match="empty solution"):
        validate_one(task, ROOT)
