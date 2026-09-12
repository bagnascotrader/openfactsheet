# Decision criteria reference

Every rule OpenFactsheet applies between receiving data and printing a report,
stated exactly: thresholds, comparison operators and order of evaluation, with
a pointer to the implementing code. All rules are part of methodology 0.1.0;
changing any of them changes results and requires a methodology version bump
(see [methodology decisions](../methodology/decisions/README.md)).

Related references: exact metric formulas are in
[formulas.md](formulas.md), minimum-data policies in
[policies.md](policies.md), notation in [notation.md](notation.md), and the
JSON output in [report_schema.md](report_schema.md).

Notation used below: `r` is the vector of analyzed simple decimal returns,
`n` its length, `P` the periods-per-year factor, `years = n / P`.

---

## 1. Pipeline and order of operations

| Step | What happens | Code |
|---|---|---|
| 1. Input | Any supported source is parsed into one or more `RawReturns` (values may contain NaN and may be in percent). | [input/dispatcher.py](../../src/openfactsheet/input/dispatcher.py) `to_raw` |
| 2. Normalization | Validation, sorting, missing-data handling, frequency inference, scale detection → `ReturnSeries` + `InputDiagnostics`. | [normalization/returns.py](../../src/openfactsheet/normalization/returns.py) `normalize_returns` |
| 3. Diagnostics | Data-quality checks → `DataQualityReport` (runs before any metric). | [diagnostics/data_quality.py](../../src/openfactsheet/diagnostics/data_quality.py) `run_diagnostics` |
| 4. Benchmark alignment | Only if a benchmark is supplied. | [compare/alignment.py](../../src/openfactsheet/compare/alignment.py) `align_benchmark` |
| 5. Metrics | Every registered metric, in canonical order: applicability pre-check → calculation → outcome handling. | [metrics/engine.py](../../src/openfactsheet/metrics/engine.py) `compute_all`, `evaluate` |
| 6. Policy | Status, confidence, warnings and assumptions for each computed value. | [policy/confidence.py](../../src/openfactsheet/policy/confidence.py) `assess` |
| 7. Interpretation | Plain and professional text plus context notes. | [interpretation/engine.py](../../src/openfactsheet/interpretation/engine.py) |
| 8. Report | Assembly and rendering (terminal, Markdown, HTML, JSON). | [report/builder.py](../../src/openfactsheet/report/builder.py), [report/](../../src/openfactsheet/report/) |

`ofs.analyze(returns, benchmark=None, *, name=None, return_scale=None,
frequency=None)` ([api.py](../../src/openfactsheet/api.py)) runs steps 1–8.
`return_scale` and `frequency` are *input declarations*, applied to both fund
and benchmark, and are recorded in the report; they are not tuning parameters.

---

## 2. Input parsing criteria

### 2.1 Source dispatch — [input/dispatcher.py](../../src/openfactsheet/input/dispatcher.py)

Checked in this order:

| Source | Treatment |
|---|---|
| `RawReturns` | Used as is. |
| `pandas.Series` | `from_series`. |
| `pandas.DataFrame` | `from_frame` (may yield several series). |
| `pathlib.Path` | By file suffix (below). |
| `str` containing a newline after stripping | Pasted table text. |
| other `str` | Treated as a file path. |
| `numpy.ndarray`, `list`, `tuple` (or other sequence) | `from_sequence` (undated). |
| anything else | `InputError`. |

File suffixes (case-insensitive): `.csv`, `.txt`, `.tsv` → CSV reader;
`.xlsx`, `.xlsm`, `.xls` → Excel reader; `.png .jpg .jpeg .gif .bmp .tif .tiff
.webp` → OCR reader (2.9); `.pdf` → embedded-text PDF reader (2.8), with OCR
for pages that have no text (2.9); any other suffix → `InputError`; a non-existent path →
`InputError("File not found")`. When a file yields exactly one series whose
name is the default `"Returns"` and no `name` was passed, the series is named
after the file stem. The file name is stored in metadata.

`analyze()` requires exactly one series after parsing; more than one raises
`InputError` suggesting `ofs.compare()`.

A `ReturnSeries` passed to `analyze()` that carries its `input_diagnostics`
(e.g. from `ofs.load`) is reused unchanged when no declaration is passed
(only renamed if `name` differs). Otherwise it is re-normalized with
`return_scale="decimal"` unless another scale is declared.

### 2.2 Cell parsing — [input/values.py](../../src/openfactsheet/input/values.py) `parse_cell`

| Cell | Result |
|---|---|
| `None` | missing (NaN) |
| `bool` | `InputError` (a boolean is not a return) |
| `int`, `float`, NumPy number | its float value; carries no percent evidence |
| string, after stripping, whose lower-case form is one of `""`, `-`, `--`, `—`, `–`, `na`, `n/a`, `nan`, `none`, `null`, `#n/a` | missing (NaN) |
| other string | parsed as below |

String parsing, in order:

1. `%` anywhere in the string sets the percent flag for that cell; all `%`
   characters are removed.
2. The unicode minus `−` becomes `-`; spaces and non-breaking spaces are removed.
3. Parentheses around the whole value, `(1.2)`, mean a negative number.
4. If the string contains `,` and no `.`, the comma is a decimal separator
   (`1,5` → `1.5`). Thousands separators are not supported because they are not
   plausible in return data.
5. The remainder must match `^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$`,
   otherwise `InputError`.

Percent hint for a whole column (`parse_cells`): `True` if any cell contained
`%`; `False` if cells were strings but none contained `%`; `None` if no cell
was a string (numeric input carries no label evidence).

