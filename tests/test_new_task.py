"""Scaffolder tests. The new directory is not science and is not registered."""

from __future__ import annotations

from pathlib import Path

import pytest

from new_task import scaffold_task
from qoinfer.taskfmt.validate import TaskFormatError, validate_task_dir


def test_scaffold_writes_a_valid_draft(tmp_path: Path) -> None:
    dest = scaffold_task("readout_003_counts", tmp_path)
    manifest = validate_task_dir(dest)
    assert manifest.task_id == "readout_003_counts"
    assert manifest.family == "readout"
    assert manifest.format_demo is False
    assert (dest / "solution" / "solve.sh").stat().st_mode & 0o111


def test_scaffold_rejects_a_bad_id_and_a_repeat(tmp_path: Path) -> None:
    with pytest.raises(TaskFormatError):
        scaffold_task("Not_A_Task", tmp_path)
    scaffold_task("readout_003_counts", tmp_path)
    with pytest.raises(FileExistsError):
        scaffold_task("readout_003_counts", tmp_path)
