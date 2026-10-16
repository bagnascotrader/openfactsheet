# Security review: OpenFactsheet public alpha

| | |
|---|---|
| Date | 2026-10-16 |
| Reviewed commit | `abc55206bf2cc1cdb85bf1b591745e39f798bf84` (`main`) |
| Remediation branch | `security-alpha-review` |
| Package / methodology | openfactsheet 0.1.0 · Methodology 0.1.0 |
| Reviewer | Maintainer review with Claude Code (AI-assisted), supported by automated scanners |

**This is not a third-party audit.** It is an internal review of the checked-out
source, the CI configuration and the declared dependencies, supported by
automated tools. Passing automated scans are **not a guarantee of security**:
scanners find known patterns and known advisories, not every defect. Each check
below is recorded as *passed*, *failed* (findings reported) or *not run*.

## 1. Scope

In scope:

- `src/openfactsheet/` (all modules), with particular attention to untrusted
  input processing: `input/` (dispatcher, CSV, pasted text, Excel, images, PDF),
  `documents/` (pypdf text extraction, pypdfium2 rendering, OCR adapters), and
  report rendering in `report/` (HTML, Markdown, terminal, SVG charts, JSON).
- `pyproject.toml` dependency declarations (core and all extras).
- `.github/workflows/ci.yml`, `.github/workflows/manual.yml`,
  `.pre-commit-config.yaml`, `.secrets.baseline`, `SECURITY.md`.
- Git history of all refs reachable in the local clone (49 commits).
- `examples/` (run, see §3) and `scripts/` (static checks only).

Out of scope / not covered: the PyPI publishing workflow (being added
separately; it must be reviewed when it lands), the openfactsheet.org website,
GitHub organisation/account settings beyond the read-only queries in §3.8, and
the internals of third-party libraries (assessed only through their published
advisories).

## 2. Environment and tool versions

| Tool | Version |
|---|---|
| Python | 3.13.5 (Windows 11, project venv) |
| pip-audit | 2.10.1 (PyPI advisory service / OSV-backed PYSEC IDs) |
| bandit | 1.9.4 |
| ruff | 0.16.7 |
| detect-secrets | 1.5.0 |
| mypy / pytest | as pinned by the dev extra in the venv; full suite results in §3.9 |
| gitleaks | **not installed — not run** |

Resolved versions of security-relevant libraries in the reviewed environment
(after remediation): numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, statsmodels
0.15.0, openpyxl 3.1.5, defusedxml 0.7.1, pypdf 6.21.0 (6.18.1 before the
review), pypdfium2 5.13.0, Pillow 12.3.0, rapidocr 3.9.2, onnxruntime 1.30.0,
typst 0.15.0, pikepdf 10.13.0.post1.

## 3. Checks and status

### 3.1 Dependency vulnerabilities (pip-audit)

| Run | Status | Result |
|---|---|---|
| `pip-audit` on the project venv (core + all extras + dev + validation as installed) | **failed** → remediated | 14 advisories in 3 packages: pypdf 6.18.1 (3, fixed in 6.19.0), urllib3 2.7.0 (3, fixed in 2.8.0), virtualenv 21.7.9 (4 unique, fixed in ≤21.7.13). urllib3 and virtualenv are transitive **development-tool** dependencies (pre-commit, requests via reference libraries), not dependencies of the openfactsheet package. All three were upgraded in the venv; re-run: **passed** (no known vulnerabilities; `openfactsheet` itself is not on PyPI and was skipped). |
| `pip-audit -r` on the **declared minimum versions** (`--no-deps`, one pin per floor of core and extras) | **failed** → remediated | `pypdf>=4.0` admitted 49 distinct PDF denial-of-service advisories, several in code paths OpenFactsheet uses (layout-mode text extraction, content-stream and FlateDecode parsing). `Pillow>=10` admitted 18 distinct advisories fixed between 10.0.1 and 12.3.0. All other floors (numpy, pandas, scipy, statsmodels, openpyxl, defusedxml, rapidocr, onnxruntime, pypdfium2, pytesseract, typst, pikepdf): no known advisories. See F-01, F-02. |
| `pip-audit -r` on a **freshly resolved** set of core + `excel`/`pdf`/`ocr`/`tesseract`/`docs` requirements (new floors) | **passed** | No known vulnerabilities. |
| `pip-audit -r` on a freshly resolved set of `dev` + `validation` requirements | **passed** | No known vulnerabilities. |

