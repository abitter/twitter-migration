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

##########################################################
# Intial data preparation/setup for influencers followers 
##########################################################

# Followers of #TwitterMigration influencers were collected in several batches.
# Concatenating all files into one dataframe with two columns:
# `to_id` and `from_id` (each row holds one influencer and a list of their
# follower(s)). Exporting to json.

flatten_and_aggregate_df <- function(data) {

  # Input: list, each element represents an influencer and contains 'from_id'
  # and 'to_id' keys for follower and influencer IDs, respectively. NULLs in the
  # list (missing influencers) are counted/printed and filtered out. Each list
  # element is converted into a df and aggregated by 'to_id' (influencer),
  # creating a list of 'from_id' values (followers) for each 'to_id'. The number
  # of influencers for whom no followers were retrieved is counted/printed.
  # Returning aggregated df.
  
  # Filter out NULLs
  data_filtered <- data[sapply(data, is.null) == FALSE]

  # Count and print the number of Non-NULLs
  num_non_nulls <- length(data_filtered)
  print(paste("Number of retrieved influencers:", num_non_nulls))

  # Count and print the number of NULLs
  num_nulls <- length(data) - length(data_filtered)
  print(paste("Number of missing influencers:", num_nulls))
  
  # Convert each inner list to a dataframe
  df_list <- lapply(data_filtered, function(x) {
    if (!"from_id" %in% names(x)) { 
      x$from_id <- NA  # if 'from_id' key is not present, add it and set it to NA
    }
    if (!"to_id" %in% names(x)) { 
      x$to_id <- NA  # if 'to_id' key is not present, add it and set it to NA
    }
    data.frame(from_id = x$from_id, to_id = x$to_id, stringsAsFactors = FALSE)
  })
  
  # Combine all dataframes into a single dataframe
  flattened_df <- bind_rows(df_list)

  #  Group by 'to_id' (influencers) and create a list of 'from_id' values (followers) for each 'to_id'
    df_agg <- flattened_df %>%
      group_by(to_id) %>%
      summarise(from_id = list(from_id))

  # Count and print the number of NaNs in df_agg
  num_NaNs = sum(is.na(df_agg$from_id))
  print(paste("Number of retrieved influencers for whom no followers were retrieved:", num_NaNs))
    
  # Return aggregated df 
  return(df_agg)
}

process_nullfixed_df <- function(df) {

  # Input: dataframe (df). Selecting only the 'id' and 'from_id' columns and
  # renaming them to 'from_id' and 'to_id', respectively, aligning with other
  # dfs. Aggregating the df by 'to_id' (influencer), creating a list of
  # 'from_id' values (followers) for each 'to_id'. Printing the count of
  # previously missing influencers that were now retrieved and the count of
  # newly retrieved influencers for whom no followers were retrieved. Returning
  # aggregated df.

  # Load required library
  library(dplyr)
  
  # Retain only columns 'id' and 'from_id'
  df <- df[, c('id', 'from_id')]
  
  # Rename the columns to match existing DataFrame
  names(df) <- c('from_id', 'to_id')
  
  # Group by 'to_id' (influencers) and create a list of 'from_id' values (followers) for each 'to_id'
  df_agg <- df %>%
    group_by(to_id) %>%
    summarise(from_id = list(from_id)) 
  
  # Print len of df_agg
  print(paste0("Number of previously missing influencers that were now retrieved: ", nrow(df_agg)))

  # Count and print the number of NaNs in flattened_df
  num_NaNs = sum(is.na(df_agg$from_id))
  print(paste("Number of newly retrieved influencers for whom no followers were retrieved:", num_NaNs))
  
  return(df_agg)
}

##### Batch 1 #####

# Read and process followers_influencers_100.RDS
rawdata_followers_influencers_100 <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_100.RDS"))
df_followers_influencers_100 <- flatten_and_aggregate_df(rawdata_followers_influencers_100)

# Read and process followers_influencers_100_null_fixed.RDS
rawdata_followers_influencers_100_nullfixed <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_100_null_fixed.RDS"))
df_followers_influencers_100_nullfixed <- process_nullfixed_df(rawdata_followers_influencers_100_nullfixed)

##### Batch 2 #####

