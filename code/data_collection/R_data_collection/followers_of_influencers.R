library(academictwitteR)
library(rtweet)
auth <- rtweet_app()

library(readr)


# top 100 influencers ----

Influencers_100 <- read_csv("Influencers_20_80_IDs_ordered_by_influence.csv", 
                        col_types = cols(id = col_character()))
influencers_100 <- unlist(as.vector(Influencers_100[,1]))


# get followers
followers_influencers_100 <- list()


start <- Sys.time()
for (i in 1:length(influencers_100)){
  
  skip_to_next <- FALSE
  
  print(paste("Progress: Iteration", i, (i/(length(influencers_100)))*100, "%"))
  print(start - Sys.time())
  
  tryCatch(followers_influencers_100[[i]] <- rtweet::get_followers(influencers_100[i], n = Inf, retryonratelimit = TRUE, token = auth),
           error = function(e){
             if(grepl("Sorry, that page does not exist", e$message)){
               skip_to_next <<- TRUE}
           })
  
  
  if(skip_to_next){next}
  
  saveRDS(followers_influencers_100, file = "./RDS/followers_influencers_100.RDS")
  
}
end <-  Sys.time()



## Check which cases contain NULL ----
cases_null <- which(unlist(lapply(followers_influencers_100, is.null)))

## get their followers with academictwitteR package ----
followers_influencers_100_null_fixed <- get_user_followers(influencers_100[cases_null])
saveRDS(followers_influencers_100_null_fixed, file = "./RDS/followers_influencers_100_null_fixed.RDS")
# id of influencer is in columns from_id



# remaining influencers ----

Influencers <- read_csv("Influencers_20_80_IDs_ordered_by_influence_continued.csv", 
                        col_types = cols(id = col_character()))
influencers <- unlist(as.vector(Influencers[,1]))


# get followers
followers_influencers <- list()


start <- Sys.time()
for (i in 1:length(influencers)){
  
  skip_to_next <- FALSE
  
  print(paste("Progress: Iteration", i, (i/(length(influencers)))*100, "%"))
  print(start - Sys.time())
  
  tryCatch(followers_influencers[[i]] <- rtweet::get_followers(influencers[i], n = Inf, retryonratelimit = TRUE, token = auth),
           error = function(e){
             if(grepl("Sorry, that page does not exist", e$message)){
               skip_to_next <<- TRUE}
           })
  
  
  if(skip_to_next){next}
  
  #saveRDS(followers_influencers, file = "./RDS/followers_influencers.RDS")
  saveRDS(followers_influencers, file = "./RDS/followers_influencers_continued.RDS")
}
end <-  Sys.time()


