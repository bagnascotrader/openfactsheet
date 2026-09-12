"""Security identifiers with deterministic validation (decision 0032).

Identifiers with a check digit (ISIN, CUSIP, SEDOL, LEI, FIGI) are validated and
never "repaired": a code whose check digit fails is reported as invalid. Codes
without a check digit (WKN, Valor, tickers) are accepted only next to their
label. Several national codes are embedded in the ISIN, which links identifiers
to one another (a DE ISIN contains the WKN, US/CA the CUSIP, GB/IE the SEDOL,
CH/LI the Valor).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _value(ch: str) -> int:
    return _ALNUM.index(ch)


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


ISIN_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
CUSIP_RE = re.compile(r"\b([0-9A-Z]{8}[0-9])\b")
SEDOL_RE = re.compile(r"\b([0-9BCDFGHJKLMNPQRSTVWXYZ]{6}[0-9])\b")
LEI_RE = re.compile(r"\b([0-9A-Z]{18}[0-9]{2})\b")
FIGI_RE = re.compile(r"\b([B-DF-HJ-NP-TV-Z]{2}G[B-DF-HJ-NP-TV-Z0-9]{8}[0-9])\b")
WKN_RE = re.compile(r"\b([A-HJ-NP-Z0-9]{6})\b")
VALOR_RE = re.compile(r"\b([0-9]{5,9})\b")
TICKER_RE = re.compile(r"\b([A-Z0-9]{1,12}(?:[ /][A-Z]{2})(?: (?:Equity|Index|EQUITY|INDEX))?)\b")
RIC_RE = re.compile(r"\b([A-Z0-9]{2,15}\.[A-Z]{1,5})\b")


def isin_valid(code: str) -> bool:
    """ISO 6166: letters become 10..35, then the Luhn check over all digits."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", code):
        return False
    return _luhn_ok("".join(str(_value(c)) for c in code))


def cusip_valid(code: str) -> bool:
    """CUSIP check digit: doubled values at even positions, digit sums, mod 10."""
    if not re.fullmatch(r"[0-9A-Z*@#]{8}[0-9]", code):
        return False
    extra = {"*": 36, "@": 37, "#": 38}
    total = 0
    for i, ch in enumerate(code[:8]):
        v = extra[ch] if ch in extra else _value(ch)
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(code[8])


def sedol_valid(code: str) -> bool:
    """SEDOL: weights 1, 3, 1, 7, 3, 9 on six characters (no vowels), check to mod 10."""
    if not re.fullmatch(r"[0-9BCDFGHJKLMNPQRSTVWXYZ]{6}[0-9]", code):
        return False
    weights = (1, 3, 1, 7, 3, 9)
    total = sum(_value(c) * w for c, w in zip(code[:6], weights, strict=True))
    return (10 - total % 10) % 10 == int(code[6])


def lei_valid(code: str) -> bool:
    """ISO 17442: letters become 10..35 and the number is 1 modulo 97."""
    if not re.fullmatch(r"[0-9A-Z]{18}[0-9]{2}", code):
        return False
    return int("".join(str(_value(c)) for c in code)) % 97 == 1


def figi_valid(code: str) -> bool:
    """FIGI (OMG standard): values doubled at odd positions, digit sums, mod 10."""
    if not re.fullmatch(r"[B-DF-HJ-NP-TV-Z]{2}G[B-DF-HJ-NP-TV-Z0-9]{8}[0-9]", code):
        return False
    if code[:2] in {"BS", "BM", "GG", "GB", "GH", "KY", "VG"}:
        return False
    total = 0
    for i, ch in enumerate(code[:11]):
        v = _value(ch)
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(code[11])


CHECKED = {
    "ISIN": (ISIN_RE, isin_valid),
    "CUSIP": (CUSIP_RE, cusip_valid),
    "SEDOL": (SEDOL_RE, sedol_valid),
    "LEI": (LEI_RE, lei_valid),
    "FIGI": (FIGI_RE, figi_valid),
}
# Identifiers without a check digit: only accepted right after their label.
LABEL_ONLY = {"WKN": WKN_RE, "Valor": VALOR_RE, "Bloomberg": TICKER_RE, "RIC": RIC_RE}


@dataclass(frozen=True)
class NationalCode:
    kind: str
    value: str


def national_code(isin: str) -> NationalCode | None:
    """The national identifier embedded in an ISIN, where the construction is standard."""
    country, body = isin[:2], isin[2:11]
    if country in ("US", "CA"):
        return NationalCode("CUSIP", body)
    if country == "DE" and body.startswith("000"):
        return NationalCode("WKN", body[3:])
    if country in ("GB", "IE") and body.startswith("00"):
        return NationalCode("SEDOL", body[2:])
    if country in ("CH", "LI"):
        return NationalCode("Valor", body.lstrip("0"))
    return None


def consistent(isin: str, kind: str, value: str) -> bool | None:
    """Whether ``value`` equals the ``kind`` code embedded in ``isin`` (None: not embedded)."""
    embedded = national_code(isin)
    if embedded is None or embedded.kind != kind:
        return None
    if kind == "Valor":
        return embedded.value == value.lstrip("0")
    return embedded.value == value
