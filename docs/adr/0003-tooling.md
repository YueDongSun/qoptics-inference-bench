# 3. Tooling and hooks

Date: 2026-11-12

Status: accepted

## Context

Local `make check` is the source of truth. Git hooks, Cursor hooks, and Claude
Code hooks must agree, and agents must not edit `spec/` or `data/gold/`.

## Decision

- Python 3.12, dependencies managed by `uv`, lockfile `uv.lock` committed.
  Direct dependency versions in `pyproject.toml` are exact.
- `ruff` formats and lints with rule set E, F, W, I, B, UP, SIM, RUF, N, PL
  and line length 100. The pre-commit lint hook does not pass `--fix`.
- `mypy --strict` checks `src/` only.
- `pytest --strict-markers` runs `tests/`. Slow tests use `@pytest.mark.slow`
  and are included in `make check`. `make check` is `fmt-check`, `lint`,
  `type`, `test`, and `validate`.
- No checksum manifests, signing, or live or paid LLM calls.
- Numerical code, when a spec section requires it, uses numpy and scipy.
  Those dependencies are not added until that code exists.
- Git hooks are installed by `make setup` through `pre-commit`:
  format, lint, mypy, nbstripout, YAML/TOML checks, end-of-file, trailing
  whitespace, added-file size (500 kB, `data/gold/` up to 5 MB),
  `tools/check_spec_untouched.py`, `no-commit-to-branch` for `main`,
  Conventional Commits with scope
  `task|verify|reference|taskfmt|tooling|docs|ci|deps|spec`,
  and a pre-push hook that refuses `main` and runs `make check`.
- `tools/check_spec_untouched.py` rejects a staged path under `spec/` or
  `data/gold/` unless `OWNER_SPEC_EDIT=1`. Agents must never set that
  variable. The initial skeleton is the baseline this milestone commits
  before the hook is installed; later edits are rejected.
- Cursor (`.cursor/hooks.json`) and Claude Code (`.claude/settings.json`)
  call `tools/hooks/run.py`. Shell denials: `git push --force*`,
  `git push` to `main`, `git commit --no-verify`, `git reset --hard` while
  the current branch is `main` (or when the branch cannot be resolved),
  `OWNER_SPEC_EDIT=`, and `pip install` / `pip3 install` /
  `python -m pip install`.
- `beforeReadFile` allows reads, including `spec/`, because an agent must
  quote a spec line when it opens a `needs-science-decision` issue.
  Cursor `preToolUse` on write and delete tools, and `afterFileEdit`, deny
  owner-only paths. Claude `PreToolUse` denies `Edit`, `Write`, and
  `MultiEdit` on those paths. `afterFileEdit` and Claude `PostToolUse` on
  `Edit|Write` run `ruff format` on Python files.
- The Cursor and Claude stop hooks run `make check`. On failure, Cursor
  returns `followup_message` and Claude returns `decision: block`.

## Consequences

`make setup` needs network access the first time so `pre-commit` can fetch
hook repositories. A green `make check` does not by itself mean GitHub Actions
ran. Pushing `main` is refused by the pre-push hook when the current branch
is `main` or the pre-push stdin updates `refs/heads/main`.