Coverage note: advisories are only as complete as the PyPI/OSV databases.
`empyrical-reloaded` was not installed in the venv; it was covered only by the
freshly resolved `validation` run.

### 3.2 Static analysis

| Check | Status | Result |
|---|---|---|
| `bandit -r src -ll` (medium and high severity) | **passed** | No issues (15,330 lines scanned, no `# nosec`). |
| `bandit -r src` (all severities) | informational | 5 low-severity B101 `assert_used` (see F-14). |
| `ruff check --select S src` | informational | The same 5 asserts (S101); nothing else. |
| `ruff check --select S --ignore S101 .` (whole repository: src, tests, scripts, examples) | **passed** | No findings. The `S` rule set is now enabled in `pyproject.toml` (with `S101` ignored, documented), so CI and pre-commit enforce it from now on. |
| Manual grep for `pickle`, `marshal`, `eval`, `exec`, `__import__`, `subprocess`, `os.system`, `shell=True`, `yaml`, `urllib`, `requests`, `socket`, `http.client`, `tempfile` in `src/` | **passed** | None present except `tempfile.TemporaryDirectory` in `manual/build.py` (safe, auto-cleaned private directory) and pytesseract's own subprocess call (F-04). No network calls in the package. |

### 3.3 Secrets

| Check | Status | Result |
|---|---|---|
| `detect-secrets scan` of all tracked files (default plugins of `.secrets.baseline`) | **passed** | 7 hits, all `Hex High Entropy String` on `input_sha256` / `benchmark_sha256` / `factors_sha256` keys of `tests/golden/*.json`: SHA-256 fingerprints of synthetic fixture data, not secrets (already excluded by the pre-commit hook). Values not reproduced here. |
| `detect-secrets scan` of the full history (`git log -p --all`, 49 commits, 5.8 MB patch written outside the repository; golden JSON and binary PDFs excluded) | **passed** | 0 hits. The scanner was sanity-checked on a sample containing a documented example AWS key format (1 hit, as expected). |
| gitleaks | **not run** | Not installed. |
| GitHub secret scanning / push protection | **not enabled** (remote setting) | See O-02. |

### 3.4 Input processing (manual review)

Reviewed: path dispatch, CSV/TSV/TXT, pasted text, Excel, images, PDF text,
PDF rendering, both OCR engines, temporary files, error handling.

- No content from input files is executed: no `eval`/`pickle`; openpyxl does
  not run macros (`.xlsm` is read as data only); pandas is given a local
  `Path`, never a URL (a URL string fails `Path.exists()` and is refused, so
  there is no SSRF path through `analyze`/`load`).
- Before this review there were **no explicit resource limits** (F-03); limits
  are now enforced and tested.
- XML in Excel packages: openpyxl uses `defusedxml` when it is installed (now
  declared in the `excel` extra, F-13); Python's bundled expat also mitigates
  entity-expansion attacks.
- Spreadsheet formula injection: **not applicable**: OpenFactsheet has no CSV
  or XLSX exporter (exports are JSON, Markdown, HTML, text).

### 3.5 Report rendering (manual review)

- HTML (`report/html.py`, `report/charts.py`): every interpolated user or
  document string goes through `html.escape` (quotes included); attributes are
  quoted; CSS custom-property names in `style` attributes are literals from the
  code, never input; the inline script inserts tooltip text with `textContent`
  and parses `data-points` with `JSON.parse` (no `innerHTML`, no `eval`). A
  regression test now asserts that a hostile series name is escaped.
- Markdown and terminal output: F-05, F-06.
- JSON: produced by `json.dumps`; no injection surface.

