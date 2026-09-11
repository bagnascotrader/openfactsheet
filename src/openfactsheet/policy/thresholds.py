"""Named minimum-data policies (decision 0015).

Each policy has a *mathematical* minimum (below it the metric cannot be
computed → ``insufficient_data``) and *statistical* thresholds (below them the
value is shown with reduced confidence). Low confidence never hides a value.

Thresholds are conventions, not laws of nature; they are versioned with the
methodology and never tuned per fund.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from openfactsheet.models.metric import Confidence

Basis = Literal["none", "years", "observations", "tail_observations"]


@dataclass(frozen=True)
class MinDataPolicy:
    key: str
    math_min_obs: int
    basis: Basis
    low_below: float | None = None
    moderate_below: float | None = None
    description: str = ""

    def confidence(
        self,
        n: int,
        years: float | None,
        tail_probability: float | None = None,
    ) -> tuple[Confidence, str | None]:
        """Return the statistical confidence label and, if reduced, the reason."""
        if self.basis == "none":
            return "high", None
        low = self.low_below
        moderate = self.moderate_below
        assert low is not None and moderate is not None
        if self.basis == "years":
            if years is None:
                return (
                    "low",
                    "History length in years cannot be established without dates or a "
                    "declared observation frequency.",
                )
            if years < low:
                return "low", f"Only {years:.1f} years of history (< {low:g} years)."
            if years < moderate:
                return "moderate", f"{years:.1f} years of history (< {moderate:g} years)."
            return "high", None
        if self.basis == "observations":
            if n < low:
                return "low", f"Only {n} observations (< {low:g})."
            if n < moderate:
                return "moderate", f"{n} observations (< {moderate:g})."
            return "high", None
        # tail_observations
        p = tail_probability if tail_probability is not None else 0.05
        expected = n * p
        if expected < low:
            return (
                "low",
                f"Only about {expected:.1f} observations are expected in the {p:.0%} tail "
                f"(< {low:g}); the tail estimate rests on very few data points.",
            )
        if expected < moderate:
            return (
                "moderate",
                f"About {expected:.1f} observations are expected in the {p:.0%} tail "
                f"(< {moderate:g}).",
            )
        return "high", None


MIN_DATA_POLICIES: dict[str, MinDataPolicy] = {
    p.key: p
    for p in (
        MinDataPolicy(
            "observed_point",
            1,
            "none",
            description="Observed fact about the supplied history; any non-empty history suffices.",
        ),
        MinDataPolicy(
            "path_risk",
            1,
            "years",
            3.0,
            5.0,
            "Path statistics (drawdowns, streaks) are computable from one observation but are "
            "unrepresentative below 3 years (low) and 5 years (moderate); longer histories "
            "tend to reveal deeper drawdowns.",
        ),
        MinDataPolicy(
            "location",
            1,
            "years",
            3.0,
            5.0,
            "Mean-type estimates: low confidence below 3 years, moderate below 5 years.",
        ),
        MinDataPolicy(
            "dispersion",
            2,
            "years",
            3.0,
            5.0,
            "Requires at least 2 observations; low confidence below 3 years, moderate below 5.",
        ),
        MinDataPolicy(
            "ratio_standard",
            2,
            "years",
            3.0,
            5.0,
            "Risk-adjusted ratios: at least 2 observations; low confidence below 3 years, "
            "moderate below 5 years.",
        ),
        MinDataPolicy(
            "skewness",
            3,
            "observations",
            60,
            120,
            "Requires at least 3 observations; standard error is roughly sqrt(6/n), so low "
            "confidence below 60 and moderate below 120 observations.",
        ),
        MinDataPolicy(
            "kurtosis",
            4,
            "observations",
            120,
            240,
            "Requires at least 4 observations; kurtosis estimates are highly unstable, so low "
            "confidence below 120 and moderate below 240 observations.",
        ),
        MinDataPolicy(
            "tail",
            2,
            "tail_observations",
            5,
            10,
            "Requires at least 2 observations; low confidence when fewer than 5 observations "
            "are expected in the 5% tail (n < 100), moderate when fewer than 10 (n < 200).",
        ),
        MinDataPolicy(
            "autocorrelation",
            5,
            "observations",
            36,
            60,
            "Requires at least 5 observations; standard error is roughly 1/sqrt(n), so low "
            "confidence below 36 and moderate below 60 observations.",
        ),
        MinDataPolicy(
            "ljung_box",
            10,
            "observations",
            36,
            60,
            "Requires at least 10 observations for a 3-lag test; low below 36, moderate below 60.",
        ),
        MinDataPolicy(
            "benchmark_regression",
            3,
            "years",
            3.0,
            5.0,
            "Requires at least 3 aligned observations; low confidence below 3 years of overlap, "
            "moderate below 5 years.",
        ),
        MinDataPolicy(
            "benchmark_simple",
            2,
            "years",
            3.0,
            5.0,
            "Requires at least 2 aligned observations; low confidence below 3 years of overlap, "
            "moderate below 5 years.",
        ),
    )
}


def get_policy(key: str) -> MinDataPolicy:
    try:
        return MIN_DATA_POLICIES[key]
    except KeyError as exc:  # pragma: no cover - guarded by registry tests
        raise KeyError(f"Unknown minimum-data policy {key!r}") from exc
