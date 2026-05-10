"""FastAPI app + lifespan for the receipt-ocr sidecar service.

Walking-skeleton (Phase 1) shipped /healthz only. Phase 2a (this
commit) wires up the PaddleOCR runner: container start downloads /
loads the engine into the mounted /models volume; /healthz reflects
`model_loaded` from the runner's actual state. /ocr-receipt continues
to 503 until Phase 2b lands the parsing layer.

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
from receipt_ocr.inference.runner import OcrRunner, RawOcrLine
from receipt_ocr.schemas import HealthzResponse

log = logging.getLogger(__name__)


class _UnloadedStub:
    """Sentinel runner used when PaddleOCR didn't load.

    Hit when `settings.disable_engine=True` (CI / dev) or when the
    runner build threw — in both cases /healthz reports
    `model_loaded=false` and /ocr-receipt 503s. Same pattern as the
    off-classifier's _UnloadedStub.
    """

    @property
    def model_id(self) -> str:
        return "unloaded"

    @property
    def is_loaded(self) -> bool:
        return False

    def ocr(self, image_bytes: bytes) -> list[RawOcrLine]:
        # Endpoints short-circuit on is_loaded=False before reaching
        # this; raising loudly here surfaces accidental bypasses.
        raise RuntimeError("ocr engine not loaded")


def _build_runner(settings: Settings) -> OcrRunner:
    """Resolve to a PaddleRunner or fall through to the stub.

    The build_paddle_runner_or_stub helper lives next to the engine
    code (paddle_runner.py) so it can lazy-import paddleocr without
    pulling the whole engine surface into the test path.
    """
    if settings.disable_engine:
        log.warning("disable_engine=True; running as stub (no PaddleOCR load)")
        return _UnloadedStub()

    # Lazy import: keeps the unit-test suite import-free of paddleocr.
    from receipt_ocr.inference.paddle_runner import (  # noqa: PLC0415
        build_paddle_runner_or_stub,
    )

    return build_paddle_runner_or_stub(lang=settings.lang)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    runner = _build_runner(settings)
    app.state.runner = runner
    app.state.settings = settings
    log.warning(
        "receipt-ocr started: channel=%s sha=%s model_loaded=%s model_id=%s",
        settings.build_channel,
        settings.build_sha,
        runner.is_loaded,
        runner.model_id,
    )
    try:
        yield
    finally:
        # Engine instances free internal resources via GC; explicit
        # teardown of PaddleOCR isn't required and the wrapper has no
        # close() that we'd need to call. Drop the reference and let
        # process exit handle the rest.
        app.state.runner = None
        app.state.settings = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="receipt-ocr",
        version=__version__,
        description=(
            "Printed-receipt photo to structured per-line tokens. "
            "Sidecar in the vorrat-services TrueNAS app stack per "
            "vorrat ADR-0039. Phase 2a: PaddleOCR engine integration; "
            "/ocr-receipt parsing wires up in Phase 2b."
        ),
        lifespan=lifespan,
    )

    @app.get("/healthz", response_model=HealthzResponse)
    async def healthz() -> HealthzResponse:
        runner: OcrRunner | None = getattr(app.state, "runner", None)
        settings: Settings | None = getattr(app.state, "settings", None)
        # Settings should always be present once lifespan ran; fall
        # through to defaults if a test hits /healthz outside lifespan.
        channel = settings.build_channel if settings else "dev"
        commit = settings.build_sha if settings else "unknown"
        version = settings.build_date if settings else __version__
        return HealthzResponse(
            ok=True,
            channel=channel,
            version=version,
            commit=commit,
            model_loaded=bool(runner and runner.is_loaded),
            model_id=runner.model_id if runner else "unloaded",
        )

    app.include_router(ocr_receipt_router)
    return app


app = create_app()
