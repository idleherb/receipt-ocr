"""Shared fixtures.

Tests run against a deterministic stub runner — no PaddleOCR import,
no model files on disk. The integration path (real engine) is
exercised in CI via the Docker container's smoke test (with
`disable_engine=true` to keep CI fast) and on the live server after
Watchtower deploys a fresh image.
"""

from __future__ import annotations

import os

# Disable engine load for the entire suite — Settings reads
# RECEIPT_OCR_DISABLE_ENGINE at the moment a Settings() is constructed,
# so we set this BEFORE any test imports config or main.
os.environ.setdefault("RECEIPT_OCR_DISABLE_ENGINE", "true")

from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from receipt_ocr.inference.runner import RawOcrLine
from receipt_ocr.main import app


class StubRunner:
    """Deterministic OcrRunner: returns a fixed list of lines.

    Configurable via constructor args so tests can verify the response
    is plumbed through (vs e.g. always returning empty).
    """

    def __init__(
        self,
        *,
        lines: list[RawOcrLine] | None = None,
        is_loaded: bool = True,
        model_id: str = "stub",
    ) -> None:
        self._lines = lines or []
        self._is_loaded = is_loaded
        self._model_id = model_id
        self.calls: list[bytes] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def ocr(self, image_bytes: bytes) -> list[RawOcrLine]:
        self.calls.append(image_bytes)
        return list(self._lines)


@pytest.fixture
def stub_runner() -> StubRunner:
    return StubRunner()


@pytest.fixture
def unloaded_stub_runner() -> StubRunner:
    return StubRunner(is_loaded=False, model_id="unloaded")


async def _make_client(runner: StubRunner) -> AsyncIterator[AsyncClient]:
    """Wire `runner` onto app.state via lifespan + override."""
    async with LifespanManager(app):
        # Lifespan attached its own (stub-via-disable_engine) runner;
        # we override with the test-supplied one so /healthz reflects
        # the desired load-state.
        app.state.runner = runner
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
async def client(stub_runner: StubRunner) -> AsyncIterator[AsyncClient]:
    async for c in _make_client(stub_runner):
        yield c


@pytest.fixture
async def unloaded_client(
    unloaded_stub_runner: StubRunner,
) -> AsyncIterator[AsyncClient]:
    async for c in _make_client(unloaded_stub_runner):
        yield c
