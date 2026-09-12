# Independent reference values from R PerformanceAnalytics.
#
# Reads the committed fixtures in tests/fixtures/, computes reference values
# with PerformanceAnalytics, and writes tests/fixtures/reference/performanceanalytics.json.
# The JSON is committed so the Python test suite never needs R at runtime.
#
# PerformanceAnalytics is GPL-licensed. It is used here purely as an external
# numerical oracle; no PerformanceAnalytics code is copied into OpenFactsheet.
#
# Usage (from the repository root):
#   Rscript validation/r/performanceanalytics_reference.R

suppressPackageStartupMessages({
  library(PerformanceAnalytics)
  library(xts)
  library(jsonlite)
})

fixtures <- file.path("tests", "fixtures")
out_dir <- file.path(fixtures, "reference")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

read_fixture <- function(name) {
  df <- read.csv(file.path(fixtures, name), stringsAsFactors = FALSE)
  xts(df$return, order.by = as.Date(df$date))
}

num <- function(x) as.numeric(x)[1]

# NA (JSON null) when PerformanceAnalytics refuses a case (e.g. PSR / MinTRL with a
# negative Sharpe ratio stop() in PerformanceAnalytics 2.0.4).
safe <- function(expr) tryCatch(num(expr), error = function(e) NA_real_)

phase2 <- function(R) {
  r <- as.numeric(R)
  n <- length(r)
  cagr <- num(Return.annualized(R, scale = 12, geometric = TRUE))
  dd <- as.numeric(Drawdowns(R))
  episodes <- findDrawdowns(R)
  depths <- episodes$return[episodes$return < 0]
  g1 <- num(skewness(R, method = "moment"))
  g2 <- num(kurtosis(R, method = "excess"))
  jb <- n / 6 * (g1^2 + g2^2 / 4)
  tt <- t.test(r)
  # Episode table (PerformanceAnalytics findDrawdowns): negative episodes only.
  neg <- episodes$return < 0
  last_open <- tail(as.numeric(Drawdowns(R)), 1) < 0
  # Complete calendar years: years with 12 monthly observations.
  yr <- format(index(R), "%Y")
  year_ret <- tapply(r, yr, function(x) prod(1 + x) - 1)
  year_n <- tapply(r, yr, length)
  complete <- year_ret[year_n == 12]
  # Rolling one-year (12-month) compounded returns.
  rolled <- as.numeric(zoo::rollapply(R, 12, function(x) prod(1 + x) - 1, align = "right"))
  rolled <- rolled[!is.na(rolled)]  # drop the padding before the first full window
  list(
    episode_depths = depths,
    episode_lengths = episodes$length[neg],
    episode_peak_to_trough = episodes$peaktotrough[neg],
    episode_recovery = episodes$recovery[neg],
    last_episode_open = last_open,
    calendar_year_returns = as.list(complete),
    rolling_year_min = min(rolled),
    rolling_year_max = max(rolled),
    rolling_year_positive_share = mean(rolled > 0),
    rolling_year_windows = length(rolled),
    es_modified_95 = num(ES(R, p = 0.95, method = "modified")),
    cdd_pa = num(CDD(R, p = 0.95)),
    all_run_returns = episodes$return,  # drawdown episodes and the zero runs between them
    mean_geometric = num(mean.geometric(R)),
    iqr = IQR(r),
    kappa_3 = num(Kappa(R, MAR = 0, l = 3)),
    upside_potential_full = num(UpsidePotentialRatio(r, MAR = 0, method = "full")),
    upside_potential_subset = num(UpsidePotentialRatio(r, MAR = 0, method = "subset")),
    semi_deviation_per_period = num(SemiDeviation(R)),
    mean_absolute_deviation = num(MeanAbsoluteDeviation(R)),
    downside_potential = num(DownsideDeviation(R, MAR = 0, potential = TRUE)),
    sterling_ratio = num(SterlingRatio(R, scale = 12, excess = 0.1)),
    burke_ratio_pa = num(BurkeRatio(R)),
    burke_from_find_drawdowns = cagr / sqrt(sum(depths^2)),
    pain_ratio_from_drawdowns = cagr / mean(abs(dd)),
    var_gaussian_95 = num(VaR(R, p = 0.95, method = "gaussian")),
    var_modified_95 = num(VaR(R, p = 0.95, method = "modified")),
    psr_ref0_with_kurtosis = safe(
      ProbSharpeRatio(R, Rf = 0, refSR = 0, ignore_kurtosis = FALSE)$sr_prob
    ),
    min_trl_ref0_with_kurtosis = safe(
      MinTrackRecord(R, Rf = 0, refSR = 0, p = 0.95, ignore_kurtosis = FALSE)$min_TRL
    ),
    # PA reports the interval rounded to 4 decimals; half-width = qnorm(0.95) * SE.
    psr_ci_half_width_per_period = tryCatch({
      ci <- ProbSharpeRatio(R, Rf = 0, refSR = 0, ignore_kurtosis = FALSE)$sr_confidence_interval
      (num(ci[["Upper Bound"]]) - num(ci[["Lower Bound"]])) / 2
    }, error = function(e) NA_real_),
    jarque_bera_statistic = jb,
    jarque_bera_pvalue = 1 - pchisq(jb, 2),
    t_test_ci_lower = tt$conf.int[1],
    t_test_ci_upper = tt$conf.int[2],
    t_test_statistic = unname(tt$statistic),
    t_test_pvalue = tt$p.value
  )
}

