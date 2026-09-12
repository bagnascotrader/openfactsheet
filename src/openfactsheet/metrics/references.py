"""Shared academic and library references used in metric documentation.

Library versions inspected for methodology 0.1.0 conventions:
PerformanceAnalytics 2.0.4 (R, GPL — conventions only, no code copied),
empyrical-reloaded 0.5.12 (Apache-2.0), QuantStats 0.0.81 (Apache-2.0).
"""

from __future__ import annotations

from openfactsheet.models.metric import AcademicReference, LibraryReference

# --- Academic / practitioner sources ---------------------------------------
BACON = AcademicReference(
    "Bacon, C. R. (2021). Practical Risk-Adjusted Performance Measurement (2nd ed.). Wiley."
)
GIPS = AcademicReference(
    "CFA Institute (2020). Global Investment Performance Standards (GIPS) for Firms, "
    "provisions on annualized returns.",
    "https://www.gipsstandards.org/",
)
SHARPE_1966 = AcademicReference(
    "Sharpe, W. F. (1966). Mutual Fund Performance. Journal of Business, 39(1), 119-138."
)
SHARPE_1994 = AcademicReference(
    "Sharpe, W. F. (1994). The Sharpe Ratio. Journal of Portfolio Management, 21(1), 49-58."
)
LO_2002 = AcademicReference(
    "Lo, A. W. (2002). The Statistics of Sharpe Ratios. Financial Analysts Journal, 58(4), 36-52."
)
SORTINO_PRICE_1994 = AcademicReference(
    "Sortino, F. A., & Price, L. N. (1994). Performance Measurement in a Downside Risk "
    "Framework. Journal of Investing, 3(3), 59-64."
)
YOUNG_1991 = AcademicReference(
    "Young, T. W. (1991). Calmar Ratio: A Smoother Tool. Futures, 20(1), 40."
)
MARTIN_MCCANN_1989 = AcademicReference(
    "Martin, P. G., & McCann, B. B. (1989). The Investor's Guide to Fidelity Funds. Wiley "
    "(Ulcer Index and Ulcer Performance Index)."
)
KEATING_SHADWICK_2002 = AcademicReference(
    "Keating, C., & Shadwick, W. F. (2002). A Universal Performance Measure. Journal of "
    "Performance Measurement, 6(3), 59-84."
)
SCHWAGER_2012 = AcademicReference(
    "Schwager, J. D. (2012). Market Sense and Nonsense. Wiley (Gain-to-Pain ratio)."
)
MAGDON_ISMAIL_2004 = AcademicReference(
    "Magdon-Ismail, M., & Atiya, A. (2004). Maximum Drawdown. Risk, 17(10), 99-102."
)
JORION_2006 = AcademicReference("Jorion, P. (2006). Value at Risk (3rd ed.). McGraw-Hill.")
ACERBI_TASCHE_2002 = AcademicReference(
    "Acerbi, C., & Tasche, D. (2002). On the Coherence of Expected Shortfall. Journal of "
    "Banking & Finance, 26(7), 1487-1503."
)
HYNDMAN_FAN_1996 = AcademicReference(
    "Hyndman, R. J., & Fan, Y. (1996). Sample Quantiles in Statistical Packages. The American "
    "Statistician, 50(4), 361-365 (definition 7 = linear interpolation)."
)
JOANES_GILL_1998 = AcademicReference(
    "Joanes, D. N., & Gill, C. A. (1998). Comparing Measures of Sample Skewness and Kurtosis. "
    "Journal of the Royal Statistical Society D, 47(1), 183-189."
)
LJUNG_BOX_1978 = AcademicReference(
    "Ljung, G. M., & Box, G. E. P. (1978). On a Measure of Lack of Fit in Time Series Models. "
    "Biometrika, 65(2), 297-303."
)
GLM_2004 = AcademicReference(
    "Getmansky, M., Lo, A. W., & Makarov, I. (2004). An Econometric Model of Serial Correlation "
    "and Illiquidity in Hedge Fund Returns. Journal of Financial Economics, 74(3), 529-609."
)
JENSEN_1968 = AcademicReference(
    "Jensen, M. C. (1968). The Performance of Mutual Funds in the Period 1945-1964. Journal of "
    "Finance, 23(2), 389-416."
)
TREYNOR_1965 = AcademicReference(
    "Treynor, J. L. (1965). How to Rate Management of Investment Funds. Harvard Business "
    "Review, 43(1), 63-75."
)
GRINOLD_KAHN_2000 = AcademicReference(
    "Grinold, R. C., & Kahn, R. N. (2000). Active Portfolio Management (2nd ed.). McGraw-Hill."
)
GOODWIN_1998 = AcademicReference(
    "Goodwin, T. H. (1998). The Information Ratio. Financial Analysts Journal, 54(4), 34-43."
)
MORNINGSTAR_CAPTURE = AcademicReference(
    "Morningstar, Inc. Upside/Downside Capture Ratio methodology (geometric compounding of "
    "returns in up/down benchmark periods)."
)

