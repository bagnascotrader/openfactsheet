"""Label vocabularies for fund-profile extraction (decision 0032).

Kept as data (English, German, French, Spanish, Italian) so that the rules are
auditable and extensible; matching is case-insensitive and ignores accents and
trailing colons. Longer labels are tried first.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from types import MappingProxyType

LABELS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "name": (
            "fund name", "name of the fund", "fondsname", "name des fonds", "nom du fonds",
            "nombre del fondo", "nome del fondo", "denominazione del fondo",
        ),
        "objective": (
            "objective and investment policy", "investment objective", "fund objective",
            "investment policy", "investment strategy", "objective", "anlageziel",
            "anlagepolitik", "anlagestrategie", "objectif d'investissement",
            "objectif de gestion", "politique d'investissement", "objetivo de inversion",
            "politica de inversion", "obiettivo d'investimento", "obiettivo di investimento",
            "politica d'investimento",
        ),
        "benchmark": (
            "comparator benchmark", "reference benchmark", "benchmark index", "target benchmark",
            "reference index", "benchmark", "vergleichsindex", "referenzindex",
            "indice de reference", "indice de referencia", "indice di riferimento",
            "parametro di riferimento",
        ),
        "currency": (
            "share class currency", "reference currency", "fund currency", "base currency",
            "currency", "fondswahrung", "wahrung", "devise de reference", "devise", "moneda",
            "divisa", "valuta",
        ),
        "launch_date": (
            "share class launch date", "fund launch date", "launch date", "inception date",
            "auflagedatum", "auflegungsdatum", "date de lancement", "date de creation",
            "fecha de lanzamiento", "fecha de creacion", "data di lancio", "data di avvio",
        ),
        "ISIN": ("isin code", "isin"),
        "WKN": ("wkn",),
        "Valor": ("swiss valor", "valor number", "valorennummer", "valoren", "valor"),
        "SEDOL": ("sedol",),
        "CUSIP": ("cusip",),
        "LEI": ("lei",),
        "FIGI": ("figi",),
        "Bloomberg": ("bloomberg ticker", "bloomberg code", "bloomberg", "ticker"),
        "RIC": ("reuters code", "reuters", "ric"),
    }
)  # fmt: skip

# Words that make a title line look like a fund name.
FUND_WORDS = (
    "fund", "fonds", "sicav", "ucits", "etf", "trust", "portfolio", "fondo", "icav", "fcp",
    "strategy", "strategie",
)  # fmt: skip

ISO_CURRENCIES = frozenset(
    {
        "USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD", "NZD", "SEK", "NOK", "DKK", "HKD",
        "SGD", "CNY", "CNH", "ZAR", "BRL", "MXN", "INR", "KRW", "PLN", "CZK", "HUF", "TRY",
        "ILS", "AED", "SAR", "TWD", "THB", "IDR", "MYR", "PHP", "CLP", "COP", "PEN", "ARS",
        "UYU",
    }
)  # fmt: skip


def fold(text: str) -> str:
    """Lower case without accents, for label matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def match_label(text: str, field: str, *, at_start: bool = True) -> tuple[str, int] | None:
    """Find a label of ``field`` in ``text``: returns (label, end offset) or None.

    With ``at_start`` the label must begin the line; it must be followed by a colon,
    a dash, whitespace or the end of the line.
    """
    folded = fold(text)
    for label in sorted(LABELS[field], key=len, reverse=True):
        pattern = (r"^\s*" if at_start else r"(?:^|(?<=\W))") + re.escape(label)
        m = re.search(pattern + r"(?=\s*[:\-–]|\s|$)", folded)
        if m:
            return label, m.end()
    return None
