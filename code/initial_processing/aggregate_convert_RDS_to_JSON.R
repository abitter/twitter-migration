# Utility script for intial data preparation/setup:
# combining and converting various RDS files (to json) for further processing in Python

# clear workspace
rm(list = ls())

##############################################################
# Install and/or load required packages, load config
##############################################################

# Install and/or load required packages
if (!requireNamespace("jsonlite", quietly = TRUE)) {
    install.packages("jsonlite")
}
library(jsonlite)

# Check and install the yaml package if not already installed
if (!requireNamespace("yaml", quietly = TRUE)) {
    install.packages("yaml")
}
library(yaml)
library(dplyr)

# set working directory to location of this file
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Load the configuration
config <- yaml.load_file("../../config.yml")

##############################################################
# Intial data preparation/setup for timelines
##############################################################

# Twitter timelines were collected, among other things, to determine activity on
# the platform. Timelines were collected in two batches: For some people, we
# have individual json files for Nov and Dec 2022 that are concatenated in
# bind_json_tweets.py. For others, we have three RDS files (Nov, Dec, and Apr)
# that are concatenated here and exported as json. They contain both people from
# the Mongeon et al. sample and people from the OpenCheck list.

##### timelines #####

# concatenate RDS timelines
data_timelines_nov <- readRDS(paste0(config$paths$data$raw$twitter$`researcher timelines json (mongeon + opencheck)`, "timelines_nov_tryCatch.RDS"))
data_timelines_dec <- readRDS(paste0(config$paths$data$raw$twitter$`researcher timelines json (mongeon + opencheck)`, "timelines_dec_tryCatch.RDS"))
data_timelines_apr <- readRDS(paste0(config$paths$data$raw$twitter$`researcher timelines json (mongeon + opencheck)`, "timelines_april_tryCatch.RDS"))

data_timelines_combined <- bind_rows(
    data_timelines_nov,
    data_timelines_dec,
    data_timelines_apr
)

# sanity check that IDs are represented as char
sapply(data_timelines_combined, class)
class(data_timelines_combined$author_id)

# Write the JSON data to a file using stream_out
# con <- file("/home/lauer/projects/Mastodon/data/processed/twitter/0_setup/timelines_rds_combined.json", "wb")
filepath <- paste0(config$paths$data$processed$twitter$setup, "timelines_rds_combined.json")
con <- file(filepath, "wb")
stream_out(data_timelines_combined, con, pagesize = 10000) # Adjust pagesize as needed
close(con)

##############################################################
# Intial data preparation/setup for influencer identification
##############################################################

# Influencers need to be identified using posts with certain keywords (hashtag
# queries) made by researchers (profiles researchers). For both hashtag queries
# and profiles, different files are aggregated and saved as json to be processed
# in Python.

##### hashtag queries #####

# read all hashtag query data
data_tweets_migration <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration.RDS"))
data_tweets_migration_update_070223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_update_070223.RDS"))
data_tweets_migration_update_080223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_update_080223.RDS"))
data_tweets_migration_update_100223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_update_100223.RDS"))
data_tweets_migration_update_310323 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_update_310323.RDS"))
data_tweets_migration_2 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_2.RDS"))
data_tweets_migration_2_update_082323 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_2_update_082323.RDS"))
data_tweets_migration_2_update_100223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_2_update_100223.RDS"))
data_tweets_migration_2_update_310323 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_migration_2_update_310323.RDS"))
data_tweets_mastodon <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_mastodon.RDS"))
data_tweets_mastodon_update_070223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_mastodon_update_070223.RDS"))
data_tweets_mastodon_update_080223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_mastodon_update_080223.RDS"))
data_tweets_mastodon_update_100223 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_mastodon_update_100223.RDS"))
data_tweets_mastodon_update_310323 <- readRDS(paste0(config$paths$data$raw$twitter$`hashtag queries`, "tweets_mastodon_update_310323.RDS"))

# bind all data frames together
data_tweets_combined <- bind_rows(
    data_tweets_migration,
    data_tweets_migration_update_070223,
    data_tweets_migration_update_080223,
    data_tweets_migration_update_100223,
    data_tweets_migration_update_310323,
    data_tweets_migration_2,
    data_tweets_migration_2_update_082323,
    data_tweets_migration_2_update_100223,
    data_tweets_migration_2_update_310323,
    data_tweets_mastodon,
    data_tweets_mastodon_update_070223,
    data_tweets_mastodon_update_080223,
    data_tweets_mastodon_update_100223,
    data_tweets_mastodon_update_310323
)

# save as json using stream_out
filepath <- paste0(config$paths$data$processed$twitter$setup, "hashtag_queries_combined.json")
con <- file(filepath, "wb")
stream_out(data_tweets_combined, con, pagesize = 10000) # adjust pagesize as needed
close(con)

##### profiles researchers #####

# read profiles of researchers identified by Mongeon et al. and profiles from the public list "Opencheck"
data_profiles_researchers <- readRDS(paste0(config$paths$data$raw$twitter$`researcher profiles and timelines`, "profiles_researchers.RDS"))
data_profiles_researchers_opencheck <- readRDS(paste0(config$paths$data$raw$twitter$`researcher profiles and timelines`, "profiles_researchers_opencheck.RDS"))

# sanity check that IDs are represented as char
sapply(data_profiles_researchers, class)
sapply(data_profiles_researchers_opencheck, class)

# bind data frames together
data_tweets_combined <- bind_rows(
    data_profiles_researchers,
    data_profiles_researchers_opencheck,
)

# sanity check that IDs are represented as char
sapply(data_tweets_combined, class)

# save as json using stream_out
filepath <- paste0(config$paths$data$processed$twitter$setup, "profiles_researchers_combined.json")
con <- file(filepath, "wb")
stream_out(data_tweets_combined, con, pagesize = 10000) # Adjust pagesize as needed
close(con)

##### followers influencers #####

# NOTE: this file does not seem to exist anymore - it seems the section below is the updated version of this
data_followers_influencers <- readRDS("/home/shared_folder/followers_influencers.RDS")

# save as json
# write_json(data_followers_influencers, output_file)
filepath <- paste0(config$paths$data$processed$twitter$setup, "followers_influencers.json")
write_json(data_followers_influencers, filepath)
