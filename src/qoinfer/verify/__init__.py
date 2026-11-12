"""Verifier helpers.

Acceptance criteria are ``TODO(owner)`` in ``spec/SCIENCE.md`` and
``spec/TOLERANCES.md``. This package does not define a numeric threshold.
"""

from qoinfer.verify.tolerances import ToleranceMissingError, require_heading

__all__ = ["ToleranceMissingError", "require_heading"]
