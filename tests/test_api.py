import io
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from dataset_investigator.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_csv_parquet_invalid_and_immutable_replacement(client):
    assert client.get("/api/datasets/current").json() is None
    response = client.post("/api/datasets", files={"file": ("a.csv", b"a,b\n1,x\n2,y\n")})
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["profile"]["row_count"] == 2
    session = app.state.session
    before = session.snapshot.read_bytes()
    error = client.post("/api/datasets", files={"file": ("bad.csv", b"a,b\n1,2,3\n")})
    assert error.status_code == 400 and error.json()["code"] == "MALFORMED_CSV"
    assert client.get("/api/datasets/current").json()["dataset_id"] == first["dataset_id"]
    assert session.snapshot.read_bytes() == before
    buffer = io.BytesIO()
    pd.DataFrame({"value": [4, 5, 6]}).to_parquet(buffer)
    response = client.post("/api/datasets", files={"file": ("b.parquet", buffer.getvalue())})
    assert response.status_code == 200 and response.json()["rows"] == 3
    assert not (session.root / first["dataset_id"]).exists()


def test_demo_chart_and_invalid_specs(client):
    response = client.post("/api/datasets/demo")
    assert response.status_code == 200, response.text
    assert response.json()["rows"] == 1212
    assert response.json()["profile"]["duplicate_rows"] == 12
    for spec in [
        {"type": "histogram", "x": "age"},
        {"type": "scatter", "x": "age", "y": "income"},
        {"type": "bar", "x": "state"},
        {"type": "line", "x": "signup_date"},
        {"type": "box", "x": "age"},
        {"type": "missingness"},
    ]:
        chart = client.post("/api/datasets/chart", json={**spec, "title": "Test"})
        assert chart.status_code == 200, chart.text
    for spec in [
        {"type": "arbitrary_js"},
        {"type": "histogram", "x": "state"},
        {"type": "scatter", "x": "age", "y": "missing"},
    ]:
        response = client.post("/api/datasets/chart", json={**spec, "title": "Bad"})
        assert response.status_code in (400, 422)
    response = client.post(
        "/api/datasets/chart",
        json={"type": "bar", "x": "state", "title": "Test", "top_n": 999},
    )
    assert response.json()["spec"]["top_n"] == 30


def test_size_limit_and_external_origin(client, monkeypatch):
    monkeypatch.setattr("dataset_investigator.main.settings.max_upload_mb", 1)
    response = client.post("/api/datasets", files={"file": ("large.csv", b"x" * (1024 * 1024 + 1))})
    assert response.status_code == 413 and response.json()["code"] == "FILE_TOO_LARGE"
    response = client.post("/api/datasets/demo", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_ollama_missing_does_not_break_profile(client, monkeypatch):
    monkeypatch.setattr(
        "dataset_investigator.agent.client.OllamaClient.status",
        AsyncMock(
            return_value={
                "connected": False,
                "model_available": False,
                "model": "test",
                "code": "OLLAMA_UNAVAILABLE",
                "message": "Start Ollama.",
            }
        ),
    )
    assert client.post("/api/datasets/demo").status_code == 200
    response = client.post("/api/investigations", json={"question": "Investigate ages"})
    assert response.status_code == 503 and response.json()["code"] == "OLLAMA_UNAVAILABLE"
    assert client.get("/api/datasets/profile").status_code == 200


def test_active_investigation_blocks_replacement_and_double_start(client):
    client.post("/api/datasets/demo")
    app.state.session.active_id = "active"
    assert client.post("/api/datasets/demo").status_code == 409
    assert (
        client.post("/api/investigations", json={"question": "Compare source groups"}).status_code
        == 409
    )
    app.state.session.active_id = None