### 2.3 Sequences — [input/arrays.py](../../src/openfactsheet/input/arrays.py)

A 2-D array with one dimension equal to 1 is flattened; any other non-1-D shape
raises `InputError`. Sequences are undated. Default name `"Returns"`.

### 2.4 pandas Series — [input/pandas_input.py](../../src/openfactsheet/input/pandas_input.py) and [normalization/dates.py](../../src/openfactsheet/normalization/dates.py)

Index handling (`coerce_dates`):

| Index | Result |
|---|---|
| `PeriodIndex` | Converted to period-end dates, normalized to midnight (recorded as a transformation). |
| `DatetimeIndex` | Used as dates. |
| `RangeIndex` or any numeric dtype (integer or float) | Undated: numeric labels are positions, never dates (converting them would produce 1970-epoch timestamps). |
| other (e.g. strings) | `pd.to_datetime`; failure → `InputError`. |
| timezone-aware | Timezone removed, wall-clock dates kept (recorded). |
| any `NaT` | `InputError`. |

The series name becomes the report name unless `name` is given.

### 2.5 pandas DataFrame layouts — `from_frame`

Evaluated in this order:

1. Empty frame → `InputError`.
2. **Wide monthly table** if the column labels contain at least 12 distinct
   month names (`is_monthly_table`). Month labels are matched after removing
   non-letters and lower-casing: `jan`/`january`, `feb`/`february`, …,
   `sep`/`sept`/`september`, …, `dec`/`december`. See 2.6.
3. If the index is not a `DatetimeIndex`/`PeriodIndex`, a **date column** is
   searched for: first, a column whose stripped name matches
   `^(date|dates|period|month|time|timestamp|as of|asof|day)$`
   (case-insensitive) *and* looks like dates; otherwise the first column if it
   looks like dates. "Looks like dates" (`_looks_like_dates`): datetime or
   period dtype → yes; numeric dtype → no; otherwise every non-null value must
   parse with `pd.to_datetime(format="mixed")`. The date column becomes the index.
4. Remaining columns are return series. Duplicate column names → `InputError`;
   no columns → `InputError`.

Series naming: with one column, the `name` argument if given; otherwise
`"Returns"` if the header is generic (after removing `% ( ) [ ]`, lower-cased:
`return`, `returns`, `ret`, `rets`, `r`, `value`, `values`, `performance`,
`monthly return(s)`, `daily return(s)`, `total return`); otherwise the column
header. With several columns, each series is named by its header.

A `%` in a column header sets the percent hint to `True` for that column.

### 2.6 Wide monthly tables — [input/monthly_table.py](../../src/openfactsheet/input/monthly_table.py)

- Exactly one column per month is required (a repeated month → `InputError`;
  missing months → `InputError`).
- Year labels: a column named `year`, `yr`, `years` or `fy` (case-insensitive),
  otherwise the index. Labels must convert to integers in `[1800, 2200]` and be
  unique; otherwise `InputError`.
- Every cell becomes the return for the month-end date of its (year, month).
  Empty cells stay missing, so trailing future months are trimmed later and are
  never treated as zero.
- Other columns (e.g. `YTD`, `Total`) are ignored for calculation and listed in
  the transformations.
- Percent hint: `True` if any column header contains `%`, else the cell-based hint.

### 2.7 CSV, Excel and pasted text

- **CSV** ([input/csv.py](../../src/openfactsheet/input/csv.py)): read as text
  with delimiter sniffing (`sep=None`, Python engine, `skipinitialspace`) so that
  `%` labels and accounting negatives survive; all-empty columns dropped; then
  `from_frame`.
- **Excel** ([input/excel.py](../../src/openfactsheet/input/excel.py)): requires
  `openpyxl` (else `InputError` naming the `excel` extra); **only the first
  sheet** is read; all-empty rows and columns dropped; then `from_frame`.
- **Pasted text** ([input/clipboard.py](../../src/openfactsheet/input/clipboard.py)):
  lines are stripped and blank lines dropped. Delimiter: tab if every line has a
  tab; else `;` if every line has one; else `,` if every line has a comma *and*
  commas do not look like decimal separators (they do when the data rows contain
  no `.` and do contain whitespace); else runs of whitespace. If the header has
  one field fewer than the data rows (blank top-left cell), the first column is
  restored and named `Year`.

### 2.8 PDF factsheets — [input/pdf.py](../../src/openfactsheet/input/pdf.py) (decision 0030)

Requires the `pdf` extra (pypdf); otherwise `OCRExtractionError` naming it.

1. Each page's embedded text is extracted **with layout** (character positions
   kept). No page has any text → `OCRExtractionError` (scanned PDF; OCR is not
   part of the core library).
2. **Header line**: its tokens include exactly one month name for each month,
   January to December, left to right (month names as in 2.5). A token to the
   right of December whose letters are `ytd`, `year`, `total`, `annual`, `yr`,
   `fy`, `cum` or `cumulative` is the total column. A detached `%` token joins
   the number before it.
3. **Year rows**: the following lines whose first token is a year
   `^(18|19|20|21)\d{2}$`; up to two blank lines are skipped; any other line ends
   the table. No header followed by a year row anywhere → `OCRExtractionError`.
4. **Column assignment**: each value goes to the column (12 months + total)
   whose header centre is nearest to the value's centre, if within half the
   median month spacing. Problems (any one refuses the table): a value under no
   column; two values under one column; a token that is not a return (2.2); a
   year in two rows; a table with no monthly values.
5. **Reconciliation** of each year with a total cell: the months compound (as
   percentages; also as decimals unless the table is labelled in percent) to the
   total within `0.5·10^−d_total + 0.5·10^−d_cells × months` (worst-case
   rounding) → check passed; else if their arithmetic sum matches → warning (the
   total is a sum); else a **problem** (refused).
