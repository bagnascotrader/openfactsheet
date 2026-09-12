"""Identifier validation against public codes and single-character corruption (decision 0032)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from openfactsheet.documents.identifiers import (
    consistent,
    cusip_valid,
    figi_valid,
    isin_valid,
    lei_valid,
    national_code,
    sedol_valid,
)

# Public identifiers of listed companies (Apple, SAP, Nestle, BAE Systems) and funds.
VALID = {
    "ISIN": ["US0378331005", "DE0007164600", "CH0038863350", "GB0002634946", "LU0048578792"],
    "CUSIP": ["037833100"],
    "SEDOL": ["2046251", "0263494"],
    "FIGI": ["BBG000B9XRY4"],
    "LEI": ["HWUPKR0MPOU8FGXBT394"],
}
CHECKS = {
    "ISIN": isin_valid,
    "CUSIP": cusip_valid,
    "SEDOL": sedol_valid,
    "FIGI": figi_valid,
    "LEI": lei_valid,
}
_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@pytest.mark.parametrize(("kind", "code"), [(k, c) for k, cs in VALID.items() for c in cs])
def test_public_codes_are_valid(kind: str, code: str) -> None:
    assert CHECKS[kind](code)


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("ISIN", "US0378331006"),
        ("ISIN", "us0378331005"),
        ("CUSIP", "037833101"),
        ("SEDOL", "2046252"),
        ("SEDOL", "2A46251"),  # vowels are not used in SEDOLs
        ("FIGI", "BBG000B9XRY5"),
        ("FIGI", "GBG000B9XRY4"),  # reserved prefix
        ("LEI", "HWUPKR0MPOU8FGXBT395"),
    ],
)
def test_corrupted_codes_are_invalid(kind: str, code: str) -> None:
    assert not CHECKS[kind](code)


# The check digits catch every single-digit substitution. A letter becomes two digits
# before checking, so some letter substitutions pass: a documented limitation
# (decision 0032) that the cross-identifier checks and OCR confidence complement.
@given(position=st.integers(min_value=2, max_value=11), char=st.sampled_from("0123456789"))
def test_any_single_digit_change_to_an_isin_breaks_it(position: int, char: str) -> None:
    isin = "US0378331005"
    if not isin[position].isdigit():
        return
    changed = isin[:position] + char + isin[position + 1 :]
    if changed != isin:
        assert not isin_valid(changed)


@given(position=st.integers(min_value=0, max_value=19), char=st.sampled_from("0123456789"))
def test_any_single_digit_change_to_an_lei_breaks_it(position: int, char: str) -> None:
    lei = "HWUPKR0MPOU8FGXBT394"
    if not lei[position].isdigit():
        return
    changed = lei[:position] + char + lei[position + 1 :]
    if changed != lei:
        assert not lei_valid(changed)


def test_national_codes_embedded_in_isins() -> None:
    assert national_code("DE0007164600") == national_code("DE0007164600")
    assert consistent("DE0007164600", "WKN", "716460") is True
    assert consistent("DE0007164600", "WKN", "716461") is False
    assert consistent("US0378331005", "CUSIP", "037833100") is True
    assert consistent("GB0002634946", "SEDOL", "0263494") is True
    assert consistent("CH0038863350", "Valor", "003886335") is True
    assert consistent("LU0048578792", "WKN", "123456") is None  # LU ISINs embed no code
