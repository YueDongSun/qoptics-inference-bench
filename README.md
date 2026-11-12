# qoptics-inference-bench

Execution-graded agent benchmark: inferring quantum-optics experiment
parameters from synthetic count data. Package name: `qoinfer`.

Scientific definitions are not written yet. `spec/` is headings and
`TODO(owner)` markers. `example_000_smoke` is a format demo, not a physics
task.

## Status

| Piece | State |
| --- | --- |
| M0 scaffold | pull request open, not merged |
| `spec/` | headings only |
| Tasks | `example_000_smoke` format demo |

## Quickstart

```sh
make setup && make check
```

`make check` formats, lints, typechecks `src/`, runs pytest, and validates
every task.

## Add a task

```sh
uv run python tools/new_task.py <family>_<nnn>_<slug>
```

Then fill the instruction, the reference solution, and `tests/test_outputs.py`.
Read tolerances from [`spec/TOLERANCES.md`](spec/TOLERANCES.md) by name. Do not
edit `spec/`. If a value is missing, open a `needs-science-decision` issue.

## Contract

- Agent rules: [AGENTS.md](AGENTS.md)
- Science (owner-only): [spec/](spec/)
- Task format: [docs/adr/0002-task-format.md](docs/adr/0002-task-format.md)
- Milestone table: [PROGRESS.md](PROGRESS.md)
