# This script performs the statistical/ML analysis using the preprocessed data
# from the main script.

# Table of contents:
# 0. Setup
# 1. Z-standardize predictors
# 2. Predictive performance on test set
# 3. SHAP values for feature importance
# 4. Odds ratio for Open Science Endorsement
# 5. Robustness of results: Predictive performance on test set for 50 different seeds
# 6. Robustness of results: Feature importance for 50 different seeds
# 7. Table for descriptives of predictors
# 8. Number of sources turning point
# 9. Descriptives of potential influencers
# 10. Save final data frame
# 11. Logistic Regression (for completeness)

########################################################
# 0. Setup
########################################################

library(mgcv)
library(jsonlite)
library(dplyr)
library(itsadug)
library(visibly)
library(iml)
library(shapr)
library(caret)
library(DHARMa)
library(kernelshap)
library(shapviz)
library(ggplot2)
library(gridExtra)
library(corrplot)
library(ggforce)
library(reshape2)
library(tidyr)
library(yaml)
library(patchwork)
library(cowplot)

# Set working directory to location of this file
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Load config
config <- yaml.load_file("../../config.yml")

# Common theme for plotting
color_twitter <- "#a4c2f4"
color_mastodon <- "#93c47d"
color_mastodon_migrated <- "#a2c4c9"
color_mastodon_returned <- "#a4c2f4"
color_os_endorsement <- "#6d9eeb"
color_no_os_endorsement <- "#b1cfff"
color_social_impact <- "#d5a6bd"
color_twitter_account_age <- "#e1dfdf"
color_twitter_tweet_count <- "#d0cece"
color_SI_I <- "#e4c7d5"
color_SI_N <- "#d6aec1"
color_SI_S <- "#d79fb9"
color_influence_score <- "#d79fb9"
my_theme <- theme(
  plot.title = element_text(size = 19, hjust = 0.5, vjust = 3),
  axis.title = element_text(size = 17),
  axis.text.x = element_text(color = "black", size = 17, margin = margin(t = 5, b = 20)), # Increased bottom margin for x-axis labels
  axis.text.y = element_text(color = "black", size = 17, margin = margin(r = 5, l = 20)), # Increased right margin for y-axis labels
  axis.ticks = element_line(color = "black"),
  legend.position = "none",
  plot.margin = margin(t = 50, r = 50, b = 50, l = 50, unit = "pt") # Adjust top margin to allow space for the title
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

# Read preprocessed data
path_df <- paste0(config$paths$data$processed$final_processed, "final_processed_data.json")
df <- stream_in(file(path_df))
nrow(df)
table(df$is_m_created_or_revital_nov_dec) # n researchers with mastodon account in Nov/Dec 2022
table(df$is_migrated) # n migrated researchers

########################################################
# 1. Z-standardize predictors
########################################################

# Define the function to z-standardize a column
z_standardize_column <- function(df, column_name) {
  column_data <- df[[column_name]]
  z_scores <- (column_data - mean(column_data, na.rm = TRUE)) / sd(column_data, na.rm = TRUE)
  return(z_scores)
}

# Z-standardize social impact components
df$SI_S_abs_minmax_sign_z <- z_standardize_column(df, "SI_S_abs_minmax_sign")
df$SI_N_minmax_z <- z_standardize_column(df, "SI_N_minmax")
df$SI_I_minmax_z <- z_standardize_column(df, "SI_I_minmax")

#  Z-standardize covariates
df$twitter_followers_count_z <- z_standardize_column(df, "twitter_followers_count")
df$twitter_following_count_z <- z_standardize_column(df, "twitter_following_count")
df$twitter_tweet_count_z <- z_standardize_column(df, "twitter_tweet_count")
df$twitter_account_age_z <- z_standardize_column(df, "twitter_account_age")

# Compute final social impact score
df$social_impact <- df$SI_S_abs_minmax_sign * df$SI_N_minmax * df$SI_I_minmax

# Z-standardize final social impact score
df$social_impact_z <- z_standardize_column(df, "social_impact")

# Fill up NAs in the raw social impact component columns with 0s
# NOTE: these are people with 0 followed influencers, so they should get 0 for
# SI_N, SI_S, and SI_I. In the min-max scaled versions of the components used
# for modelling above, the NAs were already replaced with 0s in Python
# preprocessing script.
df$SI_S[is.na(df$SI_S)] <- 0
df$SI_N[is.na(df$SI_N)] <- 0
df$SI_I[is.na(df$SI_I)] <- 0

# Copy of df for analysis of SI components
df_SI_components <- df

# Clipping extreme outliers of the standardized predictors for the SI components
# analysis (for feature importance)
sum(df_SI_components$SI_N_minmax_z < -10 | df_SI_components$SI_N_minmax_z > 10)
sum(df_SI_components$SI_I_minmax_z < -10 | df_SI_components$SI_I_minmax_z > 10)
sum(df_SI_components$SI_S_abs_minmax_sign_z < -10 | df_SI_components$SI_S_abs_minmax_sign_z > 10)
sum(df_SI_components$twitter_account_age_z < -10 | df_SI_components$twitter_account_age_z > 10)
sum(df_SI_components$twitter_tweet_count_z < -10 | df_SI_components$twitter_tweet_count_z > 10)
df_SI_components$SI_N_minmax_z <- pmax(pmin(df_SI_components$SI_N_minmax_z, 10), -10)
df_SI_components$SI_I_minmax_z <- pmax(pmin(df_SI_components$SI_I_minmax_z, 10), -10)
df_SI_components$SI_S_abs_minmax_sign_z <- pmax(pmin(df_SI_components$SI_S_abs_minmax_sign_z, 10), -10)
df_SI_components$twitter_account_age_z <- pmax(pmin(df_SI_components$twitter_account_age_z, 10), -10)
df_SI_components$twitter_tweet_count_z <- pmax(pmin(df_SI_components$twitter_tweet_count_z, 10), -10)

# Also clipping outliers in the raw number of sources predictor for examining
# the smooth in the SI components analysis. For this, we apply the same
# threshold (reversing z-standardization and min-max scaling)
X_min <- min(df_SI_components$SI_N, na.rm = TRUE)
X_max <- max(df_SI_components$SI_N, na.rm = TRUE)
df_SI_components$SI_N_minmax <- (df_SI_components$SI_N - X_min) / (X_max - X_min)
mean_scaled <- mean(df_SI_components$SI_N_minmax, na.rm = TRUE)
sd_scaled <- sd(df_SI_components$SI_N_minmax, na.rm = TRUE)
Z_threshold <- c(-10, 10)
X_scaled_thresholds <- Z_threshold * sd_scaled + mean_scaled
X_raw_thresholds <- X_scaled_thresholds * (X_max - X_min) + X_min
print(X_raw_thresholds)
df_SI_components$SI_N <- pmax(pmin(df_SI_components$SI_N, X_raw_thresholds[2]), X_raw_thresholds[1])

# value counts of df is_migrated column
table(df$is_migrated)

########################################################
# 2. Predictive performance on test set
########################################################

# We set up a Generalized Additive Model (GAM) and look at predictive
# performance. As there is strong class imbalance, we first downsample the
# majority class (not migrated), and then randomly split into training (80%) and
# test set (20%). We fit two models: the main model with social impact as a
# product of components (strength, immediacy, number of sources), and another
# one with separate social impact components.

# Set seed for reproducibility
set.seed(16)

# Downsampling
df_sampled <- df %>%
  group_by(is_migrated) %>%
  sample_n(min(table(df$is_migrated)), replace = FALSE) %>%
  ungroup()

# Re-set seed: downsampling for exporatory model should be the same
set.seed(16)

df_sampled_SI_components <- df_SI_components %>%
  group_by(is_migrated) %>%
  sample_n(min(table(df_SI_components$is_migrated)), replace = FALSE) %>%
  ungroup()

# Train/test split
index <- createDataPartition(df_sampled$is_migrated, p = 0.8, list = FALSE)
trainData <- df_sampled[index, ]
testData <- df_sampled[-index, ]

# Re-set seed
set.seed(16)

# Main: Fit the GAM model on the training set with social impact as product of components
mod_gam_pred <- gam(
  is_migrated ~ s(social_impact_z) +
    is_os_endorsement +
    s(twitter_account_age_z) +
    s(twitter_tweet_count_z),
  family = binomial, data = trainData
)

# SI components: Fit the GAM model on the training set with social impact as separate components
mod_gam_pred_sep <- gam(
  is_migrated ~ s(SI_S_abs_minmax_sign_z) +
    s(SI_N_minmax_z) +
    s(SI_I_minmax_z) +
    is_os_endorsement +
    s(twitter_account_age_z) +
    s(twitter_tweet_count_z),
  family = binomial, data = trainData
)

# Main: Predictions and performance metrics
predicted_probabilities_test_main <- predict(mod_gam_pred, newdata = testData, type = "response")
predicted_classes_test_main <- ifelse(predicted_probabilities_test_main > 0.5, 1, 0)
actual_classes_test <- testData$is_migrated
TP_main <- sum(predicted_classes_test_main == 1 & actual_classes_test == 1)
FP_main <- sum(predicted_classes_test_main == 1 & actual_classes_test == 0)
FN_main <- sum(predicted_classes_test_main == 0 & actual_classes_test == 1)
TN_main <- sum(predicted_classes_test_main == 0 & actual_classes_test == 0)
precision_main <- TP_main / (TP_main + FP_main)
recall_main <- TP_main / (TP_main + FN_main)
f1_score_main <- 2 * (precision_main * recall_main) / (precision_main + recall_main)
accuracy_main <- (TP_main + TN_main) / (TP_main + FP_main + FN_main + TN_main)

# SI components: Predictions and performance metrics
predicted_probabilities_test_sep <- predict(mod_gam_pred_sep, newdata = testData, type = "response")
predicted_classes_test_sep <- ifelse(predicted_probabilities_test_sep > 0.5, 1, 0)
TP_sep <- sum(predicted_classes_test_sep == 1 & actual_classes_test == 1)
FP_sep <- sum(predicted_classes_test_sep == 1 & actual_classes_test == 0)
FN_sep <- sum(predicted_classes_test_sep == 0 & actual_classes_test == 1)
TN_sep <- sum(predicted_classes_test_sep == 0 & actual_classes_test == 0)
precision_sep <- TP_sep / (TP_sep + FP_sep)
recall_sep <- TP_sep / (TP_sep + FN_sep)
f1_score_sep <- 2 * (precision_sep * recall_sep) / (precision_sep + recall_sep)
accuracy_sep <- (TP_sep + TN_sep) / (TP_sep + FP_sep + FN_sep + TN_sep)

# Main: create a dataframe for plotting
observations_df_single <- data.frame(
  Metric = c("Precision", "Recall", "F1", "Accuracy"),
  Value = c(precision_main, recall_main, f1_score_main, accuracy_main)
)

# SI components: create a dataframe for plotting
observations_df_single_exploratory <- data.frame(
  Metric = c("Precision", "Recall", "F1", "Accuracy"),
  Value = c(precision_sep, recall_sep, f1_score_sep, accuracy_sep)
)

# Main: plot the performance metrics
colors <- c(color_twitter_tweet_count, color_twitter_tweet_count, color_twitter_tweet_count, color_twitter_tweet_count)
p1 <- ggplot(observations_df_single, aes(x = Metric, y = Value, fill = Metric)) +
  geom_bar(stat = "identity", width = 0.5, color = "black") +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "black", linewidth = 1) + # Baseline
  geom_text(aes(label = round(Value, 2)), # Add labels with values rounded to 2 decimals
    vjust = -0.5, # Position above the bars
    size = 6
  ) + # Text size
  labs(title = "Performance Metrics:\nSocial Impact Model", x = "Metric", y = "Value") +
  ylim(0, 1) +
  my_theme +
  scale_fill_manual(values = colors)
