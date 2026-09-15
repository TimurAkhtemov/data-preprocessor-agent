# Implementation progress

Source of truth: `PRD — Local Dataset Investigator.md` (95 sections, inspected in full).

## Current status

- Core application implemented and exercised live through Qwen, Python, chart and final finding.
- Profiler/worker/API/agent tests pass; frontend builds and lints; eight real browser regression tests pass.
- Post-MVP evaluation underway. Baseline exposed protocol failures; revision 1 completed all four workflows but semantic review found unsupported conclusions. Both runs are preserved. A new run is testing native Qwen reasoning and stricter evidence guidance on the same questions.
- Remaining: semantic review of the updated four-case run, final full checks, dev-script verification, and final README/progress reconciliation.
- Checkpoints below are chronological records; their pending-work statements describe that time, not current status.

## Implementation order

1. Configuration, immutable loader/snapshot, deterministic profiler and heuristic tests.
2. React/Vite/Tailwind/shadcn shell, upload, Overview, Findings, Columns, Plotly charts.
3. Ollama client, strict action schemas and parser.
4. Restricted Python child process, AST policy, bounded serialization and execution tests.
5. Bounded agent loop, API lifecycle/concurrency, investigation UI.
6. Live backend/frontend verification, visual review, README and final acceptance audit.

## Decisions and conventions

- Keep one active dataset per local server instance, shared by its browser tabs. No persistence/database.
- Source upload and canonical Parquet snapshot live in a private temporary directory. Replace state only after successful parsing/profiling; reject replacement while investigating.
- Each Python action loads the canonical snapshot into an isolated child process and fresh dataframe copy.
- Maximum five analytical actions, one parsing repair across an investigation, and at most one final summarization call. No unbounded retries.
- Neutral analytical UI with teal controls, semantic severity accents, system sans, modest radius, horizontal tabs, no permanent sidebar or chat bubbles.
- Keep models/data contracts explicit and abstractions small. Tests should check actual behavior, execution boundaries, immutability and failure modes.
- Update this file at each checkpoint. It is working progress, not a claim that untested features work.

## Initial state

- The repository initially contained only the PRD. Implementation began after its full inspection.

## Checkpoint 1 — profiler foundation

- Implemented configuration, flat CSV/Parquet loader, Pydantic profiles, numeric/categorical/datetime statistics, stable heuristic findings, deterministic sampling, immutable temporary snapshots, initial FastAPI dataset endpoints and validated chart preparation.
- Added reproducible synthetic demo: 1,212 rows; 14 extreme ages (13 source B / 999, one source A / 222), category variants, skewed/missing income, missing dates, 12 duplicate rows, nearly unique IDs.
- Verified 14 profiler/loader tests pass. Includes UTF-8/BOM/Latin-1, Parquet, malformed/ragged CSV, null/constant/near-constant data, no normalization mutation, and exact-versus-sampled metrics.
- Python runtime chosen: Homebrew Python 3.12 (uv initially selected 3.14; explicitly selected 3.12 for broad library support). Backend dependencies installed and uv.lock generated.
- Network access required sandbox escalation for package installation and localhost verification; both approved. Default sandbox cannot reach even local Ollama.
- Local Ollama is running. Installed relevant model is `qwen3.6:35b`, not the PRD example `qwen3.6:35b-a3b`. Use an environment override for live testing; retain configurable PRD default.
- Frontend setup underway. Vite 7 + React 19 + Tailwind 4; local shadcn-style Radix Button/Sheet/Tabs primitives. No remote fonts or image assets.
- Still pending: frontend application views, agent, worker, integration/security tests, visual QA, benchmark and docs.

## Checkpoint 2 — frontend and agent integration

