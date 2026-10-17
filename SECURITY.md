# Security policy

## Supported versions

OpenFactsheet 0.1.0 is the first full release, following the 0.1.0a1 public alpha. Security fixes are made on the `main`
branch and released in the next 0.1.x version.

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| 0.1.0a1 (public alpha) | No; upgrade to 0.1.0 |
| < 0.1 (unreleased development snapshots) | No |

## Reporting a vulnerability

Please report security issues privately through GitHub's
**private vulnerability reporting** (repository → *Security* → *Report a
vulnerability*). Do not open a public issue for security problems, and do not
put exploit details in public issues or pull requests.

Include a description, affected versions, and steps to reproduce. We aim to
acknowledge reports within 7 days.

## Scope and design commitments

- OpenFactsheet is **local-first**: core analysis never sends return data to a
  third party, and the package makes no network calls. OCR engines run locally
  with their bundled models. Any future cloud or LLM integration will be
  opt-in and documented.
- Input files (CSV, Excel, PDF, images, pasted text) are treated as untrusted
  data; report parser crashes or resource-exhaustion issues as security bugs.
  OpenFactsheet never executes content from input files (Excel macros are not
  run; nothing is evaluated or unpickled).
- HTML reports escape all user-supplied text (names, labels, document text).
  Markdown reports write `<` and `>` in such text as entities, and terminal
  reports replace control characters.
- Never commit private return histories or credentials; the repository's
  `.gitignore` excludes common secret files and a `data/private/` folder, and a
  `detect-secrets` pre-commit hook scans every commit.

## Resource limits on input files

To keep a hostile or corrupt file from exhausting memory or CPU, OpenFactsheet
refuses inputs beyond these limits with `InputError` (or its subclass
`OCRExtractionError`). They are defined in one place,
`src/openfactsheet/input/limits.py`. They are safety limits, not analysis
parameters: they never change a metric value, and they are set far above any
real return history or factsheet.

| Limit | Value |
|---|---|
| Input file size (CSV/TXT/TSV, Excel, PDF, image) and pasted text | 64 MiB |
| Excel workbook, total uncompressed size of its zip parts | 256 MiB |
| Image size, and size of a rendered scanned PDF page | 50,000,000 pixels |
| Pages in one PDF | 200 |
| Run time of one Tesseract OCR process | 120 s |

Parsing within these limits is still done by third-party libraries (pandas,
openpyxl, pypdf, pypdfium2, Pillow, RapidOCR/onnxruntime, Tesseract). Keep
them up to date; the declared minimum versions exclude releases with known
advisories at the time of the last review.

## Reviews

The most recent security review, its scope, the tools run and the outstanding
items are in [`docs/audits/security_alpha_review.md`](docs/audits/security_alpha_review.md).
It is a maintainer review supported by automated scanners, not a third-party
audit, and passing scans are not a guarantee of security.
