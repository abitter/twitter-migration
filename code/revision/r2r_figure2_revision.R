# ==============================================================================
# Figure 2, revised (revision, September 2026): remove excess white space
# before/after the first/last bar and above the bars
# ------------------------------------------------------------------------------
# Standalone reproduction of Figure 2 only. It repeats analysis.R sections 0-3
# (setup, z-standardisation, seed-16 downsample and 80/20 split, the two GAMs,
# performance metrics, SHAP) verbatim, and differs from analysis.R only in the
# axis settings of the four panels:
#   - discrete x axes: padding before the first / after the last bar reduced
#   - y axes: no padding below zero, upper limit tightened to the tallest bar
#     (plus room for the value labels in panels a and b)
# Writes a single new file and overwrites nothing:
#   results/figures/combined_plots_with_white_margins_seed16_revised.png
#
#   Rscript r2r_figure2_revision.R
# ==============================================================================

suppressMessages({
  library(mgcv)
  library(jsonlite)
  library(dplyr)
  library(caret)
  library(kernelshap)
  library(shapviz)
  library(ggplot2)
  library(cowplot)
  library(yaml)
})

config <- yaml.load_file("/home/lauer/projects/Mastodon/config.yml")
FIG_DIR <- config$paths$figures

# --- theme, colours, labels (copied verbatim from analysis.R) -----------------
color_os_endorsement <- "#6d9eeb"
color_social_impact <- "#d5a6bd"
color_twitter_account_age <- "#e1dfdf"
color_twitter_tweet_count <- "#d0cece"
color_SI_I <- "#e4c7d5"
color_SI_N <- "#d6aec1"
color_SI_S <- "#d79fb9"
my_theme <- theme(
  # analysis.R uses 19/17/17 pt; enlarged here because the panels are bigger once
  # the outer margins are trimmed, so the text keeps its relative size
  plot.title = element_text(size = 24, hjust = 0.5, vjust = 3),
  axis.title = element_text(size = 22),
  axis.text.x = element_text(color = "black", size = 21, margin = margin(t = 5, b = 20)),
  axis.text.y = element_text(color = "black", size = 21, margin = margin(r = 5, l = 20)),
  axis.ticks = element_line(color = "black"),
  legend.position = "none",
  # analysis.R uses 50 pt on all sides; reduced here to trim white space between panels
  plot.margin = margin(t = 30, r = 20, b = 10, l = 45, unit = "pt")
)
new_labels <- c(
  "is_os_endorsement" = "Open Science Endorsement",
  "social_impact_z" = "Social Impact",
  "twitter_account_age_z" = "Twitter Account Age",
  "twitter_tweet_count_z" = "Twitter Tweet Count",
  "SI_S_abs_minmax_sign_z" = "Strength",
  "SI_N" = "Number of Sources (non-transformed)",
  "SI_N_minmax_z" = "Number of Sources",
  "SI_I_minmax_z" = "Immediacy"
)

# --- axis settings that differ from analysis.R --------------------------------
tight_x <- function(add) scale_x_discrete(expand = expansion(add = add))
tight_y <- function(upper) scale_y_continuous(limits = c(0, upper), breaks = seq(0, upper, by = 0.25), expand = expansion(mult = c(0, 0.01)))

# --- data and preprocessing (analysis.R sections 0 and 1) ---------------------
df <- stream_in(file(paste0(
  config$paths$data$processed$final_processed, "final_processed_data.json"
)), verbose = FALSE)
z_standardize_column <- function(d, col) {
  (d[[col]] - mean(d[[col]], na.rm = TRUE)) / sd(d[[col]], na.rm = TRUE)
}
df$SI_S_abs_minmax_sign_z <- z_standardize_column(df, "SI_S_abs_minmax_sign")
df$SI_N_minmax_z <- z_standardize_column(df, "SI_N_minmax")
df$SI_I_minmax_z <- z_standardize_column(df, "SI_I_minmax")
df$twitter_followers_count_z <- z_standardize_column(df, "twitter_followers_count")
df$twitter_following_count_z <- z_standardize_column(df, "twitter_following_count")
df$twitter_tweet_count_z <- z_standardize_column(df, "twitter_tweet_count")
df$twitter_account_age_z <- z_standardize_column(df, "twitter_account_age")
df$social_impact <- df$SI_S_abs_minmax_sign * df$SI_N_minmax * df$SI_I_minmax
df$social_impact_z <- z_standardize_column(df, "social_impact")
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

