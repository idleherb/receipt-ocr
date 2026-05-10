"""Shared fixtures.

Phase 1: there is no OCR engine to stub; the test-suite simply hits
the FastAPI app with a real ASGI transport via httpx. Phase 2 will
introduce a Stub-Runner Protocol analogous to off-classifier's
StubRunner once the engine module exists.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from receipt_ocr.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """ASGI test client with the FastAPI lifespan correctly wrapped."""
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
