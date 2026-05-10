"""Integration tests for POST /ocr-receipt.

The route is exercised with a loaded StubRunner (configured to return
canned OCR output); the engine itself is never imported during tests.
The Phase-1 `503-when-stub-unloaded` behaviour is preserved and
covered too.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from receipt_ocr.inference.runner import RawOcrLine
from receipt_ocr.main import app
from tests.conftest import StubRunner


def _kaufland_lines() -> list[RawOcrLine]:
    return [
        RawOcrLine(text="Kaufland Stiftung", confidence=0.95, y_offset_px=50),
        RawOcrLine(text="69115 Heidelberg-Bahnstadt", confidence=0.94, y_offset_px=80),
        RawOcrLine(text="MEHL TYPE 405   0,49 A", confidence=0.93, y_offset_px=200),
        RawOcrLine(text="BIO TAI.TOFU 1,99 € x 2   3,98 A", confidence=0.91, y_offset_px=230),
        RawOcrLine(text="Posten: 2", confidence=0.96, y_offset_px=300),
        RawOcrLine(text="SUMME EUR 4,47", confidence=0.97, y_offset_px=330),
    ]


@pytest.fixture
async def kaufland_client():
    """A test client wired with a Kaufland-receipt-fixture StubRunner."""
    runner = StubRunner(lines=_kaufland_lines(), model_id="stub-kaufland")
    async with LifespanManager(app):
        app.state.runner = runner
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c, runner


async def test_ocr_receipt_with_loaded_runner_returns_parsed_response(
    kaufland_client,
) -> None:
    client, runner = kaufland_client
    files = {"image": ("fake.jpg", BytesIO(b"\xff\xd8\xff\xd9"), "image/jpeg")}
    response = await client.post("/ocr-receipt", files=files)
    assert response.status_code == 200
    body = response.json()

    assert body["market"]["chain_guess"] == "kaufland"
    assert body["market"]["store_label_guess"] == "heidelberg-bahnstadt"
    assert len(body["lines"]) == 2
    assert body["lines"][1]["raw"] == "BIO TAI.TOFU"
    assert body["lines"][1]["multiplier"] == 2
    assert body["lines"][1]["line_total_eur"] == 3.98
    assert body["totals"]["items_count"] == 2
    assert body["totals"]["total_eur"] == 4.47
    assert body["model_id"] == "stub-kaufland"
    assert "ocr_ms" in body
    # The runner saw exactly one image upload.
    assert len(runner.calls) == 1


async def test_ocr_receipt_with_unloaded_stub_returns_503(
    unloaded_client: AsyncClient,
) -> None:
    """When the runner reports is_loaded=False, /ocr-receipt 503s."""
    files = {"image": ("fake.jpg", BytesIO(b"\xff\xd8\xff\xd9"), "image/jpeg")}
    response = await unloaded_client.post("/ocr-receipt", files=files)
    assert response.status_code == 503
    assert response.json()["detail"] == "model not loaded"


async def test_ocr_receipt_rejects_non_image_content_type(
    kaufland_client,
) -> None:
    client, _ = kaufland_client
    files = {"image": ("notes.txt", BytesIO(b"hello"), "text/plain")}
    response = await client.post("/ocr-receipt", files=files)
    assert response.status_code == 422
    assert "unsupported content-type" in response.json()["detail"]


async def test_ocr_receipt_rejects_empty_image(kaufland_client) -> None:
    client, _ = kaufland_client
    files = {"image": ("empty.jpg", BytesIO(b""), "image/jpeg")}
    response = await client.post("/ocr-receipt", files=files)
    assert response.status_code == 422
    assert "empty image" in response.json()["detail"]


async def test_ocr_receipt_rejects_oversized_image(kaufland_client) -> None:
    client, _ = kaufland_client
    # 8 MiB + 1 byte
    big = BytesIO(b"\x00" * (8 * 1024 * 1024 + 1))
    files = {"image": ("big.jpg", big, "image/jpeg")}
    response = await client.post("/ocr-receipt", files=files)
    assert response.status_code == 413