# --- downsample, split, fit, metrics (analysis.R section 2) -------------------
set.seed(16)
df_sampled <- df %>%
  group_by(is_migrated) %>%
  sample_n(min(table(df$is_migrated)), replace = FALSE) %>%
  ungroup()
set.seed(16)
df_sampled_SI_components <- df_SI_components %>%
  group_by(is_migrated) %>%
  sample_n(min(table(df_SI_components$is_migrated)), replace = FALSE) %>%
  ungroup()
index <- createDataPartition(df_sampled$is_migrated, p = 0.8, list = FALSE)
trainData <- df_sampled[index, ]
testData <- df_sampled[-index, ]
set.seed(16)
mod_gam_pred <- gam(
  is_migrated ~ s(social_impact_z) + is_os_endorsement +
    s(twitter_account_age_z) + s(twitter_tweet_count_z),
  family = binomial, data = trainData
)
mod_gam_pred_sep <- gam(
  is_migrated ~ s(SI_S_abs_minmax_sign_z) + s(SI_N_minmax_z) + s(SI_I_minmax_z) +
    is_os_endorsement + s(twitter_account_age_z) + s(twitter_tweet_count_z),
  family = binomial, data = trainData
)
metrics <- function(mod) {
  pred <- ifelse(predict(mod, newdata = testData, type = "response") > 0.5, 1, 0)
  act <- testData$is_migrated
  TP <- sum(pred == 1 & act == 1); FP <- sum(pred == 1 & act == 0)
  FN <- sum(pred == 0 & act == 1); TN <- sum(pred == 0 & act == 0)
  precision <- TP / (TP + FP); recall <- TP / (TP + FN)
  data.frame(
    Metric = c("Precision", "Recall", "F1", "Accuracy"),
    Value = c(precision, recall, 2 * precision * recall / (precision + recall), (TP + TN) / (TP + FP + FN + TN))
  )
}
observations_df_single <- metrics(mod_gam_pred)
observations_df_single_exploratory <- metrics(mod_gam_pred_sep)
cat("panel a:", paste(observations_df_single$Metric, round(observations_df_single$Value, 2), collapse = ", "), "\n")
cat("panel b:", paste(observations_df_single_exploratory$Metric, round(observations_df_single_exploratory$Value, 2), collapse = ", "), "\n")

colors <- rep(color_twitter_tweet_count, 4)
p1 <- ggplot(observations_df_single, aes(x = Metric, y = Value, fill = Metric)) +
  geom_bar(stat = "identity", width = 0.5, color = "black") +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "black", linewidth = 1) +
  geom_text(aes(label = round(Value, 2)), vjust = -0.5, size = 7) +
  labs(title = "Performance Metrics:\nSocial Impact Model", x = "Metric", y = "Value") +
  tight_x(0.4) + tight_y(1) +
  my_theme +
  scale_fill_manual(values = colors)
p2 <- ggplot(observations_df_single_exploratory, aes(x = Metric, y = Value, fill = Metric)) +
  geom_bar(stat = "identity", width = 0.5, color = "black") +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "black", linewidth = 1) +
  geom_text(aes(label = round(Value, 2)), vjust = -0.5, size = 7) +
  labs(title = "Performance Metrics:\nSocial Impact Components Model", x = "Metric", y = "Value") +
  tight_x(0.4) + tight_y(1) +
  my_theme +
  scale_fill_manual(values = colors)

