#!/usr/bin/env python3
"""Agent hook entry point shared by Cursor and Claude Code.

Subcommands read one JSON object on stdin and print a decision on stdout.
See docs/adr/0003-tooling.md.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hook_gate import (
    SCIENCE_DECISION_MESSAGE,
    git_current_branch,
    is_owner_only_path,
    repo_root,
    shell_denial,
)

_PATH_KEYS = frozenset({"file_path", "path", "notebook_path"})
_CHECK_FLAG = "--check-cmd"
_OUTPUT_TAIL = 8000


def main() -> None:
    """Dispatch one hook subcommand."""

    hook, check_cmd = _parse_args(sys.argv[1:])
    payload = _load_payload()
    if hook == "cursor-after-edit":
        _cursor_after_edit(payload)
        return
    if hook == "cursor-stop":
        _emit(_stop_result("cursor", check_cmd))
        return
    if hook == "claude-stop":
        _emit(_stop_result("claude", check_cmd))
        return
    emitters = {
        "cursor-before-shell": _cursor_before_shell,
        "cursor-before-read": _cursor_before_read,
        "cursor-pre-tool": _cursor_pre_tool,
        "claude-pre-tool": _claude_pre_tool,
        "claude-post-tool": _claude_post_tool,
    }
    if hook not in emitters:
        raise SystemExit(f"unknown hook {hook}")
    _emit(emitters[hook](payload))


def _parse_args(argv: list[str]) -> tuple[str, list[str]]:
    if not argv:
        raise SystemExit("usage: run.py <hook> [--check-cmd <cmd>...]")
    if _CHECK_FLAG in argv:
        index = argv.index(_CHECK_FLAG)
        hook_args = argv[:index]
        check_cmd = argv[index + 1 :]
        if not hook_args or not check_cmd:
            raise SystemExit("--check-cmd needs a hook and a command")
        return hook_args[0], check_cmd
    return argv[0], ["make", "check"]


def _load_payload() -> dict[str, object]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("hook expected a JSON object on stdin")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("hook JSON must be an object")
    payload: dict[str, object] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise SystemExit("hook JSON keys must be strings")
        payload[key] = value
    return payload


def _emit(data: dict[str, object] | None) -> None:
    if data is None:
        return
    json.dump(data, sys.stdout)
    sys.stdout.write("\n")


def _cursor_before_shell(payload: dict[str, object]) -> dict[str, object]:
    command = payload.get("command")
    if not isinstance(command, str):
        raise SystemExit("beforeShellExecution payload missing string command")
    cwd_value = payload.get("cwd")
    cwd = Path(cwd_value) if isinstance(cwd_value, str) and cwd_value else repo_root()
    return _permission(shell_denial(command, git_current_branch(cwd)))


def _cursor_before_read(payload: dict[str, object]) -> dict[str, object]:
    if "file_path" not in payload:
        raise SystemExit("beforeReadFile payload missing file_path")
    # Agents must be able to read spec/ in order to quote a line in an issue.
    return {"permission": "allow"}


def _cursor_pre_tool(payload: dict[str, object]) -> dict[str, object]:
    return _permission(_owner_edit_reason(payload.get("tool_input")))


def _cursor_after_edit(payload: dict[str, object]) -> None:
    file_path = payload.get("file_path")
    if not isinstance(file_path, str):
        raise SystemExit("afterFileEdit payload missing string file_path")
    if is_owner_only_path(file_path):
        print(SCIENCE_DECISION_MESSAGE, file=sys.stderr)
        raise SystemExit(2)
    format_python(Path(file_path))


def _claude_pre_tool(payload: dict[str, object]) -> dict[str, object] | None:
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        raise SystemExit("PreToolUse payload missing tool_name")
    tool_input = payload.get("tool_input")
    if tool_name == "Bash":
        command = _command_from_input(tool_input)
        reason = shell_denial(command, git_current_branch(repo_root()))
    else:
        reason = _owner_edit_reason(tool_input)
    if reason is None:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _claude_post_tool(payload: dict[str, object]) -> dict[str, object] | None:
    paths = _string_paths(payload.get("tool_input"))
    for path in paths:
        if is_owner_only_path(path):
            return {
                "decision": "block",
                "reason": SCIENCE_DECISION_MESSAGE + " Revert the edit.",
            }
    for path in paths:
        format_python(Path(path))
    return None


def _stop_result(system: str, check_cmd: list[str]) -> dict[str, object] | None:
    result = subprocess.run(
        check_cmd,
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return None
    combined = result.stdout + result.stderr
    if len(combined) > _OUTPUT_TAIL:
        combined = combined[-_OUTPUT_TAIL:]
    message = "make check failed. Keep working until it passes.\n" + combined
    if system == "cursor":
        return {"followup_message": message}
    if system == "claude":
        return {"decision": "block", "reason": message}
    raise SystemExit(f"unknown stop system {system}")


def _permission(reason: str | None) -> dict[str, object]:
    if reason is None:
        return {"permission": "allow"}
    return {"permission": "deny", "user_message": reason, "agent_message": reason}


def _command_from_input(tool_input: object) -> str:
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    return ""


def _owner_edit_reason(tool_input: object) -> str | None:
    for path in _string_paths(tool_input):
        if is_owner_only_path(path):
            return SCIENCE_DECISION_MESSAGE
    return None


def _string_paths(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _PATH_KEYS and isinstance(item, str):
                found.append(item)
            else:
                found.extend(_string_paths(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_string_paths(item))
    return found


def format_python(path: Path) -> None:
    """Run ``ruff format`` on a Python file. Other suffixes are left untouched."""

    if path.suffix != ".py":
        return
    if not path.is_file():
        raise SystemExit(f"ruff format: {path} is not a file")
    result = subprocess.run(
        ["uv", "run", "ruff", "format", str(path)],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.stderr.write(result.stdout)
        raise SystemExit(result.returncode or 1)


if __name__ == "__main__":
    main()
