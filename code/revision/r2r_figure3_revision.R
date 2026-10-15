# ==============================================================================
# Figure 3, revised (revision, September 2026): predicted probabilities
# ------------------------------------------------------------------------------
# Standalone reproduction of Figure 3 only: it repeats only the preprocessing
# and the single model Figure 3 needs, and writes two new files with a
# "_revised" suffix, overwriting nothing.
#
#   Rscript r2r_figure3_revision.R
#
# Outputs (results/figures/):
#   inferential_SI_N_log_odds_revised.png     Figure SA4.1: centred smooth term, relabelled
#   inferential_SI_N_probability_revised.png  Figure 3: predicted probability, prior-corrected
#
# Revision code for Figure 3 is maintained here rather than in analysis.R, so
# that analysis.R stays as originally submitted.
# ==============================================================================

suppressMessages({
  library(mgcv)
  library(jsonlite)
  library(dplyr)
  library(yaml)
  library(ggplot2)
})

config <- yaml.load_file("/home/lauer/projects/Mastodon/config.yml")
FIG_DIR <- config$paths$figures

# --- theme (copied verbatim from analysis.R so the panels match) --------------
color_SI_N <- "#d6aec1"
my_theme <- theme(
  plot.title = element_text(size = 19, hjust = 0.5, vjust = 3),
  axis.title = element_text(size = 17),
  axis.text.x = element_text(color = "black", size = 17, margin = margin(t = 5, b = 20)),
  axis.text.y = element_text(color = "black", size = 17, margin = margin(r = 5, l = 20)),
  axis.ticks = element_line(color = "black"),
  legend.position = "none",
  plot.margin = margin(t = 50, r = 50, b = 50, l = 50, unit = "pt")
)

# --- data and preprocessing (identical to analysis.R sections 1 and 2) --------
df <- stream_in(file(paste0(
  config$paths$data$processed$final_processed, "final_processed_data.json"
)), verbose = FALSE)

z_standardize_column <- function(d, col) {
  (d[[col]] - mean(d[[col]], na.rm = TRUE)) / sd(d[[col]], na.rm = TRUE)
}
for (v in c("SI_S_abs_minmax_sign", "SI_N_minmax", "SI_I_minmax")) {
  df[[paste0(v, "_z")]] <- z_standardize_column(df, v)
}
df$twitter_tweet_count_z <- z_standardize_column(df, "twitter_tweet_count")
df$twitter_account_age_z <- z_standardize_column(df, "twitter_account_age")
df$SI_S[is.na(df$SI_S)] <- 0
df$SI_N[is.na(df$SI_N)] <- 0
df$SI_I[is.na(df$SI_I)] <- 0

df_SI_components <- df
for (v in c(
  "SI_N_minmax_z", "SI_I_minmax_z", "SI_S_abs_minmax_sign_z",
  "twitter_account_age_z", "twitter_tweet_count_z"
)) {
  df_SI_components[[v]] <- pmax(pmin(df_SI_components[[v]], 10), -10)
}
X_min <- min(df_SI_components$SI_N, na.rm = TRUE)
X_max <- max(df_SI_components$SI_N, na.rm = TRUE)
df_SI_components$SI_N_minmax <- (df_SI_components$SI_N - X_min) / (X_max - X_min)
thr <- c(-10, 10) * sd(df_SI_components$SI_N_minmax, na.rm = TRUE) +
  mean(df_SI_components$SI_N_minmax, na.rm = TRUE)
thr <- thr * (X_max - X_min) + X_min
df_SI_components$SI_N <- pmax(pmin(df_SI_components$SI_N, thr[2]), thr[1])

# --- the model behind Figure 3 (seed 16, as in analysis.R) -------------------
set.seed(16)
best_df_sample_SI_components <- df_SI_components %>%
  group_by(is_migrated) %>%
  sample_n(min(table(df_SI_components$is_migrated))) %>%
  ungroup()
set.seed(16)
mod <- gam(
  is_migrated ~ s(SI_S_abs_minmax_sign_z) + s(SI_N) + s(SI_I_minmax_z) +
    is_os_endorsement + s(twitter_account_age_z) + s(twitter_tweet_count_z),
  family = binomial, data = best_df_sample_SI_components
)

