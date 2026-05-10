"""OCR runner Protocol — the seam between the FastAPI app and whichever
backend actually does image-to-text.

Tests run against a deterministic stub (`tests/conftest.py:StubRunner`)
implementing this Protocol. The real engine wrapper lives in
`paddle_runner.py` and is excluded from coverage because verifying its
behaviour requires the PaddleOCR model files on disk (~100 MB) and is
covered by integration smoke tests, not unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RawOcrLine:
    """A single OCR-detected text line as the engine returns it.

    Pre-parsing form: this carries the raw recognised text plus
    confidence and vertical position. Downstream parsing
    (`receipt_ocr.parsing`) extracts price, multiplier, tax-marker, and
    classifies item-block-vs-totals-block from a list of these.
    """

    text: str
    confidence: float
    y_offset_px: int


class OcrRunner(Protocol):
    """Backend-agnostic OCR Protocol.

    Implementations: ``PaddleRunner`` (paddle_runner.py) wraps PaddleOCR;
    ``_UnloadedStub`` in ``main.py`` returns a sentinel when the engine
    failed to load. Tests use ``StubRunner`` from ``tests/conftest.py``
    which returns deterministic fixture output.
    """

    @property
    def is_loaded(self) -> bool: ...

    @property
    def model_id(self) -> str: ...

    def ocr(self, image_bytes: bytes) -> list[RawOcrLine]: ...