6. **Warnings** (confidence `moderate`, table still used): no total column (no
   cross-check possible); months missing inside the history (they stay missing,
   never zero); totals that are sums. No problems and no warnings → confidence
   `high`.
7. A refused table raises `OCRExtractionError` listing every problem and the
   reconstructed table. Accepted tables become a wide monthly table (2.6); the
   percent hint is `True` if a cell or one of the three lines above the header
   contains `%`. Several tables → several series (named `<name> (table k, page p)`).
8. Recorded: a transformation naming the page, engine version, value count and
   confidence; the warnings in `InputDiagnostics.warnings`; and
   `provenance.extraction` (engine, source SHA-256, page, confidence, checks,
   warnings, reconstructed table).

### 2.9 OCR of images and scanned pages — [input/image.py](../../src/openfactsheet/input/image.py), [documents/ocr](../../src/openfactsheet/documents/ocr/) (decision 0031)

Requires the `ocr` extra (RapidOCR, default) or `tesseract` extra; otherwise
`OCRExtractionError` naming it. Engines use only local models (RapidOCR's bundled
files, passed as explicit paths) and never access the network.

1. Images are converted to RGB; scanned PDF pages (no text layer) are rendered
   with pypdfium2 at `ocr.dpi` (300).
2. Words (pixel boxes, confidence 0–1) are grouped into lines: a word joins a
   line when it overlaps the line's vertical band by at least half the smaller
   height.
3. Table reconstruction as in 2.8, with these differences:
   - **Header**: at least `ocr.header_min_months` (9) month names read in order
     and evenly spaced (steps within 15% of the median); missing months are placed
     by that spacing (warning).
   - **Repairs**: a numeric token or year label that does not parse is retried
     with `ocr.numeric_repairs` (O/o→0, l/I/|→1) and dash variants → `-`; a
     repair is kept only if the result parses (warning, recorded per cell).
   - **Problems** (refused): any cell with confidence `< ocr.min_cell_confidence`
     (0.90); no total column; any year with values but no total cell; any failed
     reconciliation.
4. Recorded: `provenance.extraction` gains `ocr` (engine name, version, model
   files and SHA-256), `image_sha256`, `repairs`, `min_cell_confidence` and, for
   PDFs, `renderer` and `dpi`.

### 2.10 Fund profile of a document — [documents/profile.py](../../src/openfactsheet/documents/profile.py) (decision 0032)

For PDF and image inputs, the page layouts are also searched for:

| Field | Rule | Confidence |
|---|---|---|
| Identifiers | ISIN anywhere if its check digit passes; CUSIP / SEDOL / LEI / FIGI only on a line with their label; a labelled code failing its check digit is kept as `valid: false` with a note, never corrected; WKN / Valor / Bloomberg ticker / RIC only immediately after their label; a code equal to the national code embedded in an ISIN gets `linked_isin` | — |
| Fund name | text after a name label (`fund name`, `Fondsname`, `nom du fonds`, ...) | high |
| Fund name (fallback) | a page-1 line (first 15) with a fund word, at most 12 words, no colon, not a table row; tallest wins | moderate |
| Objective | text after an objective / policy heading up to a blank line, another heading or a table, at most 8 lines | high |
| Benchmark name(s) | text after a benchmark label at the start of a line (duplicates removed) | high |
| Currency | first ISO 4217 code after a currency label | high |
| Launch date | ISO as printed; dotted day-first; slash dates converted only when day and month cannot be swapped, else kept as printed | high / low |

Labels are matched at the start of a line, case- and accent-insensitively,
longest first (vocabulary in [documents/labels.py](../../src/openfactsheet/documents/labels.py)).
The profile never changes a metric; a named benchmark adds a note to the
benchmark section when no benchmark returns were supplied.

---

## 3. Validation criteria (input corruption fails early)

Applied by `normalize_returns` in this order
([normalization/validation.py](../../src/openfactsheet/normalization/validation.py)):

| Condition | Outcome |
|---|---|
| No observations | `InputError` |
| Any `+inf` or `-inf` | `InputError` listing up to 5 positions |
| All values missing | `InputError` |
| Duplicate timestamps (checked on all supplied dates, including rows whose value is missing) | `InputError` listing up to 5 dates |
| Timestamps not in increasing order | Stable sort; `was_sorted = false`; transformation and warning recorded |

Returns below −100% are **not** rejected and not clipped: they are counted
(`impossible_return_count`) and make wealth-path metrics not applicable (see 7).

---

## 4. Missing-data criteria

[normalization/returns.py](../../src/openfactsheet/normalization/returns.py):

1. Leading and trailing missing values are trimmed and counted
   (`leading_missing_trimmed`, `trailing_missing_trimmed`).
2. Interior missing values are **dropped, never filled** with zero or a previous
   value; their count is `missing_values`, and an input warning is recorded.
3. Frequency is inferred from the **grid dates**: the dates after trimming but
   *before* dropping interior missing rows, so a missing value is treated as a
   missing observation rather than as irregular spacing.
4. `missing_expected_periods` = calendar gaps in the grid dates (from frequency
   inference) **+** the number of interior missing values. It is `null` when
   the frequency does not support counting (business-daily, irregular, unknown,
   undated).

Metrics are computed on the remaining observations; compounding and
annualization skip the missing periods, and affected metrics are capped at
moderate confidence (section 9).

---

## 5. Frequency inference

[normalization/frequency.py](../../src/openfactsheet/normalization/frequency.py) `infer_frequency`.
Only calendar spacing is evidence; the number of observations never is.