### 3.6 Software supply chain and CI

| Check | Status | Result |
|---|---|---|
| `pull_request_target` or other privileged triggers on untrusted PRs | **passed** | None. `ci.yml` runs on `push` to main and `pull_request` with `contents: read`. |
| Third-party Actions pinned to full commit SHAs | **failed** → remediated | All actions used mutable tags (F-08). |
| Workflow token permissions | **failed** → remediated | `manual.yml` granted `contents: write` at workflow level (F-09). |
| Script injection via `${{ }}` in `run:` | **failed** → remediated | One instance, low exploitability (F-09). |
| Secrets used by workflows | **passed** | Only the automatic `github.token`; no stored secrets referenced. |
| Dependabot configuration | **failed** → remediated | None existed (F-10). |
| Build isolation | **passed** | PEP 517 build with `hatchling>=1.21` in an isolated build environment; wheel contains only `src/openfactsheet`; sdist uses an explicit include list. |
| Package build / `twine check` / provenance (trusted publishing, attestations) | **not run** | Publishing workflow is out of scope here (O-04). |
| License review of dependencies | partial | Direct dependencies of the core and extras, spot-checked from installed package metadata: BSD/MIT/Apache-2.0/PSF/MIT-CMU, except pikepdf (MPL-2.0, file-level copyleft; `docs` extra only, used unmodified as a library). pytesseract was not installed and not checked. R PerformanceAnalytics (GPL) is used only as an external validation oracle, not imported or vendored. No full transitive license scan was run. |

### 3.7 Examples and install paths

`examples/basic_returns.py` and `examples/compare_funds.py` run successfully
(exit 0) against the source tree. `examples/dataframe.py` was not run because it
writes report files into the repository; it was reviewed statically (writes
only to its own folder).

### 3.8 Repository settings (read-only GitHub API queries)

| Setting | State on 2026-10-16 |
|---|---|
| Visibility | public |
| Private vulnerability reporting | **disabled** (O-01) |
| Dependabot alerts | enabled |
| Dependabot security updates | disabled |
| Secret scanning / push protection | disabled (O-02) |
| Code scanning (CodeQL default setup) | not configured (O-03) |

No remote setting was changed by this review.

### 3.9 Regression suite after remediation

`ruff check .`, `ruff format --check .`, `mypy` (strict, 100 files),
`pytest` (441 passed, including 14 new security tests in
`tests/unit/test_security.py`), the OCR / manual / cross-library marked
suites, `scripts/generate_docs.py --check` and `scripts/build_manual.py
--check`: all **passed** on the remediation branch.

## 4. Findings

Severity reflects OpenFactsheet's deployment model: a local library that a user
points at files of their choosing. A hostile file therefore needs the user to
open it; the realistic impact is denial of service of the user's own process,
or misleading/active content in a report they share. No finding allowed code
execution, data exfiltration or credential exposure. Line numbers refer to the
reviewed commit `abc5520`.

