"""FastAPI app + lifespan for the receipt-ocr sidecar service.

Walking-skeleton (Phase 1, this commit): /healthz returns
``model_loaded: false``, /ocr-receipt returns 503. Phase 2 wires up
the OCR engine; Phase 3 adds parsing rules + market-header detection.
See vorrat ADR-0039 §6 for the implementation roadmap.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from receipt_ocr import __version__
from receipt_ocr.api.ocr_receipt import router as ocr_receipt_router
from receipt_ocr.config import Settings, get_settings
from receipt_ocr.schemas import HealthzResponse

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    log.warning(
        "receipt-ocr started: channel=%s sha=%s model_loaded=%s",
        settings.build_channel,
        settings.build_sha,
        settings.model_loaded,
    )
    try:
        yield
    finally:
        app.state.settings = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="receipt-ocr",
        version=__version__,
        description=(
            "Printed-receipt photo to structured per-line tokens. "
            "Sidecar in the vorrat-services TrueNAS app stack per "
            "vorrat ADR-0039. Phase 1: walking-skeleton with /healthz "
            "only — OCR engine + parsing rules land in subsequent commits."
        ),
        lifespan=lifespan,
    )

    @app.get("/healthz", response_model=HealthzResponse)
    async def healthz() -> HealthzResponse:
        settings: Settings | None = getattr(app.state, "settings", None)
        # Settings should always be present once lifespan ran; fall
        # through to defaults if a test hits /healthz outside lifespan.
        channel = settings.build_channel if settings else "dev"
        commit = settings.build_sha if settings else "unknown"
        version = settings.build_date if settings else __version__
        model_loaded = settings.model_loaded if settings else False
        return HealthzResponse(
            ok=True,
            channel=channel,
            version=version,
            commit=commit,
            model_loaded=model_loaded,
            # Phase 1 has no engine, so model_id is just "unloaded".
            # Phase 2 surfaces the actual engine identifier here.
            model_id="unloaded",
        )

    app.include_router(ocr_receipt_router)
    return app


app = create_app()
