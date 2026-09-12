# Independent reference values for the factor regression (decision 0028).
#
# Reads tests/fixtures/factor_case_{fund,factors}.csv, aligns them by calendar
# month (dropping the month with a missing factor value, never filling it), fits
# lm(fund - RF ~ Mkt-RF + SMB + HML) and computes Newey-West standard errors with
# sandwich::NeweyWest(lag = L, prewhite = FALSE, adjust = TRUE), L = floor(4 (m/100)^(2/9)),
# and Student-t inference with lmtest::coeftest. Writes
# tests/fixtures/reference/factor_models.json, which is committed so that the
# Python test suite never needs R at runtime.
#
# Usage (from the repository root):
#   Rscript validation/r/factor_reference.R

suppressPackageStartupMessages({
  library(sandwich)
  library(lmtest)
  library(jsonlite)
})

fixtures <- file.path("tests", "fixtures")
fund <- read.csv(file.path(fixtures, "factor_case_fund.csv"), stringsAsFactors = FALSE)
fac <- read.csv(file.path(fixtures, "factor_case_factors.csv"), stringsAsFactors = FALSE,
                check.names = FALSE)
fund$month <- substr(fund$date, 1, 7)
fac$month <- substr(fac$date, 1, 7)
# Each model uses the months where the fund and *its own* factor columns all have values.
aligned <- function(cols) {
  f <- fac[complete.cases(fac[, cols]), c("month", cols)]
  d <- merge(fund[, c("month", "return")], f, by = "month")
  d[order(d$month), ]
}

fit_case <- function(y, X) {
  model <- lm(y ~ ., data = data.frame(y = y, X, check.names = FALSE))
  m <- length(y)
  lag <- floor(4 * (m / 100)^(2 / 9))
  V <- NeweyWest(model, lag = lag, prewhite = FALSE, adjust = TRUE)
  ct <- coeftest(model, vcov. = V)
  ci <- coefci(model, vcov. = V, level = 0.95)
  s <- summary(model)
  list(
    observations = m,
    hac_lags = lag,
    estimate = unname(coef(model)),
    std_error = unname(ct[, 2]),
    t = unname(ct[, 3]),
    p = unname(ct[, 4]),
    ci_lower = unname(ci[, 1]),
    ci_upper = unname(ci[, 2]),
    r_squared = s$r.squared,
    adj_r_squared = s$adj.r.squared,
    sigma = s$sigma
  )
}

out <- list(
  generated_with = paste("R", getRversion(), "sandwich", packageVersion("sandwich"),
                         "lmtest", packageVersion("lmtest")),
  ff3 = with(aligned(c("Mkt-RF", "SMB", "HML", "RF")), fit_case(
    return - RF / 100,
    data.frame(mkt = get("Mkt-RF") / 100, smb = SMB / 100, hml = HML / 100)
  )),
  capm = with(aligned(c("Mkt-RF", "RF")), fit_case(
    return - RF / 100,
    data.frame(mkt = get("Mkt-RF") / 100)
  ))
)
dir.create(file.path(fixtures, "reference"), showWarnings = FALSE, recursive = TRUE)
write(toJSON(out, digits = NA, auto_unbox = TRUE, pretty = TRUE),
      file.path(fixtures, "reference", "factor_models.json"))
cat("wrote", file.path(fixtures, "reference", "factor_models.json"), "\n")
