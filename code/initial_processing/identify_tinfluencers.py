import re
import csv
import numpy as np
import pandas as pd

from utils.data_loaders import (
    load_hashtags_df,
    load_tprofiles_check_initial,
    load_top100_eval_merged_evaluated,
    load_top100_eval_merged_evaluated_v2,
    load_influencer_tprofiles_intial_check,
    load_influencer_followers_initial,
)

from utils.utils import (
    get_path,
    unnest_column,
)

from utils.nlp_utils import remove_handles_and_urls


# TODO: refactoring
def identify_tinfluencers(cfg):
    """
    This function identifies academic influencers on Twitter who post about the
    migration to Mastodon.

    1. Preprocessing Hashtag Queries
    2. Preprocessing Researcher Profiles
    3. Identifying Topic-based Influencers
    4. Saving and Evaluating Data

    Saving cleaned datasets of influencer tweets and profiles with influence
    scores, and IDs of influencers for scraping their followers.

    Parameters:
    cfg (object): Configuration object with paths and settings for loading
                  and saving data.

    Returns:
    None
    """

    # ==================================
    # 1. Preprocessing hashtag queries
    # ==================================

    # ----------------------------------
    # read combined hashtag queries
    # ----------------------------------

    hashtags_df = load_hashtags_df(cfg)

    # ----------------------------------
    # unpack nested columns
    # ----------------------------------

    # apply function for unnesting columns
    nested_columns = ["public_metrics", "entities"]  # 'referenced_tweets'
    unnested_columns = pd.concat(
        [unnest_column(hashtags_df, col) for col in nested_columns], axis=1
    )
    if not hashtags_df.index.is_unique:  # sanity check: index uniqueness before joining
        raise ValueError("The DataFrame index is not unique")
    # hashtags_df = hashtags_df.drop(columns=nested_columns).join(unnested_columns)
    hashtags_df = hashtags_df.join(unnested_columns)  # retain original columns for comp

    # new column: IDs of mentioned users
    hashtags_df["entities.mentions_id"] = hashtags_df["entities.mentions"].apply(
        lambda x: [userid["id"] for userid in x] if isinstance(x, list) else []
    )

    # sanity check: all IDs in mentions are strings
    for index, row in hashtags_df.iterrows():
        if len(row["entities.mentions_id"]) > 0:
            if not all(isinstance(item, str) for item in row["entities.mentions_id"]):
                raise TypeError("IDs in mentions are not strings")

    # new column: original tweets based on wheter referenced_tweets is empty or not
    hashtags_df["is_original_tweet"] = (hashtags_df["referenced_tweets"] == {}).astype(
        int
    )

    # ----------------------------------
    # drop tweets that are not from researchers
    # ----------------------------------

    # load profiles researchers with IDs of researchers
    profiles_researchers_df = load_tprofiles_check_initial(cfg)

    # drop tweets that are not from researchers based on their id
    hashtags_df = hashtags_df[
        hashtags_df["author_id"].isin(profiles_researchers_df["id"])
    ]

    # drop duplicate tweets
    hashtags_df = hashtags_df.drop_duplicates(
        subset=["conversation_id", "author_id", "text", "id"], ignore_index=True
    )

    # drop all non-original tweets (retweets etc.)
    # this is important because otherwise mention count is calculated on all tweets
    hashtags_df = hashtags_df[hashtags_df["is_original_tweet"] == 1]

    # drop original tweets that start with "RT @": some "original"
    # tweets returned by the API are actually retweets (with Mastodon account
    # handles, likely cross-postings) that we want to remove
    hashtags_df = hashtags_df[~(hashtags_df["text"].str.contains("RT @"))]

    # ----------------------------------
    # Drop tweets that do not contain keyword patterns
    # ----------------------------------

    # new column with cleaned tweet text (without account handles/URLs)
    hashtags_df["text_clean"] = hashtags_df["text"].apply(remove_handles_and_urls)

    # keywords to pattern-match in text of tweets, see config
    keywords_to_check = cfg["patterns"]["influencer_identification"][
        "keywords_to_check"
    ]

    # define pattern using word boundaries
    pattern = re.compile(r"\b(" + "|".join(keywords_to_check) + r")\b", re.IGNORECASE)

    # remove tweets that do not contain the pattern
    hashtags_df = hashtags_df[hashtags_df["text_clean"].str.contains(pattern)]
    # (Warning can be ignored as we are only interested in checking whether the
    # pattern exists in the text and not in extracting the matched groups)

    # print number of tweets
    print(
        "Number of original tweets with keywords by researchers:",
        len(hashtags_df),
    )

    # reset index
    hashtags_df.reset_index(drop=True, inplace=True)  # EDIT

    # ======================================
    # 2. Preprocessing profiles researchers
    # ======================================

    # The idea is that we take the profiles researchers dataframe and remove
    # irrelevant information (duplicates, researchers who don't have any original
    # tweet in the hashtags_df) so that we can then append the relevant tweet local,
    # topic-specific metrics from our hashtags_df (number of retweets, likes etc.)
    # related to TwitterMigration for each researcher - next to the important global
    # information (e.g., followers and listed count) that is already contained in
    # the profiles.

    # ----------------------------------
    # unnest columns, drop duplicates
    # ----------------------------------

    nested_columns = ["public_metrics"]  # removed entities
    unnested_columns = pd.concat(
        [unnest_column(profiles_researchers_df, col) for col in nested_columns], axis=1
    )
    if (
        not profiles_researchers_df.index.is_unique
    ):  # sanity check: index uniqueness before joining
        raise ValueError("The DataFrame index is not unique")
    profiles_researchers_df = profiles_researchers_df.join(
        unnested_columns
    )  # retain original columns for comp

    # drop rows with duplicate ids in profiles_researchers_df
    profiles_researchers_df.drop_duplicates(
        subset=["id"], inplace=True, ignore_index=True
    )

    # ----------------------------------
    # Retain researchers with >0 original tweets
    # ----------------------------------

    # drop rows (researchers) without original tweet(s) in hashtags_df (note,
    # hashtags_df only contains original tweets at this point, so no further
    # filtering necessary)
    profiles_researchers_df = profiles_researchers_df[
        profiles_researchers_df["id"].isin(hashtags_df["author_id"])
    ]

    # EDIT: reset index. by default, when using to.json, the index is omitted
    # (resulting in a new index when reading data back in), but we need it to be
    # ranging from 0 to end to align with profiles read from disk for a later check.
    profiles_researchers_df.reset_index(drop=True, inplace=True)

    # print length of profiles_researchers_orig_df
    print(
        "length of profiles_researchers_orig_df:",
        len(profiles_researchers_df),
        "(--> Number of researchers with at least one original tweet)",
    )

    # ======================================
    # 3. Identify topic-based influencers
    # ======================================

    # ----------------------------------
    # Calculate local metrics
    # ----------------------------------

    # Defining functions to calculate local metrics for a given author_id using the
    # sum appraoch (based on all original tweets by the person in hashtags_df).
    def count_retweets(author_id):
        """Counting retweets of a given author_id"""
        return (
            hashtags_df[hashtags_df["author_id"] == author_id][
                "public_metrics.retweet_count"
            ]
            .sum()
            .astype(int)
        )

    def count_likes(author_id):
        """Counting likes of a given author_id"""
        return (
            hashtags_df[hashtags_df["author_id"] == author_id][
                "public_metrics.like_count"
            ]
            .sum()
            .astype(int)
        )

    def count_impressions(author_id):
        """Counting impressions of a given author_id"""
        return (
            hashtags_df[hashtags_df["author_id"] == author_id][
                "public_metrics.impression_count"
            ]
            .sum()
            .astype(int)
        )

    def count_tweets(author_id):
        """Counting original tweets of a given author_id"""
        return len(hashtags_df[hashtags_df["author_id"] == author_id])

    def count_mentions(author_id):
        """Counting mentions of a given author id"""
        return sum(hashtags_df["entities.mentions_id"].apply(lambda x: author_id in x))

    # apply functions for calculating local metrics for each author_id in
    # profiles_researchers_df, add new columns to the df
    profiles_researchers_df["retweet_count"] = profiles_researchers_df["id"].apply(
        count_retweets
    )
    profiles_researchers_df["like_count"] = profiles_researchers_df["id"].apply(
        count_likes
    )
    profiles_researchers_df["impression_count"] = profiles_researchers_df["id"].apply(
        count_impressions
    )
    profiles_researchers_df["tweet_count"] = profiles_researchers_df["id"].apply(
        count_tweets
    )
    profiles_researchers_df["mention_count"] = profiles_researchers_df["id"].apply(
        count_mentions
    )

    # ----------------------------------
    # Calculate influence score for each researcher: 20% global, 80% local
    # ----------------------------------

    profiles_researchers_df["influence_score_20-80"] = (
        (
            0.1
            * profiles_researchers_df["public_metrics.followers_count"]
            / profiles_researchers_df["public_metrics.followers_count"].max()
        )
        + (
            0.1
            * profiles_researchers_df["public_metrics.listed_count"]
            / profiles_researchers_df["public_metrics.listed_count"].max()
        )
        + (
            (0.8 / 3)
            * profiles_researchers_df["retweet_count"]
            / profiles_researchers_df["retweet_count"].max()
        )
        + (
            (0.8 / 3)
            * profiles_researchers_df["like_count"]
            / profiles_researchers_df["like_count"].max()
        )
        + (
            (0.8 / 3)
            * profiles_researchers_df["mention_count"]
            / profiles_researchers_df["mention_count"].max()
        )
    )

    # ======================================
    # 4. Save data
    # ======================================

    # We need to save the data for manual evaluation to verify that they are 1.
    # researchers (based on profile description and web search) and 2. influencers
    # (based on top ten most influential tweets that we extract below).
    # NOTE: In a previous version of the script, we already saved data and evaluated
    # it, but we updated the code wrt mentions, resulting in four new people among
    # the top 100 influencers that have not been manually evaluated yet. therefore,
    # extracting the top 10 tweets of all influencers again below, and appending the
    # old evaluations for the overlapping people along with new evaluations for the
    # missing four people.

    # sort data by influence score
    profiles_researchers_df = profiles_researchers_df.sort_values(
        by="influence_score_20-80", ascending=False
    )

    # sanity check that influence score does not contain any NaNs (bc of the
    # bug in mentioned IDs being converted to int and not being matchable before)
    if profiles_researchers_df["influence_score_20-80"].isnull().sum() > 0:
        raise ValueError("Influence score contains NaNs")

    # Load old top100 data that was already evaluated
    # NOTE: instead of loading Top100_influencers_manual_eval_new_evaluated.csv as
    # before, using Top100_influencers_manual_eval_new_evaluated_gs, which is the
    # latest google sheet version where we added some new columns coding if an
    # influencer is against or not against migration.
    top100_eval_merged_evaluated = load_top100_eval_merged_evaluated(cfg)

    # new top100 data with new string IDs
    top100_eval_final = profiles_researchers_df[
        ["id", "name", "username", "description"]
    ].head(100)

    # Merge old top 100 into new top 100 based on username column
    top100_eval_merged = top100_eval_final.merge(
        top100_eval_merged_evaluated, how="left", on="username", suffixes=("", "_old")
    )

    # # drop old columns that are not needed anymore
    # columns_to_drop = [col for col in top100_eval_merged.columns if col.endswith("_old")]
    # top100_eval_merged = top100_eval_merged.drop(columns=columns_to_drop)

    # # rename columns
    # top100_eval_merged.rename(columns={"is_researcher": "is_researcher_old"}, inplace=True)
    # top100_eval_merged.rename(columns={"notes": "notes_old"}, inplace=True)
    top100_eval_merged.rename(
        columns={"top10_tweets": "top10_tweets_old"}, inplace=True
    )

    # # new columns for new validation
    # top100_eval_merged["is_researcher_new"] = np.nan
    # top100_eval_merged["notes_new"] = np.nan
    # top100_eval_merged["is_influencer"] = np.nan
    top100_eval_merged = top100_eval_merged.drop(
        columns=["id_old", "name_old", "description_old"]
    )

    # add mention count to hashtags_df
    hashtags_df["mention_count"] = hashtags_df["author_id"].apply(
        lambda x: count_mentions(x)
    )

    # Calculate influence score for each tweet
    hashtags_df["tweet_influence_score"] = (
        (1 / 3)
        * hashtags_df["public_metrics.retweet_count"]
        / np.where(
            hashtags_df.groupby("author_id")["public_metrics.retweet_count"].transform(
                "max"
            )
            == 0,  # if max is 0, transform to 1 to not divide by 0 (result will be the same as we divide 0/1 = 0)
            1,
            hashtags_df.groupby("author_id")["public_metrics.retweet_count"].transform(
                "max"
            ),
        )
        + (1 / 3)
        * hashtags_df["public_metrics.like_count"]
        / np.where(
            hashtags_df.groupby("author_id")["public_metrics.like_count"].transform(
                "max"
            )
            == 0,
            1,
            hashtags_df.groupby("author_id")["public_metrics.like_count"].transform(
                "max"
            ),
        )
        + (1 / 3)
        * hashtags_df["mention_count"]
        / np.where(
            hashtags_df.groupby("author_id")["mention_count"].transform("max") == 0,
            1,
            hashtags_df.groupby("author_id")["mention_count"].transform("max"),
        )
    )

    # filter hashtags_df to only have rows that match users in top100_eval_merged
    filtered_hashtags_df = hashtags_df[
        hashtags_df["author_id"].isin(top100_eval_merged["id"])
    ]

    # group by author_id and get the top 10 most influential tweets for each user
    top_tweets = (
        filtered_hashtags_df.groupby("author_id")
        .apply(lambda x: x.nlargest(10, "tweet_influence_score")["text_clean"].tolist())
        .reset_index(name="top10_tweets")
    )

    # merge the results with top100_eval_merged to add the top10_tweets column
    top100_eval_merged = top100_eval_merged.merge(
        top_tweets, left_on="id", right_on="author_id", how="left"
    )
    top100_eval_merged = top100_eval_merged.drop(
        columns="author_id"
    )  # Drop the extra column after merging

    # replace newlines in text with spaces so saving as csv works well
    top100_eval_merged["top10_tweets"] = top100_eval_merged["top10_tweets"].apply(
        lambda x: [tweet.replace("\n", " ") for tweet in x]
    )
    top100_eval_merged["description"] = top100_eval_merged["description"].apply(
        lambda x: x.replace("\n", " ")
    )

    # transform each list in top10_tweets to a list of sublists for better
    # readability
    top100_eval_merged.top10_tweets = top100_eval_merged.top10_tweets.apply(
        lambda x: [[x] for x in x]
    )

    # the new top 10 tweets (after correcting the bug in mentions) are identical to
    # the old ones for 95 people. for 5 people, there is a difference that we will
    # have a look at. 4 people are new and have empty top 10 tweets column. only 1
    # old person has a difference in the top10 tweets.
    top100_eval_merged.top10_tweets.astype(
        str
    ) == top100_eval_merged.top10_tweets_old.astype(str)

    # save as csv
    path_top100_eval_merged = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "Top100_influencers_manual_eval_new_v2.csv",
    )
    # top100_eval_merged.to_csv(
    #     path_top100_eval_merged,
    #     header=True,
    #     index=False,
    # )
    top100_eval_merged.to_csv(
        path_top100_eval_merged, header=True, index=False, quoting=csv.QUOTE_NONNUMERIC
    )

    # ----------------------------------
    # use manual eval to filter influencer profiles
    # ----------------------------------

    # reading the new csv containing final info on against/not against migration
    top100_eval_merged_evaluated_df = load_top100_eval_merged_evaluated_v2(cfg)

    # sanity check: all usernames of top 100 eval are found in the profiles
    if not top100_eval_merged_evaluated_df.username.isin(
        profiles_researchers_df.username
    ).all():
        raise ValueError("Not all usernames are found in the profiles")

    # sanity check: no duplicates in the usernames of profiles and top 100
    if (
        profiles_researchers_df.username.duplicated().sum()
        > 0 | top100_eval_merged_evaluated_df.username.duplicated().sum()
        > 0
    ):
        raise ValueError("There are duplicates in the usernames")

    # retain only non-researchers and non-influencers in top 100 evaluation df
    top100_eval_merged_evaluated_df = top100_eval_merged_evaluated_df[
        (top100_eval_merged_evaluated_df["is_researcher_new"] == 0)
        | (top100_eval_merged_evaluated_df["is_influencer"] == 0)
    ]

    # remove people from profiles_researchers who are not researchers or influencers
    print(
        "length of profiles_researchers_df BEFORE removing non-researchers/influencers:",
        len(profiles_researchers_df),
    )
    profiles_researchers_df = profiles_researchers_df[
        ~profiles_researchers_df["username"].isin(
            top100_eval_merged_evaluated_df["username"]
        )
    ]
    print(
        "length of profiles_researchers_df AFTER removing non-researchers/influencers:",
        len(profiles_researchers_df),
    )

    # reset index to compare with old data (whose index was automatically reset when
    # saving to disk)
    profiles_researchers_df.reset_index(drop=True, inplace=True)

    # sanity check: new filtered profiles after EDIT identical to old one? Yes, all
    # usernames of one are contained in the other and vice versa, but the dfs are
    # not fully matching as the influence scores were re-calculated after correcting
    # for a bug in mention count calculation.
    profiles_influencers_df_old = load_influencer_tprofiles_intial_check(cfg)
    if (
        not profiles_researchers_df.username.isin(
            profiles_influencers_df_old.username
        ).all()
        & profiles_influencers_df_old.username.isin(
            profiles_researchers_df.username
        ).all()
    ):
        raise ValueError("Not all usernames are found in the profiles")

    # ==================================
    # save processed data
    # ==================================

    # ----------------------------------
    # save hashtag queries
    # ----------------------------------

    # save all original twitter migration posts by the academic influencers so that
    # we can perform a sentiment analysis on them (e.g., is someone calling to or
    # against migration, is speaking neutrally)
    path_hashtag_queries_v2 = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "influencer_migrationtweets_v2.json",
    )

    # save to file
    hashtags_df.to_json(path_hashtag_queries_v2, orient="records", lines=True)

    # ----------------------------------
    # save influencer profiles
    # ----------------------------------

    # finally, we need to save all influencer profiles (that are truly
    # influencers/researchers based on the manual eval) with their influence scores
    path_profiles_researchers_v2 = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "influencer_profiles_v2.json",
    )
    profiles_researchers_df.to_json(
        path_profiles_researchers_v2, orient="records", lines=True
    )

    # ==================================
    # determine missing IDs for another round of follower scraping
    # ==================================

    # having exectuted the main part of the script with the new updated
    # profiles_researchers_df, we can now see how many of the influencers IDs are
    # found in the already collected influencers (followers). for the missing ones,
    # we can do another round of scraping.

    # load influencer followers already collected, using correct dtype for IDs
    influencer_followers_df = load_influencer_followers_initial(cfg)

    # how many IDs in the new processed profiles are found in the already collected
    # influencers?
    profiles_researchers_df.id.isin(influencer_followers_df["to_id"]).value_counts()

    # get IDs that are not found
    missing_IDs = profiles_researchers_df[
        ~profiles_researchers_df.id.isin(influencer_followers_df["to_id"])
    ]["id"]

    # save missing IDs as strings
    path_missing_IDs = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "Influencers_IDs_missing.csv",
    )
    missing_IDs.to_csv(
        path_missing_IDs, header=True, index=False, quoting=csv.QUOTE_NONNUMERIC
    )
