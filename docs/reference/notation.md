# Notation

Symbols used in the [exact formulas](formulas.md) and on every metric page.
All quantities are computed in `float64` without intermediate rounding.

## Returns and time

| Symbol | Meaning |
|---|---|
| $r_t$ | Simple decimal return of period $t$ after normalization ($0.01$ = +1%). Percent inputs have been divided by 100; missing values have been removed, never filled. |
| $t = 1, \dots, n$ | Observation index in chronological order. |
| $n$ | Number of analyzed observations (after trimming and removing missing values). |
| $r_{(1)} \le \dots \le r_{(n)}$ | Order statistics (returns sorted ascending). |
| $P$ | Canonical periods per year for the detected frequency: 252 (business-day daily), 365 (calendar-day daily), 52, 12, 4, 1. Undefined for irregular or unknown frequency, in which case no annualized metric is computed. See [policies](policies.md#annualization-factors). |
| $y = n / P$ | Years of history used by the confidence policy. |
| $\#\{\cdot\}$ | Number of elements of a set. |

## Moments

```math
\bar r = \frac{1}{n}\sum_{t=1}^{n} r_t, \qquad
s = \sqrt{\frac{1}{n-1}\sum_{t=1}^{n}(r_t-\bar r)^2}, \qquad
m_k = \frac{1}{n}\sum_{t=1}^{n}(r_t-\bar r)^k
```

$s$ is the sample standard deviation (denominator $n-1$); $m_k$ are central sample moments
(denominator $n$) used by skewness and kurtosis.

## Wealth and drawdowns

```math
W_0 = 1, \qquad W_t = \prod_{i=1}^{t}(1+r_i), \qquad
M_t = \max_{0 \le u \le t} W_u, \qquad D_t = \frac{W_t}{M_t} - 1 \le 0
```

- $W_0 = 1$ is the wealth before the first return and counts as the first peak, so a loss in
  the first period is a drawdown.
- A **drawdown episode** $k$ is a maximal run of consecutive periods $E_k \subseteq \{1..n\}$
  with $D_t < 0$. Its **peak index** $\pi_k$ is the period just before the run (possibly 0),
  its **trough** is the $\arg\min_{t\in E_k} D_t$ (first occurrence), its **depth** is
  $\delta_k = \min_{t\in E_k} D_t$, and its **recovery index** $\rho_k$ is the first period
  after the run with $D_t = 0$, if any. $K$ is the number of episodes.
- Episodes that have not recovered by period $n$ are **ongoing**.
- If some $r_t < -1$, the wealth path is invalid and every wealth-path metric is
  `not_applicable`; if some $r_t = -1$, wealth is 0 from then on (total loss).

## Quantiles

$Q_p(r)$ is the empirical quantile with linear interpolation (Hyndman & Fan definition 7, the
default of NumPy and R):

```math
h = (n-1)p + 1, \quad j = \lfloor h \rfloor, \quad
Q_p(r) = r_{(j)} + (h - j)\left(r_{(j+1)} - r_{(j)}\right)
```

with $r_{(n+1)} := r_{(n)}$ when $j = n$.

## Benchmark-relative quantities

| Symbol | Meaning |
|---|---|
| $b_t$ | Benchmark return in the same period as $r_t$, after alignment. |
| $m$ | Number of aligned periods (intersection of fund and benchmark; never filled). All benchmark-relative sums run over these $m$ periods, and $\bar r$, $\bar b$ are means over them. |
| $a_t = r_t - b_t$ | Active (excess-over-benchmark) return. |
| $\bar a$, $s_a$ | Mean and sample standard deviation of $a_t$. |
| $\hat\alpha, \hat\beta$ | OLS intercept and slope of $r_t = \alpha + \beta b_t + \varepsilon_t$. |
| $\hat\varepsilon_t$ | OLS residuals $r_t - \hat\alpha - \hat\beta b_t$. |

## Factor-model quantities

| Symbol | Meaning |
|---|---|
| $f_{j,t}$ | Return of supplied factor $j = 1, \dots, k$ in the same period as $r_t$, after alignment (never filled). |
| $k$ | Number of supplied factors (the risk-free column is not a factor). |
| $m$ | Number of periods where the fund and every factor (and the RF column, if supplied) have a return. Factor-model sums run over these periods. |
| $r^{\mathrm{RF}}_t$ | Value of a supplied factor-file column named `RF` (risk-free rate); taken as 0 when no such column is supplied. |
| $y_t = r_t - r^{\mathrm{RF}}_t$ | Dependent variable of the factor regression. |
| $\hat\alpha, \hat\beta_j$ | OLS intercept and loadings of $y_t = \alpha + \sum_j \beta_j f_{j,t} + \varepsilon_t$. |
| $X$ | $m \times (k + 1)$ design matrix: a column of ones and the factor returns. |
| $\hat\Gamma_\ell$ | $\frac{1}{m}\sum_{t=\ell+1}^{m} \hat\varepsilon_t \hat\varepsilon_{t-\ell}\, x_t x_{t-\ell}^\top$ (and its transpose for $\ell < 0$), with $x_t$ the $t$-th row of $X$. |
| $q$ | Newey-West lag $\lfloor 4 (m/100)^{2/9} \rfloor$. |

## Canonical constants (methodology 0.1.0)

| Symbol | Value | Meaning |
|---|---|---|
| $r_f$ | 0 | Risk-free rate per period. |
| $\tau$ | 0 | Minimum acceptable return (Sortino target) per period. |
| $L$ | 0 | Omega threshold per period. |
| $p$ | 0.05 | Tail probability for 95% VaR / ES. |

The authoritative values are in [policies](policies.md) (generated from the code).
