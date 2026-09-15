# Dataset Investigator

A local application for understanding unfamiliar CSV and Parquet datasets. A deterministic profiler surfaces missingness, repeated rows, unusual distributions, inconsistent labels and likely type mismatches. A bounded Ollama agent investigates these signals using Python, validated charts and evidence you can inspect. The source dataset is never cleaned or overwritten.

## Requirements

- macOS or Linux (the execution worker uses POSIX resource limits)
- Python 3.11+; the project pins Python 3.12 for the default `uv` environment
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 22.12+ and pnpm 10 (`packageManager` pins pnpm 10.32.1)
- [Ollama](https://ollama.com/) and an installed local model for investigations; profiling works without either

All runtime assets, data and model traffic stay on your machine. Installation downloads package dependencies. No external fonts, analytics, cloud model providers or runtime CDNs are used.

## Install

From the repository root:

```bash
cd backend
uv sync
cd ../frontend
pnpm install --frozen-lockfile
cd ..
cp .env.example .env
```

Or run `make setup` to install both dependency sets. If pnpm reports ignored dependency build scripts, no blanket approval is required: the included Vite build uses packaged platform binaries.

Configure an **installed** model tag in `.env`. The PRD default is `qwen3.6:35b-a3b`; tags vary by installation, so check yours:

```bash
ollama list
# If needed, start the local Ollama server in a separate terminal:
ollama serve
# Install a model only if it is not already available:
ollama pull qwen3.6:35b-a3b
```

The local development verification used the existing `qwen3.6:35b` model. It requires no new model download on that machine.

## Run

```bash
make dev
```

Open [Dataset Investigator](http://127.0.0.1:5173). Backend API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Ctrl+C stops both application processes started by the script; it does not stop Ollama or unrelated servers. Ports 5173 and 8000 must be free.

Override the configured model for one run:

```bash
OLLAMA_MODEL=qwen3.6:35b make dev
```

Start the services independently for backend hot reload:

```bash
# Terminal 1, from repository root
cd backend
uv run uvicorn dataset_investigator.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2, from repository root
cd frontend
pnpm dev
```

Vite proxies `/api` to FastAPI. The frontend never calls Ollama directly. This is a local development/MVP run workflow, not a public hosting setup.

## First investigation

1. Click **Load example** or upload a `.csv` / `.parquet` file up to 250 MB.
2. Inspect **Overview**, open a signal in **Findings**, or explore **Columns**.
3. Click **Investigate** on an age finding, or ask: “Are the extreme age values concentrated in one source system? Compare sources, show a chart, and distinguish observations from possible causes.”
4. Follow action progress and inspect the final evidence, recommendation, chart and expandable Python trace.

The synthetic fixture has 1,212 rows and six columns. It includes 14 extreme ages (13 source-B values of 999 and one source-A value of 222), category-label variants, missing and skewed income, missing dates, nearly unique customer IDs and 12 repeated rows. Regenerate it with `make demo`.

## Behavior and implementation decisions

- **One session per backend process.** Browser tabs share one active dataset and investigation history. Reloading a browser restores that session. Restarting the backend clears it. Loading another dataset clears prior findings/history only after its profile succeeds. There is no database or durable history.
- **Immutable originals.** Uploads are streamed into a private temporary directory. The exact uploaded bytes and canonical Parquet snapshot are made read-only. Each Python action starts a new child process, loads the snapshot and makes its own deep dataframe copy. User files are never overwritten; temporary files are removed on replacement/shutdown.
- **CSV parsing.** UTF-8, UTF-8 with BOM and Latin-1 are supported. Standard comma-delimited files with a header are expected; ragged rows, duplicate/empty headers and NUL bytes are rejected. Pandas infers storage dtypes when loading CSV. Raw bytes remain preserved; whitespace/case normalization is analysis-only. Parquet must contain flat scalar columns; nested/binary columns receive a useful error.
- **Exact vs sampled.** Shape, missingness, cardinality and duplicates are exact. Over 200,000 rows, expensive statistics use a deterministic seed-42 sample of up to 100,000 rows. Distribution counts describe that sample, not estimated full-data totals. The UI, evidence and model context disclose this. Python actions access the full snapshot unless the model explicitly samples.
- **Types and findings.** Numeric/datetime parsing needs more than 90% success on non-null strings; a date-shape gate prevents parsing arbitrary text. Identifier detection considers names/patterns and avoids continuous floats. Infinite values are reported separately and excluded from finite numeric statistics. Statistical outliers are not labeled bad data. Finding IDs are stable by category/column within a dataset.
- **Controlled charts.** The backend validates the chart schema, columns and type compatibility, then prepares bounded series. Histograms use shared bins, bar/line plots use counts or numeric means, missingness uses exact counts, and ordered line bins preserve weighted means. At most 30 bars, eight color groups and 500 ordered bins are displayed; box/scatter plots use at most 5,000 sampled rows. Plotly is lazy-loaded and uses app-controlled colors. No model-generated JavaScript or Plotly code is evaluated.
- **Bounded agent.** At most five analytical actions; failed actions consume budget. There is at most one additional finish-only summarization call and one JSON repair request across the whole investigation (maximum seven model requests). Three consecutive failed Python executions stop the run. A final finding requires at least one successful Python result and nonempty evidence. These checks prevent evidence-free completion but cannot prove every model claim; inspect the computed trace. Confidence is self-assessed model confidence, not a calibrated statistical measure.
- **Minimal local API.** Dataset uploads/profiling run off the event loop; simple polling updates progress. One upload/investigation is permitted at a time. No queues, Redis, database or multi-agent application architecture. Server errors are structured; datasets and full prompts are not logged.

## Python execution restrictions

Model-generated analytical Python is executed in a restricted child process with AST validation and resource limits. This reduces risk but should not be considered a hardened security sandbox suitable for hostile code.

The worker exposes `df`, selected pandas/numpy/scipy.stats analytical functions and deliberately selected safe builtins. It blocks imports, private/dunder traversal, filesystem and networking functions, shell access, dynamic calls, `eval`, `query`, `apply`, lambdas and non-statistical string aggregation dispatch. Use explicit dataframe column access and assign the output to `result`:

```python
result = df.groupby("source_system")["age"].agg(["count", "median", "max"])
```

Every action gets a fresh environment. Temporary assignments do not carry over. Read-only analytical transformations such as `df.assign(...)` operate on a private working copy, not the canonical data.

Limits include a 10-second wall deadline covering worker startup/loading/execution, a CPU limit, a 2 GB RSS budget monitored by the parent, a Linux address-space limit, disabled file output/core dumps, a reduced file-descriptor limit and a scrubbed environment. Results are truncated to 50 rows × 20 columns and 12,000 characters, with truncation disclosed. The worker also checks peak RSS before returning. On macOS, polling and peak checks are soft safeguards: a brief allocation can exceed the budget before detection, and there is no hard OS memory boundary. Runtime audit checks add defense in depth. AST/runtime allowlists deliberately trade some Pandas flexibility for a smaller attack surface; complex methods can be rejected and the model may correct its action within budget.

Only loopback Ollama endpoints are accepted. The servers bind to loopback; backend Host/Origin checks reject nonlocal website origins. Do not expose the app publicly or treat it as a multi-user isolation boundary.

## Configuration

Environment variables override the root `.env` file. Defaults work without `.env`.

| Variable | Default | Behavior |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Loopback only |
| `OLLAMA_MODEL` | `qwen3.6:35b-a3b` | Exact installed model tag |
| `OLLAMA_THINK` | Unset | Use the model's native reasoning default; optional `true` / `false` override |
| `MAX_UPLOAD_MB` | `250` | Can lower the upload limit |
| `AGENT_MAX_STEPS` | `5` | Can lower the analytical budget |
| `AGENT_CODE_TIMEOUT_SECONDS` | `10` | Can lower the worker deadline |
| `LARGE_DATASET_ROW_THRESHOLD` | `200000` | Sampling threshold |
| `PROFILE_SAMPLE_ROWS` | `100000` | Maximum expensive-operation sample |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | Timeout per model call |
| `WORKER_MEMORY_MB` | `2048` | Worker memory budget |

If Ollama is unavailable or the configured model is missing, only investigation actions are disabled. Overview, Findings, Columns and charts keep working. A slow model can time out; choose a smaller model, narrow the question, or adjust the model timeout.

Model calls allow up to 4,096 generated tokens, including any internal reasoning. Reasoning is not stored in the investigation trace or displayed; only structured actions and their short purposes are retained. The default does not force reasoning off: the installed Qwen model produced more reliable investigations when allowed to use its native reasoning behavior. Explicit overrides depend on the model's support and may affect latency and quality.

## Verification

```bash
make test     # deterministic unit, API, real subprocess and bounded-agent tests
make lint     # Ruff + ESLint
make build    # TypeScript + Vite production build
make check    # all three
```

`make check` covers unit/API/subprocess tests, lint and production build. It does not run browser tests or call a model. Unit agent tests use scripted model responses while execution tests run real subprocess workers.

Run browser tests against an already-running `make dev` stack in another terminal:

```bash
# Install the dedicated browser once (requires a network download):
cd frontend
pnpm exec playwright install chromium
cd ..
make e2e
# Alternatively, use an existing Chrome install in a temporary isolated profile:
E2E_CHANNEL=chrome make e2e
```

The eight serial browser tests cover actual CSV/Parquet uploads, the demo profile, finding filters/Sheet keyboard dismissal, numeric/category charts, mobile column search, themes and malformed-file recovery. They replace the active UI session with the demo dataset; finish any investigation first. They do not call a model or touch your personal browser profile. Results go to `frontend/test-results/`.

## Small live-model evaluation suite

The core MVP was exercised before adding this suite. It uses the existing synthetic fixture plus [three small attributed public datasets](examples/evaluation/README.md): Iris, Palmer penguins and red wine quality. Original downloads total about 102 KiB; raw bytes, license/source metadata, hashes and explicitly documented format-only preparations are included. Normal app use performs no downloads.

Run all four cases against your installed model:

```bash
OLLAMA_MODEL=qwen3.6:35b make eval
# Or select a case and a named output file, from repository root:
uv run --project backend python scripts/evaluate.py --model qwen3.6:35b --case penguins --output evaluations/penguins.json
```

The runner creates its own temporary FastAPI session, uses actual upload/profile/investigation routes, makes real Ollama calls, executes real workers and validates charts. It does not replace the interactive browser's dataset. Each result records timing, bounded trace, final finding, source/snapshot preservation, a deterministic numeric oracle, expected chart contract, source provenance and code digest. Re-fetching source fixtures is optional and explicit: `uv run --project backend python scripts/fetch_eval_datasets.py`.

Automated structural/numeric coverage checks are supplemented by a separate semantic review of claim-to-evidence correspondence. A passing small run demonstrates those cases; it is not a reliability benchmark. The failed baseline is preserved alongside the subsequent run in `evaluations/`. Observed failures, fixes and final case-by-case behavior are documented in [progress.md](progress.md).

## Repository

- `backend/dataset_investigator/data/`: ingestion, profiler, heuristics, bounded serialization
- `backend/dataset_investigator/execution/`: AST policy, parent monitor, isolated worker
- `backend/dataset_investigator/agent/`: Ollama client, schemas, parser, prompts, bounded loop
- `backend/dataset_investigator/visualization/`: chart schema validation and data preparation
- `backend/dataset_investigator/main.py`: in-memory session and small FastAPI surface
- `frontend/src/`: React/Vite/Tailwind UI, customized shadcn/Radix primitives and Plotly renderer
- `tests/`, `examples/`, `scripts/`: behavioral tests, synthetic fixture, local development tools

The PRD remains the product specification. Cleaning, transformations, export, persistence, multiple datasets, cloud APIs and training are intentionally outside this MVP.
