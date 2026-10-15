# https://cran.r-project.org/web/packages/academictwitteR/vignettes/academictwitteR-intro.html

library(academictwitteR)
library(rtweet)
auth <- rtweet_app() # bearer token


# Twitter Migration Mastodon ----------------------------------------------

hashtags_migration <- c("TwitterMigration", "TwitterExodus", "MastodonMigration")
hashtags_mastodon <- c("Mastodon", "ScienceMastodon", "AcademicMastodon")

# addes for first update:
hashtags_migration_2 <- c("JoinMastodon", "TwitterExit")



## get tweets ----

# start collecting: 02.02.23, 12:00
# last update: 31.03.23, 11:45

tweets_migration <-
  get_all_tweets(
    query = hashtags_migration,
    start_tweets = "2022-01-01T00:00:00Z",
    end_tweets = "2023-02-02T00:00:00Z",
    file = "./RDS/tweets_migration.RDS",
    n = Inf
  )

tweets_mastodon <-
  get_all_tweets(
    query = hashtags_mastodon,
    start_tweets = "2022-01-01T00:00:00Z",
    end_tweets = "2023-02-02T00:00:00Z",
    file = "./RDS/tweets_mastodon.RDS",
    n = Inf
  )


## First update ----

tweets_migration <-
  get_all_tweets(
    query = hashtags_migration,
    start_tweets = "2023-02-02T00:00:00Z",
    end_tweets = "2023-02-07T00:00:00Z",
    file = "./RDS/tweets_migration_update_070223.RDS",
    n = Inf
  )

# new hashtags added
tweets_migration_2 <-
  get_all_tweets(
    query = hashtags_migration_2,
    start_tweets = "2022-01-01T00:00:00Z",
    end_tweets = "2023-02-07T00:00:00Z",
    file = "./RDS/tweets_migration_2.RDS",
    n = Inf
  )

tweets_mastodon <-
  get_all_tweets(
    query = hashtags_mastodon,
    start_tweets = "2023-02-02T00:00:00Z",
    end_tweets = "2023-02-07T00:00:00Z",
    file = "./RDS/tweets_mastodon_update_070223.RDS",
    n = Inf
  )



## Second update ----

tweets_migration <-
  get_all_tweets(
    query = hashtags_migration,
    start_tweets = "2023-02-07T00:00:00Z",
    end_tweets = "2023-02-08T00:00:00Z",
    file = "./RDS/tweets_migration_update_080223.RDS",
    n = Inf
  )

tweets_migration_2 <-
  get_all_tweets(
    query = hashtags_migration_2,
    start_tweets = "2023-02-07T00:00:00Z",
    end_tweets = "2023-02-08T00:00:00Z",
    file = "./RDS/tweets_migration_2_update_080223.RDS",
    n = Inf
  )

tweets_mastodon <-
  get_all_tweets(
    query = hashtags_mastodon,
    start_tweets = "2023-02-07T00:00:00Z",
    end_tweets = "2023-02-08T00:00:00Z",
    file = "./RDS/tweets_mastodon_update_080223.RDS",
    n = Inf
  )


## Third update ----

tweets_migration <-
  get_all_tweets(
    query = hashtags_migration,
    start_tweets = "2023-02-08T00:00:00Z",
    end_tweets = "2023-02-10T00:00:00Z",
    file = "./RDS/tweets_migration_update_100223.RDS",
    n = Inf
  )

tweets_migration_2 <-
  get_all_tweets(
    query = hashtags_migration_2,
    start_tweets = "2023-02-08T00:00:00Z",
    end_tweets = "2023-02-10T00:00:00Z",
    file = "./RDS/tweets_migration_2_update_100223.RDS",
    n = Inf
  )

tweets_mastodon <-
  get_all_tweets(
    query = hashtags_mastodon,
    start_tweets = "2023-02-08T00:00:00Z",
    end_tweets = "2023-02-10T00:00:00Z",
    file = "./RDS/tweets_mastodon_update_100223.RDS",
    n = Inf
  )

## Fourth update ----

