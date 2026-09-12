# 0032 — Security identifiers and the fund profile of a document

**Status:** Accepted — methodology 0.1.0

## Problem

A factsheet says who the fund is: its name, objective, identifiers (ISIN, WKN,
SEDOL, CUSIP, Valor, LEI, FIGI, tickers), currency, launch date and the benchmark
it compares itself with. Reading these makes a report traceable to a specific
fund. But a misread or guessed identifier would attribute metrics to the wrong
security, and text such as "Index" appears in many sentences. The rules must be
deterministic, evidence-based and unable to change any metric.

## Known definitions

| Identifier | Standard | Check |
|---|---|---|
| ISIN | ISO 6166 | Letters → 10..35, Luhn over the digits |
| CUSIP | ANSI X9.6 | Positions 2, 4, 6, 8 doubled, digit sums, mod 10 |
| SEDOL | LSE | Weights 1, 3, 1, 7, 3, 9, no vowels, mod 10 |
| LEI | ISO 17442 | Letters → 10..35, number ≡ 1 (mod 97) |
| FIGI | OMG | Odd positions doubled, digit sums, mod 10; reserved prefixes excluded |
| WKN, Valor, Bloomberg ticker, RIC | — | No check digit |

**Embedded national codes:**
- A DE ISIN is `DE000` + WKN + check digit.
- A US or CA ISIN contains the CUSIP.
- A GB or IE ISIN contains `00` + SEDOL.
- A CH or LI ISIN contains the zero-padded Valor.

The check digits catch every single-digit substitution. Because a letter
becomes two digits before checking, some letter substitutions are **not**
caught (for example `US0P78331005` passes, as the property tests show).

## PerformanceAnalytics behavior

Not applicable.

## QuantStats behavior

Not applicable.

## Empyrical behavior

Not applicable.

## Academic sources

ISO 6166 (ISIN), ISO 17442 (LEI), the ANSI CUSIP and LSE SEDOL specifications,
and the Object Management Group FIGI standard (check-digit definitions).

## OpenFactsheet decision

- **Fixed fields.** `DocumentProfile` holds only: fund name, objective, benchmark
  name(s), currency, launch date and identifiers. Each carries evidence (page,
  line, snippet, rule) and a confidence. No personal data (manager names,
  contacts) is extracted.
- **Identifiers:**
  - ISINs are recognized anywhere in the text when their check digit passes.
  - CUSIP, SEDOL, LEI and FIGI shapes are recognized only next to their label.
  - Codes without a check digit (WKN, Valor, Bloomberg ticker, RIC) are taken
    only immediately after their label.
  - A labelled code whose check digit fails is reported as invalid and never
    corrected.
  - An identifier matching the national code embedded in an ISIN is linked to
    that ISIN; a mismatch against the only ISIN is noted.
- **Labels.** Label vocabularies in English, German, French, Spanish and Italian
  are data (`documents/labels.py`), matched case-insensitively and without
  accents, longest label first, and only at the start of a line.
- **Fund name.** Taken from a name label (`high`). Otherwise from a title line on
  page 1 that contains a fund word and is not a sentence, label or table row
  (`moderate`, rule "title line"); for OCR the tallest such line wins.
- **Objective.** The text after an objective or policy heading, up to the next
  heading, blank line or table (at most eight lines).
- **Launch date:**
  - ISO dates are taken as printed.
  - Dotted dates are day-first.
  - A slash date is converted only when its day and month cannot be swapped;
    otherwise it is kept as printed with `low` confidence and a note.
- **Currency.** The first ISO 4217 code after a currency label.
- **Non-interference.** The profile never changes a metric. A benchmark named in
  the document is displayed, and the benchmark section says its returns were not
  supplied; it is never used as benchmark returns (CLAUDE.md §23).
- **Where it appears.** Section 1 of every renderer ("Source document") and the
  JSON key `document`.

## Rationale

Check digits and labels are objective evidence. Accepting an unlabelled
identifier only when its check digit passes keeps random codes out, and
reporting failed check digits rather than fixing them prevents a misread code
from being silently turned into another real security. Keeping the evidence with
every field lets a reader verify each value against the source document.

## Consequences

- Identifiers printed without labels in tables with several share classes are
  handled by share-class detection (decision 0033), not here.
- Some OCR misreads of letters in ISINs can pass the check digit. The OCR
  confidence floor and the cross-identifier links reduce, but cannot eliminate,
  this risk; the evidence snippet is always shown.
- Labels in other languages are not recognized until added to the vocabulary.
