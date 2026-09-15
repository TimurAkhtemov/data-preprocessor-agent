# Product Requirements Document: Local Dataset Investigator

## 1. Product Summary

Build a local-first web application that allows a user to upload a raw tabular dataset, automatically profile it for quality issues, and use a local LLM agent to autonomously investigate suspicious patterns by executing constrained Python analysis against the dataset.

The product should feel like a lightweight combination of:

- a data profiler,
- a data-quality linter,
- an exploratory data analysis assistant,
- and a local autonomous data analyst.

The application is **not** an AutoML platform and is **not** primarily a data-cleaning tool.

Its primary job is:

> **Tell me what looks suspicious in this dataset, investigate why it looks suspicious, and show me the evidence.**

The first version must be read-only with respect to the original dataset.

It may:

- analyze,
- filter,
- aggregate,
- compute statistics,
- identify suspicious patterns,
- execute analytical Python,
- generate validated visualizations,
- and recommend possible corrective actions.

It must not:

- silently modify the source data,
- overwrite uploaded files,
- apply cleaning transformations without user approval,
- or allow the LLM unrestricted access to the machine.

The application should run entirely on the user's local machine.

The local LLM is served through Ollama.

Primary target model:

- Qwen 3.6 35B-A3B
- or another local reasoning/coding model configured by the user.

The architecture must also remain usable with smaller models by keeping the agent loop bounded and the action space constrained.

---

# 2. Working Product Name

Use:

**Dataset Investigator**

throughout the UI.

Do not spend implementation time on branding, logos, or marketing assets.

A simple text-based product mark is sufficient.

---

# 3. Core Product Concept

A conventional data profiler can tell the user:

- `age` contains 14 statistical outliers,
- `state` contains 63 unique values,
- `income` is highly skewed,
- 218 rows are duplicated.

Dataset Investigator should go one step further.

After surfacing a suspicious pattern, the local LLM can investigate it by running controlled Python against the dataframe.

Example:

The profiler finds:

```text
age
14 extreme statistical observations
```

The agent decides to inspect the affected rows:

```python
result = df.loc[
    df["age"] > 120,
    ["age", "source_system"]
].head(50)
```

The result shows that most suspicious rows originate from one source system.

The agent then investigates further:

```python
result = (
    df.groupby("source_system")["age"]
    .agg(["count", "median", "max"])
    .reset_index()
)
```

It may then conclude:

> 13 of the 14 extreme age observations originate from source system B. The remainder of source B's age distribution is similar to the other sources, suggesting that the extreme values may represent a source-specific sentinel or ingestion issue rather than genuine observations.

The product therefore contains two analytical layers:

```text
Dataset
   │
   ▼
Deterministic Profiler
   │
   ├── schema
   ├── missingness
   ├── duplicates
   ├── distributions
   ├── cardinality
   ├── type inference
   └── heuristic anomaly detection
   │
   ▼
Potential Findings
   │
   ▼
LLM Investigator
   │
   ├── inspect findings
   ├── execute constrained Python
   ├── observe results
   ├── form hypotheses
   ├── test hypotheses
   └── request visualizations
   │
   ▼
Evidence-backed Finding
```

The deterministic system identifies:

> **What may be unusual?**

The LLM investigates:

> **Why may it be unusual?**

---

# 4. Primary Goals

The MVP must allow the user to:

1. Upload a CSV or Parquet file.
2. Immediately receive a deterministic dataset profile.
3. Understand dataset shape, structure, and basic health.
4. See automatically detected data-quality concerns.
5. Explore individual columns visually.
6. Click **Investigate** on any profiler finding.
7. Ask free-form analytical questions about the dataset.
8. Allow the local LLM to execute constrained Python analysis against the dataframe.
9. Show a compact investigation trace.
10. Allow the LLM to iteratively test hypotheses.
11. Receive a concise final explanation grounded in actual computed evidence.
12. Allow the agent to request relevant visualizations.
13. Keep all data and model activity local.
14. Preserve the original dataset without mutation.

---

# 5. Non-Goals

Do **not** implement the following in V1:

- automatic dataset cleaning
- automatic mutation of source data
- user-approved transformations
- AutoML
- machine-learning model training
- feature engineering pipelines
- target-specific leakage detection
- vector databases
- embeddings
- RAG
- persistent memory
- multi-file joins
- multi-dataset projects
- authentication
- user accounts
- cloud storage
- server-side database persistence
- multi-agent orchestration
- remote LLM APIs
- arbitrary shell access
- unrestricted filesystem access
- internet access for the LLM
- notebook generation
- PDF report generation
- Excel support
- complex deployment infrastructure
- SSR
- Next.js
- Electron packaging
- desktop packaging
- arbitrary model-generated frontend code
- arbitrary model-generated Plotly code

The V1 should remain intentionally focused.

---

# 6. Technical Architecture

Use a lightweight client/server architecture optimized for a polished local experience.

Architecture:

```text
┌─────────────────────────────────────┐
│         React / Vite Frontend       │
│                                     │
│ React                               │
│ TypeScript                          │
│ shadcn/ui                           │
│ Tailwind CSS                        │
│ Plotly                              │
│                                     │
│ Overview                            │
│ Findings                            │
│ Columns                             │
│ Investigator                        │
└───────────────────┬─────────────────┘
                    │
                    │ REST / streaming
                    │
┌───────────────────▼─────────────────┐
│             FastAPI Backend         │
│                                     │
│ Dataset lifecycle                   │
│ Deterministic profiler              │
│ Heuristic findings                  │
│ Agent orchestration                 │
│ Python execution worker             │
│ Ollama client                       │
│ Visualization validation            │
└───────────────────┬─────────────────┘
                    │
                    ▼
                 Ollama
                    │
                    ▼
             Local LLM model
```

---

# 7. Frontend Stack

Use:

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Lucide icons
- Plotly.js through a React integration

Do not use:

- Next.js
- Material UI
- Ant Design
- Chakra
- Bootstrap
- Streamlit
- NiceGUI
- Gradio
- Dash

The frontend should feel like a polished modern developer/data application rather than a Python dashboard.

---

# 8. Frontend Design Philosophy

The frontend should visually resemble:

- Linear
- Vercel
- Raycast
- modern observability tools
- modern developer dashboards
- polished data tooling

It should **not** resemble:

- an autogenerated admin dashboard,
- a default BI dashboard,
- a generic AI SaaS landing page,
- a Streamlit prototype,
- or a chat app.

Avoid:

- giant gradients,
- glowing AI effects,
- oversized headings,
- excessive cards,
- every element being rounded,
- decorative icon overload,
- generic chat bubbles,
- unnecessary sidebars,
- excessive whitespace,
- heavy shadows,
- marketing-style hero sections after upload.

Favor:

- restrained surfaces,
- subtle borders,
- compact spacing,
- strong typography hierarchy,
- intentional use of whitespace,
- clean charts,
- dense but readable analytical layouts.

---

# 9. shadcn/ui Usage

Use shadcn/ui as the primitive component system.

Use components where appropriate:

- Button
- Badge
- Tabs
- Dialog
- Sheet
- Tooltip
- Progress
- Separator
- Input
- Select
- Command
- Accordion
- Alert
- Skeleton
- ScrollArea
- Table
- Dropdown Menu
- Popover

Do not leave every shadcn component in its default example/demo appearance.

Compose them into an application-specific visual system.

---

# 10. Visual System

## Typography

Use:

- Inter,
- Geist,
- or a high-quality system sans-serif stack.

Use monospace only for:

- Python code,
- dtype labels,
- technical metadata,
- debugging output.

Do not use monospace for primary UI copy.

---

## Color

Default to a neutral palette.

Use semantic colors sparingly.

Suggested semantic treatment:

- High severity: red
- Medium severity: amber
- Low severity: muted blue/gray
- Healthy/connected: green
- Neutral/information: slate/gray

Severity should generally appear through:

- a small dot,
- a badge,
- subtle left border,
- icon,
- or compact label.

Do not color entire cards red or amber.

---

## Spacing

Use medium-density spacing suitable for analytical work.

The app should feel comfortable on:

- 13-inch laptop
- 14-inch laptop
- 16-inch laptop
- larger desktop displays

Avoid excessive dashboard padding.

---

## Borders and Shadows

Prefer subtle borders over large shadows.

Use shadows sparingly for:

- popovers,
- dialogs,
- sheets.

Main analytical surfaces should generally rely on:

- layout,
- whitespace,
- borders,
- typographic hierarchy.

---

## Border Radius

Use modest radius:

```text
6px–10px
```

Use pills primarily for:

- filters,
- chips,
- statuses,
- small badges.

---

## Dark Mode

Implement dark mode.

Respect the operating system theme by default.

Provide a compact theme toggle.

Both light and dark modes should be intentionally styled.

---

# 11. Backend Stack

Use:

- Python 3.11+
- FastAPI
- Pydantic
- pandas
- numpy
- pyarrow
- scipy

Optional:

- scikit-learn only if genuinely necessary for analytical functionality.

Pandas is the canonical dataframe representation used by the analysis agent:

```python
df
```

---

# 12. Local LLM Integration

Use Ollama.

Default configurable endpoint:

```text
http://localhost:11434
```

Configuration should support:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.6:35b-a3b
```

Do not hardcode a required exact model tag.

The model should be configurable through environment variables.

The frontend must never communicate directly with Ollama.

All Ollama requests go through the FastAPI backend.

---

# 13. Visualization Stack

Use Plotly in the React frontend.

The LLM must **never generate arbitrary Plotly or JavaScript code**.

The agent instead requests a validated chart specification.

Example:

```json
{
  "type": "histogram",
  "x": "age",
  "color": "source_system",
  "title": "Age distribution by source system"
}
```

The frontend converts that validated specification into a Plotly visualization.

For extremely simple visualizations, CSS or lightweight native rendering is acceptable if cleaner than Plotly.

Examples:

- severity count bars,
- progress indicators,
- percentages,
- tiny health indicators.

---

# 14. Repository Structure

Use approximately:

```text
dataset-investigator/
│
├── frontend/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── components.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       │
│       ├── api/
│       │   └── client.ts
│       │
│       ├── components/
│       │   ├── ui/
│       │   │
│       │   ├── layout/
│       │   │   ├── AppHeader.tsx
│       │   │   ├── DatasetHeader.tsx
│       │   │   └── DatasetTabs.tsx
│       │   │
│       │   ├── dataset/
│       │   │   ├── DatasetDropzone.tsx
│       │   │   ├── DatasetSummary.tsx
│       │   │   ├── DataHealthSummary.tsx
│       │   │   └── ProfilingProgress.tsx
│       │   │
│       │   ├── findings/
│       │   │   ├── FindingRow.tsx
│       │   │   ├── FindingList.tsx
│       │   │   ├── FindingDetails.tsx
│       │   │   └── SeverityBadge.tsx
│       │   │
│       │   ├── columns/
│       │   │   ├── ColumnPicker.tsx
│       │   │   ├── ColumnSummary.tsx
│       │   │   ├── ColumnStats.tsx
│       │   │   └── ColumnChart.tsx
│       │   │
│       │   ├── investigation/
│       │   │   ├── InvestigatorInput.tsx
│       │   │   ├── InvestigationSuggestions.tsx
│       │   │   ├── InvestigationProgress.tsx
│       │   │   ├── InvestigationTrace.tsx
│       │   │   ├── InvestigationResult.tsx
│       │   │   └── AgentChart.tsx
│       │   │
│       │   └── charts/
│       │       └── ChartRenderer.tsx
│       │
│       ├── pages/
│       │   ├── UploadView.tsx
│       │   └── DatasetView.tsx
│       │
│       ├── hooks/
│       │   ├── useDataset.ts
│       │   └── useInvestigation.ts
│       │
│       ├── types/
│       │   └── api.ts
│       │
│       └── lib/
│           └── utils.ts
│
├── backend/
│   ├── pyproject.toml
│   │
│   └── dataset_investigator/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── models.py
│       │
│       ├── api/
│       │   ├── datasets.py
│       │   ├── investigations.py
│       │   └── health.py
│       │
│       ├── data/
│       │   ├── loader.py
│       │   ├── profiler.py
│       │   ├── heuristics.py
│       │   └── serialization.py
│       │
│       ├── agent/
│       │   ├── client.py
│       │   ├── investigator.py
│       │   ├── prompts.py
│       │   ├── schemas.py
│       │   └── parser.py
│       │
│       ├── execution/
│       │   ├── sandbox.py
│       │   ├── validator.py
│       │   └── worker.py
│       │
│       └── visualization/
│           ├── schemas.py
│           └── validation.py
│
├── tests/
│   ├── test_profiler.py
│   ├── test_heuristics.py
│   ├── test_code_validator.py
│   ├── test_serialization.py
│   └── fixtures/
│
├── examples/
│   └── suspicious_customers.csv
│
├── scripts/
│   └── dev.sh
│
├── Makefile
├── README.md
├── .gitignore
└── .env.example
```

Do not overengineer the repository purely to match this layout.

The important separation is:

- frontend
- API
- profiling
- agent orchestration
- code execution
- visualization validation

Do not add:

- Redux unless truly required,
- dependency injection frameworks,
- repository patterns,
- unnecessary service layers,
- event buses,
- microservices.

---

# 15. Local Development

Provide a convenient command:

```bash
make dev
```

or:

```bash
./scripts/dev.sh
```

It should start:

- FastAPI backend
- Vite frontend

The README should also document starting each independently.

Preferred frontend package manager:

```text
pnpm
```

Preferred Python package workflow:

```text
uv
```

---

# 16. Initial Application State

When the app opens, show a clean upload experience.

Suggested composition:

```text
                    Dataset Investigator

          Understand what's actually in your data.

    Profile structure, surface suspicious patterns,
   and investigate them with a local AI data analyst.


       ┌──────────────────────────────────────────┐
       │                                          │
       │                    ↑                     │
       │                                          │
       │          Drop a dataset here             │
       │                                          │
       │       CSV or Parquet · up to 250 MB      │
       │                                          │
       │              Browse files                │
       │                                          │
       └──────────────────────────────────────────┘


            ● Ollama connected
            qwen3.6:35b-a3b