Let `g` be the day gaps between consecutive grid dates and `m = median(g)`.

| Condition | Outcome |
|---|---|
| fewer than 2 dates | `unknown` (no annualization) |
| `25 ≤ m ≤ 35` | monthly candidate; steps = differences of `12·year + month` |
| `80 ≤ m ≤ 100` | quarterly candidate; steps = differences of `4·year + quarter` |
| `300 ≤ m ≤ 400` | yearly candidate; steps = differences of `year` |
| `5 ≤ m ≤ 9` | weekly candidate (below) |
| `m ≤ 4` | daily candidate (below) |
| any other `m` | `irregular` |

Bands are inclusive and tested in the order monthly, quarterly, yearly, weekly,
daily. Comparing calendar periods (not days) makes month-start, month-end and
business-month-end dates equivalent.

**Period candidates (monthly, quarterly, yearly).** With `steps` as above:

- any step equal to 0 (two observations in the same calendar period) →
  `irregular`, and the count is reported as `duplicate_periods`;
- else if the share of steps equal to exactly 1 is `< 0.5` → `irregular`;
- else **regular**; `missing_expected_periods = Σ(steps − 1)`.

**Weekly candidate.** `weeks = round(g / 7)`. The series is weekly only if every
gap satisfies `|g − 7·weeks| ≤ 1` (one-day holiday shifts allowed), every
`weeks ≥ 1`, and the share of `weeks == 1` is `≥ 0.5`; missing periods =
`Σ(weeks − 1)`. Otherwise `irregular`.

**Daily candidate.** If the share of gaps `≤ 4` days is `< 0.8` → `irregular`.
Otherwise:

- if any date falls on a Saturday or Sunday → **calendar-day** daily,
  `P = 365`, `missing_expected_periods = Σ(g − 1)`;
- else → **business-day** daily, `P = 252`, missing periods not counted
  (exchange holidays are legitimate gaps); the evidence notes the number of
  gaps longer than 7 days.

**Annualization factors** ([policy/annualization.py](../../src/openfactsheet/policy/annualization.py)):
business daily 252, calendar daily 365, weekly 52, monthly 12, quarterly 4,
yearly 1; `irregular` and `unknown` → `P = null` (never annualized).

**Declared frequency** (`frequency=` argument):

| Situation | Outcome |
|---|---|
| Declared value not one of daily, weekly, monthly, quarterly, yearly | `FrequencyInferenceError` |
| Dated input, inferred regular frequency ≠ declared | `FrequencyInferenceError` |
| Dated input, inferred `irregular` | `FrequencyInferenceError` |
| Dated input with a single timestamp (inferred `unknown`) | Declared frequency used (`frequency_source = "declared"`); one timestamp cannot contradict it |
| Dated input, inferred = declared | Inferred frequency used (`frequency_source = "inferred"`) |
| Undated input | Declared frequency used (`frequency_source = "declared"`); declared daily assumes business days (`P = 252`) with a warning |
| Undated input, nothing declared | `unknown`, `frequency_source = "none"`, warning that nothing is annualized |

For dated input without a declaration, `frequency_source` is `"inferred"` when
the inferred frequency is regular and `"none"` otherwise.

---

## 6. Return-scale classifier (percent vs decimal)

[normalization/scaling.py](../../src/openfactsheet/normalization/scaling.py) `detect_return_scale`,
thresholds in [policy/defaults.py](../../src/openfactsheet/policy/defaults.py) `return_scale`.
Runs after missing values are removed and after frequency is established.

Upper bound `U` for the median absolute return of a plausible *decimal* series:

| Frequency | `U` | Confident decimal bound `U / 4` |
|---|---|---|
| daily | 0.05 | 0.0125 |
| weekly | 0.10 | 0.025 |
| monthly | 0.20 | 0.05 |
| quarterly | 0.30 | 0.075 |
| yearly | 0.60 | 0.15 |
| irregular | 0.30 | 0.075 |
| unknown | 0.30 | 0.075 |

Let `M` = median of `|r|` over the **non-zero** raw values. Rules, first match wins:

1. `return_scale` declared → `declared_decimal` (×1) or `declared_percent` (×0.01).
   Any other declared value → `InputError`.
2. Percent hint is `True` (`%` labels in the source) → `detected_percent`.
3. All values are exactly zero → `detected_decimal` (scale immaterial).
4. `M > U`:
   - if `M / 100 > U` → `InputError` (implausible in both scales; when every
     value is positive the message suggests the data are prices/NAVs that must
     be converted explicitly);
   - else → `detected_percent`.
5. `M ≤ U / 4` → `detected_decimal`. Values below −1 stay decimal and are
   flagged as impossible, not rescaled.
6. Ambiguous zone `U/4 < M ≤ U`:
   - if any value `< −1` (impossible as a decimal return) → `detected_percent`;
   - else → `AmbiguousReturnScaleError` asking the caller to declare the scale.

Percent values are multiplied by 0.01 and the conversion is recorded as a
transformation.

---

## 7. Data-quality diagnostics

[diagnostics/data_quality.py](../../src/openfactsheet/diagnostics/data_quality.py) `run_diagnostics`
and [diagnostics/missingness.py](../../src/openfactsheet/diagnostics/missingness.py).
Diagnostics never remove or alter data.

### 7.1 Findings