tweets_migration <-
  get_all_tweets(
    query = hashtags_migration,
    start_tweets = "2023-02-10T00:00:00Z",
    end_tweets = "2023-03-31T00:00:00Z",
    file = "./RDS/tweets_migration_update_310323.RDS",
    n = Inf
  )

tweets_migration_2 <-
  get_all_tweets(
    query = hashtags_migration_2,
    start_tweets = "2023-02-10T00:00:00Z",
    end_tweets = "2023-03-31T00:00:00Z",
    file = "./RDS/tweets_migration_2_update_310323.RDS",
    n = Inf
  )

tweets_mastodon <-
  get_all_tweets(
    query = hashtags_mastodon,
    start_tweets = "2023-02-10T00:00:00Z",
    end_tweets = "2023-03-31T00:00:00Z",
    file = "./RDS/tweets_mastodon_update_310323.RDS",
    n = Inf
  )


## unique_users ----

filenames <- list.files("./RDS", pattern = "tweets", full.names = TRUE)

id_list <- list()
for (i in 1:length(filenames)){
  tmp <- readRDS(filenames[i])
  id_list[[i]] <- tmp$author_id
}

user_ids_tweets <- unique(unlist(id_list))
saveRDS(ids_tweets, file ="./RDS/user_ids_tweets.RDS")


## get profiles ----

profiles_tweets <- get_user_profile(user_ids_tweets)
saveRDS(profiles_tweets, file = "./RDS/profiles_tweets.RDS")

## get followers ----

# followers_tweets <- get_user_followers(user_ids_tweets)
# saveRDS(profiles_tweets, file = "./RDS/followers_tweets.RDS")


## get followees ----
# followees_tweets <- get_user_following(user_ids_tweets)
# saveRDS(profiles_tweets, file = "./RDS/followers_tweets.RDS")




# Profiles of researchers by Mongeon et al. -------------------------------


# Philippe Mongeon, Timothy Bowman, & Rodrigo Costas. (2022).
# Open dataset of scholars on Twitter (2020-08-23) [Data set]. Zenodo. 
# https://doi.org/10.5281/zenodo.7013518

# saved as .xlsx, as there was some problem reading the .csv file (imported only 262K cased)

authors_tweeters_2022_08_21 <- readxl::read_excel("authors_tweeters_2022_08_21.xlsx")

# drop false positives
# "This column indicates whether the match has been manually checked. 
# A 0 indicates a false positive, and a 1 indicates a true positive. Empty rows have not been manually validated."
user_id_researchers <- authors_tweeters_2022_08_21$tweeter_id[authors_tweeters_2022_08_21$valid == 1 |
                                                                is.na(authors_tweeters_2022_08_21$valid)]

# same tweeter can have different open alex ids; keep unique
user_id_researchers <- unique(user_id_researchers)
saveRDS(user_id_researchers, file ="./RDS/user_id_researchers.RDS")


# get profiles
profiles_researchers <- get_user_profile(user_id_researchers)
saveRDS(profiles_researchers, file = "./RDS/profiles_researchers.RDS")


## get followers ----

followers_researchers <- get_user_followers(user_id_researchers)
saveRDS(followers_researchers, file = "./RDS/followers_researchers.RDS")

## get followees ----
followees_researchers <- get_user_following(user_id_researchers)
saveRDS(followees_researchers, file = "./RDS/followees_researchers.RDS")


# takes too long due to rate limit (15 requests per 15 minutes)

## workaround ----

# get followers of users with most followers
user_ids_researchers_sorted <- profiles_researchers[
  order(-profiles_researchers$public_metrics$followers_count), "id"]

followers_researchers <- list()

start <- Sys.time()
for (i in 53:length(user_ids_researchers_sorted)){
  print(paste("Progress: Iteration", i, i/(length(user_ids_researchers_sorted)), "%"))
  print(start - Sys.time())
  
  followers_researchers[[i]] <- rtweet::get_followers(user_ids_researchers_sorted[i], n = Inf, retryonratelimit = TRUE)
  saveRDS(followers_researchers, file = "./RDS/followers_researchers.RDS")
}
end <-  Sys.time()




## psychologists  ----

