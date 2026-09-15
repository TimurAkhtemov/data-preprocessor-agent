.PHONY: setup dev test lint build check demo e2e eval
setup:
	cd backend && uv sync
	cd frontend && pnpm install --frozen-lockfile

dev:
	./scripts/dev.sh

test:
	cd backend && uv run pytest ../tests

lint:
	cd backend && uv run ruff check --config pyproject.toml dataset_investigator ../tests ../scripts
	cd frontend && pnpm lint

build:
	cd frontend && pnpm build

check: test lint build

demo:
	python3 scripts/generate_demo.py

e2e:
	cd frontend && pnpm test:e2e

eval:
	cd backend && uv run python ../scripts/evaluate.py --output ../evaluations/latest.json