print(p1)
ggsave(paste0(config$paths$figures, "inferential_performance_main_seed16.png"), plot = p1, width = 9, height = 8, dpi = 300)

# SI components: plot the performance metrics for the single seed
p2 <- ggplot(observations_df_single_exploratory, aes(x = Metric, y = Value, fill = Metric)) +
  geom_bar(stat = "identity", width = 0.5, color = "black") +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "black", linewidth = 1) + # Baseline
  geom_text(aes(label = round(Value, 2)), # Add labels with values rounded to 2 decimals
    vjust = -0.5, # Position above the bars
    size = 6
  ) + # Text size
  labs(title = "Performance Metrics:\nSocial Impact Components Model", x = "Metric", y = "Value") +
  ylim(0, 1) +
  my_theme +
  scale_fill_manual(values = colors)
print(p2)
ggsave(paste0(config$paths$figures, "inferential_performance_exploratory_seed16.png"), plot = p2, width = 9, height = 8, dpi = 300)

summary(mod_gam_pred)

########################################################
# 3. SHAP values for feature importance
########################################################

# NOTE: Using the complete (downsampled) dataset for SHAP (pooling train and
# testset) set. This will "allow a post-hoc explainer like SHAP to use a "larger
# set" and therefore have a more faithful representation" (see e.g. link below).
# https://stats.stackexchange.com/questions/615290/if-feature-importance-is-only-computed-based-on-training-set-does-it-mean-one-s.

