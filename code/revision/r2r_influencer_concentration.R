# ==============================================================================
# Are a few widely followed individuals driving the migration?
# (revision, September 2026; Supplementary Appendix 5)
# ------------------------------------------------------------------------------
# A low SHAP value for strength does not rule out that
# the same few influencers appear in most researchers' networks and drive the
# migration. This script checks that directly:
#   1. how concentrated the researcher -> influencer follow network is
#   2. whether following a specific top-20 (most-followed) influencer predicts
#      migration beyond the social impact components (adjusted ORs, joint model,
#      out-of-sample AUC)
# Standalone: repeats the preprocessing of analysis.R sections 1-2 and the
# components model on the seed-16 downsample. Prints aggregates only; no
# influencer-level identifiers are written out.
#
#   Rscript r2r_influencer_concentration.R
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
SI_DIR <- config$paths$data$processed$social_impact

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
D <- df
for (v in c(
  "SI_N_minmax_z", "SI_I_minmax_z", "SI_S_abs_minmax_sign_z",
  "twitter_account_age_z", "twitter_tweet_count_z"
)) {
  D[[v]] <- pmax(pmin(D[[v]], 10), -10)
}
D$SI_N_raw <- D$SI_N
X_min <- min(D$SI_N); X_max <- max(D$SI_N)
D$SI_N_minmax <- (D$SI_N - X_min) / (X_max - X_min)
thr <- c(-10, 10) * sd(D$SI_N_minmax) + mean(D$SI_N_minmax)
thr <- thr * (X_max - X_min) + X_min
D$SI_N <- pmax(pmin(D$SI_N, thr[2]), thr[1])
D$id <- as.character(D$id)
n_res <- nrow(D); n_mig <- sum(D$is_migrated == 1)

# --- influencers and the researcher -> influencer edge list -------------------
inf <- stream_in(file(paste0(SI_DIR, "profiles_influencers_weighted_remainingSI.json")), verbose = FALSE)
inf <- data.frame(
  inf_id = as.character(inf$id),
  score = inf[["influence_score_20-80_weighted"]],
  stringsAsFactors = FALSE
)
fl <- stream_in(file(paste0(SI_DIR, "researchers_followed_influencer_IDs.json")), verbose = FALSE)
edges <- data.frame(
  id = rep(as.character(fl$researcher_id), lengths(fl$followed_influencer_ids)),
  inf_id = as.character(unlist(fl$followed_influencer_ids)),
  stringsAsFactors = FALSE
)
edges <- edges[edges$id %in% D$id & edges$inf_id %in% inf$inf_id, ]
edges <- edges[!duplicated(edges), ]
cat("loaded in", format(Sys.time() - t0), "| researchers:", n_res, "| influencers:", nrow(inf), "| follow ties:", nrow(edges), "\n")

# sanity check: the edge counts must reproduce the number-of-sources component
cnt <- edges %>% count(id, name = "n_edges")
chk <- D %>% select(id, SI_N_raw) %>% left_join(cnt, by = "id") %>% mutate(n_edges = coalesce(n_edges, 0L))
cat(sprintf("number of sources reproduced from the edge list for %.2f%% of researchers\n\n", 100 * mean(chk$n_edges == chk$SI_N_raw)))

# --- 1. concentration of the follow network -----------------------------------
mig <- setNames(D$is_migrated == 1, D$id)
per_inf <- edges %>%
  mutate(m = mig[id]) %>%
  group_by(inf_id) %>%
  summarise(n_followers = n(), n_mig_followers = sum(m), .groups = "drop") %>%
  left_join(inf, by = "inf_id") %>%
  arrange(desc(n_followers))
cat("=== 1. Concentration of the follow network ===\n")
cat("followers per influencer (quantiles): "); print(round(quantile(per_inf$n_followers, c(.5, .9, .99, 1))))
for (k in c(10, 20, 50, 100, 500)) {
  cat(sprintf("  top %3d most-followed influencers receive %5.1f%% of all follow ties\n", k, 100 * sum(head(per_inf$n_followers, k)) / nrow(edges)))
}
cat(sprintf("  most-followed single influencer: followed by %.1f%% of all researchers and %.1f%% of migrated researchers\n",
  100 * per_inf$n_followers[1] / n_res, 100 * per_inf$n_mig_followers[1] / n_mig))
