"""Settings layer tests — env-prefix, defaults, types."""

from __future__ import annotations

import pytest

from receipt_ocr.config import Settings


def test_defaults_are_production_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default settings work in production without any env-var set.

    We undo conftest's `RECEIPT_OCR_DISABLE_ENGINE=true` for this test
    so we see the real default (False).
    """
    monkeypatch.delenv("RECEIPT_OCR_DISABLE_ENGINE", raising=False)
    s = Settings()
    assert s.n_threads is None
    assert s.build_channel == "dev"
    assert s.build_sha == "unknown"
    assert s.build_date == "unknown"
    assert s.lang == "german"
    assert s.disable_engine is False


def test_env_prefix_is_receipt_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings reads env vars prefixed with RECEIPT_OCR_."""
    monkeypatch.setenv("RECEIPT_OCR_BUILD_CHANNEL", "main")
    monkeypatch.setenv("RECEIPT_OCR_BUILD_SHA", "abcdef0")
    monkeypatch.setenv("RECEIPT_OCR_N_THREADS", "4")
    monkeypatch.setenv("RECEIPT_OCR_LANG", "en")
    s = Settings()
    assert s.build_channel == "main"
    assert s.build_sha == "abcdef0"
    assert s.n_threads == 4
    assert s.lang == "en"


def test_disable_engine_flag_is_a_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    """disable_engine accepts the standard pydantic-settings bool
    forms ('true', '1', 'yes', etc.).
    """
    monkeypatch.setenv("RECEIPT_OCR_DISABLE_ENGINE", "true")
    assert Settings().disable_engine is True
    monkeypatch.setenv("RECEIPT_OCR_DISABLE_ENGINE", "false")
    assert Settings().disable_engine is False


def test_unknown_env_var_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """extra='ignore' ⇒ unrelated env vars do not blow up Settings()."""
    monkeypatch.setenv("RECEIPT_OCR_NOT_A_REAL_FIELD", "anything")
    Settings()  # should not raise
