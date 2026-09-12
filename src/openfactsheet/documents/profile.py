"""Fund profile extracted from a factsheet (decision 0032).

A fixed list of fields — name, objective, benchmark name(s), currency, launch date
and security identifiers — each with the evidence it was read from (page, line,
snippet, rule) and a confidence. Label-anchored fields are ``high`` confidence;
heuristic ones (a title line taken as the fund name) are ``moderate``. The
profile describes the document: it never changes a metric, and a benchmark named
in it is never used as benchmark returns.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from openfactsheet.documents.identifiers import CHECKED, LABEL_ONLY, consistent, isin_valid
from openfactsheet.documents.labels import (
    FUND_WORDS,
    ISO_CURRENCIES,
    LABELS,
    fold,
    match_label,
)
from openfactsheet.documents.layout import Line, PageLayout
from openfactsheet.documents.tables import find_header, month_of

FieldConfidence = Literal["high", "moderate", "low"]
_SNIPPET = 160
_YEAR_START = re.compile(r"^(18|19|20|21)\d{2}\b")


@dataclass(frozen=True)
class Evidence:
    page: int
    line: int  # 1-based line on the page
    snippet: str
    rule: str

    def to_dict(self) -> dict[str, Any]:
        return {"page": self.page, "line": self.line, "snippet": self.snippet, "rule": self.rule}


@dataclass(frozen=True)
class Field:
    value: str
    confidence: FieldConfidence
    evidence: Evidence
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "evidence": self.evidence.to_dict(),
            "note": self.note,
        }


@dataclass(frozen=True)
class Identifier:
    kind: str  # ISIN, CUSIP, SEDOL, LEI, FIGI, WKN, Valor, Bloomberg, RIC
    value: str
    valid: bool | None  # check digit result; None for codes without one
    evidence: Evidence
    linked_isin: str | None = None  # the ISIN that embeds this national code

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "valid": self.valid,
            "linked_isin": self.linked_isin,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True)
class DocumentProfile:
    """What a factsheet says about the fund, with evidence for every field."""

    source: str
    name: Field | None = None
    objective: Field | None = None
    benchmarks: tuple[Field, ...] = ()
    currency: Field | None = None
    launch_date: Field | None = None
    identifiers: tuple[Identifier, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def valid_identifiers(self) -> tuple[Identifier, ...]:
        return tuple(i for i in self.identifiers if i.valid is not False)

    def to_dict(self) -> dict[str, Any]:
        def opt(f: Field | None) -> dict[str, Any] | None:
            return f.to_dict() if f is not None else None

        return {
            "source": self.source,
            "name": opt(self.name),
            "objective": opt(self.objective),
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "currency": opt(self.currency),
            "launch_date": opt(self.launch_date),
            "identifiers": [i.to_dict() for i in self.identifiers],
            "notes": list(self.notes),
        }

    def to_text(self) -> str:
        lines = [f"Document:                  {self.source}"]
        if self.name:
            lines.append(f"Fund name:                 {self.name.value} ({self.name.confidence})")
        ids = self.valid_identifiers()
        if ids:
            lines.append(
                "Identifiers:               " + ", ".join(f"{i.kind} {i.value}" for i in ids)
            )
        for b in self.benchmarks:
            lines.append(f"Benchmark named:           {b.value}")
        if self.currency:
            lines.append(f"Currency:                  {self.currency.value}")
        if self.launch_date:
            lines.append(f"Launch date:               {self.launch_date.value}")
        if self.objective:
            text = self.objective.value
            lines.append(
                "Objective:                 " + (text if len(text) <= 300 else text[:297] + "...")
            )
        lines += [f"  - {n}" for n in self.notes]
        return "\n".join(lines)


def _evidence(page: int, index: int, line: Line, rule: str) -> Evidence:
    text = line.text
    return Evidence(
        page, index + 1, text if len(text) <= _SNIPPET else text[: _SNIPPET - 3] + "...", rule
    )


def _after_label(text: str, end: int) -> str:
    """The value that follows a label ending at ``end`` (colons and dashes stripped)."""
    return text[end:].lstrip(" :-–\t").strip()


def _is_heading(text: str) -> bool:
    return any(match_label(text, f) is not None for f in ("objective", "benchmark", "currency"))


def _table_like(line: Line, index: int) -> bool:
    return find_header(line, index) is not None or bool(_YEAR_START.match(line.text))


def _identifiers(layouts: Sequence[PageLayout]) -> tuple[list[Identifier], list[str]]:
    found: dict[tuple[str, str], Identifier] = {}
    notes: list[str] = []
    for layout in layouts:
        for i, line in enumerate(layout.lines):
            text = line.text
            upper = text.upper()
            # Check-digit identifiers anywhere in the text.
            for kind, (pattern, valid) in CHECKED.items():
                labelled = match_label(text, kind, at_start=False)
                for m in pattern.finditer(upper):
                    code = m.group(1)
                    if kind != "ISIN" and not labelled:
                        continue  # CUSIP/SEDOL/LEI/FIGI shapes are common: need their label
                    ok = valid(code)
                    if not ok and not labelled:
                        continue  # an unlabelled ISIN-shaped token that fails is not an ISIN
                    key = (kind, code)
                    if key not in found:
                        found[key] = Identifier(
                            kind, code, ok, _evidence(layout.page, i, line, f"{kind} pattern")
                        )
                        if not ok:
                            notes.append(
                                f"{kind} {code} (page {layout.page}) fails its check digit and "
                                "is reported as invalid, never corrected."
                            )
            # Codes without a check digit: only right after their label.
            for kind, pattern in LABEL_ONLY.items():
                hit = match_label(text, kind, at_start=False)
                if hit is None:
                    continue
                label, end = hit
                rest = upper[end:].lstrip(" :-–\t")
                hit_code = pattern.match(rest)
                if hit_code:
                    key = (kind, hit_code.group(1).strip())
                    if key not in found:
                        found[key] = Identifier(
                            kind,
                            key[1],
                            None,
                            _evidence(layout.page, i, line, f"label '{label}'"),
                        )
    ids = list(found.values())
    isins = [i.value for i in ids if i.kind == "ISIN" and i.valid]
    linked: list[Identifier] = []
    for ident in ids:
        link = None
        for isin in isins:
            same = consistent(isin, ident.kind, ident.value)
            if same:
                link = isin
            elif same is False and len(isins) == 1:
                notes.append(
                    f"{ident.kind} {ident.value} does not match the {ident.kind} embedded in "
                    f"ISIN {isin}."
                )
        linked.append(
            Identifier(ident.kind, ident.value, ident.valid, ident.evidence, link)
            if link
            else ident
        )
    return linked, notes


def _labelled_field(layouts: Sequence[PageLayout], field_name: str) -> list[Field]:
    out: list[Field] = []
    for layout in layouts:
        for i, line in enumerate(layout.lines):
            hit = match_label(line.text, field_name)
            if hit is None:
                continue
            label, end = hit
            value = _after_label(line.text, end)
            if value:
                out.append(
                    Field(value, "high", _evidence(layout.page, i, line, f"label '{label}'"))
                )
    return out


def _objective(layouts: Sequence[PageLayout]) -> Field | None:
    for layout in layouts:
        lines = layout.lines
        for i, line in enumerate(lines):
            hit = match_label(line.text, "objective")
            if hit is None:
                continue
            label, end = hit
            parts = [_after_label(line.text, end)] if _after_label(line.text, end) else []
            for j in range(i + 1, min(i + 9, len(lines))):
                nxt = lines[j]
                if nxt.is_blank:
                    if parts:
                        break
                    continue
                if _is_heading(nxt.text) or _table_like(nxt, j):
                    break
                parts.append(nxt.text)
            if parts:
                text = re.sub(r"\s+", " ", " ".join(parts)).strip()
                return Field(text, "high", _evidence(layout.page, i, line, f"heading '{label}'"))
    return None


def _name(layouts: Sequence[PageLayout]) -> tuple[Field | None, list[str]]:
    labelled = _labelled_field(layouts, "name")
    if labelled:
        return labelled[0], []
    if not layouts:
        return None, []
    first = layouts[0]
    candidates = []
    for i, line in enumerate(first.lines[:15]):
        text = line.text.strip()
        words = fold(text).split()
        if not text or ":" in text or len(words) > 12 or _table_like(line, i):
            continue
        if any(month_of(w) for w in words):
            continue
        if any(w.strip(".,()") in FUND_WORDS for w in words):
            height = max((w.height for w in line.words), default=0.0)
            candidates.append((height, -i, i, line))
    if not candidates:
        return None, ["No fund name label or title line was found."]
    _, _, i, line = max(candidates, key=lambda c: (c[0], c[1]))
    return Field(line.text.strip(), "moderate", _evidence(first.page, i, line, "title line")), []


def _currency(layouts: Sequence[PageLayout]) -> Field | None:
    for f in _labelled_field(layouts, "currency"):
        codes = [t for t in re.findall(r"\b[A-Z]{3}\b", f.value) if t in ISO_CURRENCIES]
        if codes:
            return Field(codes[0], "high", f.evidence)
    return None


def _launch_date(layouts: Sequence[PageLayout]) -> Field | None:
    import pandas as pd

    for f in _labelled_field(layouts, "launch_date"):
        raw = f.value.split("  ")[0].strip()
        m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", raw)
        if re.match(r"\d{4}-\d{2}-\d{2}", raw):
            return Field(raw[:10], "high", f.evidence)
        if m:
            a, b, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if "." in raw[: m.end()] or a > 12:
                day, month = a, b  # dotted dates and a first part > 12 are day-first
            elif b > 12:
                day, month = b, a
            else:
                return Field(
                    raw,
                    "low",
                    f.evidence,
                    note="Day and month order is ambiguous; kept as printed.",
                )
            try:
                return Field(
                    pd.Timestamp(year, month, day).strftime("%Y-%m-%d"), "high", f.evidence
                )
            except ValueError:
                return Field(raw, "low", f.evidence, note="Not a valid calendar date.")
        try:
            if re.search(r"[A-Za-z]", raw):
                return Field(
                    pd.Timestamp(pd.to_datetime(raw)).strftime("%Y-%m-%d"), "high", f.evidence
                )
        except (ValueError, TypeError):
            pass
        return Field(raw, "low", f.evidence, note="Date format not recognized; kept as printed.")
    return None


def extract_profile(layouts: Sequence[PageLayout], source: str) -> DocumentProfile:
    """The fund profile of a document, from its page layouts (text or OCR)."""
    identifiers, id_notes = _identifiers(layouts)
    name, name_notes = _name(layouts)
    benchmarks: list[Field] = []
    seen: set[str] = set()
    for b in _labelled_field(layouts, "benchmark"):
        key = fold(b.value)
        if key not in seen and not any(month_of(w) for w in key.split()[:3]):
            seen.add(key)
            benchmarks.append(b)
    return DocumentProfile(
        source=source,
        name=name,
        objective=_objective(layouts),
        benchmarks=tuple(benchmarks),
        currency=_currency(layouts),
        launch_date=_launch_date(layouts),
        identifiers=tuple(identifiers),
        notes=tuple(id_notes + name_notes),
    )


__all__ = [
    "LABELS",
    "DocumentProfile",
    "Evidence",
    "Field",
    "Identifier",
    "extract_profile",
    "isin_valid",
]