```

The dropzone should support:

- click to upload,
- drag and drop,
- drag-over visual state,
- file validation.

Do not make the initial screen a large marketing landing page.

---

# 17. Ollama Status

Always show local model status.

Connected:

```text
● Ollama connected
qwen3.6:35b-a3b
```

Disconnected:

```text
○ Ollama unavailable
qwen3.6:35b-a3b
```

Profiling must still work without Ollama.

---

# 18. Upload Handling

Supported file types:

```text
.csv
.parquet
```

Maximum upload size:

```text
250 MB
```

Provide helpful errors for:

- malformed CSV,
- invalid Parquet,
- empty file,
- empty dataset,
- dataset with no columns,
- unsupported extension,
- file over size limit,
- parse failure.

CSV decoding fallback order:

```text
utf-8
utf-8-sig
latin-1
```

Do not build a complex encoding detection system.

---

# 19. Profiling Loading State

After upload, do not show a blank page.

Show actual profiling phases where practical:

```text
Profiling customers.csv

✓ Loaded 84,291 rows
✓ Inferred column types
✓ Calculated distributions
● Detecting suspicious patterns
```

Use skeleton loading for sections that are not ready yet.

Do not fake exact percentages unless meaningful.

---

# 20. Main Application Shell

Once profiling is complete:

```text
┌─────────────────────────────────────────────────────────────────┐
│ Dataset Investigator                           ● Ollama online  │
├─────────────────────────────────────────────────────────────────┤
│ customers.csv                                  84,291 × 27      │
│                                                                 │
│ Overview     Findings 7     Columns     Investigator             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                         ACTIVE VIEW                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Do not use a permanent sidebar in V1.

Use horizontal navigation.

Primary views:

```text
Overview
Findings
Columns
Investigator
```

---

# 21. Dataset Session State

Maintain one active dataset per local app/browser session.

State should include:

- uploaded filename,
- temporary file path,
- dataframe snapshot,
- dataset profile,
- profiler findings,
- agent findings,
- investigation history,
- Ollama status.

Loading another dataset should clear current dataset state.

Do not persist state between application restarts in V1.

---

# 22. Overview Tab

The Overview tab gives a high-level health summary.

---

## 22.1 Dataset Summary

Use one strong summary row rather than excessive cards.

Example:

```text
Dataset health

84,291          27             3.7%            218
Rows            Columns        Missing          Duplicates
```

Optional fifth metric:

```text
41.3 MB
Memory
```

Optional sixth:

```text
7
Issues
```

Use subtle dividers.

---

## 22.2 Column Type Summary

Display inferred types:

```text
Numeric        14
Categorical     9
Datetime        3
Boolean         1
```

A chart is not necessary unless it meaningfully improves the UI.

---

## 22.3 Missingness Visualization

Display a horizontal bar chart of columns containing missing values.

Requirements:

- only columns with missing data,
- sort descending,
- use percentages,
- top 30 maximum,
- if more than 30 columns contain missing data, display:

> Showing 30 columns with the highest missingness.

---

## 22.4 Dataset Health Summary

Display severity counts:

```text
2 High
3 Medium
2 Low
```

Do not use large colorful cards.

A compact visual indicator is preferable.

---

## 22.5 Needs Attention

Display the highest-priority findings.

Example:

```text
Needs attention

HIGH     age
14 extreme statistical observations
                                        Investigate →

HIGH     state
Several raw labels normalize to the same value
                                        Investigate →

MEDIUM   customer_id
Nearly unique across the dataset
                                        Investigate →
```

Show approximately the top five.

---

# 23. Deterministic Dataset Profiler

The deterministic profiler must run before any LLM analysis.

It must not depend on Ollama.

Produce a structured `DatasetProfile`.

---

# 24. Dataset Profile Schema

Use Pydantic models.

Suggested structure:

```python
class DatasetProfile(BaseModel):
    file_name: str
    row_count: int
    column_count: int
    memory_bytes: int

    duplicate_rows: int
    duplicate_ratio: float

    missing_cells: int
    missing_ratio: float

    sampled: bool
    sample_size: int | None

    columns: list["ColumnProfile"]
    findings: list["ProfilerFinding"]
```

Column profile:

```python
class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    pandas_dtype: str

    non_null_count: int
    missing_count: int
    missing_ratio: float

    unique_count: int
    unique_ratio: float

    sample_values: list

    numeric_stats: NumericStats | None = None
    categorical_stats: CategoricalStats | None = None
    datetime_stats: DatetimeStats | None = None
```

---

# 25. Type Inference

Do not blindly trust Pandas dtypes.

Infer:

- numeric,
- categorical,
- datetime,
- boolean,
- identifier-like,
- unknown.

For object/string columns, test whether values appear to represent:

- numbers,
- datetimes,
- booleans,
- true text/categories.

Example rule:

If more than 90% of non-null strings can convert to numeric while the column is stored as string:

```text
Potential numeric column stored as text.
```

Do similarly for dates.

---

# 26. Numeric Profiling

For numeric columns calculate:

- count
- non-null count
- missing count
- missing ratio
- unique count
- unique ratio
- minimum
- maximum
- mean
- median
- standard deviation
- first quartile
- third quartile
- IQR
- 1st percentile
- 99th percentile
- skewness
- zero count
- negative count

Calculate standard IQR outliers:

```text
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
```

Calculate extreme outliers:

```text
lower_extreme = Q1 - 3 * IQR
upper_extreme = Q3 + 3 * IQR
```

Track:

- standard outlier count,
- extreme outlier count,
- ratios.

Do not label statistical outliers as invalid data.

Use:

> 37 extreme statistical outliers detected.

Not:

> 37 bad values detected.

---

# 27. Categorical Profiling

For categorical/string columns calculate:

- unique count,
- unique ratio,
- top 10 raw values,
- counts,
- blank-string count,
- average string length,
- maximum string length.

Normalize strings temporarily for anomaly detection using:

1. trim leading/trailing whitespace,
2. lowercase,
3. collapse repeated whitespace.

Example:

```text
"New York"
" new york "
"NEW YORK"
```

becomes:

```text
new york
```

