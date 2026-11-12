"""Run a task solution and prove the verifier is not vacuous.

See ``docs/adr/0002-task-format.md`` and ``spec/TASKS.md``.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from qoinfer.taskfmt.validate import TaskFormatError, validate_task_dir

_PYTEST_OK = 0
_PYTEST_FAILED = 1
_PYTEST_NO_TESTS = 5


class TaskRunError(Exception):
    """A task failed structure, the reference solution, or the vacuity check."""


def repo_root_from(start: Path) -> Path:
    """Walk parents until ``pyproject.toml`` and ``tasks/`` are both present."""

    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "tasks").is_dir():
            return candidate
    raise TaskRunError(f"repo root not found from {start}")


def iter_task_dirs(root: Path) -> list[Path]:
    """Return task directories directly under ``tasks/``, sorted by id."""

    tasks = root / "tasks"
    if not tasks.is_dir():
        raise TaskRunError(f"missing {tasks}")
    return sorted(
        path for path in tasks.iterdir() if path.is_dir() and not path.name.startswith(".")
    )


def validate_all(root: Path) -> None:
    """Validate every task directory. Prints one line per check."""

    task_dirs = iter_task_dirs(root)
    if not task_dirs:
        raise TaskRunError(f"no tasks under {root / 'tasks'}")
    for task_dir in task_dirs:
        validate_one(task_dir)


def validate_one(task_dir: Path) -> None:
    """Check structure, a passing solution, and a failing do-nothing run."""

    try:
        manifest = validate_task_dir(task_dir)
    except TaskFormatError as exc:
        raise TaskRunError(str(exc)) from exc
    print(f"{manifest.task_id}: structure ok")
    solution = _run_pytest(
        task_dir,
        run_solution=True,
        timeout_sec=manifest.timeout_sec,
    )
    if solution.returncode != _PYTEST_OK:
        raise TaskRunError(
            f"{manifest.task_id}: solution failed\n{solution.stdout}\n{solution.stderr}"
        )
    print(f"{manifest.task_id}: solution passed")
    empty = _run_pytest(
        task_dir,
        run_solution=False,
        timeout_sec=manifest.timeout_sec,
    )
    if empty.returncode != _PYTEST_FAILED:
        detail = f"{empty.stdout}\n{empty.stderr}"
        if empty.returncode in {_PYTEST_OK, _PYTEST_NO_TESTS}:
            raise TaskRunError(
                f"{manifest.task_id}: empty solution did not fail the verifier\n{detail}"
            )
        raise TaskRunError(
            f"{manifest.task_id}: empty solution exited {empty.returncode}, "
            "which is not a test failure. The verifier must fail a collected "
            f"test when the solution does not run.\n{detail}"
        )
    print(f"{manifest.task_id}: empty solution failed as required")


def run_empty_only(task_dir: Path) -> int:
    """Run the verifier with no solution and return the pytest exit code."""

    manifest = validate_task_dir(task_dir)
    print(f"{task_dir.name}: running verifier with no solution", file=sys.stderr)
    completed = _run_pytest(
        task_dir,
        run_solution=False,
        timeout_sec=manifest.timeout_sec,
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode


def _run_pytest(
    task_dir: Path,
    *,
    run_solution: bool,
    timeout_sec: int,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="qoinfer-task-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(task_dir, work)
        env = os.environ.copy()
        if run_solution:
            solved = _run_bounded(
                ["bash", "solution/solve.sh"],
                cwd=work,
                env=env,
                timeout_sec=timeout_sec,
                label=f"{task_dir.name} solution",
            )
            if solved.returncode != _PYTEST_OK:
                return solved
        return _run_bounded(
            [sys.executable, "-m", "pytest", "tests/test_outputs.py", "-q", "--strict-markers"],
            cwd=work,
            env=env,
            timeout_sec=timeout_sec,
            label=f"{task_dir.name} verifier",
        )


def _run_bounded(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout_sec: int,
    label: str,
) -> subprocess.CompletedProcess[str]:
    """Run ``args`` and kill the process group when ``timeout_sec`` elapses.

    ``timeout_sec`` is the engineering limit from ``task.toml``, in seconds.
    See ``docs/adr/0002-task-format.md``.
    """

    proc = subprocess.Popen(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise TaskRunError(f"{label} timed out after {timeout_sec}s") from exc
    code = proc.returncode
    if code is None:
        raise TaskRunError(f"{label} exited without a status")
    return subprocess.CompletedProcess(args, code, stdout, stderr)
