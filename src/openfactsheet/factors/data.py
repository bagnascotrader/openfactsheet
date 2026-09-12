"""Parse and normalize caller-supplied factor returns (decision 0028).

Factor files (for example the Kenneth French data library) are usually in
percent and contain a risk-free column ``RF``. All factor columns share one
return scale, detected jointly from the non-RF columns with the same classifier
as fund returns (decision 0013), so a small RF column can never be read on a
different scale from the factors. Missing factor values are never filled.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.factors.models import FactorSet, is_risk_free_column
from openfactsheet.input.dispatcher import to_raw
from openfactsheet.models.input import (
    InputDiagnostics,
    ObservationFrequency,
    ReturnScale,
    ReturnSeries,
)
from openfactsheet.normalization.returns import normalize_returns
from openfactsheet.normalization.scaling import DeclaredScale, detect_return_scale


def _scaled(
    series: ReturnSeries,
    diag: InputDiagnostics,
    factor: float,
    scale: ReturnScale,
    evidence: str,
) -> tuple[ReturnSeries, InputDiagnostics]:
    transformations = diag.transformations
    if factor != 1.0:
        transformations += ("percent values divided by 100 to obtain decimal returns",)
    values = series.values * factor
    # The column was normalized before its scale was known: recompute the
    # impossible-return warning on the scaled values.
    warnings = tuple(w for w in diag.warnings if "below -100%" not in w)
    n_impossible = int(np.sum(values < -1.0))
    if n_impossible:
        warnings += (
            f"{n_impossible} factor return(s) below -100%: implausible for a factor "
            "return; check the return scale.",
        )
    new_diag = replace(
        diag,
        return_scale=scale,
        return_scale_evidence=evidence,
        transformations=transformations,
        warnings=warnings,
    )
    return (
        replace(series, values=values, return_scale=scale, input_diagnostics=new_diag),
        new_diag,
    )


def load_factor_set(
    source: Any,
    *,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> FactorSet:
    """Normalize factor returns supplied as a DataFrame, Series, CSV/Excel path or table text.

    One column per factor; a column named ``RF`` is taken as the risk-free rate.
    """
    if isinstance(source, FactorSet):
        return source
    if isinstance(source, pd.Series) and source.name is None:
        source = source.rename("Factor")
    raws = to_raw(source)
    if isinstance(source, pd.Series | pd.DataFrame):
        source_type = f"pandas.{type(source).__name__}"
    else:
        source_type = raws[0].source_type
    names = [r.name for r in raws]
    if len(set(names)) != len(names):
        raise InputError(f"Factor columns must have unique names; got {names}.")
    rf_names = [n for n in names if is_risk_free_column(n)]
    factor_raws = [r for r in raws if not is_risk_free_column(r.name)]
    if not factor_raws:
        raise InputError(
            "The factor data contain no factor columns (only a risk-free column 'RF')."
        )

    # Normalize every column without rescaling, then decide one scale for all of them.
    normalized = {
        r.name: normalize_returns(r, return_scale="decimal", frequency=frequency) for r in raws
    }
    freqs = {s.frequency for s, _ in normalized.values()}
    if len(freqs) > 1:
        detail = ", ".join(f"{n}: {s.frequency.value}" for n, (s, _) in normalized.items())
        raise InputError(f"Factor columns have different observation frequencies ({detail}).")
    frequency_used = next(iter(freqs))
    pooled = np.concatenate([normalized[r.name][0].values for r in factor_raws])
    decision = detect_return_scale(
        pooled,
        frequency_used,
        percent_hint=any(bool(r.percent_hint) for r in raws) or None,
        declared=return_scale,
    )
    evidence = decision.evidence + (
        " One scale is applied to every factor column"
        + (" and to the risk-free column" if rf_names else "")
        + "."
    )

    factors: dict[str, ReturnSeries] = {}
    diagnostics: dict[str, InputDiagnostics] = {}
    for name, (series, diag) in normalized.items():
        s, d = _scaled(series, diag, decision.factor, decision.scale, evidence)
        diagnostics[name] = d
        if not is_risk_free_column(name):
            factors[name] = s
    risk_free = None
    if rf_names:
        rf_series, rf_diag = normalized[rf_names[0]]
        risk_free, _ = _scaled(rf_series, rf_diag, decision.factor, decision.scale, evidence)
    return FactorSet(
        factors=factors,
        risk_free=risk_free,
        source_type=source_type,
        return_scale=decision.scale,
        return_scale_evidence=evidence,
        input_diagnostics=diagnostics,
    )
