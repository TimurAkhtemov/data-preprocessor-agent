import json

import httpx
import pytest

from dataset_investigator.agent.client import OllamaClient, OllamaError
from dataset_investigator.config import Settings


def mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )


async def test_native_reasoning_is_preserved_and_hidden_output_is_not_returned(monkeypatch):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "thinking": "Private model reasoning",
                    "content": '{"action":"run_python","reason":"Count rows","code":"result = len(df)"}',
                }
            },
        )

    mock_http(monkeypatch, handler)
    client = OllamaClient(Settings(_env_file=None))
    response = await client.chat([{"role": "user", "content": "Count rows"}])
    assert "think" not in bodies[0]
    assert bodies[0]["options"]["num_predict"] == 4096
    assert bodies[0]["stream"] is False
    assert "Private model reasoning" not in response
    assert json.loads(response)["action"] == "run_python"


async def test_explicit_nonreasoning_override_and_model_configuration(monkeypatch):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "{}"}})

    mock_http(monkeypatch, handler)
    await OllamaClient(
        Settings(_env_file=None, ollama_model="small:local", ollama_think=False)
    ).chat([])
    assert bodies[0]["think"] is False
    assert bodies[0]["model"] == "small:local"


async def test_missing_model_is_a_useful_error(monkeypatch):
    mock_http(monkeypatch, lambda request: httpx.Response(404, json={"error": "model missing"}))
    with pytest.raises(OllamaError) as exc:
        await OllamaClient(Settings(_env_file=None)).chat([])
    assert exc.value.code == "MODEL_MISSING"


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.example",
        "http://192.168.1.1:11434",
        "http://localhost@evil.example",
        "file:///tmp/ollama",
    ],
)
def test_remote_endpoints_are_rejected(url):
    with pytest.raises(ValueError):
        Settings(_env_file=None, ollama_base_url=url)