# --- SHAP on the pooled downsample (analysis.R section 3) ---------------------
mod_gam_shap <- gam(
  is_migrated ~ s(social_impact_z) + is_os_endorsement +
    s(twitter_account_age_z) + s(twitter_tweet_count_z),
  family = binomial, data = df_sampled
)
mod_gam_shap_sep <- gam(
  is_migrated ~ s(SI_S_abs_minmax_sign_z) + s(SI_N_minmax_z) + s(SI_I_minmax_z) +
    is_os_endorsement + s(twitter_account_age_z) + s(twitter_tweet_count_z),
  family = binomial, data = df_sampled_SI_components
)
shap_values <- additive_shap(mod_gam_shap, df_sampled, verbose = FALSE) |> shapviz()
mean_abs_shap_values <- colMeans(abs(as.data.frame(shap_values$S)), na.rm = TRUE)
mean_shap_data <- data.frame(Feature = names(mean_abs_shap_values), Mean = mean_abs_shap_values)
cat("panel c:", paste(mean_shap_data$Feature, round(mean_shap_data$Mean, 3), collapse = ", "), "\n")
# odds ratio for open science endorsement, annotated on its bar (the small
# mean |SHAP| of this rare binary feature understates its per-person effect)
or_main <- exp(coef(mod_gam_shap)["is_os_endorsementTRUE"])
or_label_main <- data.frame(Feature = "is_os_endorsement", Mean = mean_shap_data$Mean[mean_shap_data$Feature == "is_os_endorsement"], label = sprintf("OR = %.1f", or_main))
cat(sprintf("panel c: OR open science = %.2f\n", or_main))
colors <- c(color_os_endorsement, color_social_impact, color_twitter_account_age, color_twitter_tweet_count)
p3 <- ggplot(mean_shap_data, aes(x = Feature, y = Mean, fill = Feature)) +
  geom_bar(stat = "identity", position = position_dodge(), color = "black", width = 0.7) +
  labs(title = "Feature Importance:\nSocial Impact Model", x = "Feature", y = "Mean Absolute SHAP Value") +
  scale_fill_manual(values = colors) +
  scale_x_discrete(labels = new_labels, expand = expansion(add = 0.5)) +
  geom_text(data = or_label_main, aes(x = Feature, y = Mean, label = label), vjust = -0.6, hjust = 0, nudge_x = -0.35, size = 7, inherit.aes = FALSE) +
  tight_y(1) +
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

shap_values_SI_components <- additive_shap(mod_gam_shap_sep, df_sampled_SI_components, verbose = FALSE) |> shapviz()
mean_abs_shap_values_SI_components <- colMeans(abs(as.data.frame(shap_values_SI_components$S)), na.rm = TRUE)
mean_shap_data_SI_components <- data.frame(
  Feature = names(mean_abs_shap_values_SI_components),
  Mean = as.numeric(mean_abs_shap_values_SI_components)
)
feature_order <- c("is_os_endorsement", "SI_S_abs_minmax_sign_z", "SI_N_minmax_z", "SI_I_minmax_z", "twitter_account_age_z", "twitter_tweet_count_z")
mean_shap_data_SI_components$Feature <- factor(mean_shap_data_SI_components$Feature, levels = feature_order)
cat("panel d:", paste(mean_shap_data_SI_components$Feature, round(mean_shap_data_SI_components$Mean, 3), collapse = ", "), "\n")
or_sep <- exp(coef(mod_gam_shap_sep)["is_os_endorsementTRUE"])
or_label_sep <- data.frame(Feature = factor("is_os_endorsement", levels = feature_order), Mean = mean_shap_data_SI_components$Mean[mean_shap_data_SI_components$Feature == "is_os_endorsement"], label = sprintf("OR = %.1f", or_sep))
cat(sprintf("panel d: OR open science = %.2f\n", or_sep))
colors <- c(color_os_endorsement, color_SI_S, color_SI_N, color_SI_I, color_twitter_account_age, color_twitter_tweet_count)
p4 <- ggplot(mean_shap_data_SI_components, aes(x = Feature, y = Mean, fill = Feature)) +
  geom_bar(stat = "identity", position = position_dodge(), color = "black", width = 0.7) +
  labs(title = "Feature Importance:\nSocial Impact Components Model", x = "Feature", y = "Mean Absolute SHAP Value") +
  scale_fill_manual(values = colors) +
  scale_x_discrete(labels = new_labels, expand = expansion(add = 0.5)) +
  geom_text(data = or_label_sep, aes(x = Feature, y = Mean, label = label), vjust = -0.6, hjust = 0, nudge_x = -0.35, size = 7, inherit.aes = FALSE) +
  tight_y(1) +
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# --- combine (identical to analysis.R) ---------------------------------------
combined_plot <- plot_grid(
  p1, p2, p3, p4,
  labels = c("a", "b", "c", "d"), ncol = 2, rel_heights = c(1, 1.35),
  label_size = 26, label_fontface = "bold", label_x = 0.01, label_y = 0.97, hjust = 0, vjust = 0
)
combined_plot_with_white_margins <- ggdraw() +
  draw_plot(combined_plot, x = 0, y = 0, width = 1, height = 1) +
  theme(plot.margin = margin(10, 10, 10, 10), plot.background = element_rect(fill = "white", color = NA))
ggsave(
  filename = paste0(FIG_DIR, "combined_plots_with_white_margins_seed16_revised.png"),
  plot = combined_plot_with_white_margins, width = 16, height = 18, dpi = 300
)
cat("written:", paste0(FIG_DIR, "combined_plots_with_white_margins_seed16_revised.png"), "\n")
