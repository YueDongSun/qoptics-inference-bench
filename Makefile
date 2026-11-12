.PHONY: setup fmt fmt-check lint type test validate check

setup:
	uv sync --all-groups
	uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

fmt:
	uv run ruff format .

fmt-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

type:
	uv run mypy --strict src

test:
	uv run pytest

validate:
	uv run python tools/run_task_locally.py --all

check: fmt-check lint type test validate
