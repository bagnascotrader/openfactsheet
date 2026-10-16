"""Who originated each canonical metric, rendered as ``docs/ATTRIBUTION.md``.

The registry's ``docs.references`` say where a definition is documented; this
module adds what those references cannot: who originated the measure (where
that is reliably established), its seminal work, and how certain the
attribution is. Bacon's *Practical Risk-Adjusted Performance Measurement* is
credited as a secondary reference for the many measures it describes, never as
their author.

``scripts/generate_docs.py`` writes the page and ``--check`` fails when it is
stale, so a newly registered metric appears in it automatically; a metric
without a curated entry is listed as "pending review" until one is added here
(and a test requires one).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from openfactsheet.metrics.references import (
    ACERBI_TASCHE_2002,
    AHMADI_JAVID_2012,
    BACON,
    BAILEY_LDP_2012,
    BOUDT_PETERSON_CROUX_2008,
    BURKE_1994,
    CAJAS_2021,
    CARHART_1997,
    CHEKHLOV_2005,
    FABOZZI_FRANCIS_1977,
    FAMA_FRENCH_1993,
    FAVRE_GALEANO_2002,
    GIPS,
    JARQUE_BERA_1987,
    JENSEN_1968,
    JOANES_GILL_1998,
    KAPLAN_KNOWLES_2004,
    KEATING_SHADWICK_2002,
    KESTNER_1996,
    LJUNG_BOX_1978,
    LO_2002,
    LO_MACKINLAY_1988,
    MARTIN_MCCANN_1989,
    MERTENS_2002,
    MODIGLIANI_1997,
    MORNINGSTAR_BATTING,
    MORNINGSTAR_CAPTURE,
    NEWEY_WEST_1987,
    PARDO_2008,
    SCHWAGER_2012,
    SHARPE_1966,
    SORTINO_PRICE_1994,
    SORTINO_VDM_PLANTINGA_1999,
    STUDENT_1908,
    TREYNOR_1965,
    TREYNOR_BLACK_1973,
    YOUNG_1991,
    ZANGARI_1996,
)
from openfactsheet.models.metric import AcademicReference, MetricDefinition

# --- Seminal works not otherwise cited in the registry -------------------------------
MARKOWITZ_1952 = AcademicReference(
    "Markowitz, H. (1952). Portfolio Selection. Journal of Finance, 7(1), 77-91."
)
MARKOWITZ_1959 = AcademicReference(
    "Markowitz, H. (1959). Portfolio Selection: Efficient Diversification of Investments. "
    "Wiley (semivariance, ch. 9)."
)
SORTINO_VDM_1991 = AcademicReference(
    "Sortino, F. A., & van der Meer, R. (1991). Downside Risk. Journal of Portfolio "
    "Management, 17(4), 27-31."
)
BAWA_1975 = AcademicReference(
    "Bawa, V. S. (1975). Optimal Rules for Ordering Uncertain Prospects. Journal of Financial "
    "Economics, 2(1), 95-121."
)
FISHBURN_1977 = AcademicReference(
    "Fishburn, P. C. (1977). Mean-Risk Analysis with Risk Associated with Below-Target "
    "Returns. American Economic Review, 67(2), 116-126."
)
ROCKAFELLAR_URYASEV_2000 = AcademicReference(
    "Rockafellar, R. T., & Uryasev, S. (2000). Optimization of Conditional Value-at-Risk. "
    "Journal of Risk, 2(3), 21-41."
)
RISKMETRICS_1996 = AcademicReference(
    "J.P. Morgan/Reuters (1996). RiskMetrics: Technical Document (4th ed.)."
)
SHARPE_1964 = AcademicReference(
    "Sharpe, W. F. (1964). Capital Asset Prices: A Theory of Market Equilibrium under "
    "Conditions of Risk. Journal of Finance, 19(3), 425-442."
)
LINTNER_1965 = AcademicReference(
    "Lintner, J. (1965). The Valuation of Risk Assets and the Selection of Risky Investments in "
    "Stock Portfolios and Capital Budgets. Review of Economics and Statistics, 47(1), 13-37."
)
GRINOLD_1989 = AcademicReference(
    "Grinold, R. C. (1989). The Fundamental Law of Active Management. Journal of Portfolio "
    "Management, 15(3), 30-37."
)
GINI_1912 = AcademicReference("Gini, C. (1912). Variabilità e mutabilità. Bologna: C. Cuppini.")

Certainty = Literal["established", "attributed", "convention", "uncertain"]

CERTAINTY_MEANING: dict[str, str] = {
    "established": "The originator and seminal work are well documented in the literature.",
    "attributed": "Commonly attributed to the named originator(s), but the primary source, its "
    "date or the exact original definition is not fully verified.",
    "convention": "A standard statistic or practitioner convention with no single originator.",
    "uncertain": "The originator is not reliably established; the entry names where the measure "
    "is documented instead.",
    "pending": "No curated attribution yet; the registry's references are listed.",
}


@dataclass(frozen=True)
class Attribution:
    """Originator credit for one canonical metric.

    Attributes:
        originators: Who originated the measure, or a description when none is established.
        seminal: The seminal work(s) defining it.
        certainty: How reliable the attribution is (see :data:`CERTAINTY_MEANING`).
        note: Material adaptations, naming history or open questions.
    """

    originators: str
    seminal: tuple[AcademicReference, ...]
    certainty: Certainty
    note: str = ""


_STANDARD = "Standard statistic (no single originator)"
_PRACTICE = "Practitioner convention (no single originator)"
_DRAWDOWN = "Practitioner drawdown statistic (no single originator)"


def _conv(*seminal: AcademicReference, who: str = _STANDARD, note: str = "") -> Attribution:
    return Attribution(who, seminal, "convention", note)


ATTRIBUTIONS: dict[str, Attribution] = {
    # Return summary
    "cumulative_return": _conv(),
    "cagr": _conv(GIPS, note="Annualization conventions follow GIPS."),
    "arithmetic_mean": _conv(),
    "geometric_mean_return": _conv(),
    "annualized_arithmetic_mean": _conv(),
    "median_return": _conv(),
    "best_period": _conv(),
    "worst_period": _conv(),
    "gain_to_pain_ratio": Attribution(
        "Jack D. Schwager",
        (SCHWAGER_2012,),
        "attributed",
        "Popularized by Schwager; a similarly named trading statistic predates it.",
    ),
    "payoff_ratio": _conv(who=_PRACTICE),
    "profit_factor": _conv(PARDO_2008, who=_PRACTICE),
    # Risk summary
    "volatility": _conv(
        MARKOWITZ_1952, note="Variance as the measure of portfolio risk: Markowitz (1952)."
    ),
    "annualized_volatility": _conv(
        MARKOWITZ_1952, note="Square-root-of-time scaling; see Lo (2002) on its limits."
    ),
    "mean_absolute_deviation": _conv(),
    "interquartile_range": _conv(),
    "downside_deviation": Attribution(
        "Harry Markowitz (semivariance); Frank A. Sortino and co-authors (deviation below a "
        "target)",
        (MARKOWITZ_1959, SORTINO_VDM_1991, SORTINO_PRICE_1994),
        "established",
    ),
    "semi_deviation": Attribution("Harry Markowitz", (MARKOWITZ_1959,), "established"),
    "downside_potential": Attribution(
        "Vijay S. Bawa; Peter C. Fishburn (lower partial moments)",
        (BAWA_1975, FISHBURN_1977),
        "attributed",
        "The name 'downside potential' for the first lower partial moment follows Bacon.",
    ),
    # Drawdowns
    "max_drawdown": _conv(who=_DRAWDOWN, note="Statistical properties: Magdon-Ismail & Atiya."),
    "average_drawdown": _conv(who=_DRAWDOWN),
    "current_drawdown": _conv(who=_DRAWDOWN),
    "longest_drawdown_duration": _conv(who=_DRAWDOWN),
    "drawdown_count": _conv(who=_DRAWDOWN),
    "time_underwater_pct": _conv(who=_DRAWDOWN),
    "ulcer_index": Attribution(
        "Peter G. Martin",
        (MARTIN_MCCANN_1989,),
        "established",
        "Introduced by Martin in 1987; published in Martin & McCann (1989).",
    ),
    "pain_index": Attribution(
        "Thomas Becker (Zephyr Associates)",
        (BACON,),
        "attributed",
        "Attribution as given in Bacon; primary source not verified.",
    ),
    "median_drawdown": _conv(who=_DRAWDOWN),
    "average_drawdown_duration": _conv(who=_DRAWDOWN),
    "max_peak_to_trough_duration": _conv(who=_DRAWDOWN),
    "average_recovery_duration": _conv(who=_DRAWDOWN),
    "drawdown_at_risk_95": Attribution(
        "Alexei Chekhlov, Stanislav Uryasev, Michael Zabarankin", (CHEKHLOV_2005,), "established"
    ),
    "cdar_95": Attribution(
        "Alexei Chekhlov, Stanislav Uryasev, Michael Zabarankin", (CHEKHLOV_2005,), "established"
    ),
    "edar_95": Attribution(
        "Dany Cajas (EDaR), building on Amir Ahmadi-Javid (EVaR)",
        (CAJAS_2021, AHMADI_JAVID_2012),
        "established",
    ),
    # Risk-adjusted performance
    "sharpe_ratio": Attribution(
        "William F. Sharpe",
        (SHARPE_1966,),
        "established",
        "Introduced as the 'reward-to-variability ratio'; restated by Sharpe (1994).",
    ),
    "sortino_ratio": Attribution(
        "Frank A. Sortino and co-authors",
        (SORTINO_VDM_1991, SORTINO_PRICE_1994),
        "established",
    ),
    "calmar_ratio": Attribution("Terry W. Young", (YOUNG_1991,), "established"),
    "martin_ratio": Attribution(
        "Peter G. Martin",
        (MARTIN_MCCANN_1989,),
        "established",
        "Also known as the Ulcer Performance Index.",
    ),
    "omega_ratio": Attribution(
        "Con Keating, William F. Shadwick", (KEATING_SHADWICK_2002,), "established"
    ),
    "kappa_3_ratio": Attribution(
        "Paul D. Kaplan, James A. Knowles", (KAPLAN_KNOWLES_2004,), "established"
    ),
    "upside_potential_ratio": Attribution(
        "Frank A. Sortino, Robert van der Meer, Auke Plantinga",
        (SORTINO_VDM_PLANTINGA_1999,),
        "established",
    ),
    "burke_ratio": Attribution("Gibbons Burke", (BURKE_1994,), "established"),
    "sterling_ratio": Attribution(
        "Attributed to Deane Sterling Jones",
        (KESTNER_1996,),
        "attributed",
        "Several definitions are in use; the canonical variant is documented on the metric page.",
    ),
    "pain_ratio": Attribution(
        "Thomas Becker (Zephyr Associates)",
        (BACON,),
        "attributed",
        "Attribution as given in Bacon; primary source not verified.",
    ),
    "recovery_factor": _conv(who=_PRACTICE),
    "sharpe_ratio_autocorrelation_adjusted": Attribution("Andrew W. Lo", (LO_2002,), "established"),
    # Tail behavior
    "var_historical_95": _conv(
        RISKMETRICS_1996,
        who="Industry risk-management practice (no single originator)",
        note="Popularized by J.P. Morgan's RiskMetrics.",
    ),
    "expected_shortfall_historical_95": Attribution(
        "Carlo Acerbi, Dirk Tasche; R. Tyrrell Rockafellar, Stanislav Uryasev (CVaR)",
        (ACERBI_TASCHE_2002, ROCKAFELLAR_URYASEV_2000),
        "established",
    ),
    "tail_ratio": _conv(who=_PRACTICE),
    "gaussian_var_95": _conv(
        RISKMETRICS_1996,
        who="Industry risk-management practice (no single originator)",
        note="Variance-covariance VaR as popularized by RiskMetrics.",
    ),
    "modified_var_95": Attribution(
        "Peter Zangari; Laurent Favre, José-Antonio Galeano",
        (ZANGARI_1996, FAVRE_GALEANO_2002),
        "established",
    ),
    "modified_es_95": Attribution(
        "Kris Boudt, Brian G. Peterson, Christophe Croux",
        (BOUDT_PETERSON_CROUX_2008,),
        "established",
    ),
    "evar_95": Attribution("Amir Ahmadi-Javid", (AHMADI_JAVID_2012,), "established"),
    # Distribution
    "skewness": _conv(JOANES_GILL_1998, note="Moment statistic; estimator per Joanes & Gill."),
    "excess_kurtosis": _conv(
        JOANES_GILL_1998, note="Moment statistic; estimator per Joanes & Gill."
    ),
    "jarque_bera_pvalue": Attribution(
        "Carlos M. Jarque, Anil K. Bera", (JARQUE_BERA_1987,), "established"
    ),
    # Consistency
    "positive_period_pct": _conv(who=_PRACTICE),
    "negative_period_pct": _conv(who=_PRACTICE),
    "longest_winning_streak": _conv(who=_PRACTICE),
    "longest_losing_streak": _conv(who=_PRACTICE),
    "best_calendar_year": _conv(GIPS, who=_PRACTICE),
    "worst_calendar_year": _conv(GIPS, who=_PRACTICE),
    "positive_calendar_years_pct": _conv(GIPS, who=_PRACTICE),
    "best_rolling_year": _conv(who=_PRACTICE),
    "worst_rolling_year": _conv(who=_PRACTICE),
    "positive_rolling_year_pct": _conv(who=_PRACTICE),
    # Serial dependence & smoothing
    "autocorrelation_lag1": _conv(note="Use as a smoothing diagnostic: Getmansky, Lo & Makarov."),
    "autocorrelation_lag2": _conv(note="Use as a smoothing diagnostic: Getmansky, Lo & Makarov."),
    "autocorrelation_lag3": _conv(note="Use as a smoothing diagnostic: Getmansky, Lo & Makarov."),
    "ljung_box_pvalue": Attribution(
        "Greta M. Ljung, George E. P. Box", (LJUNG_BOX_1978,), "established"
    ),
    "zero_return_pct": _conv(
        who="Data-quality diagnostic (no single originator)",
        note="Motivated by the illiquidity analysis of Getmansky, Lo & Makarov.",
    ),
    "variance_ratio_1y": Attribution(
        "Andrew W. Lo, A. Craig MacKinlay", (LO_MACKINLAY_1988,), "established"
    ),
    # Benchmark-relative analysis
    "beta": Attribution(
        "William F. Sharpe; John Lintner (CAPM)",
        (SHARPE_1964, LINTNER_1965),
        "established",
        "Use in fund performance evaluation: Treynor (1965), Jensen (1968).",
    ),
    "alpha": Attribution("Michael C. Jensen", (JENSEN_1968,), "established"),
    "r_squared": _conv(),
    "correlation": _conv(),
    "tracking_error": _conv(who=_PRACTICE),
    "active_return": _conv(who=_PRACTICE),
    "information_ratio": Attribution(
        "Jack L. Treynor, Fischer Black (appraisal ratio); Richard C. Grinold (information ratio)",
        (TREYNOR_BLACK_1973, GRINOLD_1989),
        "attributed",
        "The origin of the name and of the benchmark-relative form is not settled; see Goodwin "
        "(1998).",
    ),
    "treynor_ratio": Attribution("Jack L. Treynor", (TREYNOR_1965,), "established"),
    "upside_capture": _conv(
        MORNINGSTAR_CAPTURE,
        who="Industry practice (Morningstar methodology)",
    ),
    "downside_capture": _conv(
        MORNINGSTAR_CAPTURE,
        who="Industry practice (Morningstar methodology)",
    ),
    "capture_ratio": _conv(MORNINGSTAR_CAPTURE, who="Industry practice (Morningstar methodology)"),
    "batting_average": _conv(MORNINGSTAR_BATTING, who=_PRACTICE),
    "residual_volatility": _conv(
        TREYNOR_BLACK_1973, note="Denominator of the Treynor-Black appraisal ratio."
    ),
    "appraisal_ratio": Attribution(
        "Jack L. Treynor, Fischer Black", (TREYNOR_BLACK_1973,), "established"
    ),
    "m_squared": Attribution(
        "Franco Modigliani, Leah Modigliani", (MODIGLIANI_1997,), "established"
    ),
    "bull_beta": Attribution(
        "Frank J. Fabozzi, Jack C. Francis", (FABOZZI_FRANCIS_1977,), "established"
    ),
    "bear_beta": Attribution(
        "Frank J. Fabozzi, Jack C. Francis", (FABOZZI_FRANCIS_1977,), "established"
    ),
    "timing_ratio": Attribution(
        "Not reliably established",
        (BACON, FABOZZI_FRANCIS_1977),
        "uncertain",
        "Ratio of the Fabozzi-Francis bull and bear betas, as described in Bacon.",
    ),
    # Factor analysis
    "factor_alpha": Attribution(
        "Michael C. Jensen (alpha); Eugene F. Fama, Kenneth R. French; Mark M. Carhart (factor "
        "models)",
        (JENSEN_1968, FAMA_FRENCH_1993, CARHART_1997),
        "established",
    ),
    "factor_alpha_t_statistic": Attribution(
        "Whitney K. Newey, Kenneth D. West (HAC standard errors)",
        (NEWEY_WEST_1987,),
        "established",
    ),
    "factor_r_squared": _conv(FAMA_FRENCH_1993),
    "factor_residual_volatility": _conv(FAMA_FRENCH_1993),
    # Statistical confidence
    "probabilistic_sharpe_ratio": Attribution(
        "David H. Bailey, Marcos López de Prado", (BAILEY_LDP_2012,), "established"
    ),
    "sharpe_ratio_standard_error": Attribution(
        "Andrew W. Lo; Elmar Mertens (non-normal correction)",
        (LO_2002, MERTENS_2002),
        "established",
    ),
    "minimum_track_record_length": Attribution(
        "David H. Bailey, Marcos López de Prado", (BAILEY_LDP_2012,), "established"
    ),
    "mean_return_standard_error": _conv(STUDENT_1908),
    # Wave 1 monthly-only measures (credited here before or with their registration).
    "gini_mean_difference": Attribution(
        "Corrado Gini", (GINI_1912,), "established", "Bacon, 2nd ed., eq. (2.8)."
    ),
    "relative_mean_difference": Attribution(
        "Corrado Gini",
        (GINI_1912,),
        "established",
        "Bacon, 2nd ed., eq. (2.9); equals twice the Gini coefficient for positive means.",
    ),
    "skewness_kurtosis_ratio": Attribution(
        "Watanabe (as cited by Bacon)",
        (BACON,),
        "attributed",
        "Bacon, 2nd ed., eq. (3.7); primary source not verified.",
    ),
    "bias_ratio": Attribution(
        "Adil Abdulali (as cited by Bacon)",
        (BACON,),
        "attributed",
        "Bacon, 2nd ed., eq. (10.17); primary source not verified. A diagnostic, not a fraud "
        "detector.",
    ),
    "volatility_skewness": Attribution(
        "Not reliably established",
        (BACON,),
        "uncertain",
        "Bacon, 2nd ed., eq. (6.32): upside variance / downside variance.",
    ),
}


_CITATION = re.compile(r"^(?P<authors>.+?)\s*\((?P<year>\d{4})\)")
_AUTHOR_SPLIT = re.compile(r"\s*&\s*|(?<=\.),\s*(?=[A-Za-z])")


def short_citation(ref: AcademicReference) -> str:
    """Author-year label of a reference, e.g. ``Martin & McCann (1989)``."""
    m = _CITATION.match(ref.citation)
    if not m:
        return ref.citation.split(".")[0]
    authors, year = m.group("authors"), m.group("year")
    names = [
        part.split(" [")[0].split(",")[0].strip()
        for part in _AUTHOR_SPLIT.split(authors.rstrip(", "))
        if part.strip(", ")
    ]
    if len(names) == 1:
        label = names[0]
    elif len(names) == 2:
        label = f"{names[0]} & {names[1]}"
    else:
        label = f"{names[0]} et al."
    return f"{label} ({year})"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_attribution(metrics: list[MetricDefinition], generated_note: str) -> str:
    """``docs/ATTRIBUTION.md`` for the given (registered) metrics."""
    from openfactsheet.models.metric import CATEGORY_TITLES

    lines = [
        generated_note,
        "",
        "# Metric attribution",
        "",
        "OpenFactsheet seeks to credit the people who originated each measure it reports. This "
        "page lists, for every canonical metric, the originator(s) where that is reliably "
        "established, the seminal work, and how certain the attribution is. It is generated from "
        "the metric registry (`src/openfactsheet/metrics/attribution.py` and each metric's "
        "references), so every registered metric appears here.",
        "",
        "- **Bacon as a secondary reference.** Carl R. Bacon's *Practical Risk-Adjusted "
        "Performance Measurement* (2nd ed., Wiley; dated 2021 in the registry, some catalogues "
        "list 2022) documents many of these measures. It is credited as a secondary reference "
        "where the registry cites it, not as the originator of the measures it describes.",
        "- **Exact definitions.** Each metric's page in the [metric catalog](metric_catalog.md) "
        "gives the full citations, the exact formula OpenFactsheet implements and the "
        "convention chosen where definitions differ.",
        "- **Attribution is not endorsement.** Naming an author, a book, a firm or a library is "
        "not an endorsement, affiliation, license grant, or permission to reproduce protected "
        "content. Formulas are implemented independently from their published mathematical "
        "definitions; no text, tables or figures of the cited works are reproduced.",
        "- **Corrections.** If an attribution, citation, copyright notice or license is "
        "incomplete or wrong, please open an issue at "
        "<https://github.com/bagnascotrader/openfactsheet/issues> with the source that supports "
        "the correction. Report security vulnerabilities privately as described in "
        "[SECURITY.md](../SECURITY.md), never in a public issue.",
        "",
        "## Attribution status",
        "",
        "| Status | Meaning |",
        "| :-- | :-- |",
        *(f"| {k} | {v} |" for k, v in CERTAINTY_MEANING.items()),
        "",
    ]
    for category, title in CATEGORY_TITLES.items():
        rows = [d for d in metrics if d.category == category]
        if not rows:
            continue
        lines += [
            f"## {title}",
            "",
            "| ID | Metric | Originator(s) | Seminal work | Bacon (secondary) | Status | Notes |",
            "| :-- | :-- | :-- | :-- | :-: | :-- | :-- |",
        ]
        for d in rows:
            a = ATTRIBUTIONS.get(d.id)
            cites_bacon = BACON in d.docs.references
            if a is None:
                others = [r for r in d.docs.references if r != BACON]
                who, seminal, status, note = "—", others, "pending", ""
            else:
                who, seminal, status, note = a.originators, list(a.seminal), a.certainty, a.note
                cites_bacon = cites_bacon or BACON in a.seminal
            works = "; ".join(short_citation(r) for r in seminal if r != BACON) or "—"
            lines.append(
                f"| [`{d.id}`](interpretation/{d.id}.md) | {_cell(d.name)} | {_cell(who)} | "
                f"{_cell(works)} | {'yes' if cites_bacon else '—'} | {status} | "
                f"{_cell(note) or '—'} |"
            )
        lines.append("")

    cited: dict[str, AcademicReference] = {}
    for d in metrics:
        a = ATTRIBUTIONS.get(d.id)
        for r in a.seminal if a is not None else d.docs.references:
            cited.setdefault(r.citation, r)
    lines += ["## Works cited above", ""]
    for citation in sorted(cited, key=str.lower):
        r = cited[citation]
        lines.append(f"- {citation}" + (f" <{r.url}>" if r.url else ""))
    lines.append("")
    return "\n".join(lines)
