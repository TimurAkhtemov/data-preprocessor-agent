import json
import logging

import httpx

from ..config import Settings
from .schemas import ACTION_SCHEMA

log = logging.getLogger(__name__)
NUM_PREDICT = 4096
MIN_CONTEXT = 16384


class OllamaError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class OllamaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def status(self) -> dict:
        model = self.settings.ollama_model
        try:
            async with httpx.AsyncClient(
                timeout=3, trust_env=False, follow_redirects=False
            ) as client:
                response = await client.get(self.settings.ollama_base_url + "/api/tags")
                response.raise_for_status()
                names = [item.get("name", "") for item in response.json().get("models", [])]
            # Ollama canonicalizes untagged names to :latest.
            available = model in names or (":" not in model and model + ":latest" in names)
            return {
                "connected": True,
                "model_available": available,
                "model": model,
                "code": "OK" if available else "MODEL_MISSING",
                "message": "Local model ready."
                if available
                else f"The configured model {model} is not installed. Install it in Ollama or change OLLAMA_MODEL.",
            }
        except (httpx.HTTPError, ValueError, TypeError):
            log.debug("Ollama unavailable")
            return {
                "connected": False,
                "model_available": False,
                "model": model,
                "code": "OLLAMA_UNAVAILABLE",
                "message": "Could not connect to Ollama. Start Ollama and ensure the configured model is installed.",
            }

    def context_window(self, messages: list[dict], schema: dict) -> int:
        # Rough token estimate for JSON-heavy prompts, plus the generation budget.
        # Ollama reloads the model when num_ctx changes, so grow in power-of-two steps.
        characters = sum(len(str(m.get("content", ""))) for m in messages) + len(json.dumps(schema))
        needed = characters // 3 + NUM_PREDICT + 1024
        window = MIN_CONTEXT
        while window < needed and window < self.settings.ollama_max_context:
            window *= 2
        return min(window, self.settings.ollama_max_context)

    async def chat(self, messages: list[dict], finish_only=False) -> str:
        from .schemas import Finish

        schema = Finish.model_json_schema() if finish_only else ACTION_SCHEMA
        body = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0.1,
                "num_predict": NUM_PREDICT,
                "num_ctx": self.context_window(messages, schema),
            },
        }
        if self.settings.ollama_think is not None:
            body["think"] = self.settings.ollama_think
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.ollama_timeout_seconds,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = await client.post(self.settings.ollama_base_url + "/api/chat", json=body)
                if response.status_code == 404:
                    raise OllamaError(
                        "MODEL_MISSING",
                        f"The configured model {self.settings.ollama_model} is not installed in Ollama.",
                    )
                response.raise_for_status()
                # Hidden reasoning is never stored or returned to the user.
                content = response.json()["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("Invalid response")
                return content
        except httpx.TimeoutException as exc:
            raise OllamaError(
                "OLLAMA_TIMEOUT",
                "The local model took too long to respond. Try a smaller model or a narrower question.",
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(
                "OLLAMA_UNAVAILABLE", "Could not complete the request to the local Ollama server."
            ) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaError(
                "INVALID_MODEL_RESPONSE", "Ollama returned an unreadable response."
            ) from exc
