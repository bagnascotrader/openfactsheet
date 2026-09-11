"""Run every data-quality check before metrics are calculated (CLAUDE.md section 13)."""

from __future__ import annotations

import numpy as np

from openfactsheet.diagnostics.autocorrelation import ljung_box, sample_autocorrelation
from openfactsheet.diagnostics.missingness import missingness_findings
from openfactsheet.diagnostics.outliers import robust_outlier_count
from openfactsheet.diagnostics.smoothing import assess_smoothing
from openfactsheet.diagnostics.stale_returns import longest_identical_run, zero_return_count
from openfactsheet.models.diagnostics import DataQualityReport, DiagnosticFinding
from openfactsheet.models.input import InputDiagnostics, ReturnSeries
from openfactsheet.policy.defaults import canonical_methodology


def run_diagnostics(series: ReturnSeries, input_diag: InputDiagnostics) -> DataQualityReport:
    m = canonical_methodology()
    r = series.values
    n = series.n
    findings: list[DiagnosticFinding] = list(missingness_findings(input_diag))

    # Frequency.
    if input_diag.frequency_source == "declared":
        findings.append(
            DiagnosticFinding(
                "frequency_declared",
                "info",
                f"Observation frequency ({series.frequency.value}) was declared by the caller, "
                "not inferred from dates.",
            )
        )
    elif not series.frequency.is_regular:
        findings.append(
            DiagnosticFinding(
                "frequency_not_established",
                "warning",
                f"Observation frequency is {series.frequency.value}: annualized metrics are not "
                "computed. " + input_diag.frequency_evidence,
            )
        )

    # Scale.
    if input_diag.return_scale == "detected_percent":
        findings.append(
            DiagnosticFinding(
                "percent_scale_detected",
                "info",
                "Values were interpreted as percentages and divided by 100. "
                + input_diag.return_scale_evidence,
            )
        )

    # History length.
    years = series.years
    if years is not None and years < 1:
        findings.append(
            DiagnosticFinding(
                "very_short_history",
                "warning",
                f"Very short history: {years:.1f} years ({n} observations). Most statistics are "
                "estimated with low confidence.",
                years,
            )
        )
    elif years is not None and years < 3:
        findings.append(
            DiagnosticFinding(
                "short_history",
                "warning",
                f"Short history: {years:.1f} years ({n} observations); it may not span a full "
                "market cycle.",
                years,
            )
        )
    elif years is None and n < 12:
        findings.append(
            DiagnosticFinding(
                "very_few_observations", "warning", f"Only {n} observations supplied.", n
            )
        )

    # Impossible / extreme returns.
    impossible = int(np.sum(r < -1.0))
    total_loss = bool(np.any(r == -1.0))
    if impossible:
        findings.append(
            DiagnosticFinding(
                "impossible_returns",
                "critical",
                f"{impossible} return(s) below -100%, impossible for ordinary simple returns. "
                "Values were not clipped; wealth-path metrics are not applicable.",
                impossible,
            )
        )
    if total_loss:
        findings.append(
            DiagnosticFinding(
                "total_loss",
                "critical",
                "A -100% return (total loss) occurs; wealth is zero from that point and "
                "subsequent returns cannot rebuild it.",
            )
        )
    outliers = robust_outlier_count(r, float(m.get("outliers.robust_z_threshold")))
    if outliers:
        findings.append(
            DiagnosticFinding(
                "suspicious_large_returns",
                "warning",
                f"{outliers} return(s) are extreme relative to the rest of the series (robust "
                "z-score > 5). Check for data errors; they are kept in all calculations.",
                outliers,
            )
        )

    # Stale returns.
    zeros = zero_return_count(r)
    zero_pct = zeros / n
    run = longest_identical_run(r)
    stale = m.get("stale_returns")
    if zero_pct >= float(stale["zero_share_warning"]):
        findings.append(
            DiagnosticFinding(
                "excessive_zero_returns",
                "warning",
                f"{zero_pct:.0%} of returns are exactly zero, which can indicate stale pricing "
                "and understated volatility.",
                zero_pct,
            )
        )
    if run >= int(stale["identical_run_warning"]):
        findings.append(
            DiagnosticFinding(
                "repeated_returns",
                "warning",
                f"{run} consecutive identical returns occur, which can indicate stale or "
                "estimated pricing.",
                run,
            )
        )

    # Serial dependence and smoothing.
    acf = tuple(sample_autocorrelation(r, k) for k in (1, 2, 3))
    bound = 1.96 / float(np.sqrt(n)) if n > 3 else None
    lb = ljung_box(r, int(m.get("dependence.ljung_box_lags"))) if n >= 10 else None
    smoothing, evidence = assess_smoothing(acf[0], n)
    if smoothing in ("moderate", "high"):
        findings.append(
            DiagnosticFinding(
                "smoothing_risk",
                "warning",
                f"{smoothing.capitalize()} return-smoothing / serial-correlation risk. {evidence} "
                "Volatility-based metrics (volatility, Sharpe, Sortino, Information Ratio) may "
                "overstate risk-adjusted performance.",
                acf[0],
            )
        )
    elif lb is not None and lb[1] < 0.05:
        findings.append(
            DiagnosticFinding(
                "serial_correlation",
                "info",
                f"Ljung-Box test (3 lags) rejects no serial correlation (p = {lb[1]:.3f}).",
                lb[1],
            )
        )

    return DataQualityReport(
        observations=n,
        years=years,
        frequency=series.frequency.value,
        missing_values=input_diag.missing_values,
        missing_expected_periods=input_diag.missing_expected_periods,
        duplicate_periods=input_diag.duplicate_dates,
        zero_return_count=zeros,
        zero_return_pct=zero_pct,
        longest_identical_run=run,
        impossible_return_count=impossible,
        total_loss=total_loss,
        suspicious_large_return_count=outliers,
        autocorrelation=(acf[0], acf[1], acf[2]),
        autocorrelation_significance_bound=bound,
        ljung_box_pvalue=lb[1] if lb is not None else None,
        smoothing_risk=smoothing,
        smoothing_evidence=evidence,
        findings=tuple(findings),
    )
