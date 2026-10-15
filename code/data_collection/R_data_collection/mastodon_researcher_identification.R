# identifying researchers on mastodon

# idea:
# 1. collect toots with #introduction (starting point) of researchers (pattern matching with list of terms)
# 2. use account information for validation
# 3. add accounts from curated lists
# 4. crawl their follower and/or mentions network (finding those without introduction)
# 5. collect timelines of researchers


devtools::install_github("schochastics/rtoot")
packageVersion("rtoot")

library(rtoot)
library(textclean)


#1. #introduction ----

researcher_terms <- c("research(|er)", "\\bphd", "scien(ce|tist)", "academic", "scholar", "\\bprof", "post(|-)doc",
                      "post(|-)graduate", "grad( |-|)student")

# filter researchers
filter_researcher <- function(x){
  sapply(researcher_terms, function(y){
    grepl(y, x, ignore.case = TRUE)
  })
}


## backwards search ----

# 11.11.22 15:00

# https://github.com/schochastics/rtoot/wiki/Pagination
# The idea is to make the oldest status ID the max_id of the next call.

max_id <- NULL
output <- tibble::tibble()
res_last_0 <- FALSE # checks whether last iteration returned 0 results
continue <- TRUE # break if two iterations in a row yielded 0 API returns
i <- 1 # iteration count


while (continue) {
  res <- get_timeline_hashtag(hashtag = "introduction", max_id = max_id,
                              limit = 40, instance = "mastodon.social")
  
  print(paste("nrow res:", nrow(res)))
  
  # break if res == 0 in two subsequent iterations
  if(nrow(res) == 0 & res_last_0){
    continue <- FALSE
  }
  
  # API rate limit or no more toots left
  if(nrow(res) == 0){
    
    # set check for empty results to TRUE
    res_last_0 <- TRUE
    
    # wait 5 minutes
    print("Sleeping for 5 minutes")
    Sys.sleep(300)
    next
  }
  
  # set check for empty results back to FALSE
  res_last_0 <- ifelse(nrow(res) != 0, FALSE, TRUE)
  
  
  # keep id, uri, created_at, content, account
  res <- res[,c(1:4,19)]
  
  # clean content
  res$content <- replace_white(replace_html(res$content))
  
  # get max_id
  # use only the first one if there more toots at the same time
  max_id <- res$id[res$created_at == min(res$created_at)][1]
  
  # filter researchers
  cond <- unname(sapply(res$content, function(x){
    any(filter_researcher(x))
  }))
  res <- res[cond,]
  
  # output
  output <- rbind(res, output)
  
  i <- i+1
  print(paste0("iteration ", i, ": ", nrow(output), " toots"))
  
  Sys.sleep(5)
}


# save
saveRDS(output, file = "./RDS/output_backward_before_dedup.RDS")

# remove duplicates
output <- output[-which(duplicated(output$uri)),]
saveRDS(output, file = "./RDS/output_backward.RDS")

# check where it stopped
min(output$created_at)




## forward search ----

# update the search

# last: 16.01.2023 10:42

min_id <- output$id[output$created_at == max(output$created_at)][1]
output_update <- tibble::tibble()
res_last_0 <- FALSE # checks whether last iteration returned 0 results
continue <- TRUE # break if two iterations in a row yielded 0 API returns
i <- 1 # iteration count


while (continue) {
  res <- get_timeline_hashtag(hashtag = "introduction", min_id = min_id,
                              limit = 40, instance = "mastodon.social")
  
  print(paste("nrow res:", nrow(res)))
  
  # break if res == 0 in two subsequent iterations
  if(nrow(res) == 0 & res_last_0){
    continue <- FALSE
  }
  
  # API rate limit or no more toots left
  if(nrow(res) == 0){
    
    # set check for empty results to TRUE
    res_last_0 <- TRUE
    
    # wait 5 minutes
    print("Sleeping for 5 minutes")
    Sys.sleep(300)
    next
  }
  
  # set check for empty results back to FALSE
  res_last_0 <- ifelse(nrow(res) != 0, FALSE, TRUE)
  
  
  # keep id, uri, created_at, content, account
  res <- res[,c(1:4,19)]
  
  # clean content
  res$content <- replace_white(replace_html(res$content))
  
  # get min_id
  # use only the first one if there more toots at the same time
  min_id <- res$id[res$created_at == max(res$created_at)][1]
  
  # filter researchers
  cond <- unname(sapply(res$content, function(x){
    any(filter_researcher(x))
  }))
  res <- res[cond,]
  
  # output
  output_update <- rbind(res, output_update)
  
  i <- i+1
  print(paste0("iteration ", i, ": ", nrow(output_update), " toots"))
  
  Sys.sleep(5)
}


# remove duplicates
# output_update <- output_update[-which(duplicated(output_update$uri)),]
saveRDS(output_update, file = paste0("./RDS/output_update_", substr(Sys.time(), 1, 10), ".RDS"))

# add
output <- rbind(output_update, output)
saveRDS(output, file = paste0("./RDS/output_", substr(Sys.time(), 1, 10), ".RDS"))




# 2. account validation ----

# check for multiple introductions

# check of institutions / organisations

# ORCID, website, profile description

# descriptives: prof, phd, etc., discipline via hashtags or n_gram



# 3. curated lists ----

# https://github.com/nathanlesage/academics-on-mastodon
# https://opencheck.is/people