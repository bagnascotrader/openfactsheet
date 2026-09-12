"""Direction labels must not be misread for losses stated as negative numbers.

A maximum drawdown of -25% is worse than one of -10%. On the signed value that is
"higher is better", which readers take to mean "a bigger drawdown is better", so
signed-loss metrics are flagged and documented as "smaller loss is better".
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.metrics.catalog_docs import direction_text, render_all
from openfactsheet.metrics.registry import all_metrics, metric
from openfactsheet.models.metric import MetricDocs

SIGNED_LOSSES = {
    "max_drawdown",
    "average_drawdown",
    "current_drawdown",
    "median_drawdown",
    "drawdown_at_risk_95",
    "cdar_95",
    "edar_95",
    "var_historical_95",
    "expected_shortfall_historical_95",
    "gaussian_var_95",
    "modified_var_95",
    "modified_es_95",
    "evar_95",
    "worst_period",
    "worst_calendar_year",
    "worst_rolling_year",
}


def test_signed_loss_metrics_are_flagged() -> None:
    assert {d.id for d in all_metrics() if d.signed_loss} == SIGNED_LOSSES


def test_signed_losses_say_smaller_loss_is_better() -> None:
    pages = render_all()
    for d in all_metrics():
        if not d.signed_loss:
            continue
        assert d.direction == "higher_is_better", d.id  # on the signed value
        page = pages[f"docs/interpretation/{d.id}.md"]
        section = page.split("## 4. Is higher or lower better?")[1].split("## 5.")[0]
        assert "Smaller loss is better" in section, d.id
        assert "Higher is better" not in page, d.id
        assert "Smaller loss is better" in direction_text(d, short=True)


def test_drawdowns_are_never_positive() -> None:
    rng = np.random.default_rng(7)
    returns = pd.Series(
        rng.normal(0.005, 0.04, 120), index=pd.date_range("2015-01-31", periods=120, freq="ME")
    )
    report = ofs.analyze(returns)
    for mid in ("max_drawdown", "average_drawdown", "current_drawdown", "median_drawdown"):
        value = report.metrics[mid].value
        assert value is not None
        assert value <= 0, mid
    assert report.metrics["max_drawdown"].value < -0.05  # a real loss, stated as negative


def _docs() -> MetricDocs:
    return MetricDocs(
        measures="x",
        formula="x",
        inputs="x",
        retail="x",
        institutional="x",
        assumptions=(),
        misleading_when=(),
        minimum_data="x",
        reference_implementations=(),
        references=(),
        convention="x",
    )


def _never_called(ctx: object) -> float:  # pragma: no cover - registration fails first
    return 0.0


def test_an_unflagged_drawdown_return_is_rejected_at_registration() -> None:
    with pytest.raises(ValueError, match="declare signed_loss=True"):
        metric(
            id="_test_unflagged_drawdown",
            name="x",
            category="drawdown",
            unit="decimal_return",
            direction="higher_is_better",
            nature="observed",
            min_data_policy="path_risk",
            docs=_docs(),
        )(_never_called)
    with pytest.raises(ValueError, match="must be a higher-is-better return"):
        metric(
            id="_test_bad_signed_loss",
            name="x",
            category="drawdown",
            unit="ratio",
            direction="lower_is_better",
            nature="observed",
            min_data_policy="path_risk",
            signed_loss=True,
            docs=_docs(),
        )(_never_called)
