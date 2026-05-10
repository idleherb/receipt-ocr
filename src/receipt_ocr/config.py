"""Runtime settings, loaded from environment variables.

Phase 1 (walking-skeleton): only the build-channel + thread-count knobs
are wired. Phase 2 will add the OCR-engine settings (backend choice,
model path / cache dir, language list).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RECEIPT_OCR_",
        case_sensitive=False,
        extra="ignore",
    )

    # CPU thread count for the future OCR engine. None ⇒ engine picks
    # a reasonable default. Override on shared hosts to leave room for
    # other apps. Currently unused in Phase 1; reserved for Phase 2.
    n_threads: int | None = None

    # Build-channel + commit, exposed via /healthz. Same convention as
    # the off-classifier and main vorrat app — keeps Watchtower / debug
    # stories aligned.
    build_channel: str = "dev"
    build_sha: str = "unknown"
    build_date: str = "unknown"

    # Phase 1: always False because no OCR engine exists yet. Phase 2
    # will compute this dynamically based on the engine's load state.
    model_loaded: bool = Field(default=False)


def get_settings() -> Settings:
    """Module-level loader. FastAPI's lifespan instantiates once."""
    return Settings()
