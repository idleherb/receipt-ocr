"""Tests for `parsing.line_parser.parse_item_line`."""

from __future__ import annotations

import pytest

from receipt_ocr.parsing.line_parser import parse_item_line


def test_simple_item_with_price_and_tax_marker() -> None:
    out = parse_item_line("FROSTA CORN.STAEB.   4,19 A")
    assert out.raw == "FROSTA CORN.STAEB."
    assert out.price_eur == 4.19
    assert out.multiplier == 1
    assert out.line_total_eur == 4.19
    assert out.tax_marker == "A"


def test_item_with_multiplier() -> None:
    out = parse_item_line("BIO TAI.TOFU 1,99 € x 2   3,98 A")
    assert out.raw == "BIO TAI.TOFU"
    assert out.price_eur == 1.99
    assert out.multiplier == 2
    assert out.line_total_eur == 3.98
    assert out.tax_marker == "A"


def test_item_with_asterisk_separator_before_tax() -> None:
    """Some chains print prices like '12,99*A' without a space."""
    out = parse_item_line("ZEITSCHRIFT.ERM.    12,99*A")
    assert out.raw == "ZEITSCHRIFT.ERM."
    assert out.price_eur == 12.99
    assert out.tax_marker == "A"


def test_item_with_two_letter_tax_marker() -> None:
    out = parse_item_line("DE CEC.FARFALLE  1,49 AW")
    assert out.raw == "DE CEC.FARFALLE"
    assert out.price_eur == 1.49
    assert out.tax_marker == "AW"


def test_item_without_tax_marker() -> None:
    out = parse_item_line("BIO E.ESL-MILCH    1,25")
    assert out.raw == "BIO E.ESL-MILCH"
    assert out.price_eur == 1.25
    assert out.tax_marker is None


def test_item_with_dot_decimal_separator() -> None:
    """Some OCR outputs use '.' instead of ',' as decimal separator."""
    out = parse_item_line("KERRYGOLD CHEDDAR  2.99 A")
    assert out.price_eur == 2.99


def test_line_with_no_price_returns_raw_only() -> None:
    """OCR artifacts that strayed into the item block — no price found."""
    out = parse_item_line("---some-noise---")
    assert out.raw == "---some-noise---"
    assert out.price_eur is None
    assert out.line_total_eur is None
    assert out.tax_marker is None
    assert out.multiplier == 1


def test_empty_line_returns_empty_raw() -> None:
    out = parse_item_line("")
    assert out.raw == ""
    assert out.price_eur is None


def test_whitespace_only_line_returns_empty() -> None:
    out = parse_item_line("   ")
    assert out.raw == ""


@pytest.mark.parametrize(
    ("text", "expected_price", "expected_multiplier", "expected_total"),
    [
        ("LOEWENSENF MEDIUM    1,79 A", 1.79, 1, 1.79),
        ("LOEWENSENF SCHARF    1,69 A", 1.69, 1, 1.69),
        ("SCHW.SPEISEQU 1,05 € x 2   2,10 A", 1.05, 2, 2.10),
        ("BIO SWM SPEI. 1,69 € x 2   3,38 A", 1.69, 2, 3.38),
    ],
)
def test_real_kaufland_receipt_lines(
    text: str, expected_price: float, expected_multiplier: int, expected_total: float
) -> None:
    """A small sampling from Eric's 2026-05-09 Kaufland receipt."""
    out = parse_item_line(text)
    assert out.price_eur == pytest.approx(expected_price)
    assert out.multiplier == expected_multiplier
    assert out.line_total_eur == pytest.approx(expected_total)