If multiple raw values collapse to one normalized representation, create a category consistency finding.

Do not automatically modify the values.

---

# 28. Datetime Profiling

For datetime-like columns calculate:

- non-null count,
- missing ratio,
- earliest timestamp,
- latest timestamp,
- unique count,
- approximate date span.

If object/string values are strongly datetime-like but stored as text, create a type mismatch finding.

---

# 29. Identifier Detection

Flag a column as potentially identifier-like when:

```text
row_count >= 50
AND
unique_ratio >= 0.98
```

Avoid applying this blindly to continuous floating-point measurements.

Consider:

- column name,
- discreteness,
- dtype,
- value patterns.

Examples likely to flag:

```text
customer_id
transaction_id
uuid
order_number
```

Finding wording:

> Column is nearly unique across rows and may function as an identifier.

Severity:

- generally Low or Medium.

---

# 30. Constant and Near-Constant Detection

Constant:

```text
unique_count <= 1
```

Near constant:

```text
most_common_value_ratio >= 0.99
```

Flag both.

---

# 31. Duplicate Detection

Calculate exact duplicate rows where practical.

Suggested severity:

```text
duplicate_ratio == 0:
    no finding

duplicate_ratio < 0.01:
    low

duplicate_ratio < 0.05:
    medium

otherwise:
    high
```

---

# 32. Missingness Detection

Suggested severity thresholds:

```text
< 1%       no finding / informational
1–5%       low
5–30%      medium
> 30%      high
```

Do not state that missing values are inherently invalid.

Use wording like:

> 37.2% of values are missing in this column.

---

# 33. Statistical Distribution Warnings

## High Skew

If:

```text
abs(skewness) > 2
```

create a Low or Medium finding.

---

## Extreme Outlier Concentration

If:

```text
extreme_outlier_ratio > 0.01
```

create a Medium finding.

---

## Large Max-to-P99 Gap

If the maximum is dramatically separated from the 99th percentile, consider a suspicious extreme-value finding.

Do not encode semantic assumptions like:

```text
age < 120
```

inside deterministic heuristics unless explicitly supplied by the user.

The profiler must remain domain-agnostic.

---

# 34. Finding Data Model

Use:

```python
class ProfilerFinding(BaseModel):
    id: str

    severity: Literal[
        "high",
        "medium",
        "low"
    ]

    category: str

    title: str
    description: str

    columns: list[str]

    evidence: dict

    source: Literal["profiler"] = "profiler"
```

Possible categories:

```text
missingness
duplicates
outliers
type_mismatch
identifier
constant
near_constant
categorical_consistency
skew
cardinality
```

Each finding must have a stable generated ID.

---

# 35. Findings Tab

Display findings in a compact list rather than a card grid.

Example:

```text
Findings                                          7 issues

[All] [High 2] [Medium 3] [Low 2]       [Source ▾]


● HIGH
Extreme statistical values in age
14 observations exceed the extreme IQR boundary.

age                                            Investigate →


● MEDIUM
Possible inconsistent categories in state
63 raw labels collapse to 48 normalized labels.

state                                          Investigate →


● MEDIUM
customer_id appears identifier-like
99.99% of non-null values are unique.

customer_id                                    Investigate →
```

---

# 36. Findings Filters

Support:

Severity:

```text
All
High
Medium
Low
```

Source:

```text
All
Profiler
Agent
```

Potential category filter is optional.

---

# 37. Finding Details

Clicking a finding should open a right-side Sheet or clean expanded detail panel.

Prefer a Sheet.

Show:

- severity,
- source,
- title,
- full description,
- affected columns,
- evidence,
- numerical values,
- recommended investigation,
- **Investigate** action.

Agent findings should additionally show:

- confidence,
- evidence,
- recommendation,
- trace,
- chart if present.

---

# 38. Columns Tab

Use a two-pane layout on larger displays.

Example:

```text
┌────────────────────┬─────────────────────────────────────────┐
│ Columns            │ age                                     │
│                    │ Numeric · 14 missing · 72 unique       │
│ Search...          │                                         │
│                    │ Min   Q1   Median   Mean   Q3   Max    │
│ age              → │ 18    31   42       43.7   55   999    │
│ balance            │                                         │
│ customer_id        │ [ Histogram                           ]  │
│ income             │                                         │
│ signup_date        │ Potential issues                        │
│ source_system      │ ● 14 extreme statistical values        │
│ state              │                                         │
└────────────────────┴─────────────────────────────────────────┘
```

On narrow screens, replace the left pane with a searchable combobox.

---

# 39. Column Search

Provide a fast searchable column selector.

Search by:

- column name,
- optionally inferred type.

Do not render hundreds of columns at once unnecessarily.

---

# 40. Column Header

Example:

```text
age

Numeric
84,277 non-null
14 missing
72 unique
```

---

# 41. Numeric Column Statistics

Show:

```text
Min
Q1
Median
Mean
Q3
Max
Std
Skew
Missing
Unique
```

Do not over-format with separate cards for every statistic.

Use a compact metric grid.

---

# 42. Categorical Column Statistics

Show:

```text
Unique values
Missing
Most common value
Most common frequency
Blank strings
Average string length
Maximum string length
```

---

# 43. Automatic Column Visualizations

Choose chart type deterministically.

Numeric:

- histogram,
- optionally box plot.

Categorical:

- top-value bar chart.

Datetime:

- count over time when sensible.

Boolean:

- simple value-count bar chart.

Identifier-like:

- do not chart every value,
- show uniqueness metrics instead.

---

# 44. Column-Level Findings

Below the visualization show findings related to that column.

Example:

```text
Potential issues

● 14 extreme statistical values
● Distribution is highly right-skewed
```

Each can be opened or investigated.

---

# 45. Investigator Tab

The Investigator should feel like an analytical workspace, not a chatbot.

Do not use alternating speech bubbles.

Suggested composition:

```text
Investigate this dataset

┌──────────────────────────────────────────────────────────────┐
│ Ask a question about the data...                             │
│                                                              │
│ Why does age have extreme values?                            │
│                                                    [Run →]   │
└──────────────────────────────────────────────────────────────┘

Suggestions

[Investigate age outliers]
[Check state categories]
[Explain duplicate rows]
```

---

# 46. Suggested Investigation Questions

Generate suggestions from current findings.

Examples:

```text
Investigate extreme values in age
Check whether state labels are inconsistent
Explain where duplicate rows come from
Determine whether income outliers are segment-specific
Check why signup_date has missing values
```

Suggestions should be deterministic based on findings.

Do not require the LLM to generate suggestion chips.

---

# 47. Starting an Investigation

When the user clicks:

```text
Investigate
```

or submits a free-form question:

1. disable repeated submissions,
2. begin an investigation,
3. show progress,
4. stream or update step progress,
5. render final result.

Do not freeze the interface.

