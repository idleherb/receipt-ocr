"""Tests for the OCR runner Protocol surface.

Real PaddleRunner is excluded from coverage and tested via the
integration smoke flow. This file pins the Protocol contract: the
StubRunner must satisfy OcrRunner, and _UnloadedStub must report
is_loaded=False and raise on .ocr() so accidental bypasses surface
loudly rather than returning fake data.
"""

from __future__ import annotations

import pytest

from receipt_ocr.inference.runner import OcrRunner, RawOcrLine
from receipt_ocr.main import _UnloadedStub
from tests.conftest import StubRunner


def test_stub_runner_satisfies_runner_protocol() -> None:
    runner: OcrRunner = StubRunner()
    assert runner.is_loaded is True
    assert runner.model_id == "stub"
    assert runner.ocr(b"") == []


def test_stub_runner_returns_configured_lines() -> None:
    lines = [
        RawOcrLine(text="MEHL", confidence=0.95, y_offset_px=100),
        RawOcrLine(text="MILCH", confidence=0.91, y_offset_px=140),
    ]
    runner = StubRunner(lines=lines)
    out = runner.ocr(b"\xff\xd8\xff\xd9")
    assert out == lines
    # Calls are recorded for assertion in higher-level tests.
    assert runner.calls == [b"\xff\xd8\xff\xd9"]


def test_unloaded_stub_reports_unloaded() -> None:
    stub = _UnloadedStub()
    assert stub.is_loaded is False
    assert stub.model_id == "unloaded"


def test_unloaded_stub_raises_on_ocr_bypass() -> None:
    """Endpoints short-circuit on is_loaded=False before .ocr() is
    called; an accidental bypass should raise rather than silently
    return fake data."""
    stub = _UnloadedStub()
    with pytest.raises(RuntimeError, match="not loaded"):
        stub.ocr(b"")
