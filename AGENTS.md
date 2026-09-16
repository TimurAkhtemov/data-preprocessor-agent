# Repository Guidelines

## Project Structure & Module Organization

- `backend/dataset_investigator/`: FastAPI application; `data/` handles ingestion/profiling, `agent/` the bounded Ollama loop, `execution/` restricted Python workers, and `visualization/` chart validation.
- `frontend/src/`: React/TypeScript UI, shared components, API client, and types. Static assets live in `frontend/public/`.
- `tests/`: Python tests and fixtures; `frontend/e2e/`: Playwright browser tests.
- `examples/`: synthetic and attributed evaluation datasets; `scripts/`: development and evaluation tools; `evaluations/`: saved model results.
- Read `README.md` for workflows, the root PRD for scope, and `progress.md` for verification history.

## Build, Test, and Development Commands

Run from the repository root:

- `make setup`: install backend dependencies with uv and frontend dependencies with pnpm.
- `make dev`: start FastAPI on port 8000 and Vite on port 5173.
- `make test`: run pytest unit, API, worker, and agent tests.
- `make lint`: run Ruff and ESLint.
- `make build`: type-check TypeScript and build the frontend with Vite.
- `make check`: run tests, lint, and build.
- `make e2e`: run Playwright against an already-running development stack. First install Chromium with `cd frontend && pnpm exec playwright install chromium`. Browser tests replace the active dataset.
- `OLLAMA_MODEL=<installed-tag> make eval`: run live-model evaluations and write `evaluations/latest.json`.

## Coding Style & Naming Conventions

Use four-space Python indentation, snake_case functions/modules, and PascalCase classes. Follow Ruff's configured checks and 100-character line-length setting. Use two-space TypeScript indentation, PascalCase React components, and camelCase functions/variables. Match `.prettierrc.json`: single quotes, no semicolons, trailing commas, and 100-column wrapping. ESLint checks TypeScript and React hooks.

## Testing Guidelines

Name Python tests `tests/test_*.py` with `test_*` functions; use pytest and pytest-asyncio. Browser tests use `frontend/e2e/*.spec.ts`. Add behavioral regression coverage for substantive changes, especially dataset preservation, execution restrictions, and agent budgets. No numeric coverage threshold is configured. Run `make check` before review; browser tests and real Ollama evaluations are separate checks. Review model claims against computed evidence.

## Commit & Pull Request Guidelines

Follow existing imperative commit subjects: `feat:`, `fix:`, `test:`, or `docs:`. Keep commits focused. PR descriptions should explain behavior changes, link relevant issues, list verification results, and include screenshots for UI changes.

## Security & Configuration

Copy `.env.example` to `.env` for local overrides; keep secrets untracked. Preserve immutable source datasets, loopback-only services, bounded execution, and validated chart schemas. Keep runtime data and model traffic local.