# --- panel a: centred partial effect -----------------------------------------
png(tempfile())
sm <- plot(mod, select = 2)[[2]]
dev.off()
gam_data_SI_N <- data.frame(
  SI_N = sm$x, fit = sm$fit,
  se_upper = sm$fit + 2 * sm$se, se_lower = sm$fit - 2 * sm$se
)
p_a <- ggplot() +
  geom_line(data = gam_data_SI_N, aes(x = SI_N, y = fit), color = "black") +
  geom_ribbon(data = gam_data_SI_N, aes(x = SI_N, ymin = se_lower, ymax = se_upper),
    fill = color_SI_N, alpha = 0.2
  ) +
  geom_rug(data = best_df_sample_SI_components, aes(x = SI_N),
    sides = "b", alpha = 0.5, color = "#858585"
  ) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "#8c8c8c") +
  geom_hline(yintercept = 1.016993, linetype = "dashed", color = "#8c8c8c") +
  geom_vline(xintercept = 17.83577, linetype = "dashed", color = "#8c8c8c") +
  geom_vline(xintercept = 44.90793, linetype = "dashed", color = "#8c8c8c") +
  scale_x_continuous(breaks = c(0, 18, 44, 100, 200, 300)) +
  labs(
    title = "Effect of Number of Followed Influencers\non Migration Likelihood",
    x = "Number of Followed Influencers",
    y = "Partial effect on log odds of migration (centred)"
  ) +
  coord_cartesian(ylim = c(-5, 5)) +
  theme(
    panel.grid.major = element_line(color = "white", size = 0.5),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = "white", size = 0.5),
    panel.grid.major.y = element_line(color = "white", size = 0.5)
  ) +
  my_theme
ggsave(paste0(FIG_DIR, "inferential_SI_N_log_odds_revised.png"),
  plot = p_a, width = 11, height = 10, dpi = 300
)

# --- panel b: predicted probability, corrected for the downsampling ----------
n_mig_pop <- sum(df_SI_components$is_migrated == 1)
n_non_pop <- sum(df_SI_components$is_migrated == 0)
undersampling_offset <- log(n_non_pop / n_mig_pop)
# median number of followed influencers in the FULL sample (8). The class-
# balanced sample's median is 20, but it over-represents migrated researchers,
# who follow more influencers, so the population median is the one to quote
# alongside prior-corrected (population-scale) probabilities.
median_SI_N_pop <- median(df_SI_components$SI_N)

PROB_PANEL_XMAX <- max(best_df_sample_SI_components$SI_N) # full range, to match panel a
si_n_grid <- seq(0, PROB_PANEL_XMAX, length.out = 500)
pred <- predict(mod, data.frame(
  SI_N = si_n_grid, SI_S_abs_minmax_sign_z = 0, SI_I_minmax_z = 0,
  twitter_account_age_z = 0, twitter_tweet_count_z = 0, is_os_endorsement = FALSE
), se.fit = TRUE, type = "link")
prob_df <- data.frame(
  SI_N = si_n_grid,
  fit = plogis(pred$fit - undersampling_offset),
  lo = plogis(pred$fit - 1.96 * pred$se.fit - undersampling_offset),
  hi = plogis(pred$fit + 1.96 * pred$se.fit - undersampling_offset)
)
p_b <- ggplot(prob_df, aes(x = SI_N, y = fit)) +
  geom_ribbon(aes(ymin = lo, ymax = hi), fill = color_SI_N, alpha = 0.2) +
  geom_line(color = "black") +
  geom_rug(data = subset(best_df_sample_SI_components, SI_N <= PROB_PANEL_XMAX),
    aes(x = SI_N), inherit.aes = FALSE, sides = "b", alpha = 0.5, color = "#858585"
  ) +
  # dashed lines: full-sample median (8) and 44 followed influencers (roughly
  # the 90th percentile), after which the increase flattens
  geom_vline(xintercept = median_SI_N_pop, linetype = "dashed", color = "#8c8c8c") +
  geom_vline(xintercept = 44.90793, linetype = "dashed", color = "#8c8c8c") +
  # the ticks at 0 and 8 are only ~14 pt apart at this font size, so the two
  # labels are padded with spaces: "0  " renders slightly left of its tick and
  # "  8" slightly right, keeping all labels on one line without a collision
  # No padding before x = 0 or after the end of the curve. The default vertical padding is kept: below 0% it keeps the rug clear
  # of the curve, above it keeps the 30% tick label
  scale_x_continuous(
    breaks = c(0, median_SI_N_pop, 44, 100, 200, 300),
    labels = c("0  ", paste0("  ", median_SI_N_pop), "44", "100", "200", "300"),
    expand = expansion(mult = c(0, 0))
  ) +
  scale_y_continuous(
    labels = function(x) paste0(round(100 * x, 1), "%"),
    expand = expansion(mult = c(0.05, 0.05))
  ) +
  coord_cartesian(xlim = c(0, PROB_PANEL_XMAX)) +
  labs(
    title = "Predicted Migration Probability by Number of Followed Influencers",
    x = "Number of Followed Influencers",
    y = "Predicted probability of migration"
  ) +
  theme(
    panel.grid.major = element_line(color = "white", size = 0.5),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = "white", size = 0.5),
    panel.grid.major.y = element_line(color = "white", size = 0.5)
  ) +
  my_theme
