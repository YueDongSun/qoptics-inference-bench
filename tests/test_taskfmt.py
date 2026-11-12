"""Task-format validator tests. No scientific values."""

from __future__ import annotations

from pathlib import Path

import pytest

from qoinfer.taskfmt.validate import TaskFormatError, parse_task_id, validate_task_dir
from qoinfer.verify.tolerances import ToleranceMissingError, require_heading

ROOT = Path(__file__).resolve().parents[1]


def test_parse_task_id_allows_underscores_in_family() -> None:
    assert parse_task_id("example_000_smoke") == ("example", "000", "smoke")
    assert parse_task_id("cf_t2_001_laf3_er_levels") == ("cf_t2", "001", "laf3_er_levels")
    with pytest.raises(TaskFormatError):
        parse_task_id("Example_000_smoke")


def test_smoke_task_structure() -> None:
    manifest = validate_task_dir(ROOT / "tasks" / "example_000_smoke")
    assert manifest.task_id == "example_000_smoke"
    assert manifest.format_demo is True
    assert manifest.status == "draft"
    assert manifest.spec_ref == "spec/TASKS.md#task-families"


def test_latest_base_image_is_rejected(tmp_path: Path) -> None:
    task = tmp_path / "example_001_bad"
    _write_min_task(task, dockerfile="FROM python:latest\n")
    with pytest.raises(TaskFormatError, match="latest"):
        validate_task_dir(task)


def test_tolerances_heading_is_required() -> None:
    path = ROOT / "spec" / "TOLERANCES.md"
    require_heading(path, "Tolerances")
    with pytest.raises(ToleranceMissingError):
        require_heading(path, "not-a-heading")


def _write_min_task(task: Path, dockerfile: str) -> None:
    (task / "environment").mkdir(parents=True)
    (task / "solution").mkdir()
    (task / "tests").mkdir()
    (task / "task.toml").write_text(
        "\n".join(
            [
                'id = "example_001_bad"',
                'family = "example"',
                'difficulty = "trivial"',
                'spec_ref = "spec/TASKS.md#task-families"',
                "timeout_sec = 60",
                'author = "scaffold"',
                'status = "draft"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (task / "instruction.md").write_text("Do the format demo step.\n", encoding="utf-8")
    (task / "environment" / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    (task / "solution" / "solve.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (task / "tests" / "test_outputs.py").write_text(
        "def test_ok() -> None:\n    assert True\n", encoding="utf-8"
    )
