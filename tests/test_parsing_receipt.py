"""End-to-end orchestrator tests for `parsing.receipt.parse_receipt`."""

from __future__ import annotations

from receipt_ocr.inference.runner import RawOcrLine
from receipt_ocr.parsing.receipt import parse_receipt


def _kaufland_receipt() -> list[RawOcrLine]:
    """A trimmed-down version of Eric's 2026-05-09 Kaufland Bahnstadt
    receipt — header, four item lines including a multiplier, and the
    totals block. Hand-built rather than from a real OCR run so the
    test stays deterministic."""
    return [
        RawOcrLine(text="Kaufland Stiftung & Co. KG", confidence=0.95, y_offset_px=50),
        RawOcrLine(text="Galileistraße 4", confidence=0.93, y_offset_px=80),
        RawOcrLine(text="69115 Heidelberg-Bahnstadt", confidence=0.94, y_offset_px=110),
        RawOcrLine(text="Tel. +49 6221 714000", confidence=0.91, y_offset_px=140),
        RawOcrLine(text="EUR", confidence=0.85, y_offset_px=200),
        RawOcrLine(text="FROSTA CORN.STAEB.   4,19 A", confidence=0.94, y_offset_px=240),
        RawOcrLine(text="BIO E.ESL-MILCH      1,25 A", confidence=0.93, y_offset_px=270),
        RawOcrLine(text="BIO TAI.TOFU 1,99 € x 2   3,98 A", confidence=0.91, y_offset_px=300),
        RawOcrLine(text="LOEWENSENF MEDIUM    1,79 A", confidence=0.92, y_offset_px=330),
        RawOcrLine(text="Posten: 4", confidence=0.96, y_offset_px=400),
        RawOcrLine(text="SUMME EUR  11,21", confidence=0.97, y_offset_px=430),
    ]


def test_parse_kaufland_receipt_identifies_chain() -> None:
    response = parse_receipt(_kaufland_receipt(), model_id="stub", ocr_ms=42)
    assert response.market.chain_guess == "kaufland"
    assert response.market.store_label_guess == "heidelberg-bahnstadt"


def test_parse_kaufland_receipt_extracts_four_item_lines() -> None:
    response = parse_receipt(_kaufland_receipt(), model_id="stub", ocr_ms=42)
    assert len(response.lines) == 4
    assert [line.line_no for line in response.lines] == [1, 2, 3, 4]


def test_parse_kaufland_receipt_handles_multiplier_line() -> None:
    response = parse_receipt(_kaufland_receipt(), model_id="stub", ocr_ms=42)
    tofu = response.lines[2]  # third item
    assert tofu.raw == "BIO TAI.TOFU"
    assert tofu.price_eur == 1.99
    assert tofu.multiplier == 2
    assert tofu.line_total_eur == 3.98


def test_parse_kaufland_receipt_extracts_totals() -> None:
    response = parse_receipt(_kaufland_receipt(), model_id="stub", ocr_ms=42)
    assert response.totals.items_count == 4
    assert response.totals.total_eur == 11.21


def test_parse_kaufland_receipt_passes_through_metadata() -> None:
    response = parse_receipt(_kaufland_receipt(), model_id="paddleocr-german", ocr_ms=850)
    assert response.model_id == "paddleocr-german"
    assert response.ocr_ms == 850


def test_receipt_with_no_totals_block() -> None:
    """OCR truncated before the SUMME line — totals stay None, items survive."""
    lines = [
        RawOcrLine(text="EDEKA Markt", confidence=0.9, y_offset_px=50),
        RawOcrLine(text="MEHL TYPE 405   0,49 A", confidence=0.9, y_offset_px=200),
    ]
    response = parse_receipt(lines, model_id="stub", ocr_ms=10)
    assert response.market.chain_guess == "edeka"
    assert len(response.lines) == 1
    assert response.totals.items_count is None
    assert response.totals.total_eur is None


def test_empty_input_returns_empty_response() -> None:
    response = parse_receipt([], model_id="stub", ocr_ms=0)
    assert response.market.chain_guess is None
    assert response.lines == []
    assert response.totals.items_count is None


def test_header_without_chain_match_still_passes_through_lines() -> None:
    """Unknown chain — chain_guess None but item parsing still works."""
    lines = [
        RawOcrLine(text="My Local Bakery", confidence=0.85, y_offset_px=50),
        RawOcrLine(text="BAGUETTE          2,50 A", confidence=0.92, y_offset_px=200),
        RawOcrLine(text="Posten: 1", confidence=0.95, y_offset_px=300),
    ]
    response = parse_receipt(lines, model_id="stub", ocr_ms=15)
    assert response.market.chain_guess is None
    assert len(response.lines) == 1
    assert response.lines[0].raw == "BAGUETTE"
    assert response.totals.items_count == 1
