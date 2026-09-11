# 0013 — Percent-versus-decimal return-scale detection

**Status:** Accepted — methodology 0.1.0

## Problem

`1.5, -0.8, 2.1` are probably percentages; `0.015, -0.008, 0.021` are probably
decimals. Reading one as the other changes every metric by a factor of 100 (or
more after compounding). A single threshold misclassifies low-volatility
percent series and high-volatility decimal series.

## Known definitions

No standard exists; libraries assume decimals.

## PerformanceAnalytics behavior

Assumes decimals except `DrawdownPeak` (and therefore `UlcerIndex`,
`PainIndex`, `MartinRatio`), which divides by 100, i.e. assumes percent.

## QuantStats behavior

Assumes decimals; no detection.

## Empyrical behavior

Assumes decimals; no detection.

## Academic sources

None; this is an input-validation convention.

## OpenFactsheet decision

A deterministic classifier (`normalization/scaling.py`) returns
`detected_decimal`, `detected_percent` or raises `AmbiguousReturnScaleError`:

1. A scale declared by the caller (`return_scale="decimal" | "percent"`) always
   wins and is recorded as `declared_*`.
2. Explicit `%` labels in cells or column headers → percent.
3. All values zero → decimal (immaterial).
4. Let `m` be the median absolute non-zero value and `U` the plausible-decimal
   upper bound for the frequency: daily 0.05, weekly 0.10, monthly 0.20,
   quarterly 0.30, yearly 0.60, irregular/unknown 0.30
   (`return_scale.decimal_median_abs_upper`).
   - `m > U`: percent, unless `m / 100 > U` as well, in which case an
     `InputError` is raised (implausible in either scale; if all values are
     positive the message suggests price/NAV levels).
   - `m <= U / 4` (`confident_divisor = 4`): decimal. Any values below -1 are
     kept and flagged as impossible, not rescaled.
   - `U / 4 < m <= U` (ambiguous zone): percent if any value is below -1
     (impossible as a decimal return); otherwise `AmbiguousReturnScaleError`
     asking the caller to declare the scale.

Fund and benchmark are classified independently; a declared scale applies to both.

## Rationale

The median absolute return is robust to a few extreme periods, and plausible
magnitudes depend on frequency. Refusing to guess in the ambiguous zone follows
the rule "do not silently guess in high-risk cases".

## Consequences

- Money-market-like percent series (e.g. 0.1% per month written as `0.1`) and
  very volatile decimal series (crypto) may require an explicit declaration.
- The evidence string is shown in the input diagnostics
  (`return_scale_evidence`), and a percent conversion is recorded as a
  transformation.
- Threshold changes are methodology changes.
