"""Real-model acceptance evaluation via the app's API in an isolated temporary session.

No mock Ollama responses. Does not replace the interactive app's dataset. Structural
checks are automated; correctness of natural-language claims still needs trace review.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from dataset_investigator.config import settings
from dataset_investigator.main import app

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    {
        "id": "synthetic",
        "file": ROOT / "examples/suspicious_customers.csv",
        "shape": [1212, 6],
        "finding": ("outliers", "age"),
        "question": "Investigate the extreme age observations using the profiler extreme IQR boundaries. Compute their counts by source_system and compare typical ages across sources. Request a useful chart, then finish with measured evidence and a cautious recommendation.",
    },
    {
        "id": "iris",
        "file": ROOT / "examples/evaluation/prepared/iris.csv",
        "shape": [150, 5],
        "question": "Are petal_length_cm and petal_width_cm associated overall and within each species? Compute Pearson correlations and group medians, request a scatter chart colored by species, and finish with measured evidence. Do not infer causation or call natural group differences errors.",
    },
    {
        "id": "penguins",
        "file": ROOT / "examples/evaluation/prepared/penguins.csv",
        "shape": [344, 8],
        "finding": ("missingness", "sex"),
        "question": "Are missing sex values concentrated in a species or island? Compute missing counts and rates using each group's row count as denominator, compare groups, request a missingness chart, and finish with measured evidence. Do not invent a cause for missing data.",
    },
    {
        "id": "wine_red",
        "file": ROOT / "examples/evaluation/prepared/wine_red.csv",
        "shape": [1599, 12],
        "finding": ("duplicates", None),
        "question": "Are exact repeated wine rows concentrated in particular quality scores? Count duplicates excluding their first occurrence and compare counts and within-group duplicate rates by quality. Request a bar chart of quality frequencies for context. Finish with measured evidence; distinguish repeated measurements from a proven ingestion error.",
    },
]


def oracle(case, df):
    if case == "synthetic":
        q1, q3 = df.age.quantile([0.25, 0.75])
        extreme = df[(df.age < q1 - 3 * (q3 - q1)) | (df.age > q3 + 3 * (q3 - q1))]
        return {
            "extreme_count": len(extreme),
            "extreme_by_source": extreme.source_system.value_counts().to_dict(),
            "source_medians": df.groupby("source_system").age.median().to_dict(),
        }
    if case == "iris":
        return {
            "overall_pearson": df.petal_length_cm.corr(df.petal_width_cm),
            "pearson_by_species": {
                name: group.petal_length_cm.corr(group.petal_width_cm)
                for name, group in df.groupby("species")
            },
            "median_by_species": df.groupby("species")[["petal_length_cm", "petal_width_cm"]]
            .median()
            .to_dict(),
        }
    if case == "penguins":
        result = {"missing_sex": int(df.sex.isna().sum())}
        for col in ["species", "island"]:
            result[col] = {
                name: {
                    "rows": len(group),
                    "missing": int(group.sex.isna().sum()),
                    "rate": float(group.sex.isna().mean()),
                }
                for name, group in df.groupby(col)
            }
        return result
    duplicate = df.duplicated()
    return {
        "duplicate_rows": int(duplicate.sum()),
        "by_quality": {
            str(name): {
                "rows": len(group),
                "duplicates": int(duplicate.loc[group.index].sum()),
                "rate": float(duplicate.loc[group.index].mean()),
            }
            for name, group in df.groupby("quality")
        },
    }


def expected_chart(case_id, charts):
    for chart in charts:
        spec = chart["spec"]
        if (
            case_id == "synthetic"
            and spec["type"] == "bar"
            and spec["x"] == "source_system"
            and spec["y"] == "age"
        ):
            return True
        if (
            case_id == "synthetic"
            and spec["type"] in {"histogram", "box"}
            and spec["x"] == "age"
            and spec["color"] == "source_system"
        ):
            return True
        if (
            case_id == "iris"
            and spec["type"] == "scatter"
            and {spec["x"], spec["y"]} == {"petal_length_cm", "petal_width_cm"}
            and spec["color"] == "species"
        ):
            return True
        if case_id == "penguins" and spec["type"] == "missingness":
            return True
        if (
            case_id == "wine_red"
            and spec["type"] == "bar"
            and spec["x"] == "quality"
            and not spec["y"]
        ):
            return True
    return False


def computed_value_coverage(case_id, reference, steps):
    """A numeric smoke check, not proof of value-to-label association or interpretation."""

    def numbers(value):
        if isinstance(value, bool):
            return []
        if isinstance(value, (int, float)):
            return [float(value)]
        if isinstance(value, dict):
            return [n for child in value.values() for n in numbers(child)]
        if isinstance(value, list):
            return [n for child in value for n in numbers(child)]
        return []

    observed = []
    for step in steps:
        raw = step["result_summary"]
        try:
            payload = json.loads(raw.split("\n", 1)[1] if raw.startswith("DataFrame:") else raw)
            observed.extend(numbers(payload))
        except (ValueError, IndexError):
            pass
    required = reference
    if case_id == "synthetic":
        required = {
            "counts": reference["extreme_by_source"],
            "medians": reference["source_medians"],
        }
    elif case_id == "penguins":
        required = {"species": reference["species"], "island": reference["island"]}
    elif case_id == "wine_red":
        required = reference["by_quality"]
    expected = sorted(set(numbers(required)))
    missing = [
        v
        for v in expected
        if not any(
            abs(n - v) <= max(1e-4, abs(v) * 1e-4) or (0 < v < 1 and abs(n / 100 - v) <= 1e-4)
            for n in observed
        )
    ]
    return {
        "passed": not missing,
        "expected_numeric_values": expected,
        "missing_numeric_values": missing,
        "limitation": "Checks computed numeric values, not labels or natural-language truth. Separate semantic review remains required.",
    }


async def evaluate(args):
    if args.model:
        settings.ollama_model = args.model
    sources_path = ROOT / "examples/evaluation/sources.json"
    sources = {item["id"]: item for item in json.loads(sources_path.read_text())["datasets"]}
    source_hash = hashlib.sha256(sources_path.read_bytes()).hexdigest()
    code_hash = hashlib.sha256(
        b"".join(
            p.read_bytes() for p in sorted((ROOT / "backend/dataset_investigator").rglob("*.py"))
        )
    ).hexdigest()
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.ollama_model,
        "model_endpoint": settings.ollama_base_url,
        "thinking": settings.ollama_think if settings.ollama_think is not None else "model default",
        "backend_code_sha256": code_hash,
        "source_manifest_sha256": source_hash,
        "method": "Real Ollama calls through FastAPI ASGI routes, real subprocess execution and chart validation in an isolated app lifespan. No mocks.",
        "limits": {
            "analytical_actions": settings.agent_max_steps,
            "code_timeout_seconds": settings.agent_code_timeout_seconds,
        },
        "claim_review": "Structural checks cannot establish semantic correctness; compare each final finding with the independent oracle and computed trace.",
        "cases": [],
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://testserver", timeout=30
        ) as api,
    ):
        status = (await api.get("/api/ollama/status")).json()
        if not status["model_available"]:
            raise RuntimeError(status["message"])
        for case in CASES:
            if args.case and case["id"] not in args.case:
                continue
            started = time.monotonic()
            raw = case["file"].read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if case["id"] in sources and digest != sources[case["id"]]["prepared_sha256"]:
                raise RuntimeError(f"Fixture hash mismatch: {case['id']}")
            upload = await api.post("/api/datasets", files={"file": (case["file"].name, raw)})
            upload.raise_for_status()
            dataset = upload.json()
            session = app.state.session
            snapshot_hash = hashlib.sha256(session.snapshot.read_bytes()).hexdigest()
            body = {"question": case["question"]}
            if "finding" in case:
                category, column = case["finding"]
                match = next(
                    (
                        f
                        for f in dataset["profile"]["findings"]
                        if f["category"] == category and (column is None or column in f["columns"])
                    ),
                    None,
                )
                if match is None:
                    raise RuntimeError(f"Expected profiler finding missing for {case['id']}")
                body["finding_id"] = match["id"]
            start = await api.post("/api/investigations", json=body)
            start.raise_for_status()
            state = start.json()
            deadline = time.monotonic() + settings.ollama_timeout_seconds * 7 + 60
            while state["status"] == "running" and time.monotonic() < deadline:
                await asyncio.sleep(0.5)
                response = await api.get("/api/investigations/" + state["investigation_id"])
                response.raise_for_status()
                state = response.json()
            successful = [
                step
                for step in state["trace"]
                if step["action"] == "run_python"
                and step.get("result_summary")
                and not step.get("error")
            ]
            reference = oracle(case["id"], pd.read_csv(case["file"]))
            coverage = computed_value_coverage(case["id"], reference, successful)
            checks = {
                "expected_shape": [dataset["rows"], dataset["columns"]] == case["shape"],
                "profile_generated": bool(dataset["profile"]["columns"]),
                "completed": state["status"] == "completed",
                "python_evidence": bool(successful),
                "validated_chart": bool(state["charts"]),
                "requested_chart_contract": expected_chart(case["id"], state["charts"]),
                "required_computed_values": coverage["passed"],
                "profiler_finding_selected": "finding" not in case or "finding_id" in body,
                "evidence_backed_finding": bool(
                    state.get("final_finding") and state["final_finding"]["evidence"] and successful
                ),
                "bounded_actions": len(state["trace"]) <= settings.agent_max_steps,
                "uploaded_bytes_unchanged": (session.directory / "source.csv").read_bytes() == raw,
                "snapshot_unchanged": hashlib.sha256(session.snapshot.read_bytes()).hexdigest()
                == snapshot_hash,
                "fixture_unchanged": hashlib.sha256(case["file"].read_bytes()).hexdigest()
                == digest,
            }
            result = {
                "id": case["id"],
                "file": str(case["file"].relative_to(ROOT)),
                "sha256": digest,
                "provenance": sources.get(
                    case["id"],
                    {
                        "source": "scripts/generate_demo.py",
                        "attribution": "Deterministically generated synthetic fixture; no real customer data.",
                    },
                ),
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "checks": checks,
                "structural_pass": all(checks.values()),
                "profile": {
                    key: dataset["profile"][key]
                    for key in [
                        "row_count",
                        "column_count",
                        "missing_cells",
                        "duplicate_rows",
                        "sampled",
                        "duration_seconds",
                        "findings",
                    ]
                },
                "oracle": reference,
                "computed_value_coverage": coverage,
                "semantic_review": None,
                "investigation": state,
            }
            report["cases"].append(result)
            target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            print(
                json.dumps(
                    {
                        "case": case["id"],
                        "pass": result["structural_pass"],
                        "elapsed": result["elapsed_seconds"],
                        "actions": len(state["trace"]),
                        "action_errors": [s["error"] for s in state["trace"] if s.get("error")],
                        "title": state.get("final_finding", {}).get("title")
                        if state.get("final_finding")
                        else None,
                    }
                ),
                flush=True,
            )
            if state["status"] == "running":
                raise RuntimeError("Evaluation exceeded the bounded model deadline.")
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report["structural_pass"] = all(case["structural_pass"] for case in report["cases"])
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report["structural_pass"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Installed Ollama model tag; otherwise use .env/default")
    parser.add_argument("--case", action="append", choices=[c["id"] for c in CASES])
    parser.add_argument("--output", default="evaluations/latest.json")
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(0 if asyncio.run(evaluate(args)) else 1)
