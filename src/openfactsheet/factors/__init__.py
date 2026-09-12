"""Factor analysis with caller-supplied factor returns (decision 0028).

:mod:`~openfactsheet.factors.data` parses and normalizes factor returns (one
return scale for all columns; an ``RF`` column is the risk-free rate);
:mod:`~openfactsheet.factors.regressions` aligns them with the fund (never
filling gaps) and estimates the regression with statsmodels OLS and Newey-West
standard errors; :mod:`~openfactsheet.factors.models` holds the results. Factor
data are always supplied explicitly; OpenFactsheet never downloads them.
"""