reach <- function(ids) {
  r <- unique(edges$id[edges$inf_id %in% ids])
  c(all = 100 * length(r) / n_res, migrated = 100 * sum(mig[r]) / n_mig)
}
cat("reach (% following at least one of the top-k most-followed influencers):\n")
for (k in c(1, 5, 10, 20, 50)) {
  r <- reach(head(per_inf$inf_id, k))
  cat(sprintf("  top %2d: %5.1f%% of all researchers, %5.1f%% of migrated researchers\n", k, r["all"], r["migrated"]))
}
r <- reach(head(inf$inf_id[order(-inf$score)], 20))
cat(sprintf("  top 20 by influence score: %.1f%% of all, %.1f%% of migrated\n", r["all"], r["migrated"]))
cat(sprintf("migration rate among followers of the 20 most-followed influencers: %.1f%% to %.1f%% (overall rate %.2f%%)\n",
  100 * min(head(per_inf$n_mig_followers / per_inf$n_followers, 20)), 100 * max(head(per_inf$n_mig_followers / per_inf$n_followers, 20)), 100 * n_mig / n_res))
cat(sprintf("Spearman correlation, influence score vs followers in sample: %.2f\n\n", cor(per_inf$score, per_inf$n_followers, method = "spearman")))

# --- 2. do specific top influencers add to the components model? --------------
set.seed(16)
bal <- D %>% group_by(is_migrated) %>% sample_n(min(table(D$is_migrated))) %>% ungroup()
base_f <- is_migrated ~ s(SI_S_abs_minmax_sign_z) + s(SI_N) + s(SI_I_minmax_z) +
  is_os_endorsement + s(twitter_account_age_z) + s(twitter_tweet_count_z)
set.seed(16)
m0 <- gam(base_f, family = binomial, data = bal)
top20 <- head(per_inf$inf_id, 20)
for (j in seq_along(top20)) bal[[paste0("f", j)]] <- bal$id %in% edges$id[edges$inf_id == top20[j]]

cat("=== 2. Following a specific top-20 (most-followed) influencer, adjusted for the components model ===\n")
ors <- sapply(seq_along(top20), function(j) {
  mj <- gam(update(base_f, as.formula(paste(". ~ . + f", j, sep = ""))), family = binomial, data = bal)
  co <- summary(mj)$p.table[paste0("f", j, "TRUE"), ]
  c(OR = exp(co["Estimate"]), p = co["Pr(>|z|)"])
})
ors <- t(ors); colnames(ors) <- c("OR_adj", "p")
cat(sprintf("adjusted odds ratios: range %.2f to %.2f ; significantly > 1: %d ; significantly < 1: %d ; not significant: %d (alpha = .05)\n",
  min(ors[, "OR_adj"]), max(ors[, "OR_adj"]),
  sum(ors[, "p"] < .05 & ors[, "OR_adj"] > 1), sum(ors[, "p"] < .05 & ors[, "OR_adj"] < 1), sum(ors[, "p"] >= .05)))

# observed migration rate among the followers of each top-20 influencer vs the
# rate the base components model predicts for those same researchers from their
# own predictor values (prior-corrected to the population, King & Zeng, 2001)
offset <- log(sum(D$is_migrated == 0) / n_mig)
cmp <- t(sapply(top20, function(i) {
  s <- D[D$id %in% edges$id[edges$inf_id == i], ]
  c(obs = 100 * mean(s$is_migrated == 1), pred = 100 * mean(plogis(predict(m0, s) - offset)))
}))
cat(sprintf("followers of the top-20: observed migration rate %.1f%% to %.1f%% ; model-predicted from own covariates %.1f%% to %.1f%% ; observed/predicted ratio %.2f to %.2f (median %.2f)\n",
  min(cmp[, "obs"]), max(cmp[, "obs"]), min(cmp[, "pred"]), max(cmp[, "pred"]),
  min(cmp[, "obs"] / cmp[, "pred"]), max(cmp[, "obs"] / cmp[, "pred"]), median(cmp[, "obs"] / cmp[, "pred"])))

joint_f <- update(base_f, as.formula(paste(". ~ . +", paste0("f", seq_along(top20), collapse = " + "))))
set.seed(16)
mj <- gam(joint_f, family = binomial, data = bal)
cat(sprintf("joint model with all 20 indicators: deviance explained %.1f%% vs %.1f%% (base) ; AIC difference %.1f\n",
  100 * summary(mj)$dev.expl, 100 * summary(m0)$dev.expl, AIC(mj) - AIC(m0)))

auc <- function(p, y) {
  r <- rank(p); n1 <- sum(y); n0 <- length(y) - n1
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}
set.seed(16)
idx <- sample(nrow(bal), 0.8 * nrow(bal)); tr <- bal[idx, ]; te <- bal[-idx, ]
m0t <- gam(base_f, family = binomial, data = tr)
mjt <- gam(joint_f, family = binomial, data = tr)
cat(sprintf("out-of-sample AUC (80/20 split): base %.3f ; base + 20 indicators %.3f\n", auc(predict(m0t, te), te$is_migrated == 1), auc(predict(mjt, te), te$is_migrated == 1)))
cat("\ndone in", format(Sys.time() - t0), "\n")
