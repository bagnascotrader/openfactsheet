"""Findings about missing observations and gaps (never filled)."""

from __future__ import annotations

from openfactsheet.models.diagnostics import DiagnosticFinding
from openfactsheet.models.input import InputDiagnostics


def missingness_findings(diag: InputDiagnostics) -> list[DiagnosticFinding]:
    findings: list[DiagnosticFinding] = []
    if diag.missing_values:
        findings.append(
            DiagnosticFinding(
                "missing_values",
                "warning",
                f"{diag.missing_values} interior missing value(s) excluded; they were not "
                "replaced by zero or forward-filled.",
                diag.missing_values,
            )
        )
    if diag.missing_expected_periods:
        findings.append(
            DiagnosticFinding(
                "missing_periods",
                "warning",
                f"{diag.missing_expected_periods} expected {diag.frequency.value} period(s) are "
                "absent from the history; path metrics compound across the gaps.",
                diag.missing_expected_periods,
            )
        )
    if diag.duplicate_dates:
        findings.append(
            DiagnosticFinding(
                "duplicate_periods",
                "critical",
                f"{diag.duplicate_dates} pair(s) of observations share a calendar period.",
                diag.duplicate_dates,
            )
        )
    if not diag.was_sorted:
        findings.append(
            DiagnosticFinding(
                "unsorted_dates", "info", "Timestamps were unsorted and have been sorted."
            )
        )
    return findings