- First frontend production build passed: application bundle ~345 KB (110 KB gzip), Plotly lazy-loaded separately ~1.43 MB (474 KB gzip). ESLint has one nonfunctional Fast Refresh naming warning to clean up.
- Implemented Overview/Findings/Columns/Investigator, actual upload/profiling phases, filters, right Sheet, numeric/category/date charts, theme toggle/OS default, mobile layouts, local-model status, polling, investigation history and trace/result display.
- API running locally at 127.0.0.1:8000; Vite at 127.0.0.1:5173. Server uses OLLAMA_MODEL=qwen3.6:35b for live validation.
- Completed agent action schemas/parser/client, one repair budget, five-action loop + finish-only summary, mandatory successful Python evidence, three-consecutive-execution-failure stop, validated chart requests and session concurrency guard.
- Implemented isolated worker, explicit AST/analytical API allowlists, private/dunder/I/O/indirect-dispatch rejection, CPU/wall/memory/file-output limits, minimized environment, runtime audit checks and bounded serialization. Execution tests are now running; security correctness is not claimed yet.
- Independent profiler review reproduced and main agent fixed: date spans exceeding pandas Timedelta range; literal '(missing)' vs null chart group collision; unweighted means during line coalescing; silent CSV NUL truncation. All 27 profiler tests now pass.
- Narrowed date-shape inference to avoid attempting date parsing on arbitrary unique text; performance benchmark must be rerun.
- Added user-requested strategic delegation. Earlier profiler review launched before model-routing instruction; new independent reviews are Terra frontend QA and Sol execution restrictions review. Main owns production integration.
- User requested post-MVP evaluation on demo plus several small attributed public datasets. Deferred until core acceptance is demonstrated. Results will be recorded here.
- Renamed PROGRESS.md to progress.md per user's requested path.
- Test runner issue found: root invocations did not discover backend pytest asyncio settings. Added root pytest.ini so repository-root and make test runs behave consistently.

## Checkpoint 3 — live UI review and execution corrections

- Terra exercised the live UI in light/dark at 1280×800 and narrow 390×844. Upload example, exact metrics, Plotly, severity/source filters, Sheet + Escape, keyboard details, numeric box/histogram, categorical and date charts all worked with no browser console errors.
- Fixed its reproduced mobile column-search mismatch by moving the selected column to a matching result when the previous selection is filtered out. Retest pending.
- Main agent inspected light/dark overview screenshots; charts and intentional styling render correctly.
- Re-ran 100,000×30 mixed profiling benchmark after tightening date inference: 2.018 seconds (prior review 6.465 seconds). Meets the <5 second PRD target on this machine.
- Expanded backend tests initially reached 59 passing / 1 failing: crosstab lazily imported a Pandas reshape module after runtime imports closed. Fixed by warming the public crosstab path on a tiny trusted fixture before closing imports, keeping the restriction intact.
- Sol review found starred positional arguments could bypass aggregate-dispatch validation; rejected AST Starred nodes. Also found brief allocations can finish between memory polls; worker now checks peak RSS before returning, alongside the parent monitor. macOS polling cannot prevent every instantaneous peak and is not a hard OS memory isolation boundary.
- Added date/timedelta/complex NumPy scalar serialization support. Continued independent restriction testing is underway.
- README, make targets, reproducible dependency locks, .env example and local dev script are in place. Need final verification and actual Qwen acceptance, then public-dataset evaluation.

## Checkpoint 4 — core live Qwen acceptance

- Real local Qwen (`qwen3.6:35b`) completed the synthetic age investigation through the app API with four analytical actions, a validated histogram and a final evidence-backed finding.
- Measured: extreme IQR bounds −20 / 106, 14 extreme ages, B=13 and A=1. Median ages A=42, B=44, C=43, unchanged after excluding extremes. Final explanation correctly distinguished source concentration from a confirmed cause.
- Observed agent behavior: first Python action incorrectly included imports and was rejected; next action corrected itself and computed valid evidence. First chart request used an incompatible box spec and was rejected; next request produced a valid grouped histogram. Both failures consumed analytical budget. Final completed within the five-action cap with no source mutation.
- Saved full local live trace at `/private/tmp/di-core-investigation.json`; durable evaluation summary/artifact will be added with the requested suite. UI reviewer is verifying the resulting final finding, chart, trace and Agent filter before running regression tests.
- Sol execution review: 17/17 tests pass after fixes. Representative exposed pandas/numpy/scipy functions work under the runtime gate. Trivial workers can exceed 128 MB baseline, so raised configurable minimum to 256 MB. Default remains 2 GB.
- Core automated integration subset: 60 passed (plus 27 profiler tests and independent execution suite pending final combined run). Production frontend lint and build pass; cleanup renamed Plot component to remove Fast Refresh warning.
- README explicitly describes macOS soft memory safeguards. Source restriction is defense in depth, not a hardened hostile-code sandbox.
- Next: repeatable browser regressions, public dataset evaluation (small attributed fixtures), final complete build/test/run audit.