| id | Severity | Exact trigger | Effect on metrics |
|---|---|---|---|
| `missing_values` | warning | interior missing values `> 0` | wealth-path and annualized metrics capped at moderate, with a warning |
| `missing_periods` | warning | `missing_expected_periods > 0` | same as above |
| `duplicate_periods` | critical | two or more observations in the same calendar period (frequency becomes irregular) | annualized metrics not applicable (no `P`) |
| `unsorted_dates` | info | input was not chronologically sorted | none (data sorted) |
| `frequency_declared` | info | `frequency_source == "declared"` | warning on annualized metrics |
| `frequency_not_established` | warning | not declared and frequency is `irregular` or `unknown` | annualized metrics not applicable |
| `percent_scale_detected` | info | `return_scale == "detected_percent"` | none |
| `very_short_history` | warning | `years` known and `years < 1` | none directly (years-based policies already give low confidence) |
| `short_history` | warning | `years` known and `1 ≤ years < 3` | none directly |
| `very_few_observations` | warning | `years` unknown and `n < 12` | none directly |
| `impossible_returns` | critical | any `r_t < −1` | every wealth-path metric not applicable; drawdown episodes omitted from the report |
| `total_loss` | critical | any `r_t = −1` exactly | warning on wealth-path metrics (wealth is 0 afterwards) |
| `suspicious_large_returns` | warning | robust outlier count `> 0` (7.2) | none (values are kept) |
| `excessive_zero_returns` | warning | share of exact zeros `≥ 0.10` | volatility-based metrics capped at moderate, with a warning |
| `repeated_returns` | warning | longest run of identical consecutive returns `≥ 3` | none |
| `smoothing_risk` | warning | smoothing risk is `moderate` or `high` (7.4) | volatility-based metrics: high → low confidence, moderate → capped at moderate |
| `serial_correlation` | info | smoothing risk is neither moderate nor high, Ljung-Box computed and `p < 0.05` | none |

History findings are mutually exclusive and evaluated in the order shown.

### 7.2 Outliers — [diagnostics/outliers.py](../../src/openfactsheet/diagnostics/outliers.py)

```math
z_t = \frac{|r_t - \operatorname{median}(r)|}{1.4826 \cdot \operatorname{MAD}}, \qquad \operatorname{MAD} = \operatorname{median}\left(|r - \operatorname{median}(r)|\right)
```

An observation is flagged when `z_t > 5`. No observation is flagged when
`n < 5` or `MAD = 0`. Flagged values are kept in every calculation.

### 7.3 Stale returns — [diagnostics/stale_returns.py](../../src/openfactsheet/diagnostics/stale_returns.py)

- zero-return share = `#{r_t = 0} / n` (exact equality after normalization);
- longest identical run = longest run of consecutive, exactly equal returns
  (1 when nothing repeats; 0 for an empty series).

### 7.4 Serial dependence and smoothing

- **Autocorrelation** ([diagnostics/autocorrelation.py](../../src/openfactsheet/diagnostics/autocorrelation.py)),
  lags 1–3, statsmodels `acf(adjusted=False)`:

  ```math
  \hat\rho_k = \frac{\sum_{t=k+1}^{n} (r_t - \bar r)(r_{t-k} - \bar r)}{\sum_{t=1}^{n} (r_t - \bar r)^2}
  ```

  undefined (`null`) when `n ≤ k + 1` or all returns are identical.
- **Significance bound** reported as `±1.96 / √n` when `n > 3`.
- **Ljung-Box** with 3 lags (statsmodels `acorr_ljungbox`), computed only when
  `n ≥ 10` and returns are not constant.
- **Smoothing risk** ([diagnostics/smoothing.py](../../src/openfactsheet/diagnostics/smoothing.py)),
  with `z = ρ̂₁ · √n`:

  | Condition (first match) | Risk |
  |---|---|
  | `n < 12` | `not_assessable` |
  | `ρ̂₁` undefined | `not_assessable` |
  | `ρ̂₁ ≥ 0.30` and `z ≥ 1.96` | `high` |
  | `ρ̂₁ ≥ 0.15` and `z ≥ 1.645` | `moderate` |
  | otherwise | `none` |

  The thresholds are a documented heuristic
  ([decision 0014](../methodology/decisions/0014-smoothing-risk.md)).
  Returns are never unsmoothed.

---

## 8. Applicability criteria

[policy/applicability.py](../../src/openfactsheet/policy/applicability.py) `precheck`,
evaluated before calculation, first match wins:

| # | Condition | Status | Reason (abridged) |
|---|---|---|---|
| 1 | metric requires a benchmark and none was supplied | `not_applicable` | no benchmark supplied; no default benchmark is ever assumed |
| 2 | metric requires factor returns and none were supplied | `not_applicable` | no factor returns supplied; factor data are never downloaded |
| 3 | metric is annualized and `P` is `null` | `not_applicable` | annualization requires a regular frequency |
| 4 | metric uses the wealth path and any `r_t < −1` | `not_applicable` | compounded wealth path not meaningful |
| 5 | observations `<` the policy's mathematical minimum (for factor metrics `max(3, k + 2)` with *k* factors) | `insufficient_data` | requires at least *N* observations |

The observation count is `n` for single-series metrics and the number of
**aligned** observations for benchmark and factor metrics. For benchmark and
factor metrics, check 3 uses the fund's `P`. Mathematical minimums per policy are listed in
[policies.md](policies.md).

A metric is never withheld because its value is unfavorable or because its
confidence is low.

---

## 9. Metric-function outcomes

[metrics/engine.py](../../src/openfactsheet/metrics/engine.py) `evaluate`:

