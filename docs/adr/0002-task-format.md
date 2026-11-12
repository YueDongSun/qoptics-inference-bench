# 2. Task format

Date: 2026-11-12

Status: accepted

## Context

Tasks are execution-graded and Terminal-Bench shaped. The owner has not filled
task families, estimators, or numeric tolerances (`spec/TASKS.md`,
`spec/TOLERANCES.md`, `spec/SCIENCE.md` are headings and `TODO(owner)` only).
The harness still needs one concrete directory layout so later tasks do not
drift.

## Decision

Each `tasks/<task_id>/` contains:

- `task.toml` with `id`, `family`, `difficulty`, `spec_ref`, `timeout_sec`
  (seconds, engineering limit), `author`, `status` (`draft` or `ready`), and
  optional `format_demo`.
- `instruction.md` for the agent under test. No hidden-test details and no
  answers.
- `environment/Dockerfile` with a pinned base image. No floating `:latest` tag.
  The image is not built by `make validate` in this milestone. When a later
  harness runs it, that run uses network disabled.
- `solution/solve.sh`, executed with the task directory as the working
  directory. It writes outputs under `artifacts/`.
- `tests/test_outputs.py`, a deterministic pytest module. The tolerance
  format is TBD by owner.

Task ids match `<family>_<nnn>_<slug>` in snake_case. The family may itself
contain underscores; the three-digit field is the `_nnn_` segment.
`tools/new_task.py <task_id>` creates the directory.

`make validate` (`tools/run_task_locally.py`) checks structure, runs the
solution, and requires the verifier to fail when the solution is not run.
`timeout_sec` from `task.toml` is applied separately to the solution
and to pytest; exceeding it kills that process group and fails the task.
The empty run counts only when pytest exit code is 1 (collected tests
failed). Exit code 0 or 5 is a vacuous verifier. Any other status, including
a collection error, is a broken verifier and fails validation.

`example_000_smoke` is a format demo, marked `format_demo = true` and stated
as such in `instruction.md`. It is not science. The instruction assigns the
integer 1 and the verifier checks exact equality. The tolerance format is
TBD by owner.

## Consequences

Scientific pass criteria wait on the owner. A task whose tests pass with no
solution cannot be marked ready by the harness. Docker build and
`--network none` are not part of `make validate` yet.
