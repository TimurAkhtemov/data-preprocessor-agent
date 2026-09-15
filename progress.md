# Implementation progress

Source of truth: `PRD — Local Dataset Investigator.md` (95 sections, inspected in full).

## Current status

- Functional PRD MVP complete and running at `http://127.0.0.1:5173`, using installed `qwen3.6:35b`. Demo plus a successful browser-submitted investigation remain in the local session.
- Profiler/worker/API/agent tests pass; frontend builds and lints; eight real browser regression tests pass.
- Post-MVP evaluation complete: final four-case run passes all structural/numeric/chart checks with no rejected actions or source mutation. Independent semantic review: one pass, three qualified passes, no false numerical claims. Earlier failures and remaining interpretation/method limitations are preserved below.
- Implementation, full checks, launcher lifecycle, browser regressions, final visual review, real browser-submitted investigation and evaluation review are complete. No required MVP implementation work remains. Known model interpretation and execution-isolation limits are documented; this is a local MVP, not a hardened public service.
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

## Checkpoint 6 — Git, final browser checks and native-reasoning review

- Corrected a workflow omission after the user called it out: Git should have been initialized at the beginning. Initialized `main` and committed the original PRD/ignore rules (`129d520`), the implemented application (`c8f2c54`), and the evaluation suite with preserved results (`f94e65b`). These are current checkpoints, not reconstructed historical implementation commits. Further edits are tracked incrementally.
- Ignore dependencies, caches, local environment files, build output and browser artifacts. Git attributes preserve all fixture bytes exactly, including CRLF and intentionally inconsistent whitespace; no dataset normalization was performed to satisfy whitespace checks.
- Full verification: **119 tests passed in 12.34 seconds**, Ruff/ESLint clean, TypeScript and Vite production build passed. The only warnings are upstream Starlette test-client deprecations.
- Verified the documented combined launcher starts both services and reports the installed model ready. Signaling the launcher stops both owned services; Ctrl+C was tested too, and both ports were released. Fixed misleading `make` error output on the normal signal cleanup path. Ollama remains running.
- Re-ran all eight browser tests on the final app: **8 passed in 7.5 seconds**. Added an assertion that the selected column's related findings appear. Both real CSV/Parquet uploads, errors preserving the active dataset, charts, filters, Sheet/Escape, theme changes and mobile search pass.
- Native-reasoning run `evaluations/qwen3.6-35b-2026-09-15.json`: **4/4 structural/numeric/chart passes**, four successful Python actions, five chart actions (one rejected then corrected), all original/snapshot/fixture hashes unchanged. Durations: synthetic 138.91s, Iris 66.93s, Penguins 55.79s, Wine 77.96s. Independent Sol review plus main review: synthetic pass; Iris qualified (overgeneralizes correlation strengths); Penguins qualified (overstates Gentoo vs almost-equal Adelie rate); Wine semantic fail (unsupported systematic-vs-random explanation and omitted quality-8 comparison). Recorded reviews alongside unchanged model outputs in the artifact.
- Added six lines of general guidance to preserve every small-group comparison, describe near-equal rates and heterogeneous associations accurately, and keep process/cause explanations as untested hypotheses. The final repeat uses exactly the same questions, fixtures and limits. No additional agent phases, verification agents, retries or dataset-specific answers were added to the application.

## Final evaluation — September 15

Artifact: `evaluations/qwen3.6-35b-2026-09-15-final.json`, backend source matches commit `b8044e1` and the saved code digest. Real Ollama `qwen3.6:35b`, native reasoning default, unchanged questions/fixtures, no mocks. Four Python actions and four validated charts; **two analytical actions per case**, no rejections, no repairs, every original/snapshot/fixture hash unchanged. All 4 structural/numeric/chart checks pass. Total case time 418.06 seconds; this is a single run, not a reliability estimate.

