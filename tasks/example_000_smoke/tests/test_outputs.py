"""Format-demo verifier for example_000_smoke.

This is not a scientific test. The instruction assigns the integer 1.
The check is exact equality. The tolerance format is TBD by owner.
"""

from __future__ import annotations

import json
from pathlib import Path

_FORMAT_DEMO_VALUE = 1


def test_format_demo_exact_value() -> None:
    """The solution writes the integer the instruction assigns."""

    payload = json.loads(Path("artifacts/result.json").read_text(encoding="utf-8"))
    if payload != {"value": _FORMAT_DEMO_VALUE}:
        raise AssertionError(f"artifacts/result.json must equal {{'value': {_FORMAT_DEMO_VALUE}}}")
