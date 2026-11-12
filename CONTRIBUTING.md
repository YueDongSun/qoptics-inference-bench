# Contributing

Humans and agents follow the same contract. The full agent rules are in
[AGENTS.md](AGENTS.md). `spec/` and `data/gold/` are owner-only.

## Setup

```sh
make setup
make check
```

`make setup` creates the uv environment and installs the pre-commit,
commit-msg, and pre-push hooks. If `core.hooksPath` is set, the hook files
are still written under `.git/hooks` and git config is left unchanged. Do not
use `pip install`. Add a dependency with `uv add` and commit `uv.lock`.

## Commits

Conventional Commits with a required scope:

```text
feat(task): add example_000_smoke
fix(verify): report a missing tolerance name
chore(tooling): add M0 scaffold
```

Scopes: `task`, `verify`, `reference`, `taskfmt`, `tooling`, `docs`, `ci`,
`deps`, `spec`. The `spec` scope is for the owner. Agents must not stage
`spec/` or `data/gold/`, and must not set `OWNER_SPEC_EDIT`.

No `Co-authored-by`, `Generated-by`, or `Made-with` trailers. No
`--no-verify`.

## Branches and pull requests

`main` is protected. One issue, one branch, one pull request:

```text
<agent>/<issue_number>_<slug>
```

Comment `claim` on the issue and add the `in-progress` label before editing.
Do not push another agent's branch. Do not force-push. Agents do not merge.

The pull request template sections are mandatory: issue link, spec reference,
contract changes, local `make check` output, what is not verified, and open
science questions. Rebase on `main` before review. The owner squash-merges.

Say which state each claim reached: prepared, installed, registered,
successfully called, or verified end to end. Paste the command output for
anything called verified.

A task-format, public-API, or layout change needs a new file in `docs/adr/`.
Update `PROGRESS.md` when a milestone or task status changes. Update the
README only with behaviour you have verified in that pull request.

## Tasks

```sh
uv run python tools/new_task.py <family>_<nnn>_<slug>
```

Fill `instruction.md`, `solution/solve.sh`, and `tests/test_outputs.py`.
Tolerances come from `spec/TOLERANCES.md` by name. If the spec does not state
the value, open a `needs-science-decision` issue and stop.

## Science gaps

Quote the spec line, list concrete options, and stop. Do not invent a
convention, unit, tolerance, or literature value.
