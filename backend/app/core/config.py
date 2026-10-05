"""
Application configuration using pydantic-settings.
All settings are loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "Industrial Failure Mechanism Discovery"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = Field(default="changeme_dev_secret_key_12345", min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://ifmd_user:changeme@localhost:5432/ifmd_db"
    )
    database_url_sync: str = (
        "postgresql://ifmd_user:changeme@localhost:5432/ifmd_db"
    )
    db_echo: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: Literal["none", "openai", "google", "ollama"] = "none"
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.2

    # ── Data ─────────────────────────────────────────────────────────────────
    data_dir: str = "./data"
    max_upload_size_mb: int = 100

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"

    # ── Research / Experiments ────────────────────────────────────────────────
    experiment_output_dir: str = "./research/results"
    random_seed: int = 42

    # ── Mechanism Discovery ───────────────────────────────────────────────────
    # Minimum temporal window (hours) to look back from a failure event
    temporal_lookback_hours: float = 72.0
    # Minimum association strength to consider a variable relevant
    min_association_threshold: float = 0.15
    # Minimum number of evidence items to report a mechanism
    min_evidence_count: int = 2
    # Maximum candidate mechanisms to evaluate per investigation
    max_candidate_mechanisms: int = 20
    # Change-point detection model (l2 | rbf | cosine)
    changepoint_model: str = "rbf"
    # Penalty for ruptures change-point detection
    changepoint_penalty: float = 3.0

    # ── Ranking weights ───────────────────────────────────────────────────────
    weight_temporal_consistency: float = 0.25
    weight_evidence_strength: float = 0.30
    weight_evidence_coverage: float = 0.20
    weight_recurrence: float = 0.10
    weight_mechanism_plausibility: float = 0.15

    # ── Pagination ────────────────────────────────────────────────────────────
    default_page_size: int = 20
    max_page_size: int = 100

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