KAPLAN_KNOWLES_2004 = AcademicReference(
    "Kaplan, P. D., & Knowles, J. A. (2004). Kappa: A Generalized Downside Risk-Adjusted "
    "Performance Measure. Journal of Performance Measurement, 8(3), 42-54."
)
SORTINO_VDM_PLANTINGA_1999 = AcademicReference(
    "Sortino, F. A., van der Meer, R., & Plantinga, A. (1999). The Dutch Triangle. Journal of "
    "Portfolio Management, 26(1), 50-57 (upside potential ratio)."
)
BURKE_1994 = AcademicReference("Burke, G. (1994). A Sharper Sharpe Ratio. Futures, 23(3), 56.")
KESTNER_1996 = AcademicReference(
    "Kestner, L. N. (1996). Getting a Handle on True Performance. Futures, 25(1), 44-46 "
    "(Sterling ratio)."
)
ZANGARI_1996 = AcademicReference(
    "Zangari, P. (1996). A VaR Methodology for Portfolios That Include Options. RiskMetrics "
    "Monitor, First Quarter, 4-12 (Cornish-Fisher VaR)."
)
FAVRE_GALEANO_2002 = AcademicReference(
    "Favre, L., & Galeano, J.-A. (2002). Mean-Modified Value-at-Risk Optimization with Hedge "
    "Funds. Journal of Alternative Investments, 5(2), 21-25."
)
BOUDT_PETERSON_CROUX_2008 = AcademicReference(
    "Boudt, K., Peterson, B. G., & Croux, C. (2008). Estimation and Decomposition of Downside "
    "Risk for Portfolios with Non-Normal Returns. Journal of Risk, 11(2), 79-103."
)
MERTENS_2002 = AcademicReference(
    "Mertens, E. (2002). Comments on Variance of the IID Estimator in Lo (2002). Working paper, "
    "University of Basel."
)
OPDYKE_2007 = AcademicReference(
    "Opdyke, J. D. (2007). Comparing Sharpe Ratios: So Where Are the p-Values? Journal of Asset "
    "Management, 8(5), 308-336."
)
BAILEY_LDP_2012 = AcademicReference(
    "Bailey, D. H., & Lopez de Prado, M. (2012). The Sharpe Ratio Efficient Frontier. Journal "
    "of Risk, 15(2), 3-44 (Probabilistic Sharpe Ratio, Minimum Track Record Length)."
)
JARQUE_BERA_1987 = AcademicReference(
    "Jarque, C. M., & Bera, A. K. (1987). A Test for Normality of Observations and Regression "
    "Residuals. International Statistical Review, 55(2), 163-172."
)
STUDENT_1908 = AcademicReference(
    "Student [Gosset, W. S.] (1908). The Probable Error of a Mean. Biometrika, 6(1), 1-25."
)

CHEKHLOV_2005 = AcademicReference(
    "Chekhlov, A., Uryasev, S., & Zabarankin, M. (2005). Drawdown Measure in Portfolio "
    "Optimization. International Journal of Theoretical and Applied Finance, 8(1), 13-58 "
    "(Drawdown-at-Risk and Conditional Drawdown-at-Risk)."
)
AHMADI_JAVID_2012 = AcademicReference(
    "Ahmadi-Javid, A. (2012). Entropic Value-at-Risk: A New Coherent Risk Measure. Journal of "
    "Optimization Theory and Applications, 155(3), 1105-1123."
)
CAJAS_2021 = AcademicReference(
    "Cajas, D. (2021). Entropic Portfolio Optimization: A Disciplined Convex Programming "
    "Framework. SSRN working paper 3792520 (Entropic Drawdown-at-Risk)."
)
TREYNOR_BLACK_1973 = AcademicReference(
    "Treynor, J. L., & Black, F. (1973). How to Use Security Analysis to Improve Portfolio "
    "Selection. Journal of Business, 46(1), 66-86 (appraisal ratio)."
)
MODIGLIANI_1997 = AcademicReference(
    "Modigliani, F., & Modigliani, L. (1997). Risk-Adjusted Performance. Journal of Portfolio "
    "Management, 23(2), 45-54 (M-squared)."
)
FABOZZI_FRANCIS_1977 = AcademicReference(
    "Fabozzi, F. J., & Francis, J. C. (1977). Stability Tests for Alphas and Betas over Bull "
    "and Bear Market Conditions. Journal of Finance, 32(4), 1093-1099."
)
MORNINGSTAR_BATTING = AcademicReference(
    "Morningstar, Inc. Batting average: share of periods in which a fund outperformed its "
    "benchmark (Morningstar Direct data definitions)."
)
# --- Library references ----------------------------------------------------
PA = "PerformanceAnalytics 2.0.4 (R)"
EMP = "empyrical-reloaded 0.5.12"
QS = "QuantStats 0.0.81"
NUMPY = "NumPy"
SCIPY = "SciPy"
STATSMODELS = "statsmodels"
PANDAS = "pandas"
SKFOLIO = "skfolio 1.0.6"


def lib(library: str, function: str, agrees: bool = True, note: str = "") -> LibraryReference:
    return LibraryReference(library=library, function=function, agrees=agrees, note=note)
