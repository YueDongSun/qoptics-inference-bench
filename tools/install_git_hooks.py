#!/usr/bin/env python3
"""Install pre-commit, commit-msg, and pre-push hooks.

``pre-commit install`` refuses to run when ``core.hooksPath`` is set. Cursor
sets that value and chains to ``.git/hooks``. This script installs into
``.git/hooks`` without changing git config.
"""

from __future__ import annotations

import os
import subprocess
import sys

INSTALL = (
    "uv",
    "run",
    "pre-commit",
    "install",
    "--install-hooks",
    "--hook-type",
    "pre-commit",
    "--hook-type",
    "commit-msg",
    "--hook-type",
    "pre-push",
)


def hooks_path() -> str | None:
    """Return ``core.hooksPath`` when git has one."""

    result = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    return value


def env_without_hooks_path(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment whose git config override clears ``core.hooksPath``."""

    env = dict(os.environ if base is None else base)
    count = int(env.get("GIT_CONFIG_COUNT", "0"))
    env[f"GIT_CONFIG_KEY_{count}"] = "core.hooksPath"
    env[f"GIT_CONFIG_VALUE_{count}"] = ""
    env["GIT_CONFIG_COUNT"] = str(count + 1)
    return env


def main() -> None:
    """Install the three hook stages. Exit with pre-commit's status."""

    configured = hooks_path()
    env = os.environ.copy()
    if configured is not None:
        print(
            "core.hooksPath is set. Installing pre-commit hooks into .git/hooks "
            "without changing git config.",
            file=sys.stderr,
        )
        env = env_without_hooks_path(env)
    result = subprocess.run(INSTALL, env=env, check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