# Read and process followers_influencers_continued.RDS
rawdata_followers_influencers_continued <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_continued.RDS"))
df_followers_influencers_continued <- flatten_and_aggregate_df(rawdata_followers_influencers_continued)

# Read and process followers_influencers_null_fixed.RDS
rawdata_followers_influencers_continued_nullfixed <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_null_fixed.RDS"))
df_followers_influencers_continued_nullfixed <- process_nullfixed_df(rawdata_followers_influencers_continued_nullfixed)

##### Batch 3 #####

# Read and process followers_influencers_continued_1770.RDS
rawdata_followers_influencers_continued_1770 <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_continued_1770.RDS"))
df_followers_influencers_continued_1770 <- flatten_and_aggregate_df(rawdata_followers_influencers_continued_1770)

# Read and process followers_influencers_null_fixed_1770.RDS
rawdata_followers_influencers_continued_nullfixed_1770 <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_null_fixed_1770.RDS"))
df_followers_influencers_continued_nullfixed_1770 <- process_nullfixed_df(rawdata_followers_influencers_continued_nullfixed_1770)

##### Exploration/Checking of results: Batch 2 should be a subset of Batch 3 #####

# how many to_ids in df_followers_influencers_continued are found in df_followers_influencers_continued_1770
sum(df_followers_influencers_continued$to_id %in% df_followers_influencers_continued_1770$to_id)
nrow(df_followers_influencers_continued)
# -> all ids are found, meaning that df_followers_influencers_continued is indeed a subset of df_followers_influencers_continued_1770

# just to confirm that the followers for these overlapping ids are also identical
df_followers_influencers_continued_1770_subset <- df_followers_influencers_continued_1770[df_followers_influencers_continued_1770$to_id %in% df_followers_influencers_continued$to_id,]
identical(df_followers_influencers_continued, df_followers_influencers_continued_1770_subset)
# -> indeed, the dataframes are identical

# moving on to nullfixed: how many to_ids in df_followers_influencers_continued_nullfixed are found in df_followers_influencers_continued_nullfixed_1770
sum(df_followers_influencers_continued_nullfixed$to_id %in% df_followers_influencers_continued_nullfixed_1770$to_id)
nrow(df_followers_influencers_continued_nullfixed)
# -> only 3/72 ids are found, meaning that not all cases in df_followers_influencers_continued_nullfixed are contained in df_followers_influencers_continued_nullfixed_1770

# checking if maybe only cases where NO followers were retrieved were NOT found
df_followers_influencers_continued_nullfixed_nonnull <- df_followers_influencers_continued_nullfixed[!(is.na(df_followers_influencers_continued_nullfixed$from_id)),]
sum(df_followers_influencers_continued_nullfixed_nonnull$to_id %in% df_followers_influencers_continued_nullfixed_1770$to_id)
# -> this is not the case as there are two non-nulls that were not found in df_followers_influencers_continued_nullfixed_1770

# So we cannot entirely skip Batch2 which we thought was a subset of Batch3. So concatenating the nullfixed dataframes of Batch2 and Batch3 and then removing duplicates
df_followers_influencers_continued_nullfixed_1770_combined <- bind_rows(df_followers_influencers_continued_nullfixed, df_followers_influencers_continued_nullfixed_1770)
# how many duplicates are there?
sum(duplicated(df_followers_influencers_continued_nullfixed_1770_combined))
# remove duplicates 
df_followers_influencers_continued_nullfixed_1770_combined <- df_followers_influencers_continued_nullfixed_1770_combined[!duplicated(df_followers_influencers_continued_nullfixed_1770_combined),]
# -> removed three duplicates

##### Concatenating Batches #####

# Concatenate dataframes that we need
df_complete <- bind_rows(
    df_followers_influencers_100,
    df_followers_influencers_100_nullfixed,
    df_followers_influencers_continued_1770, # all cases in df_followers_influencers_continued are contained in df_followers_influencers_continued_1770, so only using the latter
    df_followers_influencers_continued_nullfixed_1770_combined # this is the combined nullfixed df of Batch2 and Batch3 as not all cases in Batch2 are contained in Batch3
)

# remove duplicates 
sum(duplicated(df_complete))
df_complete <- df_complete[!duplicated(df_complete),]
# -> removed 6 duplicates (3)