# Main model
mod_gam_shap <- gam(
  is_migrated ~ s(social_impact_z) +
    is_os_endorsement +
    s(twitter_account_age_z) +
    s(twitter_tweet_count_z),
  family = binomial, data = df_sampled
)

# SI components model
mod_gam_shap_sep <- gam(
  is_migrated ~ s(SI_S_abs_minmax_sign_z) +
    s(SI_N_minmax_z) +
    s(SI_I_minmax_z) +
    is_os_endorsement +
    s(twitter_account_age_z) +
    s(twitter_tweet_count_z),
  family = binomial, data = df_sampled_SI_components
)

#-----------------------------
# Plot mean absolute SHAP values (barplot)
#-----------------------------

# Mean absolute SHAP values show the overall contribution of each feature to the
# predicted outcome.

# Main: mean absolute SHAP values
shap_values <- additive_shap(mod_gam_shap, df_sampled) |>
  shapviz()
shap_matrix <- shap_values$S
shap_df <- as.data.frame(shap_matrix)
colnames(shap_df) <- colnames(shap_matrix)
mean_abs_shap_values <- colMeans(abs(shap_df), na.rm = TRUE)
features <- names(mean_abs_shap_values)
mean_shap_data <- data.frame(
  Feature = features,
  Mean = mean_abs_shap_values
)
colors <- c(color_os_endorsement, color_social_impact, color_twitter_account_age, color_twitter_tweet_count)
p3 <- ggplot(mean_shap_data, aes(x = Feature, y = Mean, fill = Feature)) +
  geom_bar(stat = "identity", position = position_dodge(), color = "black", width = 0.7) +
  labs(
    title = "Feature Importance:\nSocial Impact Model",
    x = "Feature",
    y = "Mean Absolute SHAP Value"
  ) +
  scale_fill_manual(values = colors) +
  scale_x_discrete(labels = new_labels) + # Apply new labels
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
  ylim(0, 1)
p3
ggsave(paste0(config$paths$figures, "inferential_SHAP_main_seed16_bar.png"), plot = p3, width = 9, height = 12, dpi = 300)

# SI components: mean absolute SHAP values
shap_values_SI_components <- additive_shap(mod_gam_shap_sep, df_sampled_SI_components) |>
  shapviz()
shap_matrix_SI_components <- shap_values_SI_components$S
shap_df_SI_components <- as.data.frame(shap_matrix_SI_components)
colnames(shap_df_SI_components) <- colnames(shap_matrix_SI_components)
mean_abs_shap_values_SI_components <- colMeans(abs(shap_df_SI_components), na.rm = TRUE)
features <- names(mean_abs_shap_values_SI_components)
mean_shap_data_SI_components <- data.frame(
  Feature = features,
  Mean = as.numeric(mean_abs_shap_values_SI_components)
)
feature_order <- c("is_os_endorsement", "SI_S_abs_minmax_sign_z", "SI_N_minmax_z", "SI_I_minmax_z", "twitter_account_age_z", "twitter_tweet_count_z")
mean_shap_data_SI_components$Feature <- factor(mean_shap_data_SI_components$Feature, levels = feature_order) # reorder feature column
colors <- c(color_os_endorsement, color_SI_S, color_SI_N, color_SI_I, color_twitter_account_age, color_twitter_tweet_count)
p4 <- ggplot(mean_shap_data_SI_components, aes(x = Feature, y = Mean, fill = Feature)) +
  geom_bar(stat = "identity", position = position_dodge(), color = "black", width = 0.7) +
  labs(
    title = "Feature Importance:\nSocial Impact Components Model",
    x = "Feature",
    y = "Mean Absolute SHAP Value"
  ) +
  scale_fill_manual(values = colors) +
  scale_x_discrete(labels = new_labels) + # Apply new labels
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
  ylim(0, 1.2)
p4
ggsave(paste0(config$paths$figures, "inferential_SHAP_exploratory_seed16_bar.png"), plot = p4, width = 10, height = 12, dpi = 300)

#-----------------------------
# Combine predictive and SHAP plots in a single figure
#-----------------------------

combined_plot <- plot_grid(
  p1, p2, p3, p4,
  labels = c("a", "b", "c", "d"), # Add panel labels
  ncol = 2, # 2 columns
  rel_heights = c(1, 1.35), # Increase height of bottom row
  label_size = 22, # Adjust label size
  label_fontface = "bold", # Bold font for labels
  label_x = 0.01, # Slightly offset labels horizontally
  label_y = 0.97, # Place labels inside the visible area
  hjust = 0, # Horizontal alignment of labels
  vjust = 0 # Vertical alignment of labels
)
print(combined_plot)

# Add margins to the combined plot with a white background
combined_plot_with_white_margins <- ggdraw() +
  draw_plot(combined_plot, x = 0, y = 0, width = 1, height = 1) + # Position plot
  theme(
    plot.margin = margin(20, 20, 20, 20), # Add margins (top, right, bottom, left)
    plot.background = element_rect(fill = "white", color = NA) # Set white background
  )
print(combined_plot_with_white_margins)

# Save the plot with white margins
ggsave(
  filename = paste0(config$paths$figures, "combined_plots_with_white_margins_seed16.png"),
  plot = combined_plot_with_white_margins,
  width = 16, # 14,   # increase width bc of margins
  height = 18, # 16,  # increase height bc of margins
  dpi = 300 # Resolution
)

#-----------------------------
# Plot individual SHAP values (bee swarm plot)
#-----------------------------

# Individual SHAP values show the impact of each feature on each individual prediction.

# Main: SHAP on all data
feature_names <- colnames(shap_values) # Extract feature names from shap_values
custom_labels_ordered <- new_labels[feature_names] # Order the custom labels based on the feature names in shap_values
p <- sv_importance(shap_values, kind = "bee") +
  scale_y_discrete(labels = custom_labels_ordered) +
  my_theme +
  theme(legend.position = "right") +
  theme(
    legend.title = element_text(size = 17),
    legend.text  = element_text(size = 17)
  ) +
  labs(title = "Feature Importance: Individual SHAP Values")
p
ggsave(paste0(config$paths$figures, "inferential_SHAP_main_seed16_bee.png"), plot = p, width = 20, height = 9, dpi = 300)