---

# 48. Investigation Progress UI

Example:

```text
Investigating age outliers                               3 / 5

✓ Inspected extreme observations
✓ Compared source systems
● Checking whether 999 behaves like a sentinel value

─────────────────────────────────────────────────────────────

Current evidence

13 of 14 extreme age observations originate from source B.

[View Python]
```

Do not expose chain-of-thought.

The UI may display concise tool rationale such as:

> Compare extreme values across source systems.

Do not display hidden reasoning.

---

# 49. Investigation Trace

After completion, expose:

```text
View investigation trace
```

Collapsed by default.

Each step may show:

```text
Step 1

Action
Run Python

Purpose
Inspect whether extreme age values are concentrated in a source.

Python
df.loc[df["age"] > 120].groupby("source_system").size()

Result
source_system
A     1
B    13
```

The purpose field should contain a concise action rationale, not detailed reasoning.

---

# 50. Agent Loop

Maximum analytical steps:

```text
5
```

Allowed actions:

```text
run_python
request_chart
finish
```

One action per model response.

A sixth model call may be used only to force summarization if the agent reaches the five-step limit without finishing.

Never permit an indefinite loop.

---

# 51. Agent Workflow

The loop should be:

```text
Initial context
      │
      ▼
Model chooses action
      │
      ├── run_python
      │      │
      │      ▼
      │   execute safely
      │      │
      │      ▼
      │   return result
      │
      ├── request_chart
      │      │
      │      ▼
      │   validate chart
      │      │
      │      ▼
      │   render/store chart
      │
      └── finish
             │
             ▼
        final finding
```

---

# 52. Agent Action Protocol

Every model response must be structured JSON.

Do not allow unstructured agent instructions.

---

## Run Python

Example:

```json
{
  "action": "run_python",
  "reason": "Check whether extreme age values are concentrated in one source system.",
  "code": "result = df.loc[df['age'] > 120].groupby('source_system').size().reset_index(name='count')"
}
```

---

## Request Chart

Example:

```json
{
  "action": "request_chart",
  "reason": "A grouped histogram would show whether the unusual values are concentrated in one ingestion source.",
  "chart": {
    "type": "histogram",
    "x": "age",
    "color": "source_system",
    "title": "Age distribution by source system"
  }
}
```

---

## Finish

Example:

```json
{
  "action": "finish",
  "finding": {
    "title": "Extreme age values are concentrated in source system B",
    "severity": "high",
    "summary": "Most extreme age observations originate from one ingestion source, suggesting a source-specific encoding issue rather than a dataset-wide pattern.",
    "evidence": [
      "13 of 14 extreme age observations originate from source system B.",
      "Source system B otherwise has a similar median age to the other sources.",
      "The maximum age in source B is 999."
    ],
    "recommended_action": "Inspect how source system B represents unknown or missing ages before removing or imputing the affected rows.",
    "confidence": 0.91,
    "related_columns": [
      "age",
      "source_system"
    ]
  }
}
```

---

# 53. Agent System Prompt

Use a system prompt close to:

```text
You are a local dataset investigation agent.

Your job is to investigate suspicious patterns in a Pandas dataframe named `df`.

You are not a generic chatbot.

You must ground conclusions in evidence obtained from the dataset.

You may execute Python to test hypotheses.

Do not assume unusual values are incorrect merely because they are statistically unusual.

Distinguish clearly between:
- observed evidence,
- plausible interpretation,
- speculation.

Use as few analytical steps as necessary.

You have a maximum of 5 analytical steps.

You may choose exactly one action per response:
- run_python
- request_chart
- finish

When executing Python:
- the dataframe is available as `df`
- pandas is available as `pd`
- numpy is available as `np`
- scipy.stats is available as `stats`
- do not import modules
- do not access files
- do not access the network
- do not access the operating system
- do not use shell commands
- do not modify the source dataset
- assign the final value you want to inspect to a variable named `result`

Prefer aggregated outputs over large collections of raw rows.

Do not generate visualization code.

Request visualizations using the chart action.

Finish when the available evidence is sufficient.

Do not provide hidden chain-of-thought or extended reasoning.
Use short action rationales only.
```

---

# 54. Initial Context Given to Agent

Provide:

- investigation question,
- selected profiler finding if applicable,
- dataset dimensions,
- column names,
- inferred column types,
- relevant column profiles,
- profiler evidence,
- sample values where useful,
- sampling status.

Do not dump the full dataset into the model prompt.

Example:

```text
Dataset:
84,291 rows × 27 columns

Relevant columns:

age
- inferred type: numeric
- missing: 14
- min: 18
- median: 42
- max: 999
- Q1: 31
- Q3: 55
- skew: 8.31

source_system
- inferred type: categorical
- unique values: 3
- top values:
  A: 42,871
  B: 30,191
  C: 11,229

Profiler finding:
The age column contains 14 extreme statistical outliers.
```

---

# 55. Ollama Client

Create a small centralized Ollama client.

Responsibilities:

- health check,
- model availability,
- chat completion,
- JSON response handling,
- timeout handling,
- error reporting.

Suggested interface:

```python
class OllamaClient:

    def health_check(self) -> bool:
        ...

    def list_models(self) -> list[str]:
        ...

    def chat(
        self,
        messages: list[dict],
    ) -> str:
        ...
```

Do not spread Ollama HTTP calls throughout the codebase.

---

# 56. Structured Output Parsing

Prefer Ollama structured JSON functionality where supported.

However, do not assume perfect model compliance.

Parsing procedure:

1. attempt direct JSON parse,
2. if necessary extract the outermost JSON object,
3. validate using Pydantic,
4. if validation fails, make one repair request.

Repair prompt:

```text
Your response did not match the required JSON schema.

Return only valid JSON matching this schema:
...
```

If repair fails:

- terminate investigation gracefully,
- show an understandable error.

Do not endlessly retry.

---

# 57. Agent State

Use:

```python
class InvestigationState(BaseModel):
    investigation_id: str
    question: str

    steps_remaining: int

    messages: list[dict]

    trace: list["InvestigationStep"]

    charts: list["ChartSpec"]

    final_finding: "AgentFinding | None"
```

---

# 58. Investigation Step Model

Use:

```python
class InvestigationStep(BaseModel):
    number: int

    action: str
    reason: str

    code: str | None = None
    result_summary: str | None = None
    error: str | None = None
```

---

# 59. Agent Finding Model

Use:

```python
class AgentFinding(BaseModel):
    title: str

    severity: Literal[
        "high",
        "medium",
        "low"
    ]

    summary: str

    evidence: list[str]

    recommended_action: str

    confidence: float

    related_columns: list[str]

    source: Literal["agent"] = "agent"
```

Clamp:

```text
confidence ∈ [0, 1]
```

Confidence must be visually labeled as:

```text
Model confidence
```

or:

```text
Self-assessed confidence
```

Do not imply statistical calibration.

---

# 60. Python Analysis Capability

The agent should have substantial analytical freedom.

Allowed examples:

```python
result = df.groupby("source_system")["age"].describe()
```

```python
result = df.loc[
    df["age"] > df["age"].quantile(0.99)
].head(30)
```

```python
result = pd.crosstab(
    df["state"],
    df["source_system"]
)
```

```python
result = df[
    ["income", "age", "balance"]
].corr()
```

```python
result = (
    df.assign(
        state_normalized=df["state"]
            .str.strip()
            .str.lower()
    )
    .groupby("state_normalized")["state"]
    .nunique()
    .sort_values(ascending=False)
    .head(20)
)
```

This flexibility is a core product feature.

---

# 61. Python Execution Security Model

Treat all model-generated code as untrusted.

Never execute generated code directly inside the FastAPI process.

Use a separate child process / subprocess worker.

The security goal is:

> reduce accidental and obvious malicious execution risk.

Do not claim the sandbox is suitable for hostile adversarial code.

---

# 62. Code Validation

Before execution:

```python
tree = ast.parse(code)
```

Reject:

- `Import`
- `ImportFrom`
- dangerous function calls,
- suspicious attributes,
- shell access,
- filesystem access,
- networking,
- package loading.

Block names/references including:

```text
os
sys
subprocess
socket
pathlib
shutil
requests
httpx
urllib
builtins
importlib
pickle
marshal
ctypes
```

Block builtins:

```text
open
exec
eval
compile
__import__
globals
locals
vars
input
```

Reject dunder attribute access:

```text
__class__
__dict__
__subclasses__
__globals__
```

More generally reject attribute names beginning with:

```text
__
```

---

# 63. Allowed Execution Environment

Expose:

```python
df
pd
np
stats
```

Potential safe builtins:

```text
len
min
max
sum
sorted
round
abs
enumerate
range
list
dict
set
tuple
```

Add safe builtins deliberately if necessary.

Do not expose all Python builtins.

---

# 64. Dataset Isolation

The source dataframe must not be mutated.

Preferred design:

1. upload dataset,
2. create canonical temporary Parquet snapshot,
3. execution worker loads the snapshot,
4. worker creates:

```python
df = source_df.copy(deep=True)
```

5. generated code runs against the isolated copy,
6. worker exits after execution.

Do not rely only on Python conventions to prevent mutation.

---

# 65. Execution Limits

Per Python execution:

```text
timeout: 10 seconds
```

Maximum text result:

```text
12,000 characters
```

Maximum tabular result:

```text
50 rows
20 columns
```

If larger:

- truncate,
- tell the model it was truncated.

Example:

```text
Result truncated to first 50 of 8,412 rows.
```

---

# 66. Result Serialization

Support:

- scalar,
- string,
- dict,
- list,
- Series,
- DataFrame,
- NumPy scalar,
- NumPy array.

Example dataframe serialization:

```text
DataFrame: 3 rows × 4 columns

source_system | count | median | max
A             | 42871 | 42     | 91
B             | 30191 | 43     | 999
C             | 11229 | 41     | 87
```

Include:

- shape,
- truncation state,
- column names.

Do not send large Python repr output to the LLM.

---

# 67. Execution Error Handling

If code fails, return a structured error to the agent.

Example:

```text
Execution failed.

Exception:
KeyError: 'source'

Available columns include:
source_system
age
income
state
...
```

A failed execution consumes one step.

The model may correct its code.

If three executions fail consecutively:

terminate the investigation.

Display:

> The local model was unable to complete this investigation reliably.

---

# 68. Chart Specification

Allowed chart types:

```text
histogram
box
bar
scatter
line
missingness
```

Use:

```python
class ChartSpec(BaseModel):
    type: Literal[
        "histogram",
        "box",
        "bar",
        "scatter",
        "line",
        "missingness"
    ]

    x: str | None = None
    y: str | None = None
    color: str | None = None

    title: str

    top_n: int | None = None
```

---

# 69. Chart Validation

Before rendering:

- verify referenced columns exist,
- verify chart type is compatible with column types,
- clamp `top_n <= 30`,
- reject invalid schemas,
- reject invalid column names.

Do not crash on malformed chart requests.

Return the validation failure to the agent.

---

# 70. Chart Rendering

Use Plotly in the frontend.

Examples:

Histogram:

```text
histogram
```

Box:

```text
box plot
```

Scatter:

```text
scatter
```

Bar:

aggregate counts first where appropriate.

Missingness:

show percent missing by column.

Do not allow the model to choose arbitrary colors.

Use application theme defaults.

---

# 71. Agent-Generated Chart UX

When a chart is requested:

```text
Visualization

Age distribution by source system

[Plotly chart]

Why this helps
Shows whether unusual age values are concentrated in a particular ingestion source.
```

Charts should remain visible with the final result.

---

# 72. Final Investigation Result

Example UI:

```text
HIGH                                      91% model confidence

Extreme age values are concentrated in source system B

Most extreme age observations originate from one ingestion source,
suggesting a source-specific encoding issue rather than a dataset-wide
pattern.

Evidence

• 13 of 14 extreme observations originate from source B.
• Source B has a median age similar to other sources.
• Source B contains a maximum age value of 999.

Recommendation

Inspect how source B represents missing or unknown age values before
dropping or imputing the affected rows.

[View investigation trace]
```

---

# 73. Free-Form Questions

Support questions such as:

> Which columns have suspicious relationships?

> Are duplicate records concentrated in one customer segment?

> Why is revenue so skewed?

> Does source system B look systematically different?

> Are there inconsistent values in state?

> Is one source responsible for most missing values?

The agent should use Python whenever the question can be tested empirically.

It should not answer based only on intuition.

---

# 74. Large Dataset Behavior

For datasets larger than:

```text
200,000 rows
```

use a deterministic random sample of up to:

```text
100,000 rows
```

for expensive operations such as:

- skewness,
- categorical normalization checks,
- visualization,
- expensive distribution analysis.

Still calculate exact where feasible:

- row count,
- column count,
- missing counts,
- basic dtype info.

For duplicate calculations, use exact if reasonable; otherwise document approximation.

Expose:

```text
Distribution statistics estimated from a 100,000-row sample.
```

The agent must be told when a result is based on sampled data.

---

# 75. Performance Targets

For:

```text
100,000 rows × 30 columns
```

Target deterministic profiling:

```text
< 5 seconds
```

excluding upload time.

Agent Python execution:

```text
<= 10 seconds per step
```

UI must remain responsive during investigation.

---

# 76. Concurrency

Allow one investigation at a time per dataset/session.

If an investigation is active:

```text
Investigation in progress
```

Disable starting another.

Do not build:

- queues,
- parallel agents,
- task workers,
- Celery,
- Redis.