ggsave(paste0(FIG_DIR, "inferential_SI_N_probability_revised.png"),
  plot = p_b, width = 11, height = 10, dpi = 300
)

# --- numbers quoted in the manuscript ----------------------------------------
cat("\npopulation:", n_non_pop, "not migrated,", n_mig_pop, "migrated\n")
cat("undersampling offset (log odds):", round(undersampling_offset, 3), "\n")
cat("observed migration rate:", sprintf("%.2f%%", 100 * n_mig_pop / (n_mig_pop + n_non_pop)), "\n\n")
qtl <- function(x) paste(round(quantile(x, c(.5, .75, .9)), 1), collapse = " / ")
cat(sprintf("followed influencers, full sample:     median / p75 / p90 = %s ; share > 100 = %.1f%%\n",
  qtl(df_SI_components$SI_N), 100 * mean(df_SI_components$SI_N > 100)))
cat(sprintf("followed influencers, balanced sample: median / p75 / p90 = %s ; share > 100 = %.1f%%\n\n",
  qtl(best_df_sample_SI_components$SI_N), 100 * mean(best_df_sample_SI_components$SI_N > 100)))
# predicted exactly at the quoted values (not snapped to the 500-point plotting grid)
quote_pts <- c(0, 8, 10, 18, 20, 22, 44, 47, 100)
pq <- predict(mod, data.frame(
  SI_N = quote_pts, SI_S_abs_minmax_sign_z = 0, SI_I_minmax_z = 0,
  twitter_account_age_z = 0, twitter_tweet_count_z = 0, is_os_endorsement = FALSE
), se.fit = TRUE, type = "link")
for (j in seq_along(quote_pts)) {
  cat(sprintf(
    "  %3d followed peers -> p(migration) = %.2f%%  95%% CI [%.2f, %.2f]\n",
    quote_pts[j],
    100 * plogis(pq$fit[j] - undersampling_offset),
    100 * plogis(pq$fit[j] - 1.96 * pq$se.fit[j] - undersampling_offset),
    100 * plogis(pq$fit[j] + 1.96 * pq$se.fit[j] - undersampling_offset)
  ))
}
cat("\nwritten to", FIG_DIR, "\n")

# --- two checks referred to in the text ---------------------------------------
# (a) Figure 3 holds the other predictors at their full-sample means. Averaging
#     the prior-corrected predictions over all observed covariate rows instead
#     changes the curve by less than 0.2 percentage points up to 44 peers.
# (b) Zero followed peers implies zero strength and immediacy (both z-scores
#     are then well below their means), so the left end of the curve is a
#     model-based value. The observed migration rate for that group is 0.09%.
chk_pts <- c(0, 8, 22, 44)
at_means <- plogis(pq$fit[match(chk_pts, quote_pts)] - undersampling_offset)
avg_pop <- sapply(chk_pts, function(k) {
  nd <- df_SI_components; nd$SI_N <- k
  mean(plogis(predict(mod, nd) - undersampling_offset))
})
observed <- sapply(chk_pts, function(k) {
  s <- df_SI_components[abs(df_SI_components$SI_N - k) <= max(1, 0.1 * k), ]
  c(n = nrow(s), rate = 100 * mean(s$is_migrated == 1))
})
cat("\ncheck: predictions at means vs averaged over the population, and observed rates\n")
cat(sprintf("  %3d peers: at means %.2f%% | averaged %.2f%% | observed %.2f%% (n = %.0f, SI_N within %.0f of %.0f)\n",
  chk_pts, 100 * at_means, 100 * avg_pop, observed["rate", ], observed["n", ],
  pmax(1, 0.1 * chk_pts), chk_pts))
cat(sprintf("  z-score of zero strength: %.2f ; of zero immediacy: %.2f\n",
  df_SI_components$SI_S_abs_minmax_sign_z[df_SI_components$SI_N == 0][1],
  df_SI_components$SI_I_minmax_z[df_SI_components$SI_N == 0][1]))