# SI components: SHAP on all data
feature_names <- colnames(shap_values_SI_components) # Extract feature names from shap_values
custom_labels_ordered <- new_labels[feature_names] # Order the custom labels based on the feature names in shap_values
p <- sv_importance(shap_values_SI_components, kind = "bee") +
  scale_y_discrete(labels = custom_labels_ordered) +
  my_theme +
  theme(legend.position = "right") +
  theme(
    legend.title = element_text(size = 17),
    legend.text  = element_text(size = 17)
  ) +
  labs(title = "Feature Importance: Individual SHAP Values")
p
ggsave(paste0(config$paths$figures, "inferential_SHAP_exploratory_seed16_bee.png"), plot = p, width = 20, height = 12, dpi = 300)

########################################################
# 4. Odds ratio for Open Science Endorsement
########################################################

table(df_sampled$is_os_endorsement)
# The previous section revealed that the SHAP values for Open Science
# Endorsement are very low. This is likely due to the low number of individuals
# who endorse Open Science in the dataset. When a variable is rare, even if it
# is very predictive when it occurs, the overall impact across all predictions
# can be small, explaining its lower feature importance. In this case, the odds
# ratio provides a clearer picture, see below.

# fit GAM on complete (downsampled) dataset
mod_gam_all <- gam(
  is_migrated ~ s(social_impact_z) +
    is_os_endorsement +
    s(twitter_account_age_z) +
    s(twitter_tweet_count_z),
  family = binomial, data = df_sampled
)

summary_mod_gam_all <- summary(mod_gam_all)
summary_mod_gam_all # output for supplementary material
coeff <- summary_mod_gam_all$p.table["is_os_endorsementTRUE", "Estimate"]
se <- summary_mod_gam_all$p.table["is_os_endorsementTRUE", "Std. Error"]
odds_ratio <- exp(coeff)
odds_ratio
lower_ci <- exp(coeff - 1.96 * se)
upper_ci <- exp(coeff + 1.96 * se)
lower_ci
upper_ci

# residual diagnostics: model should be fitting well to interpret odds ratio
simulationOutput <- simulateResiduals(fittedModel = mod_gam_pred)
plot(simulationOutput)
testOutliers(simulationOutput)
testDispersion(simulationOutput)
testUniformity(simulationOutput)

########################################################
# 5. Robustness of results: Predictive performance on test set for 50 different seeds
########################################################

# Below, we check that the predictive performance is stable across different
# seeds/downsamples.

# Initialize vectors to store the performance metrics for each iteration
precision_vec_main <- numeric(50)
recall_vec_main <- numeric(50)
f1_score_vec_main <- numeric(50)
accuracy_vec_main <- numeric(50)
precision_vec_exploratory <- numeric(50)
recall_vec_exploratory <- numeric(50)
f1_score_vec_exploratory <- numeric(50)
accuracy_vec_exploratory <- numeric(50)

for (i in 1:50) {
  # Set seed based on iteration
  set.seed(i)

  # Downsampling
  df_sampled <- df %>%
    group_by(is_migrated) %>%
    sample_n(min(table(df$is_migrated)), replace = FALSE) %>%
    ungroup()

  # Re-set seed: downsampling for exporatory model should be the same
  set.seed(i)

  # Not used, kept for reference/consistency (if removed, one should also remove
  # re-setting of seed above)
  df_sampled_SI_components <- df_SI_components %>%
    group_by(is_migrated) %>%
    sample_n(min(table(df_SI_components$is_migrated)), replace = FALSE) %>%
    ungroup()

  # Train/test split
  index <- createDataPartition(df_sampled$is_migrated, p = 0.8, list = FALSE)
  trainData <- df_sampled[index, ]
  testData <- df_sampled[-index, ]

  # Re-set seed
  set.seed(i)

  # Main: Fit the GAM model on the training set with social impact as product of components
  mod_gam_pred <- gam(
    is_migrated ~ s(social_impact_z) +
      is_os_endorsement +
      s(twitter_account_age_z) +
      s(twitter_tweet_count_z),
    family = binomial, data = trainData
  )

  # SI components: Fit the GAM model on the training set with social impact as separate components
  mod_gam_pred_sep <- gam(
    is_migrated ~ s(SI_S_abs_minmax_sign_z) +
      s(SI_N_minmax_z) +
      s(SI_I_minmax_z) +
      is_os_endorsement +
      s(twitter_account_age_z) +
      s(twitter_tweet_count_z),
    family = binomial, data = trainData
  )

  # Main: Predictions and performance metrics
  predicted_probabilities_test_main <- predict(mod_gam_pred, newdata = testData, type = "response")
  predicted_classes_test_main <- ifelse(predicted_probabilities_test_main > 0.5, 1, 0)
  actual_classes_test <- testData$is_migrated
  TP_main <- sum(predicted_classes_test_main == 1 & actual_classes_test == 1)
  FP_main <- sum(predicted_classes_test_main == 1 & actual_classes_test == 0)
  FN_main <- sum(predicted_classes_test_main == 0 & actual_classes_test == 1)
  TN_main <- sum(predicted_classes_test_main == 0 & actual_classes_test == 0)
  precision_main <- TP_main / (TP_main + FP_main)
  recall_main <- TP_main / (TP_main + FN_main)
  f1_score_main <- 2 * (precision_main * recall_main) / (precision_main + recall_main)
  accuracy_main <- (TP_main + TN_main) / (TP_main + FP_main + FN_main + TN_main)
  precision_vec_main[i] <- precision_main
  recall_vec_main[i] <- recall_main
  f1_score_vec_main[i] <- f1_score_main
  accuracy_vec_main[i] <- accuracy_main

  # SI components: Predictions and performance metrics
  predicted_probabilities_test_sep <- predict(mod_gam_pred_sep, newdata = testData, type = "response")
  predicted_classes_test_sep <- ifelse(predicted_probabilities_test_sep > 0.5, 1, 0)
  TP_sep <- sum(predicted_classes_test_sep == 1 & actual_classes_test == 1)
  FP_sep <- sum(predicted_classes_test_sep == 1 & actual_classes_test == 0)
  FN_sep <- sum(predicted_classes_test_sep == 0 & actual_classes_test == 1)
  TN_sep <- sum(predicted_classes_test_sep == 0 & actual_classes_test == 0)
  precision_sep <- TP_sep / (TP_sep + FP_sep)
  recall_sep <- TP_sep / (TP_sep + FN_sep)
  f1_score_sep <- 2 * (precision_sep * recall_sep) / (precision_sep + recall_sep)
  accuracy_sep <- (TP_sep + TN_sep) / (TP_sep + FP_sep + FN_sep + TN_sep)
  precision_vec_exploratory[i] <- precision_sep
  recall_vec_exploratory[i] <- recall_sep
  f1_score_vec_exploratory[i] <- f1_score_sep
  accuracy_vec_exploratory[i] <- accuracy_sep
}

