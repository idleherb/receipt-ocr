"""Parse a single OCR line into (raw_token, price, multiplier, tax_marker).

Item-block lines on German supermarket receipts follow a few common
patterns. This parser handles the conservative subset that covers
Kaufland / Edeka / Rewe receipts seen in real-world fixtures; chain-
specific quirks land in `markets.py` not here.

Examples handled (tested in tests/test_parsing_line.py):

  "FROSTA CORN.STAEB.   4,19 A"
      -> raw="FROSTA CORN.STAEB.", price=4.19, multiplier=1, tax="A"
  "BIO TAI.TOFU 1,99 EUR x 2   3,98 A"
      -> raw="BIO TAI.TOFU", price=1.99, multiplier=2, tax="A"
  "ZEITSCHRIFT.ERM.    12,99*A"
      -> raw="ZEITSCHRIFT.ERM.", price=12.99, tax="A" (asterisk dropped)
  "GEMISCHTER STRAUSS  29,99 A"
      -> raw="GEMISCHTER STRAUSS", price=29.99, tax="A"
  "DE CEC.FARFALLE  1,49 AW"
      -> raw="DE CEC.FARFALLE", price=1.49, tax="AW"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Trailing price + optional currency + optional tax marker.
# Examples matched by group(1)/group(2):
#   "4,19 A"        -> ("4,19", "A")
#   "12,99*A"       -> ("12,99", "A")  (the * is consumed but not in groups)
#   "1,49 AW"       -> ("1,49", "AW")
#   "29,99"         -> ("29,99", None)
#   "0,30 B"        -> ("0,30", "B")
_PRICE_AND_TAX = re.compile(
    r"""
    (\d{1,3}[.,]\d{2})    # group 1: the price itself, comma or dot decimal
    \s*[*€]?              # optional asterisk (some chains print 12,99*A) or euro sign
    \s*(?:€|EUR)?         # optional currency word
    \s*([A-Z]{1,3})?      # group 2: optional 1-3 letter tax marker
    \s*$                  # anchored to end-of-line
    """,
    re.VERBOSE,
)

# Multiplier expression appearing earlier in the line.
# Examples matched by group(1)/group(2):
#   "1,99 € x 2"    -> ("1,99", "2")
#   "1,05 €  x 2"   -> ("1,05", "2")
#   "1,99€x2"       -> ("1,99", "2")
_MULTIPLIER = re.compile(
    r"""
    (\d{1,3}[.,]\d{2})    # group 1: unit price
    \s*€?                 # optional euro sign with optional whitespace
    \s*[x×]          # multiplier symbol (ASCII x or unicode times-sign)
    \s*(\d{1,2})          # group 2: count
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class ParsedLine:
    """Structured form of a single item-block line.

    Defaults match "no price could be parsed" — useful when an OCR
    artefact landed in the item block (multi-line wraps, dirt smudges)
    and downstream needs to handle the row gracefully.
    """

    raw: str
    price_eur: float | None = None
    multiplier: int = 1
    line_total_eur: float | None = None
    tax_marker: str | None = field(default=None)


def parse_item_line(text: str) -> ParsedLine:
    """Decompose a receipt line into raw-token + price + multiplier.

    Returns a ParsedLine with `price_eur=None` when no price pattern
    matched (typically: an OCR-artifact row that strayed into the item
    block). Callers can filter such rows out if they want strict-only
    behaviour.
    """
    if not text or not text.strip():
        return ParsedLine(raw="")

    price_match = _PRICE_AND_TAX.search(text)
    if not price_match:
        return ParsedLine(raw=text.strip())

    line_total = _to_float(price_match.group(1))
    tax_marker = price_match.group(2)

    # Strip the trailing price+tax span; what remains is the body.
    body = text[: price_match.start()].rstrip()

    mul_match = _MULTIPLIER.search(body)
    if mul_match:
        unit_price = _to_float(mul_match.group(1))
        multiplier = int(mul_match.group(2))
        # Token = body before the multiplier expression.
        token = body[: mul_match.start()].rstrip()
        return ParsedLine(
            raw=token,
            price_eur=unit_price,
            multiplier=multiplier,
            line_total_eur=line_total,
            tax_marker=tax_marker,
        )

    # No multiplier ⇒ line_total is itself the unit price.
    return ParsedLine(
        raw=body,
        price_eur=line_total,
        multiplier=1,
        line_total_eur=line_total,
        tax_marker=tax_marker,
    )


def _to_float(numeric: str) -> float:
    """Convert "4,19" or "4.19" to 4.19. German receipts use comma."""
    return float(numeric.replace(",", "."))
