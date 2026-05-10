"""Settings layer tests — env-prefix, defaults, types."""

from __future__ import annotations

import pytest

from receipt_ocr.config import Settings


def test_defaults_are_walking_skeleton_safe() -> None:
    """No env vars set ⇒ Settings loads with safe defaults."""
    s = Settings()
    assert s.n_threads is None
    assert s.build_channel == "dev"
    assert s.build_sha == "unknown"
    assert s.build_date == "unknown"
    assert s.model_loaded is False


def test_env_prefix_is_receipt_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings reads env vars prefixed with RECEIPT_OCR_."""
    monkeypatch.setenv("RECEIPT_OCR_BUILD_CHANNEL", "main")
    monkeypatch.setenv("RECEIPT_OCR_BUILD_SHA", "abcdef0")
    monkeypatch.setenv("RECEIPT_OCR_N_THREADS", "4")
    s = Settings()
    assert s.build_channel == "main"
    assert s.build_sha == "abcdef0"
    assert s.n_threads == 4


def test_unknown_env_var_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """extra='ignore' ⇒ unrelated env vars do not blow up Settings()."""
    monkeypatch.setenv("RECEIPT_OCR_NOT_A_REAL_FIELD", "anything")
    Settings()  # should not raise