# Main: plot violin/boxplot performance over all seeds
observations_df_main <- data.frame(
  Metric = rep(c("Precision", "Recall", "F1 Score", "Accuracy"), each = length(precision_vec_main)),
  Value = c(precision_vec_main, recall_vec_main, f1_score_vec_main, accuracy_vec_main)
)
colors <- c(color_twitter_tweet_count, color_twitter_tweet_count, color_twitter_tweet_count, color_twitter_tweet_count)
p <- ggplot(observations_df_main, aes(x = Metric, y = Value, fill = Metric)) +
  geom_violin(trim = TRUE) +
  geom_boxplot(width = 0.1, fill = "white", outliers = FALSE) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "black", linewidth = 1) +
  labs(title = "Performance Metrics Distribution for 50 Seeds", x = "Metric", y = "Value") +
  ylim(0, 1) +
  my_theme +
  scale_fill_manual(values = colors)
p
ggsave(paste0(config$paths$figures, "inferential_performance_main_box.png"), plot = p, width = 9, height = 8, dpi = 300)

# SI components: plot violin/boxplot performance over all seeds
observations_df_exploratory <- data.frame(
  Metric = rep(c("Precision", "Recall", "F1 Score", "Accuracy"), each = length(precision_vec_exploratory)),
  Value = c(precision_vec_exploratory, recall_vec_exploratory, f1_score_vec_exploratory, accuracy_vec_exploratory)
)
p <- ggplot(observations_df_exploratory, aes(x = Metric, y = Value, fill = Metric)) +
  geom_violin(trim = TRUE) +
  geom_boxplot(width = 0.1, fill = "white", outliers = FALSE) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "black", linewidth = 1) +
  labs(title = "Performance Metrics Distribution for 50 Seeds\n for Social Impact Components", x = "Metric", y = "Value") +
  ylim(0, 1) +
  my_theme +
  scale_fill_manual(values = colors)
p
ggsave(paste0(config$paths$figures, "inferential_performance_exploratory_box.png"), plot = p, width = 9, height = 8, dpi = 300)

# What is the median performance mdoel?

# median F1 score
median_f1 <- median(f1_score_vec_main)

# Find the position(s) of the closest value(s) to the median ("closest" bc if we
# have even number of elements, median = average of two middle values and not an
# actually observed value)
closest_value_position <- which.min(abs(f1_score_vec_main - median_f1))

# Print the closest value and its position
f1_score_vec_main[closest_value_position]
closest_value_position
# ->16

########################################################
# 6. Robustness of results: Feature importance for 50 different seeds
########################################################

# Below, we check that the feature importance and odds ratio is stable across
# different seeds/downsamples.

#-----------------------------
# run computations
#-----------------------------

min_count <- min(table(df$is_migrated))
min_count_SI_components <- min(table(df_SI_components$is_migrated))
results <- list()
mean_abs_shap_values_list <- list()
mean_shap_values_list <- list()
mean_abs_shap_values_list_SI_components <- list()
mean_shap_values_list_SI_components <- list()
cor_matrices <- list()
cor_matrices_SI_components <- list()

# downsample the majority class n times with different subsets
for (i in 1:50) {
  # Set seed based on iteration
  set.seed(i)

  # # Sanity check: random state should be the same at the end of each iteration
  # initial_state <- .Random.seed

  # downsample for SI model
  df_sample <- df %>%
    group_by(is_migrated) %>%
    sample_n(min_count) %>%
    ungroup()

  # Re-set seed: needed so that the two downsamples are the same
  set.seed(i)

  # downsample for SI components model
  df_sample_SI_components <- df_SI_components %>%
    group_by(is_migrated) %>%
    sample_n(min_count_SI_components) %>%
    ungroup()

  # Re-set seed
  set.seed(i)

  # fit GAM for SI model
  mod_gam <- gam(
    is_migrated ~ s(social_impact_z) +
      is_os_endorsement +
      s(twitter_account_age_z) +
      s(twitter_tweet_count_z),
    family = binomial, data = df_sample
  )

  # fit GAM for SI components model
  mod_gam_SI_components <- gam(
    is_migrated ~ s(SI_S_abs_minmax_sign_z) +
      s(SI_N_minmax_z) +
      s(SI_I_minmax_z) +
      is_os_endorsement +
      s(twitter_account_age_z) +
      s(twitter_tweet_count_z),
    family = binomial, data = df_sample_SI_components
  )

  # Extract coefficients and confidence intervals for SI model, append results
  summary_gam <- summary(mod_gam)
  coeff <- summary_gam$p.table["is_os_endorsementTRUE", "Estimate"] # This is the right way of extracting coefs and standard errors; for smooth terms use s.table
  se <- summary_gam$p.table["is_os_endorsementTRUE", "Std. Error"]
  odds_ratio <- exp(coeff)
  lower_ci <- exp(coeff - 1.96 * se)
  upper_ci <- exp(coeff + 1.96 * se)
  results[[i]] <- list(
    p_coeff = coeff,
    odds_ratio = odds_ratio,
    lower_ci = lower_ci,
    upper_ci = upper_ci,
    edf_social_impact_z = summary_gam$s.table["s(social_impact_z)", "edf"],
    edf_twitter_account_age_z = summary_gam$s.table["s(twitter_account_age_z)", "edf"],
    edf_twitter_tweet_count_z = summary_gam$s.table["s(twitter_tweet_count_z)", "edf"],
    dev_expl = summary_gam$dev.expl,
    iteration = i
  )

  # Calculate SHAP values for SI model, append results NOTE: Calculate the
  # mean of absolute SHAP values for each feature Rationale: SHAP values can be
  # either positive or negative, reflecting the direction of the impact of a
  # feature on the prediction (positive for increasing the prediction, negative
  # for decreasing it). Using absolute values allows for assessing the overall
  # strength of the influence of each feature regardless of the direction.
  # Additionally, we store the mean SHAP values to assess the direction of the
  # impact.
  shap_values <- additive_shap(mod_gam, df_sample)
  shap_matrix <- shap_values$S
  shap_df <- as.data.frame(shap_matrix)
  colnames(shap_df) <- colnames(shap_matrix)
  mean_abs_shap_values <- colMeans(abs(shap_df), na.rm = TRUE)
  mean_shap_values <- colMeans(shap_df, na.rm = TRUE)
  mean_abs_shap_values_list[[i]] <- mean_abs_shap_values
  mean_shap_values_list[[i]] <- mean_shap_values

  # Calculate SHAP values for SI components model, append results
  shap_values_SI_components <- additive_shap(mod_gam_SI_components, df_sample_SI_components)
  shap_matrix_SI_components <- shap_values_SI_components$S
  shap_df_SI_components <- as.data.frame(shap_matrix_SI_components)
  colnames(shap_df_SI_components) <- colnames(shap_matrix_SI_components)
  mean_abs_shap_values_SI_components <- colMeans(abs(shap_df_SI_components), na.rm = TRUE)
  mean_shap_values_SI_components <- colMeans(shap_df_SI_components, na.rm = TRUE)
  mean_abs_shap_values_list_SI_components[[i]] <- mean_abs_shap_values_SI_components
  mean_shap_values_list_SI_components[[i]] <- mean_shap_values_SI_components

  # retain only columns of interest numeric columns
  columns_to_keep <- c(
    "social_impact_z",
    "twitter_account_age_z",
    "twitter_tweet_count_z"
  )

  columns_to_keep_SI_components <- c(
    "SI_S_abs_minmax_sign_z", "SI_N_minmax_z", "SI_I_minmax_z",
    "twitter_account_age_z",
    "twitter_tweet_count_z"
  )

  # Subset the DataFrame to keep only the selected columns
  df_sample_cor <- df_sample[, columns_to_keep]
  df_sample_cor_SI_components <- df_sample_SI_components[, columns_to_keep_SI_components]
  cor_matrix <- cor(df_sample_cor[, sapply(df_sample_cor, is.numeric)])
  cor_matrix_SI_components <- cor(df_sample_cor_SI_components[, sapply(df_sample_cor_SI_components, is.numeric)])

  # df_sample <- df_sample[, columns_to_keep]
  # df_sample_cor_SI_components <- df_sample_SI_components[, columns_to_keep_SI_components]
  # cor_matrix <- cor(df_sample[, sapply(df_sample, is.numeric)])
  # cor_matrix_SI_components <- cor(df_sample_SI_components[, sapply(df_sample_SI_components, is.numeric)])

  # Append each matrix to the respective list
  cor_matrices[[i]] <- cor_matrix
  cor_matrices_SI_components[[i]] <- cor_matrix_SI_components

  # store median performance model
  if (i == 16) {
    best_mod_gam <- mod_gam
    best_mod_gam_SI_components <- mod_gam_SI_components
    best_df_sample <- df_sample
    best_df_sample_SI_components <- df_sample_SI_components
  }
}

