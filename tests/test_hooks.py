"""Unit tests for the git and agent hook scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hook_gate import (
    commit_message_error,
    is_owner_only_path,
    pushes_main,
    shell_denial,
)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "tools" / "hooks" / "run.py"
SPEC_HOOK = ROOT / "tools" / "check_spec_untouched.py"
COMMIT_HOOK = ROOT / "tools" / "hooks" / "check_commit_msg.py"
PUSH_HOOK = ROOT / "tools" / "hooks" / "pre_push.py"

_EXIT_BLOCK = 2
_GIT_ENV = {
    "GIT_AUTHOR_NAME": "hook-test",
    "GIT_AUTHOR_EMAIL": "hook-test@example.com",
    "GIT_COMMITTER_NAME": "hook-test",
    "GIT_COMMITTER_EMAIL": "hook-test@example.com",
}


def test_owner_only_paths() -> None:
    assert is_owner_only_path("spec/SCIENCE.md", ROOT)
    assert is_owner_only_path(str(ROOT / "data" / "gold" / "values.csv"), ROOT)
    assert is_owner_only_path("spec/../spec/TOLERANCES.md", ROOT)
    assert not is_owner_only_path("src/qoinfer/__init__.py", ROOT)
    assert not is_owner_only_path("data/other.csv", ROOT)
    assert not is_owner_only_path("/etc/passwd", ROOT)


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin cursor/m0_scaffold",
        "git push --force-with-lease",
        "git push -f origin feature",
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin refs/heads/main",
        "git commit --no-verify -m 'chore(tooling): x'",
        "git commit -n -m 'chore(tooling): x'",
        "OWNER_SPEC_EDIT=1 git commit -m 'chore(spec): edit'",
        "pip install ruff",
        "pip3 install ruff",
        "python -m pip install ruff",
        "python3 -m pip install ruff",
    ],
)
def test_shell_commands_are_denied(command: str) -> None:
    assert shell_denial(command, "cursor/m0_scaffold") is not None


def test_reset_hard_depends_on_branch() -> None:
    assert shell_denial("git reset --hard HEAD", "main") is not None
    assert shell_denial("git reset --hard", None) is not None
    assert shell_denial("git reset --hard HEAD", "cursor/m0_scaffold") is None


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git push -u origin cursor/m0_scaffold",
        "git commit -m 'chore(tooling): note'",
        "uv add ruff",
        "git reset --hard HEAD~1",
    ],
)
def test_shell_commands_are_allowed(command: str) -> None:
    assert shell_denial(command, "cursor/m0_scaffold") is None


def test_commit_messages() -> None:
    assert commit_message_error("chore(tooling): add M0 scaffold\n") is None
    assert commit_message_error("feat(task): add example_000_smoke\n\nBody.\n") is None
    assert commit_message_error("update stuff\n") is not None
    assert commit_message_error("feat: missing scope\n") is not None
    assert commit_message_error("feat(physics): not a scope\n") is not None
    assert commit_message_error("chore(tooling): subject\nno blank line\n") is not None
    trailer = "chore(tooling): subject\n\nCo-authored-by: Someone <a@example.com>\n"
    assert commit_message_error(trailer) is not None


def test_pushes_main_reads_pre_push_stdin() -> None:
    assert pushes_main("refs/heads/feature aaa refs/heads/main bbb\n")
    assert not pushes_main("refs/heads/feature aaa refs/heads/cursor/m0_scaffold bbb\n")


def _run_hook(
    mode: str, payload: dict[str, object], extra: list[str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUN), mode, *(extra or [])],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_cursor_before_shell_denies_force_push() -> None:
    result = _run_hook(
        "cursor-before-shell",
        {"command": "git push --force origin cursor/m0_scaffold", "cwd": str(ROOT)},
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["permission"] == "deny"
    assert "force" in body["agent_message"]


def test_cursor_before_shell_allows_status() -> None:
    result = _run_hook("cursor-before-shell", {"command": "git status", "cwd": str(ROOT)})
    assert result.returncode == 0
    assert json.loads(result.stdout)["permission"] == "allow"


def test_cursor_before_read_allows_spec() -> None:
    result = _run_hook(
        "cursor-before-read",
        {"file_path": str(ROOT / "spec" / "SCIENCE.md"), "content": ""},
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["permission"] == "allow"


def test_cursor_pre_tool_denies_spec_write() -> None:
    result = _run_hook(
        "cursor-pre-tool",
        {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "spec" / "SCIENCE.md")}},
    )
    body = json.loads(result.stdout)
    assert body["permission"] == "deny"
    assert "needs-science-decision" in body["agent_message"]


def test_cursor_after_edit_denies_spec() -> None:
    result = _run_hook(
        "cursor-after-edit",
        {
            "file_path": str(ROOT / "data" / "gold" / "values.csv"),
            "edits": [{"old_string": "a", "new_string": "b"}],
        },
    )
    assert result.returncode == _EXIT_BLOCK
    assert "needs-science-decision" in result.stderr


def test_cursor_after_edit_formats_python(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("x=1\n", encoding="utf-8")
    result = _run_hook("cursor-after-edit", {"file_path": str(target), "edits": []})
    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_claude_pre_tool_denies_edit_and_pip() -> None:
    edit = _run_hook(
        "claude-pre-tool",
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(ROOT / "spec" / "TASKS.md")},
        },
    )
    assert edit.returncode == 0
    edit_body = json.loads(edit.stdout)
    assert edit_body["hookSpecificOutput"]["permissionDecision"] == "deny"

    bash = _run_hook(
        "claude-pre-tool",
        {"tool_name": "Bash", "tool_input": {"command": "pip install numpy"}},
    )
    bash_body = json.loads(bash.stdout)
    assert bash_body["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "uv add" in bash_body["hookSpecificOutput"]["permissionDecisionReason"]


def test_claude_pre_tool_allows_src_edit() -> None:
    result = _run_hook(
        "claude-pre-tool",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(ROOT / "src" / "qoinfer" / "__init__.py")},
        },
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_claude_post_tool_blocks_gold_and_formats(tmp_path: Path) -> None:
    blocked = _run_hook(
        "claude-post-tool",
        {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "data" / "gold" / "a.csv")}},
    )
    body = json.loads(blocked.stdout)
    assert body["decision"] == "block"
    assert "needs-science-decision" in body["reason"]

    target = tmp_path / "sample.py"
    target.write_text("y=2\n", encoding="utf-8")
    formatted = _run_hook(
        "claude-post-tool",
        {"tool_name": "Edit", "tool_input": {"file_path": str(target)}},
    )
    assert formatted.returncode == 0, formatted.stderr
    assert formatted.stdout == ""
    assert target.read_text(encoding="utf-8") == "y = 2\n"


def test_stop_hook_reports_failure_and_success() -> None:
    failed = _run_hook("cursor-stop", {}, ["--check-cmd", "false"])
    assert failed.returncode == 0
    assert "make check failed" in json.loads(failed.stdout)["followup_message"]

    blocked = _run_hook("claude-stop", {}, ["--check-cmd", "false"])
    blocked_body = json.loads(blocked.stdout)
    assert blocked_body["decision"] == "block"

    passed = _run_hook("cursor-stop", {}, ["--check-cmd", "true"])
    assert passed.returncode == 0
    assert passed.stdout == ""


def test_commit_msg_script(tmp_path: Path) -> None:
    bad = tmp_path / "bad.txt"
    bad.write_text("update stuff\n", encoding="utf-8")
    denied = subprocess.run(
        [sys.executable, str(COMMIT_HOOK), str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert denied.returncode == 1
    good = tmp_path / "good.txt"
    good.write_text("chore(tooling): note\n", encoding="utf-8")
    allowed = subprocess.run(
        [sys.executable, str(COMMIT_HOOK), str(good)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert allowed.returncode == 0


def _git(cwd: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(_GIT_ENV)
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def test_staged_spec_edit_is_rejected(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "SCIENCE.md").write_text("# Science\n", encoding="utf-8")
    _git(tmp_path, "add", "spec/SCIENCE.md")
    denied = subprocess.run(
        [sys.executable, str(SPEC_HOOK)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert denied.returncode == 1
    assert "needs-science-decision" in denied.stderr

    allowed = subprocess.run(
        [sys.executable, str(SPEC_HOOK)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "OWNER_SPEC_EDIT": "1"},
    )
    assert allowed.returncode == 0


def test_pre_push_refuses_main(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "chore(tooling): test")
    on_main = subprocess.run(
        [sys.executable, str(PUSH_HOOK)],
        cwd=tmp_path,
        input="",
        capture_output=True,
        text=True,
        check=False,
    )
    assert on_main.returncode == 1
    assert "main" in on_main.stderr

    _git(tmp_path, "checkout", "-b", "feature")
    to_main = subprocess.run(
        [sys.executable, str(PUSH_HOOK)],
        cwd=tmp_path,
        input="refs/heads/feature aaa refs/heads/main bbb\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert to_main.returncode == 1
    assert "main" in to_main.stderr