| Outcome of the metric function | Result |
|---|---|
| Raises `UndefinedMetric(reason)` (e.g. zero volatility, no losing periods) | `not_applicable`, `value = null`, `reason` = the metric's reason, `confidence = not_assessable` |
| Raises any other exception | `error`, value withheld, reason names the exception and asks for a bug report |
| Returns `+inf` or `-inf` | `not_applicable`, value withheld, reason: the result overflows because a denominator is effectively zero (below floating-point resolution) |
| Returns `NaN` | `error`, value withheld (treated as a defect) |
| Returns a finite number | passed to the confidence engine (10) |

Calculations run with NumPy floating-point warnings suppressed; the finiteness
check above is the guard. Moment-based shape statistics (skewness, kurtosis and
everything built on them: Cornish-Fisher VaR/ES, Jarque-Bera, Sharpe inference)
are undefined when returns are numerically constant: identical values, or a
population variance `m2 <= 16 (eps · max|r|)^2` (below floating-point resolution
relative to the size of the returns;
[metrics/context.py](../../src/openfactsheet/metrics/context.py)
`_standardized_moment`). Results without a value still carry their
assumptions. Each metric's undefined conditions are listed on its page in
[`interpretation/`](../interpretation/).

---

## 10. Confidence and status algorithm

[policy/confidence.py](../../src/openfactsheet/policy/confidence.py) `assess`
with [policy/thresholds.py](../../src/openfactsheet/policy/thresholds.py).
Confidence describes the reliability of an estimate, not the quality of the
investment. Ranks: `high > moderate > low`. "Cap at X" means
`confidence = min(confidence, X)`.

**Step 1 — base confidence from the metric's minimum-data policy.** Inputs:
`n` (aligned `n` for benchmark metrics), `years = n / P` (`null` if `P` is
`null`), tail probability `p = 1 − 0.95 = 0.05`.

| Policy basis | Rule |
|---|---|
| `none` | `high` |
| `years` | `years` null → `low`; `years < low` → `low`; `years < moderate` → `moderate`; else `high` |
| `observations` | `n < low` → `low`; `n < moderate` → `moderate`; else `high` |
| `tail_observations` | `e = n · p`; `e < low` → `low`; `e < moderate` → `moderate`; else `high` |

Every reduction adds a warning stating the reason. Thresholds per policy are in
[policies.md](policies.md).

**Step 2 — modifiers, in code order.**

| # | Applies to | Trigger | Effect |
|---|---|---|---|
| a | volatility-based metrics | smoothing risk `high` | set to `low`, warning |
| b | volatility-based metrics | smoothing risk `moderate` | cap at `moderate`, warning |
| c | volatility-based metrics | zero-return share `≥ 0.10` | cap at `moderate`, warning |
| d | volatility-based metrics | `n ≥ 24`, skewness and excess kurtosis both defined, and (`skewness ≤ −1` or `excess kurtosis ≥ 3`) | warning only, no confidence change |
| e | wealth-path or annualized metrics | `missing_expected_periods > 0` or `missing_values > 0` | cap at `moderate`, warning |
| f | wealth-path metrics | a −100% return occurs | warning only |
| g | annualized metrics | `years` known and `years < 1` (`confidence.annualization_min_years`) | set to `low`, warning (annualizing a partial year) |
| h | annualized metrics | `frequency_source == "declared"` | warning only |
| i | benchmark metrics | benchmark covers `< 90%` of fund observations (`confidence.benchmark_min_coverage`) | cap at `moderate`, warning |
| j | benchmark metrics | alignment method starts with "by position" | warning only |
| k | factor metrics | factors cover `< 90%` of fund observations (`confidence.factor_min_coverage`) | cap at `moderate`, warning |
| l | factor metrics | alignment method starts with "by position" | warning only |
| m | factor metrics | smoothing risk `high` / `moderate` | set to `low` / cap at `moderate`, warning (smoothed returns bias loadings toward zero and alpha upward) |

Thresholds in modifiers a–k are read from the canonical methodology
([policy/defaults.py](../../src/openfactsheet/policy/defaults.py): `stale_returns`,
`distribution_warning`, `confidence`), so they are embedded in every report.