---

# 77. Graceful Ollama Failure

If Ollama is unavailable:

- Overview still works,
- Findings still works,
- Columns still works.

Disable investigation actions.

Display:

```text
Local AI investigator unavailable

Start Ollama and ensure the configured model is installed.

Configured model:
qwen3.6:35b-a3b
```

Do not crash.

---

# 78. API Design

Keep the API small.

Suggested endpoints:

```text
GET  /api/health
GET  /api/ollama/status

POST /api/datasets
GET  /api/datasets/current
GET  /api/datasets/profile

POST /api/investigations
GET  /api/investigations/{id}
```

Optional:

```text
GET /api/investigations/{id}/events
```

for streaming progress.

Use Server-Sent Events or another simple streaming mechanism if useful.

Do not introduce WebSockets unless necessary.

---

# 79. Dataset Upload API

Example:

```text
POST /api/datasets
multipart/form-data
```

Response:

```json
{
  "dataset_id": "uuid",
  "file_name": "customers.csv",
  "rows": 84291,
  "columns": 27,
  "profile": {}
}
```

If profiling is asynchronous within the request lifecycle, return state accordingly.

Avoid unnecessary background infrastructure.

---

# 80. Investigation API

Request:

```json
{
  "question": "Why does age have extreme values?",
  "finding_id": "optional-finding-id"
}
```

Response:

```json
{
  "investigation_id": "uuid",
  "status": "running"
}
```

Frontend can poll or subscribe to progress.

---

# 81. Investigation Status

Possible states:

```text
idle
running
completed
failed
```

---

# 82. Configuration

Create:

```text
.env.example
```

Include:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.6:35b-a3b

MAX_UPLOAD_MB=250

AGENT_MAX_STEPS=5
AGENT_CODE_TIMEOUT_SECONDS=10

LARGE_DATASET_ROW_THRESHOLD=200000
PROFILE_SAMPLE_ROWS=100000
```

Provide sane defaults if `.env` is absent.

---

# 83. Logging

Use standard Python logging.

Log:

- application startup,
- dataset upload,
- dataset parse,
- profile completion,
- profiler duration,
- Ollama status,
- investigation start,
- each tool action type,
- execution failures,
- investigation completion.

Do not log:

- entire datasets,
- thousands of rows,
- secrets,
- full model prompts unless debug logging explicitly enabled.

---

# 84. Frontend Error States

Implement clear error states for:

- upload failure,
- parse failure,
- backend disconnected,
- Ollama disconnected,
- model missing,
- malformed model response,
- Python execution rejection,
- Python timeout,
- chart validation failure,
- investigation failure.

Avoid raw stack traces in primary UI.

Provide technical details in an expandable section where useful.

---

# 85. Backend Error Handling

Use structured API errors.

Example:

```json
{
  "code": "OLLAMA_UNAVAILABLE",
  "message": "Could not connect to Ollama.",
  "details": null
}
```

Do not return raw Python tracebacks to frontend users.

Log traces server-side.

---

# 86. Demo Dataset

Include a synthetic example dataset with:

```text
customer_id
age
state
income
source_system
signup_date
```

Intentionally include:

- age value `999`,
- values like:
  - `NY`
  - `ny`
  - `NY `
- missing income,
- duplicated rows,
- nearly unique customer IDs,
- highly skewed income,
- source-specific anomaly,
- some missing signup dates.

This should demonstrate the main flow.

---

# 87. Tests

Implement meaningful unit tests.

---

## Profiler Tests

Test:

- missingness,
- duplicates,
- numeric stats,
- categorical stats,
- normalization,
- identifier detection,
- constant detection,
- near-constant detection,
- numeric-as-string detection,
- datetime-as-string detection,
- skew detection,
- outlier detection.

---

## Code Validator Tests

Must reject:

```python
import os
```

```python
open("/etc/passwd")
```

```python
__import__("os")
```

```python
df.__class__
```

```python
eval("1+1")
```

```python
import subprocess
```

Must allow:

```python
result = df.groupby("category")["value"].mean()
```

```python
result = df["value"].quantile([0.01, 0.5, 0.99])
```

```python
result = pd.crosstab(df["state"], df["source_system"])
```

---

## Serialization Tests

Test:

- scalar,
- DataFrame,
- Series,
- long string,
- row truncation,
- column truncation,
- NumPy values,
- exception output.

---

## Agent Parsing Tests

Test:

- valid run_python action,
- valid request_chart action,
- valid finish action,
- malformed JSON,
- wrong action,
- missing field,
- confidence out of range.

---

## Chart Validation Tests

Test:

- missing column,
- invalid chart type,
- invalid numeric requirement,
- valid histogram,
- valid bar,
- valid scatter.

---

# 88. README Requirements

README should contain:

## Overview

Short explanation of the product.

---

## Requirements

- Python 3.11+
- Node
- pnpm
- Ollama
- local model

---

## Install Backend

Prefer:

```bash
cd backend
uv sync
```

---

## Install Frontend

```bash
cd frontend
pnpm install
```

---

## Run

Preferred:

```bash
make dev
```

or:

```bash
./scripts/dev.sh
```

---

## Configure Model

Example:

```bash
OLLAMA_MODEL=my-model make dev
```

---

## Security Note

Include:

> Model-generated analytical Python is executed in a restricted child process with AST validation and resource limits. This reduces risk but should not be considered a hardened security sandbox suitable for hostile code.

---

# 89. Recommended Implementation Sequence

Implement in this order.

## Phase 1 — Backend Foundation

Build:

- repository structure,
- configuration,
- dataset loader,
- profile schemas,
- deterministic profiler,
- heuristic findings,
- profiler tests.

Do not implement the agent yet.

---

## Phase 2 — Frontend Shell

Build:

- React/Vite setup,
- shadcn setup,
- theme,
- upload screen,
- dataset shell,
- Overview tab,
- Findings tab,
- Columns tab,
- charts.

At the end of this phase, the app should already be useful without AI.

---

## Phase 3 — Ollama Integration

Build:

- Ollama client,
- health status,
- model configuration,
- structured output parsing,
- agent schemas,
- agent prompt.

---

## Phase 4 — Python Execution

Build:

- AST validation,
- worker process,
- execution timeout,
- isolation,
- result serialization,
- tests.

---

## Phase 5 — Agent Loop

Build:

- investigation state,
- run_python action,
- request_chart action,
- finish action,
- five-step limit,
- retries,
- error handling.

---

## Phase 6 — Investigator UI

Build:

- free-form question input,
- suggestion chips,
- progress display,
- trace,
- agent result,
- agent chart rendering,
- Ollama-unavailable state.

---

## Phase 7 — Polish

Finish:

- dark mode,
- responsive layouts,
- empty states,
- error states,
- loading skeletons,
- README,
- demo dataset,
- test suite,
- linting,
- final visual polish.

---

# 90. Core Product Principles

## Principle 1 — Evidence Before Explanation

The LLM must not conclude:

> This is a data ingestion bug.

without evidence.

Prefer:

> 13 of 14 extreme observations originate from source B. This concentration suggests a possible source-specific encoding or ingestion issue.

---

## Principle 2 — Python Calculates, the Model Investigates

The model decides:

- what to inspect,
- what hypotheses to test,
- what relationship may matter.

Python performs:

- statistics,
- filtering,
- aggregation,
- correlation,
- counting.

Do not ask the LLM to mentally calculate statistics from raw tables.

---

## Principle 3 — The LLM Does Not Own the Dataset

The model receives:

- profile information,
- schema,
- analytical results,
- targeted samples.

It does not receive the full dataset in-context.

---

## Principle 4 — Bounded Autonomy

The agent loop is:

```text
Observe
↓
Choose one action
↓
Execute
↓
Observe result
↓
Repeat
↓
Finish
```

Maximum:

```text
5 analytical actions
```

---

## Principle 5 — No Silent Cleaning

V1 diagnoses.

It does not mutate.

The model may recommend:

> Normalize equivalent category labels.

The application must not automatically apply the transformation.

---

## Principle 6 — Preserve User Trust

Always distinguish:

- measured evidence,
- inferred interpretation,
- speculation.

Do not overstate uncertainty.

---

## Principle 7 — UI Quality Is a Product Requirement

Do not treat frontend polish as optional.

The application should look like a real developer/data product rather than a generated prototype.

---

# 91. V1 Acceptance Criteria

The product is complete when all items below are satisfied.

---

## Dataset Ingestion

- CSV upload works.
- Parquet upload works.
- malformed files produce useful errors.
- file-size limit works.
- dataset state loads correctly.

---

## Profiling

- dataset shape displays correctly.
- missingness is calculated.
- duplicate rows are detected.
- types are inferred.
- numeric statistics are calculated.
- categorical statistics are calculated.
- profiler findings are generated.
- sampling state is exposed where applicable.

---

## Overview

- summary metrics render.
- missingness chart renders.
- health severity summary renders.
- top findings render.
- Investigate actions work.

---

## Findings

- full finding list renders.
- severity filtering works.
- source filtering works.
- finding detail Sheet works.
- profiler and agent findings are visually distinguishable.

---

## Columns

- searchable column selection works.
- numeric statistics work.
- categorical statistics work.
- automatic visualization works.
- related findings appear.

---

## Ollama

- connection status is visible.
- configured model is used.
- unavailable Ollama does not break profiling.
- unavailable model produces useful error.

---

## Agent

- profiler finding can be investigated.
- free-form question can be submitted.
- model can request Python execution.
- result returns to model.
- model can request charts.
- investigation terminates at five analytical steps.
- final finding includes evidence.
- trace is viewable.

---

## Python Execution

- generated code runs outside FastAPI process.
- dangerous operations are blocked.
- timeouts work.
- large output is truncated.
- original dataset is not modified.
- errors do not crash backend.

---

## Visualization

- profiler charts work.
- model-requested charts work.
- invalid chart specs fail gracefully.
- model does not generate frontend visualization code.

---

## UI

- upload flow looks polished.
- loading states exist.
- main application shell is polished.
- dark mode works.
- layout is usable on laptop screens.
- no permanent sidebar is required.
- no generic AI chat bubble interface.

---

# 92. Explicit V2 Boundary

Do not implement this in V1.

V2 may introduce:

```text
Finding
↓
Agent proposes transformation
↓
User sees exact preview
↓
Affected rows/values shown
↓
User approves
↓
Transformation applied to working copy
↓
Cleaned dataset exported
```

Example:

```text
Suggested transformation