single_series <- function(R) {
  dd <- as.numeric(Drawdowns(R))
  c(list(
    n = length(R),
    cumulative_return = num(Return.cumulative(R, geometric = TRUE)),
    cagr = num(Return.annualized(R, scale = 12, geometric = TRUE)),
    annualized_arithmetic_mean = num(Return.annualized(R, scale = 12, geometric = FALSE)),
    volatility = num(StdDev(R)),
    annualized_volatility = num(StdDev.annualized(R, scale = 12)),
    downside_deviation_per_period = num(DownsideDeviation(R, MAR = 0, method = "full")),
    sharpe_ratio_arithmetic = num(SharpeRatio.annualized(R, Rf = 0, scale = 12, geometric = FALSE)),
    sharpe_ratio_pa_default_geometric = num(SharpeRatio.annualized(R, Rf = 0, scale = 12)),
    sortino_ratio_per_period = num(SortinoRatio(R, MAR = 0)),
    calmar_ratio = num(CalmarRatio(R, scale = 12)),
    max_drawdown_magnitude = num(maxDrawdown(R)),
    average_drawdown_magnitude = num(AverageDrawdown(R)),
    ulcer_index_from_drawdowns = sqrt(mean(dd^2)),
    pain_index_from_drawdowns = mean(abs(dd)),
    ulcer_index_pa = num(UlcerIndex(R)),
    omega_ratio = num(Omega(R, L = 0, method = "simple")),
    skewness_moment = num(skewness(R, method = "moment")),
    skewness_pa_sample = num(skewness(R, method = "sample")),
    excess_kurtosis_sample = num(kurtosis(R, method = "sample_excess")),
    var_historical_95 = num(VaR(R, p = 0.95, method = "historical")),
    es_historical_95 = num(ES(R, p = 0.95, method = "historical")),
    longest_drawdown_length = max(findDrawdowns(R)$length[findDrawdowns(R)$return < 0]),
    acf_lag1 = num(acf(as.numeric(R), lag.max = 3, plot = FALSE)$acf[2]),
    acf_lag2 = num(acf(as.numeric(R), lag.max = 3, plot = FALSE)$acf[3]),
    acf_lag3 = num(acf(as.numeric(R), lag.max = 3, plot = FALSE)$acf[4]),
    ljung_box_pvalue_3 = num(Box.test(as.numeric(R), lag = 3, type = "Ljung-Box")$p.value)
  ), phase2(R))
}

