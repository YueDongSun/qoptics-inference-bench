"""Format-demo verifier for example_000_smoke.

This is not a scientific test. Numeric thresholds belong in
``spec/TOLERANCES.md`` and are still ``TODO(owner)``. The instruction assigns
the integer 1, so the check is exact equality, not a physical tolerance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from qoinfer.verify.tolerances import ToleranceMissingError, require_heading

_FORMAT_DEMO_VALUE = 1
_TOLERANCE_HEADING = "Tolerances"


def _tolerances_path() -> Path:
    root = os.environ.get("QOINFER_REPO_ROOT")
    if root is None or not root:
        raise ToleranceMissingError(
            "QOINFER_REPO_ROOT is not set. The harness must point at the repo "
            "so the verifier can read spec/TOLERANCES.md by name."
        )
    return Path(root) / "spec" / "TOLERANCES.md"


def test_format_demo_exact_value() -> None:
    """The solution writes the integer the instruction assigns."""

    require_heading(_tolerances_path(), _TOLERANCE_HEADING)
    payload = json.loads(Path("artifacts/result.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("value") != _FORMAT_DEMO_VALUE:
        raise AssertionError(
            f"artifacts/result.json must be an object with value {_FORMAT_DEMO_VALUE}"
        )
