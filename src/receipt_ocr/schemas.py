"""Pydantic schemas for the public API."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class MarketGuess(BaseModel):
    """Best-effort identification of the receipt's source store."""

    chain_guess: str | None = Field(default=None)
    """A normalised slug — e.g. `"kaufland"`, `"edeka"`, `"rewe"` —
    when the header text matches a known chain. None if no match."""

    store_label_guess: str | None = Field(default=None)
    """Coarse "which branch" hint extracted from the header (city,
    Bahnstadt, etc.). None if no extractable hint."""

    header_text: str = Field(default="")
    """Full concatenation of the header lines, joined by newlines.
    Useful for downstream tools (the food-classifier / future debug
    UIs) without re-parsing."""

    header_lines: list[str] = Field(default_factory=list)
    """The raw OCR lines identified as part of the header (typically
    the first ~5 lines before the item block)."""


class ReceiptLine(BaseModel):
    """One parsed item-block line.

    Multipliers vs. unit-price-vs-line-total semantics:
      - For a line `1,99 € x 2  3,98 A`:
        `price_eur = 1.99` (unit), `multiplier = 2`,
        `line_total_eur = 3.98`.
      - For a line `4,79 A`:
        `price_eur = 4.79` (unit = total), `multiplier = 1`,
        `line_total_eur = 4.79`.
    """

    line_no: int
    """1-indexed position in the item block (after header, before totals)."""

    raw: str
    """The item-name token, with price + multiplier expressions
    stripped. The downstream classifier (vorrat ADR-0038's
    /lebensmittel) maps this to a Lebensmittel."""

    price_eur: float | None = Field(default=None)
    """Unit price in euros. None when no price could be parsed
    (rare — usually the line was malformed OCR output)."""

    multiplier: int = Field(default=1)
    """Quantity multiplier. Default 1 when no `x N` expression was
    found on the line."""

    line_total_eur: float | None = Field(default=None)
    """Total for this line = price_eur × multiplier. Pre-computed so
    downstream consumers don't have to recompute and risk float
    rounding drift."""

    tax_marker: str | None = Field(default=None)
    """Trailing single- or double-letter MwSt-marker (e.g. `A`, `B`,
    `AW`). Surfaced because some chains use it as a signal for
    food-vs-non-food (B = reduced VAT). None if no marker present."""

    y_offset_px: int = Field(default=0)
    """Vertical position of this line in the source image, for debug."""

    ocr_confidence: float = Field(default=0.0)
    """Engine-reported confidence on the recognised text. Range [0,1]."""


class ReceiptTotals(BaseModel):
    """Totals block from the bottom of the receipt."""

    items_count: int | None = Field(default=None)
    """Number of items as the receipt itself reports — typically next
    to a `Posten:` label. None if no such line was detected."""

    total_eur: float | None = Field(default=None)
    """Total amount as the receipt reports (typically next to `SUMME`).
    Useful as an integrity check against the sum of line totals."""


class OcrReceiptResponse(BaseModel):
    """Full /ocr-receipt response per vorrat ADR-0039 §2a."""

    market: MarketGuess
    lines: list[ReceiptLine]
    totals: ReceiptTotals
    model_id: str
    ocr_ms: int
