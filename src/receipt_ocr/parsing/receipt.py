"""Orchestrator: turn a list of `RawOcrLine` into the full
`OcrReceiptResponse` shape.

Algorithm:

1. Identify the header (first lines until an item-block-start signal:
   first line containing a recognisable price, or `EUR` column header).
2. Identify the totals block (lines containing `Posten:`, `SUMME`, or
   `MwSt`).
3. Item block = everything between header end and totals start.
4. Run `parse_item_line` on each item-block line.
5. Run `identify_market` on the header lines.
6. Extract `Posten:` count + `SUMME` value from the totals lines.
"""

from __future__ import annotations

import re

from receipt_ocr.inference.runner import RawOcrLine
from receipt_ocr.parsing.line_parser import parse_item_line
from receipt_ocr.parsing.market_header import identify_market
from receipt_ocr.schemas import (
    MarketGuess,
    OcrReceiptResponse,
    ReceiptLine,
    ReceiptTotals,
)

# A line is an "item-block candidate" if it carries a price-like token.
# Checking for the lazy `\d+,\d{2}` pattern is enough — actual parsing
# happens later via `parse_item_line`. Lines without any price (e.g.
# header company-name lines) won't be misclassified as items.
_PRICE_HINT = re.compile(r"\d{1,3}[.,]\d{2}")

# Markers that signal the totals block start.
_TOTALS_START_PATTERNS = [
    re.compile(r"Posten\s*:", re.IGNORECASE),
    re.compile(r"SUMME", re.IGNORECASE),
    re.compile(r"^\s*MwSt", re.IGNORECASE),
]

# Within the totals block, the "Posten: 36" and "SUMME 135,43" extractions.
_POSTEN_COUNT = re.compile(r"Posten\s*:\s*(\d+)", re.IGNORECASE)
_SUMME_VALUE = re.compile(
    r"SUMME[^\d]*(\d{1,5}[.,]\d{2})",
    re.IGNORECASE,
)


def parse_receipt(
    raw_lines: list[RawOcrLine],
    *,
    model_id: str,
    ocr_ms: int,
) -> OcrReceiptResponse:
    """Top-level orchestrator. See module docstring."""
    header_lines, item_lines, totals_lines = _split_blocks(raw_lines)

    market_id = identify_market([line.text for line in header_lines])
    market = MarketGuess(
        chain_guess=market_id.chain_guess,
        store_label_guess=market_id.store_label_guess,
        header_text=market_id.header_text,
        header_lines=market_id.header_lines,
    )

    parsed_lines = []
    for idx, raw in enumerate(item_lines, start=1):
        parsed = parse_item_line(raw.text)
        parsed_lines.append(
            ReceiptLine(
                line_no=idx,
                raw=parsed.raw,
                price_eur=parsed.price_eur,
                multiplier=parsed.multiplier,
                line_total_eur=parsed.line_total_eur,
                tax_marker=parsed.tax_marker,
                y_offset_px=raw.y_offset_px,
                ocr_confidence=raw.confidence,
            )
        )

    totals = _extract_totals(totals_lines)

    return OcrReceiptResponse(
        market=market,
        lines=parsed_lines,
        totals=totals,
        model_id=model_id,
        ocr_ms=ocr_ms,
    )


def _split_blocks(
    raw_lines: list[RawOcrLine],
) -> tuple[list[RawOcrLine], list[RawOcrLine], list[RawOcrLine]]:
    """Split into (header, items, totals) by scanning top-down.

    Heuristic:
      - Header runs from line 0 until the first line containing a
        price-like token (e.g. the first item line).
      - Item block runs from there until the first totals-marker line.
      - Totals block runs from the totals-marker line to end-of-input.

    Edge cases:
      - No item lines at all (empty receipt, OCR misfire) → header is
        everything up to a totals marker (or full input), items is
        empty, totals is the rest.
      - No totals markers → items run to end-of-input, totals empty.
    """
    header: list[RawOcrLine] = []
    items: list[RawOcrLine] = []
    totals: list[RawOcrLine] = []

    state = "header"
    for line in raw_lines:
        text = line.text

        if state in {"header", "items"} and _is_totals_start(text):
            state = "totals"

        if state == "header":
            if _PRICE_HINT.search(text):
                state = "items"
                items.append(line)
            else:
                header.append(line)
        elif state == "items":
            items.append(line)
        else:  # totals
            totals.append(line)

    return header, items, totals


def _is_totals_start(text: str) -> bool:
    return any(p.search(text) for p in _TOTALS_START_PATTERNS)


def _extract_totals(totals_lines: list[RawOcrLine]) -> ReceiptTotals:
    items_count: int | None = None
    total_eur: float | None = None
    for line in totals_lines:
        text = line.text
        if items_count is None:
            count_match = _POSTEN_COUNT.search(text)
            if count_match:
                items_count = int(count_match.group(1))
        if total_eur is None:
            sum_match = _SUMME_VALUE.search(text)
            if sum_match:
                total_eur = float(sum_match.group(1).replace(",", "."))
    return ReceiptTotals(items_count=items_count, total_eur=total_eur)
