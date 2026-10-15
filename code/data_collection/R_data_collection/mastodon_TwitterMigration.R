#TwitterMigration

hashtags_migration <- c("TwitterMigration", "TwitterExodus", "MastodonMigration")
hashtags_academic_mastodon <- c("ScienceMastodon", "AcademicMastodon")

# 03.02.23, 17:30

timelines_migration <- list()
for (i in 1:length(hashtags_migration)){
  timelines_migration[[i]] <- get_timeline_hashtag(
    hashtag = hashtags_migration[i],
    instance = "mastodon.social",
    anonymous = TRUE,
    limit = 1e9,
    retryonratelimit = TRUE
  )
}

timelines_academic_mastodon <- list()
for (i in 1:length(hashtags_academic_mastodon)){
  timelines_academic_mastodon[[i]] <- get_timeline_hashtag(
    hashtag = hashtags_academic_mastodon[i],
    instance = "mastodon.social",
    anonymous = TRUE,
    limit = 1e9,
    retryonratelimit = TRUE
  )
}

View(timelines_migration[[1]])
