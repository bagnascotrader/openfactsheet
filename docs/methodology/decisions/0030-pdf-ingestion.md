# 0030 — Monthly-return tables from PDF factsheets (embedded text)

**Status:** Accepted — methodology 0.1.0

## Problem

Many track records exist only as PDF factsheets with a monthly-return table
(years in rows, January to December in columns, often a YTD column). Reading
them must not become a silent source of error. The main hazard is structural,
not character recognition: plain text extraction drops empty cells, so the row
of a fund launched in April reads like a row starting in January, which shifts
every return by three months without any visible failure. Scale (percent or
decimal), multiple tables per document, scanned pages and reconciliation with
annual totals also need fixed rules.

## Known definitions

There is no standard for factsheet tables. CLAUDE.md sections 26, 27 and 51 set
the policy: prefer embedded text to OCR, keep extraction optional and pluggable,
record confidence and provenance, show the reconstructed table, refuse canonical
metrics when extraction confidence is materially inadequate, and never make
correctness depend on an opaque model call.

## PerformanceAnalytics behavior

Not applicable (no document ingestion).

## QuantStats behavior

Not applicable.

## Empyrical behavior

Not applicable.

## Academic sources

None; this is a data-provenance decision. Candidate libraries were compared for
the embedded-text step: pypdf (BSD-3-Clause, pure Python, layout-preserving text
extraction), pdfplumber (MIT; depends on pdfminer.six), PyMuPDF (AGPL, excluded
by the licensing rule of CLAUDE.md section 21), Camelot (MIT; needs Ghostscript
or OpenCV for some modes). pypdf is the lightest dependency that keeps character
positions.

## OpenFactsheet decision

- **Optional extra** `openfactsheet[pdf]` (pypdf ≥ 4); the core library does not
  depend on it. `ofs.load` / `ofs.analyze` accept a `.pdf` path.
- **Embedded text only.** Pages are read with layout-preserving extraction. A
  document without any text (a scan) is refused with an explanation; OCR stays
  out of the core library.
- **Table detection.** A header line naming the twelve months in order,
  optionally followed by a total column (YTD, Year, Total, Annual, …); the year
  rows beneath it.
- **Column assignment by position.** Each value belongs to the column whose
  header centre is nearest, within half the median column spacing — never to "the
  next free month".
- **Refusal (no metrics) when** a value falls under no column, two values fall
  under one column, a cell is not a number, a year repeats, or the compounded
  months disagree with the year's total beyond worst-case rounding. The error
  lists every problem and prints the reconstructed table so the user can correct
  it and supply it as text.
- **Confidence** `high` when every year with a total reconciles and nothing else
  is noted; `moderate` when the table has no total column (no cross-check), a
  total is an arithmetic sum, or months inside the history are blank (missing,
  never zero). Moderate extractions are used, with the reasons in the input
  warnings.
- **Scale.** `%` in any cell, or in the three lines above the header (e.g. a
  title "Monthly returns (%)"), is percent evidence for the classifier of
  decision 0013; otherwise magnitudes decide.
- **Provenance.** The input transformations name the page, extraction engine and
  version, value count and confidence; `provenance.extraction` records the
  engine, the SHA-256 of the file, the page, the checks, the warnings and the
  reconstructed table.
- **Several tables** in one document become several series (for example fund
  and benchmark); `analyze` then asks the caller to select one or to use
  `compare`.

## Rationale

Position-based assignment removes the one error that text extraction makes
invisible, and reconciling each year with its printed total is a strong,
independent check: a shifted or misread month almost never compounds to the
printed YTD. Refusing rather than guessing follows principle 1.7 (never silently
fail) and section 26 (never calculate silently from low-confidence extraction).
Supplied correctly, the same returns give identical metrics whether they came
from a PDF or from a CSV (tested).

## Consequences

- Tables whose columns are not aligned under their headers (unusual layouts,
  rotated tables, tables split across pages) are refused rather than guessed.
- A factsheet whose YTD column uses a different definition (e.g. net of a
  performance fee not reflected in the months) is refused; the message shows
  the discrepancy.
- Screenshots and scanned PDFs still need transcription until an optional OCR
  extractor is added; it would feed the same validation and refusal rules.
