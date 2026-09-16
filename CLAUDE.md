# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Dataset Investigator: a local-only web app that profiles an uploaded CSV/Parquet file and lets a
local Ollama model run a bounded, evidence-backed investigation over it. FastAPI backend under
`backend/`, React/Vite frontend under `frontend/`, tests at the repo root under `tests/`.
Requires Python 3.12 (`backend/.python-version`), `uv`, `pnpm`, and a running Ollama server on
loopback for model features. Everything else works without Ollama.

`PRD — Local Dataset Investigator.md` is the product spec; `progress.md` is the implementation
log with decisions, checkpoints and reviewed evaluation results. Cleaning, transformations,
export, persistence, multiple datasets and cloud APIs are explicitly out of scope for the MVP.

## Commands

All `make` targets run from the repo root (see `Makefile`).

```bash
make setup      # uv sync in backend/, pnpm install --frozen-lockfile in frontend/
make dev        # scripts/dev.sh: uvicorn on 127.0.0.1:8000 + vite on 127.0.0.1:5173 (strict port)
make test       # cd backend && uv run pytest ../tests   (offline; no Ollama needed)
make lint       # ruff (backend, tests, scripts) + eslint (frontend)
make build      # tsc -b && vite build
make check      # test + lint + build — the pre-commit bar
make e2e        # playwright against an ALREADY-RUNNING `make dev` stack
make eval       # live-model evaluation suite -> evaluations/latest.json (needs Ollama)
make demo       # regenerate examples/suspicious_customers.csv deterministically
```

Single test / subset (pytest is configured via `pytest.ini`, `asyncio_mode = auto`, so async
tests need no marker):

```bash
cd backend && uv run pytest ../tests/test_agent.py -k five_actions
cd backend && uv run pytest ../tests/test_execution.py -x
```

Frontend only:

```bash
cd frontend && pnpm lint && pnpm build
cd frontend && pnpm exec playwright install chromium   # once; E2E_CHANNEL=chrome uses local Chrome
```

Evaluation against a specific installed model / case:

```bash
uv run --project backend python scripts/evaluate.py --model qwen3.6:35b --case penguins --output evaluations/penguins.json
```

Config comes from env vars, then the root `.env` (see `.env.example` and `Settings` in
`backend/dataset_investigator/config.py`). Defaults work with no `.env`. Several limits are
capped in the `Settings` fields themselves (e.g. `agent_max_steps` ≤ 5, code timeout ≤ 10 s,
upload ≤ 250 MB); raising a cap means editing the validator, not just the env var.

## Architecture

Backend paths below are relative to `backend/dataset_investigator/`, frontend paths to
`frontend/src/`. The Python package is installed editable via `uv`, so the worker subprocess
imports `dataset_investigator` normally.

**Two independent flows share one in-memory session.** `main.py` holds a single process-wide
session (one dataset, one investigation history, no database). Uploads and investigations are
mutually exclusive; a successful replacement upload clears prior findings, a backend restart
clears everything. The Vite dev server proxies `/api` to `127.0.0.1:8000`, and the backend
rejects non-loopback Host/Origin, so ports are effectively fixed.

1. **Upload → profile (no LLM).** `POST /api/datasets` → `ingest()` streams the file to a private
   temp dir and runs `prepare_dataset()` in a threadpool: `data/loader.py` `load_dataset()`
   (CSV/Parquet, strict validation) → `data/profiler.py` `profile_dataset()` (exact
   shape/missingness/cardinality/duplicates; expensive stats use a seed-42 sample above
   `LARGE_DATASET_ROW_THRESHOLD`) → `data/heuristics.py` `detect_findings()` (profiler
   findings with stable IDs). The original bytes and a canonical Parquet snapshot are written
   read-only; the profile is returned. Progress is polled via `GET /api/datasets/progress`.
2. **Investigate (LLM).** `POST /api/investigations` (202) → `start_investigation()` checks
   Ollama, then schedules `agent/investigator.py` `investigate()` as an asyncio task. The
   frontend polls `GET /api/investigations/{id}` about once a second and merges final agent
   findings into the profiler findings list.

