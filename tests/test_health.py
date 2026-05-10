"""Smoke tests for /healthz."""

from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True


async def test_healthz_reports_unloaded_model_in_phase_1(client: AsyncClient) -> None:
    """Phase 1 has no OCR engine; model_loaded is hardcoded false until Phase 2."""
    response = await client.get("/healthz")
    body = response.json()
    assert body["model_loaded"] is False
    assert body["model_id"] == "unloaded"


async def test_healthz_carries_build_metadata(client: AsyncClient) -> None:
    """channel/commit/version come from build args; default values in tests."""
    response = await client.get("/healthz")
    body = response.json()
    # Defaults from Settings; CI overrides via env vars at build time.
    assert "channel" in body
    assert "commit" in body
    assert "version" in body
