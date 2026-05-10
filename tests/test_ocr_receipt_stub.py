"""Phase 1: /ocr-receipt is a 503 stub. Phase 2 replaces this test."""

from __future__ import annotations

from io import BytesIO

from httpx import AsyncClient


async def test_ocr_receipt_returns_503_in_phase_1(client: AsyncClient) -> None:
    """Mirrors the off-classifier convention: routes that need a model
    return 503 cleanly when no model is loaded, rather than crashing
    or returning fake data.
    """
    # Send a tiny fake JPEG body — the route accepts any image bytes
    # and short-circuits before parsing in Phase 1.
    files = {"image": ("fake.jpg", BytesIO(b"\xff\xd8\xff\xd9"), "image/jpeg")}
    response = await client.post("/ocr-receipt", files=files)
    assert response.status_code == 503
    assert response.json()["detail"] == "model not loaded"
