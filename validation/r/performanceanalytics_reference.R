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

single_series <- function(R) {
  dd <- as.numeric(Drawdowns(R))
  list(
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
  )
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
  down_capture_pa = num(UpDownRatios(Ra, Rb, method = "Capture", side = "Down"))
)

path <- file.path(out_dir, "performanceanalytics.json")
writeLines(toJSON(results, auto_unbox = TRUE, digits = NA, pretty = TRUE), path)
cat("Wrote", path, "\n")
