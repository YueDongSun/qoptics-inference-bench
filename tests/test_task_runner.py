"""Vacuity check: a verifier that passes with no solution is rejected."""

from __future__ import annotations

from pathlib import Path

import pytest

from qoinfer.taskfmt.runner import TaskRunError, validate_one

ROOT = Path(__file__).resolve().parents[1]


def test_vacuous_verifier_fails_validation(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "example_002_vacuous",
        solve="#!/bin/sh\nexit 0\n",
        test="def test_always() -> None:\n    assert True\n",
        timeout_sec=30,
    )
    with pytest.raises(TaskRunError, match="empty solution did not fail"):
        validate_one(task, ROOT)


def test_collection_error_is_not_an_empty_solution_failure(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "example_003_collect",
        solve="#!/bin/sh\nmkdir -p artifacts\nprintf '%s\\n' '{}' > artifacts/result.json\n",
        test=(
            "from pathlib import Path\n"
            "Path('artifacts/result.json').read_text(encoding='utf-8')\n"
            "\n"
            "def test_always() -> None:\n"
            "    assert True\n"
        ),
        timeout_sec=30,
    )
    with pytest.raises(TaskRunError, match="not a test failure"):
        validate_one(task, ROOT)


def test_solution_timeout_fails_validation(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "example_004_slow",
        solve="#!/bin/sh\nexec python -c 'import time; time.sleep(30)'\n",
        test="def test_always() -> None:\n    assert True\n",
        timeout_sec=1,
    )
    with pytest.raises(TaskRunError, match="timed out after 1s"):
        validate_one(task, ROOT)


def _write_task(task: Path, *, solve: str, test: str, timeout_sec: int) -> Path:
    (task / "environment").mkdir(parents=True)
    (task / "solution").mkdir()
    (task / "tests").mkdir()
    (task / "task.toml").write_text(
        "\n".join(
            [
                f'id = "{task.name}"',
                'family = "example"',
                'difficulty = "trivial"',
                'spec_ref = "spec/TASKS.md#task-families"',
                f"timeout_sec = {timeout_sec}",
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
    (task / "solution" / "solve.sh").write_text(solve, encoding="utf-8")
    (task / "tests" / "test_outputs.py").write_text(test, encoding="utf-8")
    return task