**Agent loop** (`agent/`): `client.py` `OllamaClient.chat()` makes non-streaming `/api/chat`
calls with a JSON-schema `format` constraint (`ACTION_SCHEMA`, or `Finish` only in the
summarization step); only message content is retained, never hidden reasoning. `prompts.py`
holds `SYSTEM_PROMPT`; `parser.py` `parse_action()` extracts JSON and validates the
discriminated union `RunPython | RequestChart | Finish` from `schemas.py` (strict models,
extra fields rejected). Budget rules live in `investigate()`: at most `AGENT_MAX_STEPS`
analytical actions (failures count), one JSON repair request per investigation, one extra
finish-only summarization call, stop after three consecutive Python failures, and a `Finish`
is rejected unless at least one Python action succeeded with nonempty evidence. Changing any
of these limits means updating `tests/test_agent.py`, which pins them with a scripted client.

**Python execution** (`execution/`): `sandbox.py` `execute_python()` launches a fresh
`python -I` subprocess running `worker.py` per action, with the parent enforcing the wall
deadline and RSS budget. `validator.py` `validate_code()` is an AST allowlist (no imports,
dunder/private access, lambdas, `apply`, `eval`, `query`, file/network/shell calls; string
aggregation names are checked against an allowlist), and the worker re-runs it before exec.
The worker deep-copies the snapshot into `df`, exposes `pd`/`np`/`stats` plus `SAFE_BUILTINS`,
installs a `sys.addaudithook` that denies filesystem/network/process/import events, and
requires the code to assign `result`. `data/serialization.py` truncates results to 50 rows ×
20 columns / 12,000 chars. Adding a permitted pandas method means touching both the AST
allowlist and, usually, `tests/test_execution.py` / `tests/test_execution_review.py`.

**Charts are specs, never code.** Both the UI (`POST /api/datasets/chart`) and the agent's
`request_chart` action go through `visualization/validation.py`: `validate_chart()` checks the
`ChartSpec` (`visualization/schemas.py`) against the profile's column types, then
`build_chart()` prepares bounded series server-side. The frontend renders those series only;
no model-generated Plotly or JS is ever evaluated.

**Type contracts are hand-mirrored.** Pydantic models live in `models.py` (profile,
statistics, profiler findings), `agent/schemas.py` (actions, agent findings, request bodies)
and `visualization/schemas.py`. `frontend/src/types/api.ts` is written by hand to match the
consumed fields; there is no codegen step, so a backend field change needs a matching edit
there.

**Frontend** (`frontend/src/`): `App.tsx` owns all dataset/investigation state, the polling
loops and the upload flow, and composes `Overview`, `Columns`, `Findings` and `Investigator`
as tabs plus a finding-detail Sheet. `api/client.ts` wraps relative `/api` fetches and raises
a structured `ApiError`. Overview/Columns request charts through `DatasetChart` in
`ChartRenderer.tsx`; investigation results pass chart payloads to it directly. `Plot.tsx`
(react-plotly.js over the Plotly cartesian bundle) is `lazy()`-loaded. `components/ui/` are
customized shadcn/Radix primitives; styling is Tailwind v4 via the Vite plugin.

## Testing conventions

- `make test` is fully offline. Agent tests (`tests/test_agent.py`) drive `investigate()` with a
  scripted `FakeClient`; API tests use FastAPI `TestClient` and patch the Ollama client with
  `AsyncMock`; execution tests spawn **real** worker subprocesses through the sandbox.
- `tests/test_*_review.py` files hold regression tests added from later review passes; they
  are ordinary pytest modules, not a separate suite.
- `tests/test_eval_fixtures.py` pins the SHA-256 hashes in `examples/evaluation/sources.json`
  against the raw/prepared fixture bytes. `.gitattributes` disables text/EOL normalization for
  `examples/**` and `tests/fixtures/**`; do not reformat those files.
- Browser tests (`frontend/e2e/core.spec.ts`) are serial, do not start servers, do not call a
  model, and replace the active UI session with the demo dataset.
- `evaluations/*.json` are committed outputs of `scripts/evaluate.py` (real Ollama calls, real
  workers). Failed baselines are kept alongside later runs on purpose; do not delete them.
