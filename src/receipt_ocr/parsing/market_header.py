"""Detect the supermarket chain from a receipt's header lines.

The first ~5 OCR-line outputs of a German printed receipt almost
always carry the chain logo / brand text plus a store address. This
module matches them against a small per-chain regex dictionary and
extracts a coarse store-label hint when possible. Misses are silent:
the orchestrator handles `chain_guess=None` gracefully — downstream
classifiers (vorrat ADR-0038) just lose their per-market correction
lookup, falling back to OFF + LLM.

Adding a new chain costs one tuple in `_CHAIN_PATTERNS` plus a fixture
in `tests/test_parsing_market_header.py`. PRs welcome.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Each tuple: (chain-slug, list-of-regex-patterns). Patterns are
# matched against any of the header lines (case-insensitive). First
# slug whose pattern hits wins. Order matters only for tie-breaking
# — keep more-specific chains earlier when ambiguity is possible
# (e.g. ALDI Süd vs ALDI Nord).
_CHAIN_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    (
        "kaufland",
        [
            re.compile(r"\bKaufland\b", re.IGNORECASE),
            re.compile(r"kaufland\.de", re.IGNORECASE),
        ],
    ),
    (
        "edeka",
        [
            re.compile(r"\bEDEKA\b", re.IGNORECASE),
            re.compile(r"E[\s-]*center", re.IGNORECASE),
        ],
    ),
    (
        "rewe",
        [
            re.compile(r"\bREWE\b", re.IGNORECASE),
            re.compile(r"rewe\.de", re.IGNORECASE),
        ],
    ),
    (
        "aldi-sued",
        [
            re.compile(r"ALDI[\s-]*S(?:Ü|UE)D", re.IGNORECASE),
        ],
    ),
    (
        "aldi-nord",
        [
            re.compile(r"ALDI[\s-]*NORD", re.IGNORECASE),
        ],
    ),
    (
        "lidl",
        [
            re.compile(r"\bLIDL\b", re.IGNORECASE),
        ],
    ),
    (
        "penny",
        [
            re.compile(r"\bPENNY\b", re.IGNORECASE),
        ],
    ),
    (
        "netto",
        [
            re.compile(r"\bNETTO\b", re.IGNORECASE),
        ],
    ),
    (
        "dm",
        [
            re.compile(r"\bdm[\s-]*drogerie", re.IGNORECASE),
        ],
    ),
    (
        "rossmann",
        [
            re.compile(r"\bROSSMANN\b", re.IGNORECASE),
        ],
    ),
]


# Store-label hint extraction. We aim for the German "Postal-Code +
# City [+ District]" pattern that appears in headers (e.g.
# "69115 Heidelberg-Bahnstadt"). The label = the city + optional
# district, lowercased + slugified.
_ZIP_CITY = re.compile(
    r"""
    \b(\d{5})\s+
    # capitalised city, optional dash- or space-joined district:
    ([A-ZÄÖÜ][a-zäöüß]+(?:[\s-][A-ZÄÖÜ][a-zäöüß]+)*)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class MarketIdentification:
    """Result of header-based market detection."""

    chain_guess: str | None
    store_label_guess: str | None
    header_text: str
    header_lines: list[str]


def identify_market(header_lines: list[str]) -> MarketIdentification:
    """Match `header_lines` against the chain dictionary.

    Returns a `MarketIdentification` with `chain_guess=None` if no
    chain matched — that's a normal outcome for receipts from chains
    we haven't curated regex for yet.
    """
    chain_guess = _detect_chain(header_lines)
    store_label = _detect_store_label(header_lines)
    return MarketIdentification(
        chain_guess=chain_guess,
        store_label_guess=store_label,
        header_text="\n".join(header_lines),
        header_lines=list(header_lines),
    )


def _detect_chain(header_lines: list[str]) -> str | None:
    for chain_slug, patterns in _CHAIN_PATTERNS:
        for line in header_lines:
            for pattern in patterns:
                if pattern.search(line):
                    return chain_slug
    return None


def _detect_store_label(header_lines: list[str]) -> str | None:
    for line in header_lines:
        match = _ZIP_CITY.search(line)
        if match:
            city = match.group(2)
            return _slugify(city)
    return None


def _slugify(text: str) -> str:
    """Lowercase + dash-join a 'City-Name' or 'Heidelberg Bahnstadt'."""
    cleaned = (
        text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    )
    cleaned = re.sub(r"[\s_]+", "-", cleaned.strip())
    return cleaned