results <- list(
  generator = paste0(
    "PerformanceAnalytics ", as.character(packageVersion("PerformanceAnalytics")),
    " on ", R.version.string
  ),
  monthly_fund_10y = single_series(read_fixture("monthly_fund_10y.csv")),
  negative_fund = single_series(read_fixture("negative_fund.csv")),
  smoothed_hedge_fund = single_series(read_fixture("smoothed_hedge_fund.csv"))
)

# Benchmark case: fund is month-end dated, benchmark month-start dated. Align by
# calendar month (yearmon), matching the OpenFactsheet convention.
fund_df <- read.csv(file.path(fixtures, "benchmark_case_fund.csv"), stringsAsFactors = FALSE)
bench_df <- read.csv(file.path(fixtures, "benchmark_case_benchmark.csv"), stringsAsFactors = FALSE)
fund_df$ym <- format(as.Date(fund_df$date), "%Y-%m")
bench_df$ym <- format(as.Date(bench_df$date), "%Y-%m")
m <- merge(fund_df, bench_df, by = "ym", suffixes = c("_fund", "_bench"))
m <- m[order(m$ym), ]
idx <- as.Date(paste0(m$ym, "-01"))
Ra <- xts(m$return_fund, order.by = idx)
Rb <- xts(m$return_bench, order.by = idx)
active <- as.numeric(Ra) - as.numeric(Rb)
results$benchmark_case <- list(
  aligned_observations = nrow(m),
  beta = num(CAPM.beta(Ra, Rb)),
  alpha_per_period = num(CAPM.alpha(Ra, Rb)),
  correlation = cor(as.numeric(Ra), as.numeric(Rb)),
  r_squared = summary(lm(as.numeric(Ra) ~ as.numeric(Rb)))$r.squared,
  tracking_error = num(TrackingError(Ra, Rb, scale = 12)),
  information_ratio_pa = num(InformationRatio(Ra, Rb, scale = 12)),
  information_ratio_arithmetic = mean(active) * 12 / (sd(active) * sqrt(12)),
  active_premium_pa = num(ActivePremium(Ra, Rb, scale = 12)),
  treynor_ratio_pa = num(TreynorRatio(Ra, Rb, Rf = 0, scale = 12)),
  up_capture_pa = num(UpDownRatios(Ra, Rb, method = "Capture", side = "Up")),
  down_capture_pa = num(UpDownRatios(Ra, Rb, method = "Capture", side = "Down")),
  # Decision 0027 (benchmark-relative additions).
  up_percent_pa = num(UpDownRatios(Ra, Rb, method = "Percent", side = "Up")),
  down_percent_pa = num(UpDownRatios(Ra, Rb, method = "Percent", side = "Down")),
  specific_risk_pa = num(SpecificRisk(Ra, Rb, Rf = 0)),
  appraisal_ratio_pa = num(AppraisalRatio(Ra, Rb, Rf = 0, method = "appraisal")),
  jensen_alpha_pa = num(CAPM.jensenAlpha(Ra, Rb, Rf = 0)),
  modigliani_pa_per_period = num(Modigliani(Ra, Rb, Rf = 0)),
  bull_beta = num(CAPM.beta.bull(Ra, Rb, Rf = 0)),
  bear_beta = num(CAPM.beta.bear(Ra, Rb, Rf = 0)),
  timing_ratio = num(TimingRatio(Ra, Rb, Rf = 0)),
  residual_se_lm = summary(lm(as.numeric(Ra) ~ as.numeric(Rb)))$sigma
)

path <- file.path(out_dir, "performanceanalytics.json")
writeLines(toJSON(results, auto_unbox = TRUE, digits = NA, pretty = TRUE, na = "null"), path)
cat("Wrote", path, "\n")
