"""Heading checks against ``spec/TOLERANCES.md``.

Numeric thresholds are owner-owned and are not defined yet (``TODO(owner)``).
This module does not supply a number. See ``spec/TOLERANCES.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


class ToleranceMissingError(Exception):
    """A named heading is absent from the tolerances spec."""


def heading_names(spec_path: Path) -> list[str]:
    """Return ``##`` headings from a spec file, in order."""

    if not spec_path.is_file():
        raise ToleranceMissingError(f"missing {spec_path}")
    return _HEADING.findall(spec_path.read_text(encoding="utf-8"))


def require_heading(spec_path: Path, heading: str) -> None:
    """Fail if ``heading`` is not a ``##`` heading in ``spec_path``.

    The heading is a name, not a numeric tolerance. Units and thresholds are
    defined by the owner in ``spec/TOLERANCES.md``.
    """

    names = heading_names(spec_path)
    if heading not in names:
        raise ToleranceMissingError(
            f"{spec_path} has no heading {heading!r}. "
            "Open a needs-science-decision issue and do not invent a tolerance."
        )
