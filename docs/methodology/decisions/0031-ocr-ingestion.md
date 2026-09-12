# 0031 — Monthly-return tables by OCR (screenshots and scanned PDFs)

**Status:** Accepted — methodology 0.1.0

## Problem

Many track records exist only as screenshots or scanned factsheets. Character
recognition (OCR) turns pixels into text with errors that embedded PDF text does
not have: misread characters, lost minus signs, low-confidence cells, headers
read as nonsense. Metrics must never be calculated silently from such errors
(CLAUDE.md sections 26, 27 and 51), analysis must stay local (section 37), and
the result must be auditable.

## Known definitions

No standard exists. Candidate open-source engines, evaluated September 2026:

| Engine | Licence | Install | Notes |
|---|---|---|---|
| RapidOCR 3.x | Apache-2.0 (PaddleOCR models, Apache-2.0) | `pip` (ONNX Runtime) | Word boxes with scores; the wheel ships its default det/rec/cls models |
| Tesseract | Apache-2.0 | system program + `pytesseract` | Offline; weaker on dense numeric tables |
| PaddleOCR | Apache-2.0 | `pip` (PaddlePaddle, large) | Same models as RapidOCR with a heavier runtime |
| EasyOCR / docTR | Apache-2.0 | `pip` (PyTorch, large) | Heavier; no advantage for printed tables |
| Surya | GPL / restrictive model licence | — | Excluded (section 21) |

## PerformanceAnalytics behavior

Not applicable (no document ingestion).

## QuantStats behavior

Not applicable.

## Empyrical behavior

Not applicable.

## Academic sources

None; this is a data-provenance decision.

## OpenFactsheet decision

- **Engines.** Pluggable `OCREngine` interface. The default is RapidOCR (optional
  extra `openfactsheet[ocr]`); Tesseract is an alternative
  (`ofs.load(path, ocr_engine="tesseract")`, extra `openfactsheet[tesseract]`).
- **Local only.** RapidOCR is given the model files bundled in its installed
  wheel as explicit paths, so its automatic model download can never run.
  Tests block the network while recognizing. The engine name, version and the
  SHA-256 of every model file are recorded in `provenance.extraction.ocr`.
- **Scanned PDFs.** Pages without embedded text are rendered with pypdfium2 at
  300 DPI (`ocr.dpi`) and recognized. Pages with text keep using the text.
- **One reconstruction.** Recognized words are grouped into lines (vertical
  overlap of at least half the smaller height) and handed to the same table
  reconstruction as PDF text (decision 0030): columns by position, gaps missing
  and never zero, YTD reconciliation.
- **Stricter acceptance for OCR:**
  - any cell recognized with confidence below 0.90 (`ocr.min_cell_confidence`)
    refuses the table;
  - every year row must have a total cell, and the total must reconcile. A lost
    minus sign or digit is otherwise undetectable, so a recognized table without
    a total column is refused;
  - numeric cells that fail to parse get only the documented repairs
    (`ocr.numeric_repairs`: O/o → 0, l/I/| → 1, dash variants → minus). Each
    repair is recorded and lowers the extraction confidence to moderate;
  - at most three month headers may be unreadable. They are placed by the even
    spacing of the others (steps within 15%), and this is recorded and lowers
    confidence to moderate.
- **Refusal** raises `OCRExtractionError` with every problem and the
  reconstructed table.
- **Disclosure.** Accepted tables show the source, engine, confidence, checks and
  the table exactly as read in section 1 of every renderer. The reconciliation
  message states its tolerance: misreads smaller than the worst-case rounding
  error cannot be detected.

## Rationale

The printed YTD figure is an independent check that a misread cell almost never
passes. Requiring it for recognized text is what makes OCR acceptable for
canonical metrics. An accepted table therefore carries the printed numbers,
whichever engine read it, so the engine choice is recorded but cannot change a
metric. Bundled models with recorded hashes keep recognition reproducible and
private.

## Consequences

- Screenshots without a YTD / total column are refused; they must be transcribed.
- Engine upgrades (new models) change the recorded hashes and may accept or
  refuse different images, but never produce different accepted values.
- OCR adds heavy optional dependencies (ONNX Runtime, OpenCV); the core install
  is unaffected.