| Dataset | Rows × columns | Time | Observed behavior and semantic review |
| --- | --- | --- | --- |
| Synthetic customers | 1,212 × 6 | 108.80s | **Qualified.** Correct A=1/B=13/C=0, medians 42/44/43 and useful box. It checked only age >106, omitting the lower <-20 boundary; there are no low extremes in this fixture, so matching numbers does not prove full method coverage. “Significantly” lacks a test; follow-up should include A's one exception. |
| Iris | 150 × 5 | 144.05s | **Pass.** Correct overall r=.9628 and within-species r=.3063/.7867/.3221, all medians and species-colored scatter. No causal claim or false error diagnosis. Correlation-strength adjectives are subjective; model confidence is uncalibrated. |
| Palmer penguins | 344 × 8 | 78.07s | **Qualified.** All missing-sex counts and denominator-based rates correct. Torgersen is 9.6% versus Biscoe 3.0%/Dream 0.8%; Gentoo 4.03% is essentially tied with Adelie 3.95%, so singling out Gentoo is misleading. Chart is column-level missingness, not group evidence. |
| Red wine quality | 1,599 × 12 | 87.14s | **Qualified; earlier causal failure fixed.** Correct duplicate counts/rates for all scores, including 8. Correctly describes similar rates in common scores 5–7 and makes no ingestion-cause claim. Broad no-concentration wording should be limited to well-represented groups; sparse groups need caution, and intentional repeated measurements should be named explicitly as an alternative. |

- Sol independently reviewed the question, code, computed output, chart and final text; main reviewed the same evidence. Semantic outcome: **one pass, three qualified passes, zero fails**. No false numerical final claim remains, but prose and method coverage still require review. Stored the qualifications in the artifact without rewriting the model outputs.
- Stopped prompt tuning after this general evidence correction; further optimizing these four fixtures would overstate broader reliability and exceed the requested small evaluation scope.
- Final post-change `make check`: **119 passed in 12.10s**, clean Ruff/ESLint, TypeScript/Vite build passed. Browser suite: **8 passed in 7.5s**. No application code changed after these checks.

## Final live browser acceptance and handoff

- The last browser check was initially blocked by automatic approval review because account usage was exhausted. After the user resumed, the same authorized check ran successfully. The prior delegated visual check had produced no new artifacts; main completed final visual QA directly in an isolated Chrome profile.
- Submitted a real free-form question through the visible text area and **Run investigation** button, observed live progress, then checked the final finding, source-colored box, expanded Python/result trace and Agent finding filter. Two analytical actions, no rejected actions, correct medians A=42/B=44/C=43 and counts above 106 A=1/B=13/C=0. No cause is asserted. Saved the complete browser-run evidence in `evaluations/browser-qwen3.6-35b-2026-09-15.json`.
- Inspected fresh laptop light/dark and mobile screenshots. Mobile has no horizontal overflow; column selection, actual rendered categorical chart and related findings work. Screenshots are in `/private/tmp/di-final-qa/` (temporary visual evidence); durable JSON results are committed in `evaluations/`.
- Final visual review found two presentation issues: missing favicon (confirmed HTTP 404), and hidden box-plot outlier markers. Fixed in `d122cf2`: local SVG favicon, visible outlier markers and a short explanation of box 1.5×IQR versus profiler 3×IQR thresholds. Added the marker assertion to the numeric-column regression. No backend/agent behavior changed.
- After those presentation changes, targeted live browser checks passed for both column and agent boxes (14 and 16 markers respectively; grouping changes quartiles), SVG returned HTTP 200, and there were **zero browser console/page errors**. Frontend lint, TypeScript and production build passed again. The eight-test suite ran before these final presentation fixes; their new marker assertion was also exercised directly against the running app without replacing the completed investigation.
- Final production bundle: application ~345 KB (~110 KB gzip), Plotly lazy chunk ~1.43 MB (~474 KB gzip). No cloud runtime services, database, cleaning/export actions, or additional agent phases were added.
- Git now records the original PRD, application, evaluation suite, evidence-guidance correction, presentation fixes and final results/documentation as separate reviewable checkpoints. Dependency caches, local configuration and generated build/browser output remain ignored. The original PRD is unchanged.
- Startup remains `OLLAMA_MODEL=qwen3.6:35b make dev` on this machine, or set an installed tag in `.env` and use `make dev`. Profiling also works without Ollama. Detailed setup, limits and verification commands are in `README.md`.
