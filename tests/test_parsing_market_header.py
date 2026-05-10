"""Tests for `parsing.market_header.identify_market`."""

from __future__ import annotations

import pytest

from receipt_ocr.parsing.market_header import identify_market


def test_kaufland_header_with_address() -> None:
    """Eric's 2026-05-09 receipt header pattern."""
    out = identify_market(
        [
            "Kaufland Stiftung & Co. KG",
            "Galileistraße 4",
            "69115 Heidelberg-Bahnstadt",
            "Tel. +49 6221 714000",
        ]
    )
    assert out.chain_guess == "kaufland"
    assert out.store_label_guess == "heidelberg-bahnstadt"
    assert out.header_lines == [
        "Kaufland Stiftung & Co. KG",
        "Galileistraße 4",
        "69115 Heidelberg-Bahnstadt",
        "Tel. +49 6221 714000",
    ]
    assert "Kaufland" in out.header_text


@pytest.mark.parametrize(
    ("header_text", "expected_chain"),
    [
        ("EDEKA Markt Müller", "edeka"),
        ("REWE Markt", "rewe"),
        ("ALDI SÜD GmbH & Co. KG", "aldi-sued"),
        ("ALDI NORD GmbH & Co. KG", "aldi-nord"),
        ("LIDL Stiftung & Co. KG", "lidl"),
        ("PENNY Markt", "penny"),
        ("NETTO Marken-Discount", "netto"),
        ("dm-drogerie markt", "dm"),
        ("ROSSMANN", "rossmann"),
    ],
)
def test_chain_dictionary_covers_common_german_supermarkets(
    header_text: str, expected_chain: str
) -> None:
    out = identify_market([header_text])
    assert out.chain_guess == expected_chain


def test_unknown_chain_returns_none() -> None:
    """A receipt from a chain we haven't curated — returns None,
    doesn't crash. Downstream classifiers handle this gracefully."""
    out = identify_market(["Some Random Mom-and-Pop Shop"])
    assert out.chain_guess is None
    assert out.store_label_guess is None


def test_zip_city_extraction_from_address_line() -> None:
    out = identify_market(["EDEKA Aktiv Markt", "Hauptstr 23", "10117 Berlin"])
    assert out.chain_guess == "edeka"
    assert out.store_label_guess == "berlin"


def test_umlauts_get_slugified_to_ascii() -> None:
    out = identify_market(["REWE", "12345 München-Schwabing"])
    assert out.store_label_guess == "muenchen-schwabing"


def test_no_address_line_yields_no_store_label() -> None:
    out = identify_market(["Kaufland online", "kaufland.de"])
    assert out.chain_guess == "kaufland"
    assert out.store_label_guess is None


def test_empty_header_returns_all_none() -> None:
    out = identify_market([])
    assert out.chain_guess is None
    assert out.store_label_guess is None
    assert out.header_lines == []
    assert out.header_text == ""