## Evaluation baseline and targeted fixes

- Core workflow worked in the original live UI/API run, but the broader repeatable evaluation baseline completed only **1/4** cases (Iris). Kept the full failed run as `evaluations/qwen3.6-35b-2026-09-14-baseline.json`; do not treat it as a passing acceptance run.
- Synthetic, Penguins and Wine stopped after three consecutive rejected Python actions. Common causes: imports, print, lambda and nonstandard result variable names. No source files or snapshots changed. Iris recovered from a lazy DataFrame.to_dict import failure, computed correct correlations/medians, and produced the requested scatter.
- Sol independently matched every Iris numeric claim to the oracle; noted unsupported significance wording and an overly elevated severity for a natural association. Prompt now explicitly reserves statistical-significance claims for computed tests.
- Main fixed the demonstrated problems without expanding autonomy: action schema/prompt include a valid no-import/no-print result example and vectorized missingness example; validator reports common errors together with specific correction guidance; each tool reply reminds the model of the execution contract. Primed the trusted public DataFrame.to_dict path before closing imports. Added bounded nested DataFrame/Series serialization so dictionaries of group tables retain evidence.
- Post-fix execution/agent tests: 76 passed, including exact prior failure patterns and nested-table evidence.
- Strengthened the evaluation harness: expected profiler finding must exist; source hashes are verified and attribution embedded; exact requested chart type/columns checked; key oracle numeric values must appear in successful computed output (with explicit limitations); semantic review is recorded separately from structural pass. A code digest ties each run to backend source.
- Running the same four questions again, preserving the baseline for comparison. One pass is evidence of live acceptance, not an estimate of model reliability.

## Checkpoint 5 — resumed evaluation and claim review (September 15)

- Resumed after the usage interruption from these notes and saved artifacts; verified the two application servers and Ollama were still running. No implementation was restarted from scratch.
- Revision 1 (`evaluations/qwen3.6-35b-2026-09-14-revision1.json`) completed **4/4** workflows. Numeric/chart checks passed 2/4 under the original rubric. Main and Sol reviewed the actual claims: synthetic falsely said all extremes came from B despite A=1; Iris omitted requested within-species correlations yet claimed a within-group relationship; Penguins misattributed group evidence to a chart that only shows columns; Wine conflated group counts with rates and dismissed sparse groups. Completion alone is not semantic acceptance.
- Corrected one overly narrow evaluation check: an age-by-source mean bar is also a useful chart for the synthetic question, alongside a grouped histogram/box. The question never required a specific chart type. Iris still requires both overall and within-species correlations; the missing computation is a real failure.
- Restored native model reasoning by omitting the forced `think: false` request. `OLLAMA_THINK` is optional; hidden reasoning is discarded. Per-call generation remains bounded at 4,096 tokens, with the same five analytical actions, one JSON repair and finish-only limit.
- Strengthened final-answer guidance: cover every requested comparison, distinguish counts/rates and overall/within-group patterns, acknowledge exceptions and sparse groups, and limit chart claims to the actual specification. These are general evidence rules, not dataset-specific answers.
- Added seven client tests for native reasoning defaults, explicit overrides, hidden-reasoning exclusion, missing model diagnostics and remote endpoint rejection. Client/agent subset: **23 passed**. Full checks and the same four real-model cases are running; results will be reviewed rather than assumed correct.
