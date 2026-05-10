"""Runtime settings, loaded from environment variables.

All settings have safe production defaults — no env-var override is
required for the container to run normally inside the vorrat-services
stack. The dev/CI knob `disable_engine` exists so unit + smoke tests
can avoid the ~100 MB PaddleOCR model download.
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

    # CPU thread count for the OCR engine. None ⇒ paddle picks a
    # reasonable default. Override on shared hosts to leave room for
    # other apps. Not directly threaded to PaddleOCR yet (Phase 2a
    # accepts the engine's defaults); reserved for Phase 3 if profiling
    # shows the default is wrong.
    n_threads: int | None = None

    # Build-channel + commit, exposed via /healthz. Same convention as
    # the off-classifier and main vorrat app — keeps Watchtower / debug
    # stories aligned.
    build_channel: str = "dev"
    build_sha: str = "unknown"
    build_date: str = "unknown"

    # PaddleOCR language code. 'german' covers DE+EN script reasonably;
    # changing this triggers a fresh model download on next container
    # start. The model cache location is set in the Dockerfile via
    # PADDLE_PDX_CACHE_HOME, not here.
    lang: str = Field(default="german")

    # Disable the engine entirely and run as `_UnloadedStub`. Used by
    # CI smoke tests so the build pipeline doesn't pay the ~100 MB
    # model-download cost on every commit. Production never sets this.
    disable_engine: bool = Field(default=False)


def get_settings() -> Settings:
    """Module-level loader. FastAPI's lifespan instantiates once."""
    return Settings()
