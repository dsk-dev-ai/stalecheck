.PHONY: setup api web eval test lint fmt build docker clean

setup:
	uv sync
	cd apps/web && pnpm install

api:
	uv run uvicorn stalecheck_api.main:app --reload --port 8000

web:
	cd apps/web && pnpm dev

eval:
	uv run python evals/run_eval.py

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

build:
	cd apps/web && pnpm build

docker:
	docker build -t stalecheck-api .

clean:
	rm -rf data/*.db apps/web/.next apps/web/out
