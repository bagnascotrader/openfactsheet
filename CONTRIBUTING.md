# Contributing to OpenFactsheet

Thank you for helping build an open standard for investment-performance
measurement. OpenFactsheet is opinionated about methodology and humble about
inference; contributions are judged by correctness, transparency and
documentation more than by feature count.

By contributing you agree that your contribution is licensed under the
project's [Apache-2.0 license](LICENSE). User-facing text you add (README,
documentation, report wording, website copy) must stay consistent with
[DISCLAIMER.md](DISCLAIMER.md): describe measurements, never recommend an
investment, and avoid promotional claims such as "guaranteed", "risk-free" or
regulatory approval. When you add a metric, credit its originator in the
metric's references and in `src/openfactsheet/metrics/attribution.py`, then run
`scripts/generate_docs.py` so that [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md)
includes it.

## Development setup

```bash
pip install -e ".[dev,validation]"
pre-commit install
pytest
ruff check . && ruff format --check . && mypy
python scripts/generate_docs.py --check
pip install -e ".[docs]" && python scripts/build_manual.py
```

The reference manual (`docs/manual/openfactsheet-manual.pdf`) is committed and a
test fails when it no longer matches its sources: after changing a metric, a public
docstring or a document, rebuild it and commit it with your change.

Docstrings of public functions and classes are printed in the reference manual
(decision 0034): write them in Google style (`Args:`, `Returns:`, `Examples:`)
and document every argument; a test checks this.

R and PerformanceAnalytics are only needed to regenerate cross-library
reference values (`Rscript validation/r/performanceanalytics_reference.R`);
the test suite reads the committed JSON.

## Ground rules

1. **Do not add user-tunable knobs** to the canonical path (windows, thresholds,
   confidence levels, metric subsets). Canonical assumptions live in
   `src/openfactsheet/policy/defaults.py`.
2. **Do not remove or hide metrics** from canonical reports, and never let a
   metric's value decide whether it is shown.
3. **Metric functions calculate; policy decides.** Metric functions return a
   float (or `Computed`) or raise `UndefinedMetric(reason)`. Applicability and
   confidence belong in `policy/`.
4. **Never silently change methodology.** Any change to a formula, convention or
   threshold that changes results requires a decision note, a
   `METHODOLOGY_VERSION` bump, a CHANGELOG entry and regenerated golden files
   (`python scripts/update_golden.py`, reviewed diff).

## Formula-sourcing protocol (for every new metric)

1. Identify the authoritative definition: original paper, recognized textbook or
   practitioner standard, PerformanceAnalytics documentation, established Python
   libraries.
2. Compare implementations and note conventions (denominators, targets,
   annualization, sign, edge cases).
3. If definitions differ, write a decision note in
   `docs/methodology/decisions/` (Problem, Known definitions, library behaviors,
   Academic sources, Decision, Rationale, Consequences).
4. Implement independently from the mathematical definition.
5. Add cross-library tests; pin every documented difference with an assertion.

## License rule

OpenFactsheet is Apache-2.0. **Do not copy code from GPL-licensed projects**
(including R PerformanceAnalytics) or from projects with incompatible licenses.
Reading an implementation to understand a convention, then implementing the
mathematics independently and validating numerically, is the required process.
Record every reference in `docs/validation/reference_implementations.md`.

## Definition of done for a metric

- [ ] formula documented and authoritative reference cited
- [ ] typed implementation registered with `@metric(...)` and full `MetricDocs`
- [ ] minimum-data policy assigned; confidence rule exists or explicitly none
- [ ] assumptions declared (`assumptions=(...)`)
- [ ] edge cases tested (all positive/negative, constant, 1–2 observations,
      NaN, −100%, undated, irregular)
- [ ] cross-library comparison where possible; differences documented and pinned
- [ ] appears correctly in the canonical report and JSON; no NaN/inf possible
- [ ] generated docs refreshed (`python scripts/generate_docs.py`) and the
      reference manual rebuilt (`python scripts/build_manual.py`)

## Pull requests

Keep PRs focused. Describe any change in reported numbers explicitly. Never
commit private return data: `data/private/` is git-ignored for local files.