Normalize state values:

" ny " → "NY"
"Ny"   → "NY"
"n.y." → "NY"

Affected rows: 1,482

[Preview] [Apply]
```

Architecture should keep:

```text
analysis
```

and:

```text
mutation
```

clearly separated.

Do not implement cleaning transformations now.

---

# 93. Potential Future Features

Do not implement now, but architecture should not make them impossible:

- approved data cleaning,
- cleaned dataset export,
- multi-file analysis,
- target-aware leakage checks,
- transformation history,
- report export,
- model comparison,
- richer correlation analysis,
- semantic schema descriptions,
- saved investigation history,
- dataset project persistence,
- richer plots,
- notebook export,
- local desktop packaging.

These are future possibilities only.

---

# 94. Definition of Success

The project succeeds if this experience works smoothly:

A user uploads an unfamiliar dataset.

Within seconds they understand:

- its size,
- its column types,
- missingness,
- duplicate behavior,
- suspicious distributions,
- questionable categories.

They see:

```text
age
14 extreme observations
```

They click:

```text
Investigate
```

The local model runs several targeted Python analyses.

It discovers:

- 13 of 14 unusual ages come from source B,
- `999` is concentrated there,
- normal values from B otherwise resemble the rest of the dataset.

It returns:

> The extreme age values appear to be source-specific rather than representative of the underlying distribution. Thirteen of fourteen originate from source system B, with `999` accounting for most of the anomalies. This pattern is consistent with a possible sentinel or ingestion encoding. Inspect source B's missing-age representation before dropping or imputing these rows.

It displays a relevant chart.

The user can inspect the Python operations that produced the conclusion.

The entire process occurs locally.

The original dataset remains unchanged.

That is the core product.

---

# 95. Final Codex Implementation Directive

Implement this PRD as a complete working local application.

Required stack:

```text
Frontend:
React
TypeScript
Vite
Tailwind CSS
shadcn/ui
Plotly

Backend:
Python
FastAPI
Pydantic
pandas
numpy
scipy
pyarrow

Model:
Ollama
configurable local LLM
```

Do not replace the frontend with:

- Streamlit,
- NiceGUI,
- Gradio,
- Dash.

Do not replace Vite with Next.js unless a truly unavoidable technical requirement emerges.

Do not add:

- authentication,
- databases,
- embeddings,
- RAG,
- AutoML,
- automatic cleaning,
- multi-agent orchestration,
- cloud dependencies,
- remote LLM providers.

Favor readable code over abstraction.

Do not create unnecessary architecture merely for future flexibility.

The highest-priority engineering qualities are:

1. deterministic profiling is reliable,
2. the frontend looks polished,
3. the agent loop is bounded,
4. analytical Python execution is genuinely useful,
5. claims are evidence-backed,
6. code execution is isolated from the main backend,
7. the source dataset is preserved,
8. failures degrade gracefully,
9. charts are validated and controlled,
10. the app remains small enough to understand and extend.

When implementation choices are ambiguous, choose the simplest approach that satisfies these requirements.

The result should feel like a polished local data-quality and investigation tool that could plausibly be released publicly, not a prototype dashboard.