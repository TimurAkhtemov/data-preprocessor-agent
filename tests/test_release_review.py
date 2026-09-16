"""Regression checks from the pre-publication review pass."""

import json
import pathlib

import httpx
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from dataset_investigator.agent.client import OllamaClient
from dataset_investigator.config import Settings
from dataset_investigator.data.heuristics import detect_findings
from dataset_investigator.data.profiler import profile_dataset
from dataset_investigator.data.serialization import serialize_result
from dataset_investigator.execution.sandbox import execute_python
from dataset_investigator.execution.validator import CodeRejected, validate_code
from dataset_investigator.main import app
from dataset_investigator.visualization.schemas import ChartSpec
from dataset_investigator.visualization.validation import build_chart


def profile(frame):
    return profile_dataset(frame, "review.csv", Settings(_env_file=None))


async def test_worker_accepts_code_with_many_non_ascii_characters(tmp_path):
    snapshot = tmp_path / "snapshot.parquet"
    pd.DataFrame({"город": ["Москва", "Казань"]}).to_parquet(snapshot, index=False)
    label = "é" * 3400
    code = f"label = '{label}'\nresult = len(label) + (df['город'] == 'Москва').sum()"

    output = await execute_python(code, snapshot, Settings(_env_file=None))

    assert output == {"ok": True, "summary": "3401"}


@pytest.mark.parametrize(
    "value, expected",
    [
        (pd.Index(["age", "income"]), '["age", "income"]'),
        (pd.RangeIndex(3), "[0, 1, 2]"),
        (pd.DataFrame({"a": [1], "b": [2]}).columns, '["a", "b"]'),
    ],
)
def test_index_results_are_serialized_as_lists(value, expected):
    assert serialize_result(value) == expected


def test_upload_directory_failure_releases_the_session_lock(monkeypatch):
    calls = []
    original = pathlib.Path.mkdir

    def failing_mkdir(self, *args, **kwargs):
        if not calls:
            calls.append(self)
            raise OSError("temporary directory vanished")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "mkdir", failing_mkdir)
    with TestClient(app, raise_server_exceptions=False) as client:
        failed = client.post("/api/datasets", files={"file": ("a.csv", b"a,b\n1,x\n")})
        assert failed.status_code == 500
        recovered = client.post("/api/datasets", files={"file": ("a.csv", b"a,b\n1,x\n")})
        assert recovered.status_code == 200, recovered.text
        assert client.get("/api/datasets/progress").json()["loading"] is False


def mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )


async def test_context_window_tracks_conversation_size(monkeypatch):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "{}"}})

    mock_http(monkeypatch, handler)
    client = OllamaClient(Settings(_env_file=None))
    await client.chat([{"role": "user", "content": "short"}])
    await client.chat([{"role": "user", "content": "x" * 60_000}])
    await client.chat([{"role": "user", "content": "x" * 3_000_000}])

    short, long, huge = (body["options"]["num_ctx"] for body in bodies)
    assert short == 16384
    assert 60_000 / 4 + 4096 <= long < huge
    assert huge == Settings(_env_file=None).ollama_max_context


def test_sparse_indicator_column_has_no_extreme_gap_finding():
    flag = np.zeros(400, dtype=int)
    flag[:2] = 1
    findings = detect_findings(profile(pd.DataFrame({"flag": flag})))
    assert "extreme_gap" not in {f.category for f in findings}


def test_extreme_gap_still_fires_for_a_far_maximum():
    values = np.concatenate([np.linspace(10, 20, 399), [1_000_000]])
    findings = detect_findings(profile(pd.DataFrame({"value": values})))
    assert "extreme_gap" in {f.category for f in findings}


def test_bar_chart_requires_a_discrete_x_column():
    frame = pd.DataFrame(
        {
            "score": np.random.default_rng(1).integers(3, 9, 200),
            "amount": np.linspace(0.5, 99.5, 200),
            "when": pd.date_range("2024-01-01", periods=200, freq="D"),
        }
    )
    p = profile(frame)
    assert build_chart(ChartSpec(type="bar", x="score", title="t"), frame, p)["series"]
    with pytest.raises(ValueError, match="bar"):
        build_chart(ChartSpec(type="bar", x="amount", title="t"), frame, p)
    with pytest.raises(ValueError, match="bar"):
        build_chart(ChartSpec(type="bar", x="when", title="t"), frame, p)


@pytest.mark.parametrize(
    "code",
    [
        "p = np\nresult = p.empty(4)",
        "result = [np][0].empty(4)",
        "modules = {'n': stats}\nresult = modules['n'].norm",
    ],
)
def test_module_aliases_cannot_bypass_the_module_allowlist(code):
    with pytest.raises(CodeRejected):
        validate_code(code)