#-----------------------------
# Plot OS endorsement odds ratio and confidence interval (only for SI model)
#-----------------------------

# Convert results to a DataFrame for easier handling and visualization
results_df <- do.call(rbind, lapply(results, as.data.frame))

# Create an index for plotting positions
results_df$id <- seq_along(results_df$p_coeff)

# Visualization of Confidence Intervals for is_os_endorsementTRUE Coefficients
p <- ggplot(results_df, aes(y = id, xmin = lower_ci, xmax = upper_ci)) +
  geom_errorbarh(height = 0.3) + # Horizontal error bars
  geom_point(aes(x = odds_ratio), color = "blue", size = 2) + # Points for the actual coefficients
  labs(
    title = "Confidence Intervals of odds ratios for open science endorsement\nfor different downsamples of 'not migrated' class",
    y = "Iteration",
    x = "Odds ratio"
  ) +
  theme(
    axis.text.y = element_blank(), # Remove y-axis text for clarity
    axis.ticks.y = element_blank(),
    plot.title = element_text(hjust = 0.5)
  ) +
  scale_x_continuous(breaks = c(0, 1, 10, 20, 30), limits = c(0, NA)) + # Set x-axis breaks to include 0
  geom_vline(xintercept = 1, linetype = "dashed") # Add vertical line at x = 1
p
ggsave(paste0(config$paths$figures, "inferential_os_odds_ratios_CIs.png"), plot = p)


# Calculating the average odds ratio and confidence intervals
average_odds_ratio <- mean(results_df$odds_ratio)
average_lower_ci <- mean(results_df$lower_ci)
average_upper_ci <- mean(results_df$upper_ci)
cat("Average Odds Ratio:", average_odds_ratio, "\n")
cat("Average Confidence Interval: [", average_lower_ci, ", ", average_upper_ci, "]\n")

#-----------------------------
# Plot SHAP values for SI model: Absolute SHAP values
#-----------------------------

# Convert list of mean SHAP values to a data frame
mean_shap_df <- do.call(rbind, mean_abs_shap_values_list)

# Violin and boxplot for SHAP values
long_shap_df <- melt(mean_shap_df) # Convert the wide format data to long format
colnames(long_shap_df) <- c("Index", "Feature", "SHAP_Value")
feature_order <- c("social_impact_z", "is_os_endorsement", "twitter_account_age_z", "twitter_tweet_count_z")
long_shap_df$Feature <- factor(long_shap_df$Feature, levels = feature_order)
colors <- c(color_social_impact, color_os_endorsement, color_twitter_account_age, color_twitter_tweet_count)
p <- ggplot(long_shap_df, aes(x = Feature, y = SHAP_Value, fill = Feature)) +
  geom_violin(trim = TRUE) +
  geom_boxplot(width = 0.1, fill = "white", color = "black", outlier.shape = NA) +
  scale_fill_manual(values = colors) + # Use custom colors
  scale_x_discrete(labels = new_labels) + # Apply new labels
  labs(
    title = "Feature Importance for 50 Seeds:\nSHAP Values",
    x = "Feature",
    y = "Mean Absolute SHAP Value"
  ) +
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
print(p)
ggsave(paste0(config$paths$figures, "inferential_SHAP_main_box.png"), plot = p, width = 9, height = 12, dpi = 300)

#-----------------------------
# Plot SHAP for SI components model: Absolute SHAP values
#-----------------------------

# Convert list of mean SHAP values to a data frame
mean_shap_df_SI_components <- do.call(rbind, mean_abs_shap_values_list_SI_components)

# Convert the wide format data to long format for ggplot
long_shap_df <- melt(mean_shap_df_SI_components)
colnames(long_shap_df) <- c("Index", "Feature", "SHAP_Value")

# Specify the order of the features on the x-axis
feature_order <- c("is_os_endorsement", "SI_S_abs_minmax_sign_z", "SI_N_minmax_z", "SI_I_minmax_z", "twitter_account_age_z", "twitter_tweet_count_z")
long_shap_df$Feature <- factor(long_shap_df$Feature, levels = feature_order)