# filter profiles for "psych"
profiles_researchers_psy <- profiles_researchers[grep("psych", profiles_researchers$description, ignore.case = TRUE),]

# remove psychiatrists
profiles_researchers_psy <- profiles_researchers_psy[!grepl("psychiatrist", profiles_researchers_psy$description, ignore.case = TRUE),]

# keep psychiatry only in context of psychology
cond <- grepl("psychia", profiles_researchers_psy$description, ignore.case = TRUE) &
  !grepl("psychol", profiles_researchers_psy$description, ignore.case = TRUE)
profiles_researchers_psy <- profiles_researchers_psy[!cond,]

saveRDS(profiles_researchers_psy, file = "./RDS/profiles_researchers_psy_mongeon.RDS")


user_id_psy_mongeon <- profiles_researchers_psy$id




# Profiles and timelines of psychology researchers ------------------------

# Müller, Kotzur, Bittermann (submitted to ISSI conference)
# (updating the 2021 dataset)

# ids from Twitter researcher project (see ISSI submission)
library(readr)
ESM_user_id <- read_csv("ESM_user_id.txt", col_types = cols(user_id = col_character()))
user_id_psy <- ESM_user_id$user_id

# profiles
profiles_psy <- get_user_profile(user_id_psy)
saveRDS(profiles_psy, file = "./RDS/profiles_psy.RDS")

# timelines
timelines_psy <- get_user_timeline(
  user_id_psy,
  start_tweets = "2021-02-01T00:00:00Z",
  end_tweets = "2023-02-03T00:00:00Z",
  file = "./RDS/timelines_psy.RDS",
  n = Inf
)

saveRDS(timelines_psy, file = "./RDS/timelines_psy.RDS")


timelines_psy_update <- get_user_timeline(
  user_id_psy,
  start_tweets = "2023-02-03T00:00:00Z",
  end_tweets = "2023-02-08T00:00:00Z",
  file = "./RDS/timelines_psy_update_temp.RDS",
  n = Inf
)

saveRDS(timelines_psy_update, file = "./RDS/timelines_psy_update_080223.RDS")


timelines_psy_update <- get_user_timeline(
  user_id_psy,
  start_tweets = "2023-02-08T00:00:00Z",
  end_tweets = "2023-03-31T00:00:00Z",
  file = "./RDS/timelines_psy_update_temp.RDS",
  n = Inf
)

saveRDS(timelines_psy_update, file = "./RDS/timelines_psy_update_310323.RDS")



# Get timelines of Mongeon psychologists ----------------------------------

# that are not included in our dataset of psychologists

user_id_psy_mongeon_additional <- !(user_id_psy_mongeon %in% user_id_psy)
user_id_psy_mongeon_additional <- user_id_psy_mongeon[user_id_psy_mongeon_additional]

# # timelines
# timelines_psy_mongeon_additional <- get_user_timeline(
#   user_id_psy,
#   start_tweets = "2021-02-01T00:00:00Z",
#   end_tweets = "2023-02-08T00:00:00Z",
#   file = "./RDS/timelines_psy_mongeon_additional.RDS",
#   n = Inf
# )
# 
# saveRDS(timelines_psy_mongeon_additional, file = "./RDS/timelines_psy_mongeon_additional.RDS")


# collected with rtweet due to rate limit
timelines_psy_mongeon_additional <- list()

start <- Sys.time()
for (i in 1:length(user_id_psy_mongeon_additional)){
  print(paste("Progress: Iteration", i, i/(length(user_id_psy_mongeon_additional)), "%"))
  print(start - Sys.time())
  
  timelines_psy_mongeon_additional[[i]] <- rtweet::get_timeline(
    user_id_psy_mongeon_additional[i], n = Inf, retryonratelimit = TRUE)
  
}
end <-  Sys.time()
saveRDS(timelines_psy_mongeon_additional, file = "./RDS/timelines_psy_mongeon_additional.RDS")




# Get all Mongeon timelines -----------------------------------------------


# timelines
timelines_mongeon <- get_user_timeline(
  user_id_researchers,
  start_tweets = "2022-10-01T00:00:00Z",
  end_tweets = "2023-02-08T00:00:00Z",
  data_path = "data/",
  bind_tweets = TRUE,
  n = 1e6 # per user?
)

