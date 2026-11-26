.PHONY: install test lint format typecheck build audit bench demo web

DEMO_ARGS ?=

install:
	uv sync --locked --extra dev

test:
	uv run --locked --extra dev pytest

lint:
	uv run --locked --extra dev ruff check .

format:
	uv run --locked --extra dev ruff format .

typecheck:
	uv run --locked --extra dev mypy

build:
	uv build

audit:
	@set -eu; requirements="$$(mktemp)"; trap 'rm -f "$$requirements"' EXIT; \
	uv export --locked --extra dev --no-emit-project --format requirements-txt --output-file "$$requirements"; \
	uv run --locked pip-audit -r "$$requirements"

bench:
	uv run --locked --extra dev python benchmarks/bench.py
demo:
	uv run --locked --extra dev python -m demos.realworld_coding_assistant $(DEMO_ARGS)

web:
	python3 -m http.server 8080 --bind 127.0.0.1 --directory website