colors <- c(color_os_endorsement, color_SI_S, color_SI_N, color_SI_I, color_twitter_account_age, color_twitter_tweet_count)
p <- ggplot(long_shap_df, aes(x = Feature, y = SHAP_Value, fill = Feature)) +
  geom_violin(trim = TRUE) +
  geom_boxplot(width = 0.1, fill = "white", color = "black", outlier.shape = NA) +
  scale_fill_manual(values = colors) + # Use custom colors
  scale_x_discrete(labels = new_labels) + # Apply new labels
  labs(
    title = "Feature Importance of Social Impact Components for 50 Seeds:\nSHAP Values",
    x = "Feature",
    y = "Mean Absolute SHAP Value"
  ) +
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
print(p)
ggsave(paste0(config$paths$figures, "inferential_SHAP_exploratory_box.png"), plot = p, width = 10, height = 12, dpi = 300)

########################################################
# 7. Table for descriptives of predictors
########################################################

# Define variables to calculate stats for
variables <- c("social_impact", "twitter_tweet_count", "twitter_account_age")

# Create empty lists to store results
results <- list(migrated = list(), not_migrated = list(), combined = list())

# Function to calculate numeric stats
calculate_stats <- function(data, var) {
  list(
    Median = median(data[[var]], na.rm = TRUE),
    IQR = IQR(data[[var]], na.rm = TRUE),
    Min = min(data[[var]], na.rm = TRUE),
    Max = max(data[[var]], na.rm = TRUE),
    N = sum(!is.na(data[[var]]))
  )
}

# Filter the data for each group
migrated_data <- df[df$is_migrated == 1, ]
not_migrated_data <- df[df$is_migrated == 0, ]
combined_data <- df

# Calculate stats for numeric variables for each group
for (var in variables) {
  results$migrated[[var]] <- calculate_stats(migrated_data, var)
  results$not_migrated[[var]] <- calculate_stats(not_migrated_data, var)
  results$combined[[var]] <- calculate_stats(combined_data, var)
}

# Calculate Open Science Endorsement stats
calculate_endorsement <- function(data, var) {
  total <- nrow(data)
  endorsed <- sum(data[[var]] == 1, na.rm = TRUE)
  proportion <- endorsed / total
  list(N_endorsed = endorsed, Proportion = proportion)
}

results$migrated$is_os_endorsement <- calculate_endorsement(migrated_data, "is_os_endorsement")
results$not_migrated$is_os_endorsement <- calculate_endorsement(not_migrated_data, "is_os_endorsement")
results$combined$is_os_endorsement <- calculate_endorsement(combined_data, "is_os_endorsement")

# View results
results

colnames(df)

########################################################
# 8. Number of sources turning point
########################################################

# We examine the smooth effect of the number of followed influencers on the
# migration likelihood. For this, we refit the model using the raw
# non-transformed variable so that the effect of the number of followed
# influencers on the log odds of migration is easily interpretable.

# refit model with non-transformed SI_N
mod_gam_SI_components_nontransfSI_N <- gam(
  is_migrated ~ s(SI_S_abs_minmax_sign_z) +
    s(SI_N) +
    s(SI_I_minmax_z) +
    is_os_endorsement +
    s(twitter_account_age_z) +
    s(twitter_tweet_count_z),
  family = binomial, data = best_df_sample_SI_components
)

# SHAP plot just to confirm that refitting with non-transformed SI_N yields
# similar results
shap_values_SI_components <- additive_shap(mod_gam_SI_components_nontransfSI_N, best_df_sample_SI_components)
shap_matrix_SI_components <- shap_values_SI_components$S
shap_df_SI_components <- as.data.frame(shap_matrix_SI_components)
colnames(shap_df_SI_components) <- colnames(shap_matrix_SI_components)
mean_abs_shap_values_SI_components <- colMeans(abs(shap_df_SI_components), na.rm = TRUE)
features <- names(mean_abs_shap_values_SI_components)
mean_shap_data_SI_components <- data.frame(
  Feature = features,
  Mean = as.numeric(mean_abs_shap_values_SI_components)
)
feature_order <- c("is_os_endorsement", "SI_S_abs_minmax_sign_z", "SI_N", "SI_I_minmax_z", "twitter_account_age_z", "twitter_tweet_count_z")
# feature_order <- c("is_os_endorsement", "SI_S_abs_minmax_sign_z", "SI_N_minmax_z", "SI_I_minmax_z", "twitter_account_age_z", "twitter_tweet_count_z")
mean_shap_data_SI_components$Feature <- factor(mean_shap_data_SI_components$Feature, levels = feature_order)
colors <- c(color_os_endorsement, color_SI_S, color_SI_N, color_SI_I, color_twitter_account_age, color_twitter_tweet_count) # Add or adjust colors as per the number of features
p <- ggplot(mean_shap_data_SI_components, aes(x = Feature, y = Mean, fill = Feature)) +
  geom_bar(stat = "identity", position = position_dodge(), color = "black", width = 0.7) +
  labs(
    title = "Feature Importance for best-fitting Model:\nSHAP Values",
    x = "Feature",
    y = "Mean Absolute SHAP Value"
  ) +
  scale_fill_manual(values = colors) +
  scale_x_discrete(labels = new_labels) + # Apply new labels
  my_theme +
  theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
  ylim(0, 1.2)
p

# Plot the GAM smooth to examine the effect of the number of followed
# influencers on migration likelihood
SI_N_smooth_plot <- plot(mod_gam_SI_components_nontransfSI_N,
  select = 2, ylim = c(-10, 10), main = "Effect of Number of Followed Influencers on Migration Likelihood",
  ylab = "Log Odds of Migration"
)