saveRDS(timelines_mongeon, file = "./RDS/timelines_mongeon.RDS")



# Profiles OpenCheck ------------------------------------------------------

All_disciplines <- read.csv("./All_disciplines.csv")

opencheck_twitter_handles <- All_disciplines$twitter
table(is.na(opencheck_twitter_handles))

opencheck_twitter_handles <- gsub("@", "", opencheck_twitter_handles)
opencheck_twitter_handles <- opencheck_twitter_handles[opencheck_twitter_handles != "None"]

# which ones are not included in the Mongeon file?
table(opencheck_twitter_handles %in% profiles_researchers$username)
opencheck_non_Mongeon <- opencheck_twitter_handles[!(opencheck_twitter_handles %in% profiles_researchers$username)]
saveRDS(opencheck_non_Mongeon, file = "./RDS/opencheck_non_Mongeon.RDS")

## retweet ----
lookup_opencheck <- lookup_users(opencheck_non_Mongeon, token = auth)
# get profiles of these users
profiles_researchers_opencheck_rtweet <- get_user_profile(lookup_opencheck$id_str)
saveRDS(profiles_researchers_opencheck, file = "./RDS/profiles_researchers_opencheck_rtweet.RDS")

## academictwitteR ----
user_id_opencheck <- list()

for (i in 1:length(opencheck_non_Mongeon)){
  
  skip_to_next <- FALSE
  
  tryCatch(user_id_opencheck[[i]] <- get_user_id(opencheck_non_Mongeon[i]),
           error = function(e){skip_to_next <<- TRUE})
  
  if(skip_to_next){next}
  
}

user_id_opencheck <- unlist(user_id_opencheck)
saveRDS(user_id_opencheck , user_id_opencheck = "./RDS/user_id_opencheck.RDS")

# get profiles
profiles_researchers_opencheck <- get_user_profile(na.omit(user_id_opencheck))
saveRDS(profiles_researchers_opencheck, file = "./RDS/profiles_researchers_opencheck.RDS")




# Get November/December timelines of researchers ----

# continuing the interrupted collection of Mongeon timelines (see above)
# but for November and December 2022 only.
# In addition: include opencheck accounts


# get researcher ids of Mongeon and opencheck

user_id_researchers <- readRDS("./RDS/user_id_researchers.RDS")
user_id_opencheck <- readRDS("./RDS/user_id_opencheck.RDS")
user_id_unique <- unique(c(user_id_researchers, user_id_opencheck))


## ids of researchers missed ----

# which mongeon researchers were collected?
library(readr)
profiles_researchers_IDs_tweets <- read_csv("profiles_researchers_IDs_tweets.csv", 
                                            col_types = cols(id = col_character()))
mongeon_collected <- as.vector(unlist(profiles_researchers_IDs_tweets[,1]))

# user ids of all missing mongeon + opencheck
table(user_id_unique %in% mongeon_collected)
user_id_missed <- !(user_id_unique %in% mongeon_collected)
user_id_missed <- user_id_unique[user_id_missed]


## timelines November 2022 ----
timelines_researchers_missed_nov <- get_user_timeline(
  user_id_missed,
  start_tweets = "2022-11-01T00:00:00Z",
  end_tweets = "2022-12-01T00:00:00Z",
  # file = "./RDS/timelines_researchers_temp.RDS",
  data_path = "november/",
  bind_tweets = TRUE,
  n = Inf
)

saveRDS(timelines_researchers_missed_nov, file = "./RDS/timelines_researchers_missed_nov22.RDS")


## timelines December 2022 ----
timelines_researchers_missed_dec <- get_user_timeline(
  user_id_missed,
  start_tweets = "2022-12-01T00:00:00Z",
  end_tweets = "2023-01-01T00:00:00Z",
  # file = "./RDS/timelines_researchers_temp.RDS",
  data_path = "december/",
  bind_tweets = TRUE,
  n = Inf
)

saveRDS(timelines_researchers_missed_dec, file = "./RDS/timelines_researchers_missed_dec22.RDS")