# remove influencers for whom no followers were retrieved 
sum(is.na(df_complete$from_id))
df_complete <- df_complete[!is.na(df_complete$from_id),]
# -> For 851 influencers removed

# how many remaining influencers are there?
nrow(df_complete)
# -> 8815

# -------- EDIT: 2023-10-11 -------- #

# Read and process followers_influencers_september.RDS: this data was additionally collected bc of an update in influencer 
# identification, resulting in missing influencers
rawdata_followers_influencers_sep <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "followers_influencers_september.RDS"))

df_followers_influencers_sep <- flatten_and_aggregate_df(rawdata_followers_influencers_sep)

# remove influencers for whom no followers were retrieved
sum(is.na(df_followers_influencers_sep$from_id))
df_followers_influencers_sep <- df_followers_influencers_sep[!is.na(df_followers_influencers_sep$from_id),]
# -> For 129 influencers removed

# are there any duplicates in df_followers_influencers_sep?
sum(duplicated(df_followers_influencers_sep))
# -> no duplicates

# Concatenate with df_complete
df_complete_updated <- bind_rows(
    df_complete,
    df_followers_influencers_sep
)

# any new duplicates? 
sum(duplicated(df_complete_updated))
# -> no

# how many influencers are there?
nrow(df_complete_updated)
# -> 14064 (missing influencers added, and some people are not influencers anymore with the updated identification)

##### Export as JSON #####

# TODO: can this just be commented out or do we need it for reproducibility?
# # converting df_complete to JSON
# json_data_complete <- toJSON(df_complete, dataframe = "rows")

# # Write the JSON data to a file
# # write(json_data_complete, "../../../../data/processed/twitter/0_setup/influencers_followers_combined.json")
# filepath = paste0(config$paths$data$processed$twitter$setup, "influencers_followers_combined.json")
# write(json_data_complete, filepath)

# converting df_complete_updated to JSON
# corrected bug: needs to be df_complete_updated, not df_complete
json_data_complete_updated <- toJSON(df_complete_updated, dataframe = "rows")

# Write the JSON data to a file
# write(json_data_complete, "../../../../data/processed/twitter/0_setup/influencers_followers_combined.json")
filepath = paste0(config$paths$data$processed$twitter$setup, "influencers_followers_combined_updated.json")
write(json_data_complete_updated, filepath)

# ------------------------------------

# -------- EDIT: 2024-02-22 -------- #

# Read and process missing_influencer_followers: this data was additionally
# collected bc of an update in influencer identification, resulting in some
# missing influencers. specifically, since IDs were ints by mistake, we missed
# out on some people that we now collected in a separate batch and add to the
# existing data. 

# read additionally collected data
rawdata_followers_influencers_missing <- readRDS(paste0(config$paths$data$raw$twitter$influencers, "missing_influencer_followers.RDS"))

# apply function for flattenening and aggregating
df_followers_influencers_missing <- flatten_and_aggregate_df(rawdata_followers_influencers_missing)

# remove influencers for whom no followers were retrieved
sum(is.na(df_followers_influencers_missing$from_id))
df_followers_influencers_missing <- df_followers_influencers_missing[!is.na(df_followers_influencers_missing$from_id),]
# -> For 138 influencers removed

# are there any duplicates in df_followers_influencers_missing?
sum(duplicated(df_followers_influencers_missing))
# -> no duplicates

# Concatenate with df_complete and df_followers_influencers_sep
df_complete_updated_missing <- bind_rows(
    df_complete,
    df_followers_influencers_sep,
    df_followers_influencers_missing
)

# any new duplicates? 
sum(duplicated(df_complete_updated_missing))
# -> no

# how many influencers are there combined?
nrow(df_complete_updated_missing)
# -> 15107 (with missing influencers added)
# note that some people are not influencers, going to filter out later based on IDs

# converting df_complete_updated_missing to JSON
# corrected bug: needs to be df_complete_updated_missing, not df_complete
json_data_complete_updated_missing <- toJSON(df_complete_updated_missing, dataframe = "rows")

# Write the JSON data to a file
# write(json_data_complete, "../../../../data/processed/twitter/0_setup/influencers_followers_combined.json")
filepath = paste0(config$paths$data$processed$twitter$setup, "influencers_followers_combined_updated_v2.json")
write(json_data_complete_updated_missing, filepath)