# better plot using ggplot and custom theme
smooth_SI_N <- SI_N_smooth_plot[[2]]
gam_data_SI_N <- data.frame(
  SI_N = smooth_SI_N$x,
  fit = smooth_SI_N$fit,
  se_upper = smooth_SI_N$fit + 2 * smooth_SI_N$se,
  se_lower = smooth_SI_N$fit - 2 * smooth_SI_N$se
)
p <- ggplot() +
  geom_line(data = gam_data_SI_N, aes(x = SI_N, y = fit), color = "black") + # Smooth line
  geom_ribbon(data = gam_data_SI_N, aes(x = SI_N, ymin = se_lower, ymax = se_upper), fill = color_SI_N, alpha = 0.2) + # Confidence interval
  geom_rug(data = best_df_sample_SI_components, aes(x = SI_N), sides = "b", alpha = 0.5, color = "#858585") + # Rug plot
  geom_hline(yintercept = 0, linetype = "dashed", color = "#8c8c8c") +
  geom_hline(yintercept = 1.016993, linetype = "dashed", color = "#8c8c8c") +
  geom_vline(xintercept = 17.83577, linetype = "dashed", color = "#8c8c8c") +
  geom_vline(xintercept = 44.90793, linetype = "dashed", color = "#8c8c8c") +
  scale_x_continuous(
    breaks = c(0, 18, 44, 100, 200, 300), # Custom tick positions
    labels = c("0", "18", "44", "100", "200", "300")
  ) + # Custom labels for ticks
  labs(
    title = "Effect of Number of Followed Influencers\non Migration Likelihood",
    x = "Number of Followed Influencers",
    # REVISION 2026-09 (Fig. 3): relabelled. plot.gam() returns the
    # CENTRED partial effect of the smooth - the intercept is not added and no
    # other predictor enters - so this axis is not the log odds of migration.
    # Original label was: y = "Log Odds of Migration"
    y = "Partial effect on log odds of migration (centred)"
  ) +
  coord_cartesian(ylim = c(-5, 5)) + # Set y-axis limits while keeping confidence interval visible
  theme(
    panel.grid.major = element_line(color = "white", size = 0.5), # Major grid lines in white
    panel.grid.minor = element_blank(), # Remove minor grid lines
    panel.grid.major.x = element_line(color = "white", size = 0.5), # Set x-axis major grid lines to white
    panel.grid.major.y = element_line(color = "white", size = 0.5) # Set y-axis major grid lines to white
  ) +
  my_theme
p
ggsave(paste0(config$paths$figures, "inferential_SI_N_log_odds.png"), plot = p, width = 11, height = 10, dpi = 300)

# Examine the turning point for the number of followed influencers

# Data for SI_N is at 2nd position in the list of the plot
str(SI_N_smooth_plot)
x_values <- SI_N_smooth_plot[[2]]$x
fit_values <- SI_N_smooth_plot[[2]]$fit[, 1]

# Interpolating over a refined x range that includes all original x values and more points in between
xout_range <- seq(min(x_values), max(x_values), length.out = 1000)
interpolated <- approx(x_values, fit_values, xout = xout_range)

# Finding the x-value where y is closest to zero
zero_crossing_idx <- which.min(abs(interpolated$y))
x_at_y_zero <- interpolated$x[zero_crossing_idx]
x_at_y_zero

# Subset for x-values between 0 and 50, to find the maximum y-value in this
# range, i.e. a plateau determined by visual inspection
# subset_interpolated <- interpolated$x >= 0 & interpolated$x <= 70
subset_interpolated <- interpolated$x >= 0 & interpolated$x <= 50

# Extract the x and y values for this subset
x_values_subset <- interpolated$x[subset_interpolated]
y_values_subset <- interpolated$y[subset_interpolated]

# Find the maximum y-value in the subset
max_y_in_range_x_0_50 <- max(y_values_subset)
max_y_in_range_x_0_50

# Extract the x-value corresponding to the maximum y-value
max_y_index <- which.max(y_values_subset)
x_at_max_y_in_range_x_0_50 <- x_values_subset[max_y_index]
x_at_max_y_in_range_x_0_50

########################################################
# 9. Descriptives of potential influencers
########################################################

# Table for descriptive analysis: All influencers (including the ones with missing timelines)

# read file with influencer profiles
path_df <- paste0(config$paths$data$processed$social_impact, "profiles_influencers_weighted_remainingSI.json")
df_influencers <- stream_in(file(path_df))
nrow(df_influencers)
# -> 10742 influencers

# how many influencers have influence score of 0?
sum(df_influencers$`influence_score_20-80_weighted` < 0)

# Define variables to calculate stats for
variables <- c("influence_score_20-80_weighted", "public_metrics.followers_count", "public_metrics.listed_count", "retweet_count", "like_count", "mention_count")

# Create empty lists to store results
results <- list(combined = list())

# Function to calculate numeric stats
calculate_stats <- function(data, var) {
  list(
    Median = median(data[[var]], na.rm = TRUE),
    IQR = IQR(data[[var]], na.rm = TRUE),
    Min = min(data[[var]], na.rm = TRUE),
    Max = max(data[[var]], na.rm = TRUE),
    N = sum(!is.na(data[[var]]))
  )
}

# Filter the data for each group (here only one)
combined_data <- df_influencers

# Calculate stats for numeric variables for each group
for (var in variables) {
  results$combined[[var]] <- calculate_stats(combined_data, var)
}
results

########################################################
# 10. Save final data frame
########################################################

# List of variables to include, metadata not included for privacy/legal reasons
selected_vars <- c(
  "id",
  # "is_m_created_or_revital_nov_dec",
  "is_migrated",
  "is_returned",
  "is_os_endorsement",
  "is_influencer",
  "SI_S",
  "SI_N",
  "SI_I",
  "SI_S_abs_minmax_sign",
  "SI_N_minmax",
  "SI_I_minmax",
  "social_impact",
  # "twitter_followers_count",
  # "twitter_following_count",
  # "twitter_tweet_count",
  # "twitter_listed_count",
  # "twitter_account_age",
  # "twitter_activity_since_activity_comp",
  # "mastodon_activity_nov_dec",
  # "influencer_twitter_tweet_count",
  # "influencer_twitter_retweet_count",
  # "influencer_twitter_like_count",
  # "influencer_twitter_mention_count",
  "influencer_influence_score_20-80_weighted",
  "SI_S_abs_minmax_sign_z",
  "SI_N_minmax_z",
  "SI_I_minmax_z",
  # "twitter_followers_count_z",
  # "twitter_following_count_z",
  # "twitter_tweet_count_z",
  # "twitter_account_age_z",
  "social_impact_z"
)
df_selected <- df[, selected_vars]

# Save final data frame
path_df_selected <- paste0(config$paths$data$analyzed$final_analyzed, "final_analyzed.csv")
write.csv(df_selected, path_df_selected, row.names = FALSE)

########################################################
# 11. Logistic Regression (for completeness)
########################################################

# Initially, we planned to use Logistic Regression, but the assumptions were
# violated. For completeness, the results are included in the supplementary
# material.

# Fit logistic regression on complete dataset
mod_logistic_all <- glm(
  is_migrated ~ social_impact_z +
    is_os_endorsement +
    twitter_account_age_z +
    twitter_tweet_count_z,
  family = binomial, data = df
)
summary(mod_logistic_all)
