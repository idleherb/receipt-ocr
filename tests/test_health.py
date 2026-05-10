"""Smoke tests for /healthz."""

from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True


async def test_healthz_reflects_runner_load_state(client: AsyncClient) -> None:
    """The default `client` fixture uses a loaded StubRunner; healthz
    must report model_loaded=true and the stub's model_id."""
    response = await client.get("/healthz")
    body = response.json()
    assert body["model_loaded"] is True
    assert body["model_id"] == "stub"


async def test_healthz_reports_unloaded_when_runner_is_stub(
    unloaded_client: AsyncClient,
) -> None:
    """When the runner reports is_loaded=False, healthz follows."""
    response = await unloaded_client.get("/healthz")
    body = response.json()
    assert body["model_loaded"] is False
    assert body["model_id"] == "unloaded"


async def test_healthz_carries_build_metadata(client: AsyncClient) -> None:
    """channel/commit/version come from build args; default values in tests."""
    response = await client.get("/healthz")
    body = response.json()
    assert "channel" in body
    assert "commit" in body
    assert "version" in body
