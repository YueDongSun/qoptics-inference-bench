"""Deterministic defaults for the unit suite."""

from __future__ import annotations

import random

import pytest


@pytest.fixture(autouse=True)
def seed_random() -> None:
    """Pin the stdlib RNG. Tests that draw numbers must still pass an explicit seed."""

    random.seed(0)
