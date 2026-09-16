from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.6:35b-a3b"
    # None respects the selected model's native behavior (including non-thinking models).
    ollama_think: bool | None = None
    max_upload_mb: int = Field(250, ge=1, le=250)
    agent_max_steps: int = Field(5, ge=1, le=5)
    agent_code_timeout_seconds: float = Field(10, gt=0, le=10)
    large_dataset_row_threshold: int = Field(200_000, ge=1)
    profile_sample_rows: int = Field(100_000, ge=1, le=100_000)
    ollama_timeout_seconds: float = Field(180, ge=1, le=600)
    worker_memory_mb: int = Field(2048, ge=256, le=8192)
    ollama_max_context: int = Field(65536, ge=16384, le=262144)

    @field_validator("ollama_base_url")
    @classmethod
    def local_endpoint(cls, value: str) -> str:
        url = urlparse(value)
        if (
            url.scheme not in {"http", "https"}
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Ollama must use a loopback URL on this machine.")
        return value.rstrip("/")


settings = Settings()
