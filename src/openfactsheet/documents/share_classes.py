"""Share classes of a factsheet and which one the monthly-return table shows (decision 0033).

Classes are detected from a class table (a header with a class word and an
identifier column, then one row per class) or from lines that name a class next
to an ISIN. The performance table is attributed to a class by fixed rules, in
order:

1. its caption or footnote names exactly one class (label or ISIN);
2. the performance heading above it names exactly one class;
3. the document has exactly one class;
4. a currency printed in its caption matches exactly one class.

The first rule that decides wins; rules that decide differently make the
attribution ``ambiguous``, as does the absence of any deciding rule when there
are several classes. OpenFactsheet never guesses (for example "the first class
listed"): ambiguity is reported with the candidates.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from openfactsheet.documents.identifiers import ISIN_RE, isin_valid
from openfactsheet.documents.labels import ISO_CURRENCIES, fold
from openfactsheet.documents.layout import PageLayout

_CLASS_WORD = (
    r"(?:share\s+class|unit\s+class|class|anteilsklasse|anteilklasse|classe\s+d['e]\s*"
    r"(?:actions|parts)|classe|clase|klasse)"
)
_CLASS_IN_LINE = re.compile(
    _CLASS_WORD + r"\s+([A-Z0-9][A-Za-z0-9\-.]{0,11}(?:\s+(?:[A-Z]{3}|[A-Z]\d?|Acc|Dist|Inc"
    r"|Hedged|Hdg|H|Accumulating|Distributing|thes|aus|Cap|D|C)\b)*)",
    re.IGNORECASE,
)
_PERFORMANCE_WORDS = (
    "performance", "wertentwicklung", "rendement", "rentabilidad", "rendimento",
    "monthly returns", "monatliche", "returns",
)  # fmt: skip

AttributionStatus = Literal["attributed", "ambiguous", "no_share_classes"]


@dataclass(frozen=True)
class ShareClass:
    label: str
    isins: tuple[str, ...]
    currency: str | None
    page: int
    snippet: str

    def mentioned_in(self, text: str) -> bool:
        folded = re.sub(r"\s+", " ", fold(text))
        if any(isin in text.upper() for isin in self.isins):
            return True
        label = re.sub(r"\s+", " ", fold(self.label))
        if re.search(r"\bclass(?:e|e d'actions|e de parts)?\s+" + re.escape(label) + r"\b", folded):
            return True
        return len(label) >= 5 and re.search(r"\b" + re.escape(label) + r"\b", folded) is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "isins": list(self.isins),
            "currency": self.currency,
            "page": self.page,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class Attribution:
    """Which share class the monthly-return table shows, and why (or why not)."""

    status: AttributionStatus
    share_class: str | None = None
    rule: str | None = None
    evidence: str | None = None
    candidates: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "share_class": self.share_class,
            "rule": self.rule,
            "evidence": self.evidence,
            "candidates": list(self.candidates),
        }

    def to_text(self) -> str:
        if self.status == "attributed":
            return f"Returns table shows:       class {self.share_class} ({self.rule})"
        if self.status == "ambiguous":
            return (
                "Returns table shows:       not determinable between "
                + ", ".join(self.candidates)
                + (f" ({self.evidence})" if self.evidence else "")
            )
        return ""


def _currency(text: str) -> str | None:
    codes = [t for t in re.findall(r"\b[A-Z]{3}\b", text) if t in ISO_CURRENCIES]
    return codes[0] if codes else None


def _clean_label(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip(" :-–")


def detect_share_classes(layouts: Sequence[PageLayout]) -> list[ShareClass]:
    """Share classes named with an ISIN (same line, or a class-table row)."""
    found: dict[str, ShareClass] = {}

    def add(label: str, isins: list[str], currency: str | None, page: int, line: str) -> None:
        label = _clean_label(label)
        if not label:
            return
        key = fold(label)
        if key in found:
            old = found[key]
            merged = tuple(dict.fromkeys((*old.isins, *isins)))
            found[key] = ShareClass(
                old.label, merged, old.currency or currency, old.page, old.snippet
            )
        else:
            found[key] = ShareClass(label, tuple(isins), currency, page, line[:160])

    for layout in layouts:
        lines = layout.lines
        in_table = False
        for i, line in enumerate(lines):
            text = line.text
            isins = [m for m in ISIN_RE.findall(text.upper()) if isin_valid(m)]
            header = re.search(_CLASS_WORD, fold(text)) and "isin" in fold(text) and not isins
            if header:
                in_table = True
                continue
            m = _CLASS_IN_LINE.search(text)
            if m and isins:
                add(
                    m.group(1),
                    isins,
                    _currency(text[m.end() :]) or _currency(text),
                    layout.page,
                    text,
                )
                continue
            if m and not isins and i + 1 < len(lines):
                nxt = lines[i + 1].text
                nxt_isins = [x for x in ISIN_RE.findall(nxt.upper()) if isin_valid(x)]
                if nxt_isins and not _CLASS_IN_LINE.search(nxt):
                    add(m.group(1), nxt_isins, _currency(text) or _currency(nxt), layout.page, text)
                    continue
            if in_table:
                if not isins:
                    in_table = False  # the class table ends at the first row without an ISIN
                    continue
                first = text.upper().find(isins[0])
                label = text[:first]
                add(label, isins, _currency(text), layout.page, text)
    return list(found.values())


def attribute(
    classes: Sequence[ShareClass],
    caption: Sequence[str],
    footer: Sequence[str],
    heading_lines: Sequence[str],
) -> Attribution:
    """Attribute the returns table to one class by the fixed rules, or report ambiguity."""
    if not classes:
        return Attribution("no_share_classes")
    decisions: list[tuple[str, str, str]] = []  # (class label, rule, evidence)

    def unique(texts: Sequence[str]) -> tuple[ShareClass, str] | None:
        joined = " ".join(texts)
        hits = [c for c in classes if c.mentioned_in(joined)]
        return (hits[0], joined) if len(hits) == 1 else None

    near = unique([*caption, *footer])
    if near:
        decisions.append((near[0].label, "caption or footnote names the class", near[1][:160]))
    heading = unique(heading_lines)
    if heading:
        decisions.append(
            (heading[0].label, "performance heading names the class", heading[1][:160])
        )
    if len(classes) == 1:
        decisions.append(
            (classes[0].label, "single share class in the document", classes[0].snippet)
        )
    caption_ccy = {c for c in re.findall(r"\b[A-Z]{3}\b", " ".join(caption)) if c in ISO_CURRENCIES}
    if len(caption_ccy) == 1:
        (ccy,) = caption_ccy
        matching = [c for c in classes if c.currency == ccy]
        if len(matching) == 1:
            decisions.append((matching[0].label, f"only class in {ccy}", " ".join(caption)[:160]))
    chosen = list(dict.fromkeys(d[0] for d in decisions))
    if len(chosen) == 1:
        label, rule, evidence = decisions[0]
        return Attribution("attributed", label, rule, evidence)
    if len(chosen) > 1:
        return Attribution(
            "ambiguous",
            candidates=tuple(chosen),
            evidence="the attribution rules point to different classes",
        )
    return Attribution(
        "ambiguous",
        candidates=tuple(c.label for c in classes),
        evidence="no caption, heading or currency identifies the class",
    )


def heading_lines(layout: PageLayout, header_line: int, lookback: int = 10) -> list[str]:
    """Lines above a table that look like a performance heading."""
    start = max(0, header_line - lookback)
    return [
        line.text
        for line in layout.lines[start:header_line]
        if any(w in fold(line.text) for w in _PERFORMANCE_WORDS)
    ]
