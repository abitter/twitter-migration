# ==============================================================================
# Number vs. proportion of sources (revision, September 2026)
# ------------------------------------------------------------------------------
# Does the *proportion* of a researcher's network that
# discussed the migration (complex contagion) predict migration better than
# the *number* of such sources (the preregistered, social impact theory based
# operationalization)? This exploratory check defines
#
#   proportion = SI_N / twitter_following_count
#
# i.e. followed influencers (accounts that posted about the migration) as a
# share of all accounts the researcher follows (Twitter profile metadata),
# and compares GAMs that use the number, the proportion, both, or the number
# plus network size. Reported in the manuscript's second limitation
# (Section 4.4): deviance explained 33% vs. 28%, out-of-sample AUC 0.86 vs.
# 0.83, median share 1.9%.
#
# Caveat (see Section 4.4 of the manuscript): the numerator counts peers who posted about
# the migration, not peers who migrated, so this is not a formal test of
# simple vs. complex contagion.
#
# Standalone: repeats the preprocessing of analysis.R section 1 and the
# seed-16 balanced downsample of section 2 (the only new covariate is
# twitter_following_count, which analysis.R standardizes but never uses).
# Prints aggregates only; nothing is written to disk.
#
#   Rscript r2r_number_vs_proportion.R
# ==============================================================================

suppressMessages({
  library(mgcv)
  library(jsonlite)
  library(dplyr)
  library(yaml)
})
options(width = 160)
t0 <- Sys.time()
config <- yaml.load_file("/home/lauer/projects/Mastodon/config.yml")

# --- data and preprocessing (as in analysis.R section 1) ----------------------
df <- stream_in(file(paste0(
  config$paths$data$processed$final_processed, "final_processed_data.json"
)), verbose = FALSE)
stopifnot("twitter_following_count" %in% names(df))
df$SI_N[is.na(df$SI_N)] <- 0
z <- function(x) (x - mean(x)) / sd(x)
clip10 <- function(x) pmax(pmin(x, 10), -10)
df$SI_S_abs_minmax_sign_z <- clip10(z(df$SI_S_abs_minmax_sign))
df$SI_I_minmax_z <- clip10(z(df$SI_I_minmax))
df$twitter_account_age_z <- clip10(z(df$twitter_account_age))
df$twitter_tweet_count_z <- clip10(z(df$twitter_tweet_count))

# --- proportion of sources ----------------------------------------------------
df$prop <- ifelse(df$twitter_following_count > 0,
                  df$SI_N / df$twitter_following_count, 0)
df$prop <- pmin(df$prop, 1)  # a few stale following counts give SI_N > following

cat("following_count quantiles:\n")
print(quantile(df$twitter_following_count, c(0, .25, .5, .75, .9, .99, 1)))
cat(sprintf("following_count == 0: %d ; SI_N > following_count: %d\n",
            sum(df$twitter_following_count == 0),
            sum(df$SI_N > df$twitter_following_count)))
cat("proportion quantiles (%):\n")
print(round(100 * quantile(df$prop, c(.25, .5, .75, .9, .99)), 2))
cat(sprintf(paste0("Spearman: SI_N vs following_count %.2f ; ",
                   "SI_N vs proportion %.2f ; proportion vs following_count %.2f\n"),
            cor(df$SI_N, df$twitter_following_count, method = "spearman"),
            cor(df$SI_N, df$prop, method = "spearman"),
            cor(df$prop, df$twitter_following_count, method = "spearman")))

# --- descriptive: migration rate by proportion decile (full population) -------
cat("\nObserved migration rate by proportion decile (population):\n")
df$pdec <- cut(df$prop, quantile(df$prop, seq(0, 1, .1)), include.lowest = TRUE)
print(as.data.frame(df %>%
  group_by(pdec) %>%
  summarise(n = n(), median_SI_N = median(SI_N),
            median_following = median(twitter_following_count),
            mig_pct = round(100 * mean(is_migrated == 1), 2), .groups = "drop")))

cat("\nMigration rate (%) by SI_N bin x following-count tertile\n",
    "(same number of sources in a larger network):\n")
df$nbin <- cut(df$SI_N, c(-1, 0, 10, 25, 50, 100, 1e6))
df$ftert <- cut(df$twitter_following_count,
                quantile(df$twitter_following_count, c(0, 1/3, 2/3, 1)),
                include.lowest = TRUE, labels = c("small", "medium", "large"))
print(round(100 * with(df, tapply(is_migrated == 1, list(nbin, ftert), mean)), 2))

# --- models on the seed-16 balanced sample (as in analysis.R section 2) -------
set.seed(16)
bal <- df %>%
  group_by(is_migrated) %>%
  sample_n(min(table(df$is_migrated)), replace = FALSE) %>%
  ungroup()
base <- paste("is_migrated ~ s(SI_S_abs_minmax_sign_z) + s(SI_I_minmax_z) +",
              "is_os_endorsement + s(twitter_account_age_z) + s(twitter_tweet_count_z)")
forms <- list(
  number                  = paste(base, "+ s(SI_N)"),
  proportion              = paste(base, "+ s(prop)"),
  both                    = paste(base, "+ s(SI_N) + s(prop)"),
  number_and_network_size = paste(base, "+ s(SI_N) + s(log1p(twitter_following_count))")
)
auc <- function(p, y) {
  r <- rank(p); n1 <- sum(y); n0 <- length(y) - n1
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}
set.seed(16)
idx <- sample(nrow(bal), 0.8 * nrow(bal))
tr <- bal[idx, ]; te <- bal[-idx, ]

cat("\n=== GAMs on the seed-16 balanced sample ===\n")
cat("(deviance explained and AIC: full balanced sample; AUC: 80/20 split)\n")
res <- lapply(names(forms), function(nm) {
  m_full <- gam(as.formula(forms[[nm]]), family = binomial, data = bal)
  m_tr <- gam(as.formula(forms[[nm]]), family = binomial, data = tr)
  data.frame(model = nm,
             dev_expl = round(summary(m_full)$dev.expl, 3),
             AIC = round(AIC(m_full)),
             test_AUC = round(auc(predict(m_tr, te), te$is_migrated == 1), 3))
})
print(do.call(rbind, res), row.names = FALSE)

m_both <- gam(as.formula(forms$both), family = binomial, data = bal)
cat("\n'both' model, smooth terms for number vs. proportion:\n")
print(round(summary(m_both)$s.table[c("s(SI_N)", "s(prop)"), ], 2))
cat(sprintf("\nDone in %.1f min\n", as.numeric(difftime(Sys.time(), t0, units = "mins"))))
