# Agent contract

This repository is `qoptics-inference-bench` (package `qoinfer`). It is an
execution-graded benchmark: synthetic photon-count data is produced from a
ground-truth model, and the agent under test recovers hidden parameters.
Grading is error against that ground truth. The owner, Yuedong Sun
(`@YueDongSun`), writes the science. Agents write the engineering around it.

`CLAUDE.md` is a symlink to this file. `.cursor/rules/` repeats these rules.

## Owner-only paths

`spec/` holds definitions, conventions, tolerances, provenance, and the task
list. `data/gold/` holds curated literature values. Agents never edit either
path and never set `OWNER_SPEC_EDIT`.

If a spec point is missing or ambiguous, open a GitHub issue labelled
`needs-science-decision`, quote the exact spec line, list the concrete
options, and stop work on that piece. Do not guess a convention, tolerance,
unit, or physical constant.

Every other behaviour must trace to a line in `spec/` or an ADR in
`docs/adr/`. A change to the task format, the public API, or the directory
layout needs a new ADR in the same pull request.

## Layout

- `src/qoinfer/`: `reference/` (solvers), `verify/` (verifier helpers),
  `taskfmt/` (task-format validator).
- `tasks/<task_id>/`: `task.toml`, `instruction.md`, `environment/Dockerfile`,
  `solution/solve.sh`, `tests/test_outputs.py`.
- Task ids are `<family>_<nnn>_<slug>` in snake_case.
  `tools/new_task.py <task_id>` scaffolds one. `make validate` checks
  structure, that the solution passes, and that a do-nothing run fails.
- `example_000_smoke` is a format demo. It is not science.

## Owner workflow standard

- snake_case for project-owned paths and identifiers (directories, modules,
  task ids, scripts, labels where possible). Keep external names at the
  boundary: `AGENTS.md`, `README.md`, `Dockerfile`, `pyproject.toml`,
  `task.toml`, `.pre-commit-config.yaml`, `.cursor/`, `.claude/`, GitHub
  template filenames, and the repository name.
- Comments, docs, ADRs, and agent instructions are English.
- Ordinary commits have no attribution trailers (`Co-authored-by`,
  `Generated-by`, `Made-with`, or a "made with" line).
- One mutable owner per resource. One agent owns one issue, branch, and
  worktree at a time. Do not edit, rebase, or push another agent's branch.
  Preserve concurrent and unknown dirty work. Never force-remove a worktree
  or branch.
- Preparation, installation, registration, a successful call, and end-to-end
  acceptance are separate states. Every pull request says which state each
  claim reached. Nothing is verified without the command output that shows it.
- Never commit credentials, host inventories, personal chat histories, tokens,
  or token-bearing URLs. Keep third-party licenses and origin notes when
  vendoring (`THIRD_PARTY_NOTICES.md`).
- Update `README.md` and affected docs with verified behaviour only, in the
  same pull request.
- Repository visibility is decided by the owner only.

## Code

- Python 3.12+, `uv`, `uv.lock` committed, exact direct dependency versions.
- `ruff` (E, F, W, I, B, UP, SIM, RUF, N, PL, line length 100). Lint hooks do
  not autofix. `mypy --strict` on `src/`.
- `pytest --strict-markers`. Tests are deterministic and set an explicit seed.
  Slow tests use `@pytest.mark.slow` and still run in `make check`.
- Type hints on `src/`. Docstrings state units and conventions and point at
  the spec section.
- No defensive programming: no broad `try/except`, no silent fallback, no
  "just in case" branch, no extra input sanitising. Fail with a clear error.
- No speculative abstraction. Build what the current spec needs.
- No checksum or sha256 manifests, signing, or certificate machinery.
- No notebooks in `src/` or `tasks/`. Exploratory notebooks go in `notebooks/`
  with outputs stripped.
- Numerical code uses numpy and scipy. Prefer exact diagonalisation for
  references and document the matrix basis order. Do not add those
  dependencies until a spec section requires the code.
- No live or paid LLM calls in the test suite.

## Hooks

Three layers, same rules:

- Git, via `pre-commit` after `make setup` (hook files land in `.git/hooks`
  even when `core.hooksPath` is set; git config is not changed): format,
  lint, mypy, nbstripout,
  YAML/TOML, whitespace, end-of-file, file size (500 kB; `data/gold/` up to
  5 MB), reject staged `spec/` and `data/gold/` edits, no commits on `main`,
  Conventional Commits with scope
  `task`, `verify`, `reference`, `taskfmt`, `tooling`, `docs`, `ci`, `deps`,
  `spec`. Pre-push refuses `main` and runs `make check`.
- Cursor (`.cursor/hooks.json`) and Claude Code (`.claude/settings.json`)
  call `tools/hooks/run.py`. They deny `git push --force*`, a push to `main`,
  `git commit --no-verify`, `git reset --hard` on `main`, `OWNER_SPEC_EDIT=`,
  and `pip install` (use `uv add`). Edits under `spec/` or `data/gold/` are
  denied. Reads of `spec/` stay allowed. Python edits are formatted with
  ruff. The stop hook runs `make check` and blocks completion when it fails.

Do not skip hooks (`--no-verify`, `-n`).

## Branches and review

- `main` stays green. Require a pull request, linear history, no force-push,
  and CODEOWNERS review. Agents never merge.
- One issue, one branch, one pull request. Branch name:
  `<agent>/<issue_number>_<slug>`. Comment `claim` and add `in-progress`
  before starting. Stay inside the issue's file scope.
- Aim for under 400 changed lines excluding `data/` and lockfiles. A larger
  pull request explains why.
- Rebase on `main` before review. Squash merge only. The owner merges.
- Pull request sections, all required: issue link; spec reference
  (`spec/...#anchor`); contract changes (`none` or a list plus an ADR);
  local check output (`make check`); what is not verified; open science
  questions.
- Update `PROGRESS.md` in the same pull request when a milestone or task
  status changes.

## Commands

```sh
make setup
make check
```

`make check` is fmt-check, lint, type, pytest (including slow), and validate.
Local output decides if Actions is unavailable. Do not spend time debugging
Actions billing or infrastructure.