Which metrics are volatility-based, wealth-path, annualized, benchmark-relative
or supplementary is listed in the code-generated
[metric flags table](policies.md#metric-flags) (and on each metric page), so the
membership can never drift from the registry.

Notes produced by the metric function itself (e.g. "the longest drawdown has not
recovered") come first in the warning list. Warnings are de-duplicated,
preserving first occurrence.

**Step 3 — status.**

| Condition (first match) | Status |
|---|---|
| metric is flagged supplementary ([metric flags](policies.md#metric-flags)) | `supplementary` |
| confidence is `low` | `low_confidence` |
| otherwise | `applicable` |

A value is always shown when it exists.

**Assumptions** attached to each result come from the metric's declared
assumption keys: annualization statement, risk-free rate 0%, MAR 0%, Omega
threshold 0%, 95% historical tail convention, drawdown convention, sample
standard deviation, the benchmark name and alignment, the OLS convention, i.i.d.
asymptotics (statistical-confidence metrics), the parametric-moment convention
(Gaussian / Cornish-Fisher VaR), the Sterling 10% adjustment and the factor model
(model, factors, aligned periods, dependent variable, Newey-West lag). The keys per
metric are listed in the [metric flags table](policies.md#metric-flags).

---

## 11. Benchmark alignment criteria

[compare/alignment.py](../../src/openfactsheet/compare/alignment.py) `align_benchmark`.
Benchmark returns are normalized with the same rules as the fund. Missing
benchmark returns are never filled.

| Case | Rule |
|---|---|
| Both dated, both regular, different frequencies | `BenchmarkAlignmentError` (no resampling in 0.1.0) |
| Both dated otherwise | Key type chosen once for both series: the calendar period (`M`, `Q`, `Y`) of the fund's frequency if it is monthly/quarterly/yearly, else of the benchmark's; if neither has one, exact normalized dates. Duplicate keys in either series → `BenchmarkAlignmentError`. The intersection of keys is used, in fund order; dates are the fund's. Method: `calendar <frequency> period` or `exact date`. |
| Neither dated | Equal lengths → paired by position with a warning; different lengths → `BenchmarkAlignmentError`. |
| Exactly one dated | Equal lengths → the undated series is assumed to share the other's dates (warning); different lengths → `BenchmarkAlignmentError`. |

Reported: fund, benchmark and aligned observation counts,
`fund_only_periods = n_fund − n_aligned`, `benchmark_only_periods =
n_bench − n_aligned`, `fund_coverage = n_aligned / n_fund`, overlap start/end.
Warnings: fund observations without a benchmark return (when
`n_aligned < n_fund`), and "no periods in common" when `n_aligned = 0`.
Benchmark metrics use the fund's `P`.

**Regression** (`AlignedBenchmark.ols`): statsmodels OLS of aligned fund
returns on a constant and aligned benchmark returns (risk-free 0%),
conventional i.i.d. standard errors, residual degrees of freedom `n − 2`.
Undefined (metric not applicable) when `n < 3` or the benchmark returns are
constant. Standard errors, t-statistics and p-values are `null` when
non-finite.

### Factor returns (decision 0028)

[factors/data.py](../../src/openfactsheet/factors/data.py) `load_factor_set` and
[factors/regressions.py](../../src/openfactsheet/factors/regressions.py):

| Step | Rule |
|---|---|
| Parsing | Same parsers as fund returns; one column per factor; duplicate names → `InputError`. A column named `RF` (case-insensitive, spaces ignored) is the risk-free rate, not a factor; only an RF column → `InputError`. |
| Frequency | Every column normalized separately (missing values dropped, never filled); different frequencies across columns → `InputError`. |
| Scale | The classifier of section 6 runs once on the pooled non-RF values (`%` labels in any column count as evidence); the result, or a declared `return_scale`, is applied to every column including RF. |
| Alignment | Both dated: key type as for benchmarks (calendar period of the fund's frequency if monthly/quarterly/yearly, else of the factors', else exact date); different regular frequencies → `FactorAlignmentError`; duplicate keys → `FactorAlignmentError`; the intersection of the fund's keys with the keys present in **every** column is used, in fund order. Otherwise equal lengths are paired by position (warning), else `FactorAlignmentError`. |
| Dependent variable | `y_t = r_t − RF_t` when an RF column exists, else `y_t = r_t`. |
| Estimation | statsmodels OLS with intercept; HAC covariance, Bartlett kernel, lag `floor(4 (m/100)^(2/9))`, small-sample factor `m/(m−k−1)`; Student t with `m − k − 1` df; 95% intervals. |
| Not identified (`not_applicable`) | a factor is constant over the aligned periods; the design matrix has rank `< k + 1` (collinear factors). |
| Exact fit | constant `y`, or residual sum of squares `≤ m (16 ε max\|y\|)²`: loadings as solved, standard errors 0, t / p `null`; R² undefined (constant `y`) or 1. |
| Fit warnings | maximum VIF `≥ 10` (`factor_model.vif_warning`); residual Ljung-Box p `< 0.05` with `m ≥ 10`. |

Reported (`FactorAnalysis`): model label, factor names, dependent variable,
factor return scale and evidence, alignment counts and overlap, and the fit (or
the reason it could not be estimated).

---

## 12. Comparison criteria

[compare/comparison.py](../../src/openfactsheet/compare/comparison.py):

- Accepted inputs: mapping name → returns, `DataFrame` (one series per column),
  `ReturnTable`, or a sequence (named by each item's `.name` or `Series i`).
- At least two investments and unique names, else `InputError`.
- Every investment is analyzed by the same `analyze()` call with the same
  optional benchmark and declarations: the methodology is identical.
- Nothing is ranked.
- Note emitted when observation frequencies differ.
- **Common-period analysis** is produced when all investments are dated, share
  one regular frequency and their (start, end) ranges differ: the intersection
  of their calendar-period (or exact-date) keys is taken; if it has at least 2
  periods, each investment is re-analyzed on it (recorded as the transformation
  "restricted to the common period of all compared histories"; the fund subset
  keeps its original scale evidence and the benchmark is normalized once, as for
  the full-history reports), otherwise a note
  says the histories have fewer than 2 periods in common.

---

## 13. Interpretation rules

[interpretation/templates.py](../../src/openfactsheet/interpretation/templates.py) `RULES`.
Each metric gets its plain-language and professional text from the registry.
When the metric has no value, its reason is the first context note. Then the
rules below are applied in order. No rule grades an investment ("good",
"excellent") or gives advice.

| Rule | Applies to | Exact trigger | Note (summary) |
|---|---|---|---|
| `_smoothing` | `sharpe_ratio`, `sortino_ratio`, `information_ratio`, `annualized_volatility`, `volatility` with a value | smoothing risk `moderate` or `high` | reports lag-1 autocorrelation; treat the figure as an optimistic bound, not evidence of skill |
| `_hidden_tail` | `sharpe_ratio` with a value | skewness `≤ −1` or excess kurtosis `≥ 3` (each only if computed) | volatility-based ratios do not reflect such tail risk; compare with maximum drawdown and Expected Shortfall |
| `_alpha_significance` | `alpha` with a value and both p-value and t-statistic available | `p ≥ 0.05` / `p < 0.05` | not distinguishable from zero at 5% / significant under the single-index model, omitted factors may still explain it |
| `_short_path` | every drawdown-category metric with a value | `years` known and `years < 3` | drawdowns observed so far are likely milder than a longer history would reveal |
| `_hit_rate_smoothing` | `positive_period_pct` with a value | smoothing risk `high` and value `≥ 0.75` | very high hit rate with strong serial correlation is a pattern associated with smoothed returns |
| `_annualized_short` | `cagr`, `annualized_arithmetic_mean` with a value | `years` known and `years < 1` | annualizing extrapolates a partial year; GIPS prohibits annualized returns for periods under one year |
| `_sharpe_significance` | `probabilistic_sharpe_ratio` with a value | value `≥ 0.95` / value `< 0.95` | the Sharpe ratio is statistically above zero at 95% under i.i.d. assumptions (no guarantee of future performance) / not distinguishable from zero, the track record cannot separate skill from luck |
| `_track_record_sufficiency` | `minimum_track_record_length` with a value | `details.sufficient` true / false | the history is at least as long as the minimum track record length / states how many periods are missing (`details.additional_periods_needed`) |
| `_serial_correlation_adjustment` | `sharpe_ratio_autocorrelation_adjusted` with a value, when `sharpe_ratio` has a value | always; wording by `details.variance_ratio` `> 1` / `< 1` / `= 1` | states both annualized Sharpe ratios and the variance ratio: persistence (VR > 1) means square-root-of-time annualization overstates the conventional ratio's magnitude, reversals (VR < 1) that it understates it; the adjustment rests on estimated autocorrelations |

---

## 14. Report structure and display rules

[report/tables.py](../../src/openfactsheet/report/tables.py) and the renderers
([terminal](../../src/openfactsheet/report/terminal.py),
[markdown](../../src/openfactsheet/report/markdown.py),
[html](../../src/openfactsheet/report/html.py)).

The canonical report has exactly 14 sections; none can be removed by a flag:

1. Input & methodology
2. Data-quality diagnostics — including the serial dependence & smoothing
   metrics (`autocorrelation_lag1`–`3`, `ljung_box_pvalue`, `zero_return_pct`)
3. Return summary
4. Risk summary
5. Drawdowns
6. Risk-adjusted performance
7. Tail behavior
8. Distribution
9. Consistency
10. Benchmark-relative analysis (without a benchmark: the reason and the list
    of metrics that are not applicable)
11. Factor analysis — without factor returns: the reason and the list of
    factor metrics that are not applicable; with them: the model summary,
    alignment, a coefficient table (alpha per period and every loading with
    Newey-West standard error, t, p and 95% interval), fit statistics and the
    `factors` category metrics
12. Statistical confidence — counts of confidence labels and statuses, then the
    `statistical` category metrics (`probabilistic_sharpe_ratio`,
    `sharpe_ratio_standard_error`, `minimum_track_record_length`,
    `mean_return_standard_error`); the Deflated Sharpe Ratio is stated as not
    computable (it needs the number of strategies tried)
13. Metric catalog (pointer)
14. Assumptions & caveats (methodology description and all warning/critical
    findings)

**Charts and episode table** (decision 0026,
[report/charts.py](../../src/openfactsheet/report/charts.py)): the HTML report
draws eight fixed charts in their sections (growth of 1, calendar-year returns
and the monthly heatmap in 3; rolling one-year volatility in 4; the underwater
chart in 5; the return distribution in 8; the rolling one-year return in 9;
growth over the benchmark overlap in 10). A chart that cannot be drawn is
replaced by its reason: returns below −100% (wealth-path charts), no regular
frequency or fewer than `window + 1` observations (rolling charts), undated or
non-monthly data (heatmap), fewer than 5 or identical returns (histogram), no
benchmark or fewer than 2 aligned periods (benchmark chart). Section 5 of every
renderer lists the `charts.episode_table_rows` (10) deepest drawdown episodes,
deepest first, ties by earlier peak.

**Display rounding** (presentation only; stored values are raw `float64`):

| Unit | Display |
|---|---|
| `decimal_return` | percent, 2 decimals (`-27.32%`) |
| `fraction` | percent, 1 decimal (`54.2%`) |
| `probability` | 3 decimals |
| `periods` | integer, plus years in parentheses when `details.years` is available (`54 (4.5y)`) |
| `count` | integer |
| `ratio`, `beta`, `correlation` | 2 decimals |
| no value | `—` |

**Status column**: the confidence label when a value exists
(`supplementary (<confidence>)` for supplementary metrics); otherwise
`not applicable`, `insufficient data` or `error`.

**Notes**: each result's reason (when it has no value) and warnings are shown as
numbered footnotes; identical texts share one number across the whole report.

---

## 15. Determinism and provenance

[report/json.py](../../src/openfactsheet/report/json.py),
[report/builder.py](../../src/openfactsheet/report/builder.py):

- JSON is written with sorted keys and `allow_nan=False`; NumPy types are
  converted to plain Python and any non-finite float in nested data becomes
  `null`. No timestamps are embedded, so identical inputs give identical JSON.
- **Input fingerprint** `input_sha256`: SHA-256 of the compact JSON
  `{"dates": [...], "values": [...]}` (separators `,` and `:`), where dates are
  `YYYY-MM-DD` strings (or `null` if undated) and values are Python `repr` of
  each analyzed float (shortest round-trip form). `benchmark_sha256` uses the
  same construction for the benchmark.
- **Versions**: `package_version` is the software release;
  `methodology_version` identifies the conventions that produced the numbers.
  A package release that changes no result keeps the methodology version.
- `canonical` is `true` for every report produced by the public API.
