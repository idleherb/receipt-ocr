"""Pydantic schemas for the public API."""

from __future__ import annotations

from pydantic import BaseModel


class HealthzResponse(BaseModel):
    """Liveness + build-info report.

    Same shape as the off-classifier's /healthz, deliberately. Watchtower
    polls this; the build's CI smoke-test asserts on these fields. Adding
    fields is fine; renaming or removing requires a coordinated change in
    the consumer side.
    """

    ok: bool
    channel: str
    version: str
    commit: str
    model_loaded: bool
    model_id: str