| ID | Severity | Evidence | Exploitability | Remediation | Test | Residual risk |
|---|---|---|---|---|---|---|
| F-01 | Medium | `pyproject.toml:49-51,55,71`: `pypdf>=4.0` admitted releases with published DoS advisories (infinite loops, memory exhaustion), including layout-mode text extraction used at `documents/text_pdf.py:55` and stream decoding reached by `PdfReader` at `:39`. | A crafted PDF opened with `ofs.analyze` / `ofs.load` could hang or exhaust memory on an install that resolved an old pypdf. | Floor raised to `pypdf>=6.19` in every extra; venv upgraded and full suite re-run. | Freshly resolved and floor `pip-audit` runs (§3.1). | New pypdf advisories will keep appearing; Dependabot (F-10) proposes floor updates. |
| F-02 | Medium | `pyproject.toml:50-51,72`: `Pillow>=10` admitted releases with published advisories in image decoding; untrusted images are decoded at `input/image.py:38`. | A crafted image could trigger a vulnerable decoder on an install with an old Pillow. | Floor raised to `Pillow>=12.3`. | `pip-audit` (§3.1). | As F-01. |
| F-03 | Medium | No explicit resource limits: whole-file parsing at `input/csv.py:17` (python engine, delimiter sniffing), `input/excel.py:24` (zip package inflated by openpyxl), `input/image.py:38` (relied on Pillow's implicit bomb threshold of ~179 MP before an error), whole-file reads for hashing at `input/image.py:51` and `input/pdf.py:93`, unbounded page count (`documents/text_pdf.py:55` loop) and unbounded render size at `documents/raster.py:23-28` (page size × 300 dpi). | A very large, highly compressed or oversized-page file could exhaust memory/CPU. | New `src/openfactsheet/input/limits.py` defines all limits in one place (file size 64 MiB incl. pasted text, Excel uncompressed 256 MiB, 50 MP per image or rendered page, 200 PDF pages, Tesseract 120 s); checked before parsing/decoding; refusals raise `InputError` / `OCRExtractionError`. Pillow's `DecompressionBombError` is converted to `OCRExtractionError`. Directories are refused explicitly. Limits never change metric values; documented in `SECURITY.md`. | `tests/unit/test_security.py`: file size, pasted text, directory, Excel expansion, image pixels, Pillow bomb error, PDF pages, render pixels. | Inputs within the limits are still parsed by third-party C/C++ and Python code (PDFium, Pillow, onnxruntime, pypdf, pandas); a parser bug inside the limits remains possible. pypdf's per-page text extraction has no wall-clock timeout. |
| F-04 | Low | `documents/ocr/tesseract.py:54`: `pytesseract.image_to_data` ran the external Tesseract process with no timeout (arguments are fixed constants; no injection). | A pathological image could keep the OCR process running indefinitely (only with the optional Tesseract engine). | `timeout=TESSERACT_TIMEOUT_SECONDS` (120 s); pytesseract's timeout `RuntimeError` becomes `OCRExtractionError`. | `test_tesseract_timeout_becomes_extraction_error`. | RapidOCR (in-process onnxruntime) has no timeout; bounded indirectly by the pixel limit. |
| F-05 | Low | `report/markdown.py:35`: `_cell` did not neutralise HTML in names (series names come from file headers or document text); `:39` `_kv_block` used a fixed three-backtick fence around text that includes the table reconstructed from a PDF or image, which that text could close. | A crafted column header or factsheet could place raw HTML/Markdown in a Markdown report; harmful only if the report is rendered by a viewer that allows raw HTML. | `<`/`>` written as `&lt;`/`&gt;`; code fences are longer than any backtick run in the fenced text (CommonMark rule). | `test_untrusted_names_are_escaped_in_markdown`, `test_document_text_cannot_close_a_markdown_code_block`. | Markdown link syntax in names is not neutralised (metric links use internal names and URLs only). |
| F-06 | Low | `report/terminal.py:142`: the series name (from a file header) was printed verbatim by `report.summary()`. | A crafted header could embed terminal escape sequences (title changes, screen clearing) when the summary is printed. | Terminal output replaces C0/C1 control characters (except tab and newline) and DEL with U+FFFD. | `test_terminal_report_drops_control_sequences`. | None known. |
| F-07 | Informational | `report/html.py:410`: `f.severity` interpolated without `escape`. The value is an internal `Literal` set by OpenFactsheet's diagnostics, never input. | Not exploitable. | Escaped defensively. | Covered by existing HTML tests. | None. |
| F-08 | Low | `.github/workflows/ci.yml` (all jobs) and `manual.yml`: `actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v4`: mutable tags. | A compromised or moved tag would run attacker code in CI (with `contents: write` in `manual.yml`). | Pinned to full SHAs with version comments: checkout `3d3c42e5…` (v7.0.1), setup-python `5fda3b95…` (v7.0.0), upload-artifact `ea165f8d…` (v4.6.2), resolved via the GitHub API (lightweight tags pointing at commits). `persist-credentials: false` on every checkout. | Workflow YAML validated; CI on the PR. | Pinned actions still execute their own transitive dependencies; Dependabot keeps pins current. |
| F-09 | Low | `manual.yml:20`: `permissions: contents: write` for the whole workflow; `manual.yml:58`: `${{ github.event.release.tag_name }}` substituted directly into a `run:` script. | Tag names can only be created by users with write access, so injection needs an already-privileged actor; the workflow-level grant widened the token for every job. | Workflow default `contents: read`; `contents: write` only on the two jobs that edit releases; tag passed via `env: TAG`. | YAML validated. | Those two jobs still hold a write token by necessity. |
| F-10 | Informational | No `.github/dependabot.yml`. | n/a | Added: weekly `pip` and `github-actions` updates. | n/a | Dependabot PRs still need review; Dependabot *security updates* are disabled in repository settings. |
| F-11 | Informational | `SECURITY.md` had no supported-versions statement. | n/a | Added (0.1.x public alpha supported), kept the private reporting path, documented resource limits and this review. | n/a | See O-01: the private reporting path it names is currently disabled. |
| F-12 | Informational | `tests/cross_library/test_python_references.py:13` imports `packaging`, which no extra declared (it arrived transitively through pytest). | n/a | `packaging>=23` declared in `dev` and `validation`. | Suite passes. | None. |
| F-13 | Informational | `input/excel.py:24`: openpyxl parses workbook XML with the standard library unless `defusedxml` is installed. | Low: Python's bundled expat (≥ 2.4.1) already mitigates entity-expansion ("billion laughs"). | `defusedxml>=0.7.1` added to the `excel` (and `dev`) extra. | Existing Excel round-trip test. | None known. |
| F-14 | Informational | `assert` used for type narrowing at `compare/alignment.py:147`, `compare/comparison.py:182`, `factors/regressions.py:120`, `report/charts.py:265,472` (bandit B101 / ruff S101). | Not a security control; under `python -O` a violated invariant would raise a different exception. | Accepted; `S101` ignored with a documented reason. | n/a | None. |
| F-15 | Informational | `input/dispatcher.py:73-76`: a one-line string is treated as a file path; `FactsheetReport.to_*(path)` write to the given path. | Paths are chosen by the calling program; this is the library's intended API, not a traversal sink. | Accepted. Documented here. | `test_directory_is_not_read_as_a_file`. | Applications that pass end-user-controlled strings to `ofs.analyze` must validate paths themselves. |

No critical or high-severity issue was found.

## 5. Outstanding items

| ID | Item | Owner / action | Blocks public release? |
|---|---|---|---|
| O-01 | **Private vulnerability reporting is disabled** on the public repository, but `SECURITY.md` names it as the reporting channel. | Maintainer: enable it (Settings → Code security → Private vulnerability reporting). Requires repository admin; not changed by this review. | **Yes**: the documented private channel must work before a public release. |
| O-02 | GitHub secret scanning and push protection are disabled (free for public repositories). | Maintainer: enable in repository settings. | No (recommended). |
| O-03 | Code scanning (CodeQL) is not configured. | Maintainer: enable default setup, or add a workflow. | No (recommended). |
| O-04 | The PyPI publishing workflow is not yet in the repository. | Review it when added: trusted publishing (OIDC) with `id-token: write` only on the publish job, a protected `pypi` environment, SHA-pinned actions, no long-lived API tokens, build provenance/attestations. | Yes for publishing, until reviewed. |
| O-05 | gitleaks, OSV-Scanner, fuzzing of the parsers and a full transitive license scan were **not run**. | Optional future work. | No. |
| O-06 | Legacy `.xls` files need `xlrd`, which no extra declares; without it the error surfaces as an `ImportError` rather than `InputError` (robustness, not security). | Future change. | No. |
| O-07 | Third-party parser risk within the limits (F-03 residual): services that analyze files from anonymous users should additionally isolate parsing (separate process, memory/CPU limits, timeouts). | Integrators. | No. |
