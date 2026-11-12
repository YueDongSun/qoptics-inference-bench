"""Task directory structure checks.

The directory layout is the engineering contract in
``docs/adr/0002-task-format.md``. Scientific contents of a task are defined
by the owner in ``spec/TASKS.md``.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

TASK_ID_RE = re.compile(r"^([a-z][a-z0-9_]*?)_([0-9]{3})_([a-z0-9_]+)$")

REQUIRED_FILES: tuple[str, ...] = (
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/test_outputs.py",
)

_REQUIRED_KEYS: tuple[str, ...] = (
    "id",
    "family",
    "difficulty",
    "spec_ref",
    "timeout_sec",
    "author",
    "status",
)

_STATUSES = frozenset({"draft", "ready"})

_FROM_RE = re.compile(r"(?im)^FROM\s+(\S+)")


class TaskFormatError(Exception):
    """The task directory does not match the task format."""


@dataclass(frozen=True)
class TaskManifest:
    """Fields required in ``task.toml``.

    ``timeout_sec`` is a wall-clock limit in seconds, not a physical timescale.
    See ``docs/adr/0002-task-format.md``.
    """

    task_id: str
    family: str
    difficulty: str
    spec_ref: str
    timeout_sec: int
    author: str
    status: str
    format_demo: bool


def parse_task_id(task_id: str) -> tuple[str, str, str]:
    """Return ``(family, number, slug)`` for ``<family>_<nnn>_<slug>``."""

    match = TASK_ID_RE.fullmatch(task_id)
    if match is None:
        raise TaskFormatError(f"task id {task_id!r} must match <family>_<nnn>_<slug> in snake_case")
    return match.group(1), match.group(2), match.group(3)


def load_manifest(task_dir: Path) -> TaskManifest:
    """Load ``task.toml``. Missing or mistyped fields raise ``TaskFormatError``."""

    path = task_dir / "task.toml"
    if not path.is_file():
        raise TaskFormatError(f"missing {path}")
    data = _toml_table(path)
    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        joined = ", ".join(missing)
        raise TaskFormatError(f"{path} missing keys: {joined}")
    task_id = _require_str(data, "id", path)
    family = _require_str(data, "family", path)
    parsed_family, _number, _slug = parse_task_id(task_id)
    if family != parsed_family:
        raise TaskFormatError(
            f"{path} family {family!r} does not match id family {parsed_family!r}"
        )
    if task_dir.name != task_id:
        raise TaskFormatError(f"{path} id {task_id!r} does not match directory {task_dir.name!r}")
    spec_ref = _require_str(data, "spec_ref", path)
    if not spec_ref.startswith("spec/") or "#" not in spec_ref:
        raise TaskFormatError(
            f"{path} spec_ref must be a spec/ path with a #fragment, got {spec_ref!r}"
        )
    status = _require_str(data, "status", path)
    if status not in _STATUSES:
        raise TaskFormatError(f"{path} status must be draft or ready, got {status!r}")
    timeout = data["timeout_sec"]
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise TaskFormatError(f"{path} timeout_sec must be a positive integer number of seconds")
    format_demo = False
    if "format_demo" in data:
        flag = data["format_demo"]
        if not isinstance(flag, bool):
            raise TaskFormatError(f"{path} format_demo must be a boolean")
        format_demo = flag
    return TaskManifest(
        task_id=task_id,
        family=family,
        difficulty=_require_str(data, "difficulty", path),
        spec_ref=spec_ref,
        timeout_sec=timeout,
        author=_require_str(data, "author", path),
        status=status,
        format_demo=format_demo,
    )


def validate_task_dir(task_dir: Path) -> TaskManifest:
    """Check required files, the manifest, and a pinned Dockerfile base image."""

    if not task_dir.is_dir():
        raise TaskFormatError(f"not a task directory: {task_dir}")
    for relative in REQUIRED_FILES:
        if not (task_dir / relative).is_file():
            raise TaskFormatError(f"missing {task_dir / relative}")
    manifest = load_manifest(task_dir)
    instruction = (task_dir / "instruction.md").read_text(encoding="utf-8").strip()
    if not instruction:
        raise TaskFormatError(f"{task_dir / 'instruction.md'} is empty")
    if manifest.format_demo and "format demo" not in instruction.lower():
        raise TaskFormatError(f"{task_dir / 'instruction.md'} must say it is a format demo")
    solution = (task_dir / "solution" / "solve.sh").read_text(encoding="utf-8").strip()
    if not solution:
        raise TaskFormatError(f"{task_dir / 'solution' / 'solve.sh'} is empty")
    _check_dockerfile(task_dir / "environment" / "Dockerfile")
    return manifest


def _check_dockerfile(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    images = _FROM_RE.findall(text)
    if not images:
        raise TaskFormatError(f"{path} has no FROM instruction")
    for image in images:
        if image.upper() == "SCRATCH":
            continue
        if ":" not in image and "@" not in image:
            raise TaskFormatError(f"{path} base image {image} is not pinned")
        tag = image.rsplit("@", 1)[0]
        if tag.endswith(":latest"):
            raise TaskFormatError(f"{path} uses the floating tag latest in {image}")


def _toml_table(path: Path) -> dict[str, object]:
    loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    table: dict[str, object] = {}
    for key, value in loaded.items():
        table[str(key)] = value
    return table


def _require_str(data: dict[str, object], key: str, path: Path) -> str:
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise TaskFormatError(f"{path} key {key} must be a non-empty string")
    return value
