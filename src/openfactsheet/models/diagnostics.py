"""Data-quality diagnostics model (CLAUDE.md section 13)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["info", "warning", "critical"]
SmoothingRisk = Literal["none", "moderate", "high", "not_assessable"]


@dataclass(frozen=True)
class DiagnosticFinding:
    """One data-quality observation. ``critical`` findings materially limit metrics."""

    id: str
    severity: Severity
    message: str
    value: float | int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "value": self.value,
        }


@dataclass(frozen=True)
class DataQualityReport:
    """Results of all pre-metric data-quality checks.

    Metrics receive this object through their context so that the confidence
    policy can react to poor data.
    """

    observations: int
    years: float | None
    frequency: str
    missing_values: int
    missing_expected_periods: int | None
    duplicate_periods: int
    zero_return_count: int
    zero_return_pct: float
    longest_identical_run: int
    impossible_return_count: int
    total_loss: bool
    suspicious_large_return_count: int
    autocorrelation: tuple[float | None, float | None, float | None]
    autocorrelation_significance_bound: float | None
    ljung_box_pvalue: float | None
    smoothing_risk: SmoothingRisk
    smoothing_evidence: str
    findings: tuple[DiagnosticFinding, ...]

    @property
    def has_impossible_returns(self) -> bool:
        return self.impossible_return_count > 0

    def findings_by_severity(self, severity: Severity) -> tuple[DiagnosticFinding, ...]:
        return tuple(f for f in self.findings if f.severity == severity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observations": self.observations,
            "years": self.years,
            "frequency": self.frequency,
            "missing_values": self.missing_values,
            "missing_expected_periods": self.missing_expected_periods,
            "duplicate_periods": self.duplicate_periods,
            "zero_return_count": self.zero_return_count,
            "zero_return_pct": self.zero_return_pct,
            "longest_identical_run": self.longest_identical_run,
            "impossible_return_count": self.impossible_return_count,
            "total_loss": self.total_loss,
            "suspicious_large_return_count": self.suspicious_large_return_count,
            "autocorrelation": {
                "lag1": self.autocorrelation[0],
                "lag2": self.autocorrelation[1],
                "lag3": self.autocorrelation[2],
                "approx_95pct_significance_bound": self.autocorrelation_significance_bound,
            },
            "ljung_box_pvalue": self.ljung_box_pvalue,
            "smoothing_risk": self.smoothing_risk,
            "smoothing_evidence": self.smoothing_evidence,
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_text(self) -> str:
        def fmt(x: float | None, pct: bool = False) -> str:
            if x is None:
                return "n/a"
            return f"{x:.1%}" if pct else f"{x:.2f}"

        years = f"{self.years:.1f} years" if self.years is not None else "not determinable"
        missing = (
            str(self.missing_expected_periods)
            if self.missing_expected_periods is not None
            else "not assessed"
        )
        lines = [
            f"Observations:              {self.observations}",
            f"Frequency:                 {self.frequency}",
            f"History:                   {years}",
            f"Missing expected periods:  {missing}",
            f"Duplicate periods:         {self.duplicate_periods}",
            f"Zero-return periods:       {self.zero_return_count} ({fmt(self.zero_return_pct, True)})",
            f"Longest identical run:     {self.longest_identical_run}",
            f"Impossible returns (<-100%): {self.impossible_return_count}",
            f"Lag-1 autocorrelation:     {fmt(self.autocorrelation[0])}",
            f"Smoothing risk:            {self.smoothing_risk}",
        ]
        if self.findings:
            lines.append("Findings:")
            lines.extend(f"  [{f.severity}] {f.message}" for f in self.findings)
        return "\n".join(lines)
