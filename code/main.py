# Social Influence in the Academic Twitter Migration to Mastodon: A
# Computational Psychology Approach

# This main script goes through and explains all steps of data collection,
# processing, and analysis. Helper modules are imported.

# Table of contents:
# 0. setup
# 1. initial data collection: researchers on twitter, open lists
# 2. initial processing
# 3. data collection: researchers on mastodon
# 4. main processing
# 5. analysis

# ====================================================================
# ====================================================================
# 0. setup
# ====================================================================
# ====================================================================

# path code directory
code_dir = "/home/lauer/projects/Mastodon/code"

# path config file
config_path = "/home/lauer/projects/Mastodon/config.yml"

# generic imports
import sys
import pandas as pd
import pytz
from tqdm import tqdm
from pandarallel import pandarallel
import numpy as np
from scipy.stats import pearsonr

# append code directory to path
sys.path.append(str(code_dir))

# specific package/module imports
import utils.utils as utils
import utils.checks as checks
import utils.data_loaders as data_loaders
import data_collection.list_known_minstances
import data_collection.webscrape_opencheck
import data_collection.collect_mprofiles
import data_collection.collect_mtimelines
import data_collection.collect_mtokens
import initial_processing.bind_json_tweets
import initial_processing.concat_json_rds_tweets
import initial_processing.extract_mhandles
import initial_processing.identify_tinfluencers
import initial_processing.stance_detection
import main_processing.clean_final_processed_data
import main_processing.construct_mtimelines_df
import main_processing.detect_open_science_endorsement
import main_processing.determine_strength_nsources
import main_processing.flag_return_to_twitter
import main_processing.get_followed_influencers
import main_processing.prepost_split_immediacy
import main_processing.tprofiles_add_twitter_timeline_info
import main_processing.tprofiles_add_mastodon_timeline_info
import main_processing.remove_some_tprofiles
import main_processing.determine_immediacy

# load config
cfg = utils.load_config(config_path)

# initialize pandarallel: patches pandas df to automatically include
# parallel_apply method (in main script as well as modules, without requiring
# additional imports).
pandarallel.initialize(progress_bar=True)

# ====================================================================
# ====================================================================
# 1. initial data collection: researchers on twitter, open lists
# ====================================================================
# ====================================================================

# twitter data collection was done in R, see
# data_collection -> XYZ.R

# webscrape opencheck lists where researchers openly share their twitter and
# mastodon account information
data_collection.webscrape_opencheck.webscrape_opencheck(cfg)

# also fetch known mastodon instances (later matched against mastodon handles
# extracted from twitter profiles, see extract_mhandles_from_tprofiles())
data_collection.list_known_minstances.list_known_minstances(cfg)

# ====================================================================
# ====================================================================
# 2. initial processing
# ====================================================================
# ====================================================================

# this section prepares the collected twitter data for further processing.

# conversion of R data to JSON for processing in python was done in R, see
# initial_processing -> aggregate_convert_RDS_to_JSON.R

# parts of the twitter timelines were collected as individual json files, which
# are bound together to a single file
initial_processing.bind_json_tweets.bind_json_tweets(cfg, return_data=False)

# the json files that were bound together are concatenated with additional
# timelines collected as a single RDS file (converted to json)
initial_processing.concat_json_rds_tweets.concat_json_rds_tweets(cfg)

# identify twitter influencers based on hashtag queries related to twitter
# migration, calculating influence score for each person
initial_processing.identify_tinfluencers.identify_tinfluencers(cfg)

# weighting influencers' influence scores based on manual evaluation to account
# for anti-migration influencers
initial_processing.stance_detection.manual_stance_detection(cfg)

# collection of influencer followers was done in R, see data_collection -> XYZ.R

# converting R data to JSON for processing in python was done in R, see
# initial_processing -> aggregate_convert_RDS_to_JSON2.R

# extract mastodon handles from twitter profiles, saving new df with handles
initial_processing.extract_mhandles.extract_mhandles_from_tprofiles(cfg)

# ====================================================================
# ====================================================================
# 3. data collection: researchers on mastodon
# ====================================================================
# ====================================================================

# now that we have extracted mastodon handles from twitter profiles,
# establishing a link between twitter and mastodon accounts of researchers, we
# can collect the mastodon data using the handles.

# collect mastodon tokens for multiple instances
data_collection.collect_mtokens(cfg)

# collect mastodon profiles
data_collection.collect_mprofiles(cfg)

# collect mastodon timelines for collected profiles
data_collection.collect_mtimelines(cfg)

# ====================================================================
# ====================================================================
# 4. main processing
# ====================================================================
# ====================================================================

# this large section brings together the prepared materials, performing the main
# processing needed for subsequent statistical/ML analysis. specifically, the
# twitter researcher profiles, already containing a lot of information, are used
# as a foundation that is enriched with various additional information (e.g. on
# twitter and mastodon post activity in our time period of interest, social
# impact, and open science endorsement). So in the end, we have a single
# dataframe that is subjected to the analysis, where each row is a person
# (researcher) that either migrated to mastodon or not (dependent variable
# column), and we will have independent variables/features stored in additional
# columns.

# ====================================================================
# time constants
# ====================================================================

# read datetime constants from config

# common timezone
common_timezone = pytz.timezone(cfg["constants"]["common_timezone"])

# start and end date for migration
start_date_nov = utils.parse_config_date(cfg["constants"]["start_date_nov"])
end_date_dec = utils.parse_config_date(cfg["constants"]["end_date_dec"])

# start and end date for identifying revitalized accounts (we check that
# there is no activity in this period)
start_date_revitalized_jan = utils.parse_config_date(
    cfg["constants"]["start_date_revitalized_jan"]
)

# start and end date for assessing return to twitter after migration
end_date_revitalized_oct = utils.parse_config_date(
    cfg["constants"]["end_date_revitalized_oct"]
)
start_date_apr = utils.parse_config_date(cfg["constants"]["start_date_apr"])
end_date_apr = utils.parse_config_date(cfg["constants"]["end_date_apr"])

# ====================================================================
# enrich twitter profiles with info from mastodon timeline
# ====================================================================

# we go through the twitter profiles: for people with mastodon handles, we load
# the collected timelines and extract relevant information (e.g., account
# creation data, activity etc.) and add it to the profiles

# load twitter profiles and unnest column public metrics which holds information
# on the covariates that we will use later.
profiles_researchers_df = data_loaders.load_unnest_tprofiles_main(cfg)

# new column with ALL relevant mastodon timeline information
path_timeline_folder = utils.get_path(cfg, "raw", "mastodon", "timelines", "")
profiles_researchers_df["mastodon_timeline_info"] = profiles_researchers_df[
    "handles_valid_known_combined"
].parallel_apply(
    lambda x: [
        main_processing.tprofiles_add_mastodon_timeline_info.get_m_timeline_info(
            handle,
            path_timeline_folder,
            start_date=start_date_nov,
            end_date=end_date_dec,
            common_timezone=common_timezone,
            start_date_revitalized=start_date_revitalized_jan,
            end_date_revitalized=end_date_revitalized_oct,
            start_date_return=start_date_apr,
            end_date_return=end_date_apr,
        )
        for handle in x
    ]
)

# new columns with SELECTED mastodon timeline information add mastodon activity
# nov/dec and start date for activity comparison with twitter timeline
profiles_researchers_df = (
    main_processing.tprofiles_add_mastodon_timeline_info.new_cols_from_info_col(
        profiles_researchers_df
    )
)

# ====================================================================
# load twitter timelines
# ====================================================================

twitter_timelines_df = data_loaders.load_ttimelines_main(cfg)

# ====================================================================
# remove some twitter profiles
# ====================================================================

# --------------------------------
# remove profiles with missing twitter timelines, but not influencers
# --------------------------------

# before carrying on, we remove twitter profiles for which no twitter timeline
# is found bc we don't know if the person was inactive or we somehow failed to
# get the data. Note, however, that we do not remove influencers without twitter
# timelines at this point, as we want them to be considered in the social impact
# calculation in their role as influencers. the fact that timelines are missing
# for these influencers only affects the immediacy calculation (which would then
# be based on the profile description only). thereafter, we will remove these
# influencers without timelines from the twitter profiles as well.
profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_tprofiles_missing_ttimeline(
        cfg, profiles_researchers_df, twitter_timelines_df
    )
)

# --------------------------------
# remove profiles with missing mastodon timelines, but not influencers
# --------------------------------

# we also need to remove profiles for which we could not scrape a Mastodon timeline
# as we cannot do a true comparison with twitter activity. A special case would
# be when someone has more than one Mastodon account and only a subset of the
# timelines is missing: if the activity of the remaining timelines is higher
# than the twitter activity, the person can be considered as migrated. but there
# was no one with more than one account AND at least one missing timeline. so we
# can safely remove everyone with at least one (ultimately exactly one) missing
# mastodon timeline. Again, we do not remove influencers without mastodon
# timelines at this point, as we want them to be considered in the social impact
# calculation.
# NOTE: after this removal step everyone should have at least one toot. in some
# additional processing, we later remove some toots (e.g., without text
# content), but there is no need to then remove people who may not have any
# toots anymore as we can be certain that we have all the data there is. For
# immediacy and open science endorsement, we can simply use the profile
# description.
profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_tprofiles_missing_mtimeline(
        profiles_researchers_df
    )
)

# --------------------------------
# remove profiles with mastodon bot accounts
# --------------------------------

profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_tprofiles_mbot_accounts(
        profiles_researchers_df
    )
)

# --------------------------------
# remove twitter profiles created after start date (only 2)
# --------------------------------

profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_tprofiles_created_after_startdate(
        profiles_researchers_df, start_date_nov, common_timezone
    )
)

# ====================================================================
# enrich twitter profiles with info from twitter timeline
# ====================================================================

# --------------------------------
# preprocess twitter timelines
# --------------------------------

# preprocess timelines, apply multiindexing and sorting for fast filtering
twitter_timelines_df = (
    main_processing.tprofiles_add_twitter_timeline_info.preprocess_ttimelines_main(
        profiles_researchers_df, twitter_timelines_df, common_timezone
    )
)

# --------------------------------
# get twitter activity > start date activity comparison
# --------------------------------


# NOTE: ideally move function to module tprofiles_add_twitter_timeline_info, but
# there the code was somehow way too slow (even when using a nested function
# that does NOT pass the large dfs to the apply function). Might be an issue
# with pandarallel.
def get_twitter_activity(id, end_date):
    """
    Calculate twitter activity for a person (id) from
    start_date_activity_comparison (mastodon account creation or revitalization
    date) to end date (default: Dec31st).

    Parameters:
    - id (str): The ID of the user.
    - end_date (datetime): The end date for activity counting.

    Returns:
    - activity_count (int): The count of tweets within the specified date range.
    Returns np.nan if the user does not have a Mastodon account.
    """

    start_date_activity_comparison = profiles_researchers_df[
        profiles_researchers_df["id"] == id
    ]["start_date_activity_comparison"].iloc[0]

    # early exit for people without mastodon account, bc we do not need to
    # analyze their twitter activity
    if pd.isna(start_date_activity_comparison):
        return np.nan

    activity_count = twitter_timelines_df.loc[
        (id, start_date_activity_comparison):(id, end_date)
    ].shape[0]

    return activity_count


# apply function for all ids in profiles, calculating their twitter activity
# since Mastodon account creation date
profiles_researchers_df["twitter_activity_since_activity_comp"] = (
    profiles_researchers_df["id"].parallel_apply(
        lambda x: get_twitter_activity(x, end_date_dec)
    )
)

# ====================================================================
# determine migration
# ====================================================================

# new column for migration based on activity comparison
# NOTE: False is default, occurring not only when there is equal activity, but
# also when there is no mastodon account (bc of np.nan for
# mastodon_activity_nov_dec and twitter_activity_since_activity_comp in this case).
# NOTE: why not mastodon activity since account creation instead of nov dec? bc
# there can not be any activity before account creation
profiles_researchers_df["is_migrated"] = (
    profiles_researchers_df["mastodon_activity_nov_dec"]
    > profiles_researchers_df["twitter_activity_since_activity_comp"]
)

# ====================================================================
# construct mastodon timelines df for immediacy calculation
# ====================================================================

# ----------------------------------
# construct timelines
# ----------------------------------

# similar to the twitter timelines with only original posts, we want to
# construct a tabular dataframe with mastodon timelines, consisting of ids of
# users, toots (text), and dates etc. based on both twitter and mastodon
# timelines, we later determine immediacy of users.

# extract timeline data for each mastodon handle, concat all dfs
timeline_dfs = []
for handle_list in tqdm(profiles_researchers_df["handles_valid_known_combined"]):
    for handle in handle_list:
        df = main_processing.construct_mtimelines_df.extract_mtimeline_data(
            handle, cfg, common_timezone, start_date_nov, end_date_dec
        )
        if not df.empty:  # only append non-empty DataFrames
            timeline_dfs.append(df)
mastodon_timelines_df = pd.concat(timeline_dfs, ignore_index=True)

# save mastodon timelines to disk for fast access
path_mastodon_timelines = utils.get_path(
    cfg, "processed", "mastodon", "setup", "timelines_combined.json"
)
mastodon_timelines_df.to_json(path_mastodon_timelines, orient="records", lines=True)

# load mastodon timelines from disk for fast access
path_mastodon_timelines = utils.get_path(
    cfg, "processed", "mastodon", "setup", "timelines_combined.json"
)
mastodon_timelines_df = pd.read_json(
    path_mastodon_timelines, orient="records", lines=True
)

# ----------------------------------
# preprocess timelines
# ----------------------------------

# preprocess timelines, adding reblog text to text column, removing html tags
mastodon_timelines_df = (
    main_processing.construct_mtimelines_df.preprocess_mtimelines_main(
        mastodon_timelines_df, common_timezone
    )
)
len(mastodon_timelines_df)

# ====================================================================
# for each researcher, get followed influencers
# ====================================================================

# prepare influencers followers df
influencer_followers_df = (
    main_processing.get_followed_influencers.prep_influencers_followers_df(cfg)
)
len(influencer_followers_df)
# construct df with researcher id and followed influencer ids
results = profiles_researchers_df["id"].parallel_apply(
    lambda x: main_processing.get_followed_influencers.get_followed_influencers_researcher(
        x, influencer_followers_df
    )
)
researchers_followed_influencers_df = pd.DataFrame(list(results))

# save df for fast access
path_researchers_followed_influencer_IDs = utils.get_path(
    cfg,
    "processed",
    "social_impact",
    "researchers_followed_influencer_IDs.json",
)
researchers_followed_influencers_df.to_json(
    path_researchers_followed_influencer_IDs, orient="records", lines=True
)

# load df for fast access
path_researchers_followed_influencer_IDs = utils.get_path(
    cfg,
    "processed",
    "social_impact",
    "researchers_followed_influencer_IDs.json",
)
researchers_followed_influencers_df = pd.read_json(
    path_researchers_followed_influencer_IDs,
    orient="records",
    lines=True,
    dtype={"researcher_id": str},
)

# sanity check: both researcher_id and followed_influencer_ids should be strings
utils.check_df_dtypes(
    researchers_followed_influencers_df, columns_to_check=["researcher_id"], error=True
)
if (
    not researchers_followed_influencers_df["followed_influencer_ids"]
    .apply(lambda x: all(isinstance(i, str) for i in x))
    .all()
):
    raise ValueError("Not all followed_influencer_ids are strings")

# merge with profiles_researchers_df, so that for each researcher we have the
# followed influencers
profiles_researchers_df = profiles_researchers_df.merge(
    researchers_followed_influencers_df,
    left_on="id",  # column name in profiles_researchers_df
    right_on="researcher_id",  # column name in researchers_followed_influencers_df
    how="left",
)

# ====================================================================
# pre-post split for immediacy calculation
# ====================================================================

# Goal: For each researcher, get relevant profile description and posts in order
# to determine similarity of research interests with followed influencers based
# on text. For each researcher, use Twitter posts from Nov 1st 2022 until
# Mastodon account creation date (if any) and then either Twitter or Mastodon
# posts based on which platform the user was more active on. Use Twitter or
# Mastodon profile description (based on migration) as the first post.

# preprocess timelines and profiles for pre-post split for immediacy
# calculation
twitter_timelines_nov_dec_df, mastodon_timelines_nov_dec_df, profiles_researchers_df = (
    main_processing.prepost_split_immediacy.prep_profiles_timelines(
        twitter_timelines_df,
        mastodon_timelines_df,
        profiles_researchers_df,
        start_date_nov,
        end_date_dec,
    )
)

# ----------------------------------
# perform pre-post split
# ----------------------------------

# get posts for each user based on pre post split. specifically, we use twitter
# activity from nov1st until mastodon account creation and then either twitter
# or mastodon based on which showed higher activity. this means:
# > migrated:     twitter from Nov 1st until mastodon account creation and then
#                 mastodon until dec 31st
# > not migrated: twitter from nov 1st until dec 31st
posts_pre_post_split = profiles_researchers_df[["id"]].copy()
result = posts_pre_post_split["id"].parallel_apply(
    lambda x: main_processing.prepost_split_immediacy.get_posts_pre_post_split(
        x,
        profiles_researchers_df,
        twitter_timelines_nov_dec_df,
        mastodon_timelines_nov_dec_df,
        start_date_nov,
        end_date_dec,
    )
)
posts_pre_post_split["twitter_username"] = result.apply(lambda x: x[0])
posts_pre_post_split["is_migrated"] = result.apply(lambda x: x[1])
posts_pre_post_split["description"] = result.apply(lambda x: x[2])
posts_pre_post_split["description_is_valid"] = result.apply(lambda x: x[3])
posts_pre_post_split["description_text_combined_all"] = result.apply(lambda x: x[4])
posts_pre_post_split["text_combined_original"] = result.apply(lambda x: x[5])

# clear working memory of no-longer-needed dfs
del (
    twitter_timelines_df,
    mastodon_timelines_df,
    twitter_timelines_nov_dec_df,
    mastodon_timelines_nov_dec_df,
    influencer_followers_df,
    results,
)

# ----------------------------------
# remove people from profiles and posts_pre_post_split who have no valid profile
# description and no posts
# ----------------------------------

# remove people from profiles who dont have valid profile description and no
# posts bc we cannot calculate immediacy for them and we cannot determine open
# science endorsement
len_before = len(profiles_researchers_df)
profiles_researchers_df = profiles_researchers_df[
    ~profiles_researchers_df.id.isin(
        posts_pre_post_split[
            posts_pre_post_split.description_text_combined_all.apply(
                lambda x: len(x) == 0
            )
        ].id
    )
].reset_index(drop=True)
print(
    f" {len_before - len(profiles_researchers_df)} people removed from profiles_researchers_df who have no valid profile description and no posts"
)

# remove people from posts_pre_post_split
len_before = len(posts_pre_post_split)
posts_pre_post_split = posts_pre_post_split[
    ~posts_pre_post_split.description_text_combined_all.apply(lambda x: len(x) == 0)
].reset_index(drop=True)
print(
    f" {len_before - len(posts_pre_post_split)} people removed from posts_pre_post_split who have no valid profile description and no posts"
)

# save profiles_researchers_df
path_profiles_researchers_df = utils.get_path(
    cfg,
    "processed",
    "social_impact",
    "profiles_researchers_combined_handles_updated_prepost.json",
)
profiles_researchers_df.to_json(
    path_profiles_researchers_df, orient="records", lines=True
)

# save posts_pre_post_split
path_posts_pre_post_split = utils.get_path(
    cfg, "processed", "social_impact", "posts_pre_post_split.json"
)
posts_pre_post_split.to_json(path_posts_pre_post_split, orient="records", lines=True)

# ====================================================================
# calculate immediacy for social impact
# ====================================================================

# ----------------------------------
# preparation
# ----------------------------------

# some postprocessing of posts df for immediacy calculation: removing posts
# without text and getting right format (exploding df -> one post per row)
posts_pre_post_split_exploded_list = (
    main_processing.determine_immediacy.prep_posts_prepost_split(cfg)
)

# precompute embeddings for all posts for fast lookup
main_processing.determine_immediacy.precompute_embeddings(
    cfg, posts_pre_post_split_exploded_list
)
del posts_pre_post_split_exploded_list  # clear memory

# identify posts that exceed cosine similarity of 0.5 with at least one research
# topic (from Open Alex list of research topics)
main_processing.determine_immediacy.prep_zeroshot_topic_modelling(cfg)

# remove posts that don't exceed the cosine similarity threshold
docs, docs_embeddings, zeroshot_topics_list = (
    main_processing.determine_immediacy.prep_BERTopic(cfg)
)

# run zero-shot BERTopic on the documents
topics, probs = main_processing.determine_immediacy.run_zeroshot_BERTopic(
    cfg, docs, docs_embeddings, zeroshot_topics_list
)

# get document-topic probabilities per person per post, and average them
# to obtain a single document-topic probability vector per person
main_processing.determine_immediacy.get_doc_topic_probs(cfg)

# ----------------------------------
# main immediacy calculation
# ----------------------------------

# load profiles
profiles_researchers_df = data_loaders.load_tprofiles_prepost_main(cfg)

# sanity check that followed influencer ids are strings before we use them for
# matching for immediacy calculation
checks.check_followed_influencers_dtype(cfg, profiles_researchers_df)

# load data with aggregated document-topic probabilities
posts_research_aggregated = data_loaders.load_posts_research_aggregated_probs_main(cfg)

# remove people from profiles_researchers_df who dont have any posts that passed
# the cosine similarity threshold. this is necessary bc we cannot calculate
# immediacy for people who have no content matched to at least one topic
# (i.e., it is required for comparison between users/influencers)
profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_tprofiles_without_topics_posts(
        profiles_researchers_df, posts_research_aggregated
    )
)
len(profiles_researchers_df)  # 260121 researchers remain
profiles_researchers_df.is_influencer.value_counts()  # 11071 influencers remain

# transfer probs to profiles_researchers_df
profiles_researchers_df = profiles_researchers_df.merge(
    posts_research_aggregated[["id", "average_probs"]],
    on="id",
    how="left",
)
del posts_research_aggregated  # clear memory

# remove followed influencers IDs of influencers that are not contained in the
# profiles df anymore
id_set = set(profiles_researchers_df["id"])
profiles_researchers_df["followed_influencer_ids_remaining"] = (
    profiles_researchers_df.followed_influencer_ids.apply(
        lambda x: [elem for elem in x if elem in id_set]
    )
)


# NOTE: Ideally move to calculate_immediacy.py module, but there is some problem
# with parrallel apply when running it from there, possibly bc of nested
# df.iterrrows
def calculate_immediacy(row):
    """
    Calculate immediacy (i.e., similarity of interests) of a user and the
    followed influencers. Specifically, calculate mean correlation of (mean)
    document-topic probabilities (i.e., across all posts) of the user with
    probabilities of followed influencers.

    Returns:
        correlations_probs_user_influencers_mean: researcher's immediacy with
        followed influencers
    """
    followed_influencers_IDs = row["followed_influencer_ids_remaining"]

    # if no followed influencers, return nan
    if not followed_influencers_IDs:
        return np.nan

    # subset of df with only followed influencers
    filtered_df = profiles_researchers_df[
        profiles_researchers_df["id"].isin(followed_influencers_IDs)
    ]

    # for each followed influencer, correlate the user's average probs with the
    # influencer's average probs
    correlations_probs_user_influencers = []
    for index, row_filt in filtered_df.iterrows():
        correlation, _ = pearsonr(row["average_probs"], row_filt["average_probs"])
        if not np.isnan(correlation):  # exclude cases of zero variance (0 cases)
            correlations_probs_user_influencers.append(correlation)

    # if no correlations, return nan (should only occur if all correlations were
    # based on zero variance, so empty list) (0 cases)
    if not correlations_probs_user_influencers:
        return np.nan

    # calculate the mean of the correlations
    correlations_probs_user_influencers_mean = np.mean(
        correlations_probs_user_influencers
    )

    return correlations_probs_user_influencers_mean


# calculate mean immediacy for each person with their followed influencers
profiles_researchers_df["SI_I"] = profiles_researchers_df.parallel_apply(
    calculate_immediacy, axis=1
)

# NOTE: all people with nan SI_I have no followed influencers remaining, there
# are no people excluded due to zero variance
profiles_researchers_df["SI_I"].isnull().value_counts()
profiles_researchers_df["followed_influencer_ids_remaining"].apply(
    lambda x: len(x) == 0
).value_counts()

# ====================================================================
# calculate strength and number of sources for social impact
# ====================================================================

# calculate mean stength and number of sources for each researcher based on
# the followed influencers.
profiles_researchers_df = (
    main_processing.determine_strength_nsources.calculate_strength_nsources(
        cfg, profiles_researchers_df
    )
)

# ====================================================================
# final social impact score
# ====================================================================

# ----------------------------------
# abs for strength
# ----------------------------------

# for strength, we take the absolute values and consider the sign
# (anti-migration influencers) only after min-max scaling, so that 0 strength
# stays 0.

# store original signs before taking absolute values
profiles_researchers_df["SI_S_sign"] = profiles_researchers_df["SI_S"].apply(
    lambda x: -1 if x < 0 else 1
)

# take absolute values
profiles_researchers_df["SI_S_abs"] = profiles_researchers_df["SI_S"].abs()

# ----------------------------------
# min-max scale strength, number of sources, and immediacy
# ----------------------------------

# we min-max scale the components to get the same range for each component

# min-max scale strength
profiles_researchers_df["SI_S_abs_minmax"] = utils.min_max_scale_column(
    profiles_researchers_df, "SI_S_abs"
)

# min-max scale number of sources
profiles_researchers_df["SI_N_minmax"] = utils.min_max_scale_column(
    profiles_researchers_df, "SI_N"
)

# min-max scale immediacy
profiles_researchers_df["SI_I_minmax"] = utils.min_max_scale_column(
    profiles_researchers_df, "SI_I"
)

# ----------------------------------
# sign for strength (anti-migration influencers)
# ----------------------------------

# now, after min-max scaling, we consider the sign of the strength, so that
# anti-migration influencers (manually identified) have a negative strength

# apply the original sign to the scaled strength values
profiles_researchers_df["SI_S_abs_minmax_sign"] = (
    profiles_researchers_df["SI_S_abs_minmax"] * profiles_researchers_df["SI_S_sign"]
)

# NOTE: for immediacy, we do not consider the sign as conceptually it does not
# make sense for interest in different topics to result in a final negative
# social impact score when calculating the product of the components.

# ----------------------------------
# assign 0 for people with nan strength, number of sources, immediacy
# ----------------------------------

# people who don't have any followed influencers (nan for strength, immediacy, n
# sources) now get a 0 for strength, immediacy and number of sources. the final
# social impact score is the product of the three componts and will always with
# 0 if there are no followed influencers.
# NOTE: this is done after the min-max scaling bc if we later look at the social
# impact components individually, the 0 values for strength and immediacy should
# reflect true 0 value and not something else.
print(
    f'imputing {profiles_researchers_df["SI_S_abs_minmax_sign"].isnull().sum()} nan values out of {len(profiles_researchers_df)} people with 0'
)
profiles_researchers_df.loc[
    profiles_researchers_df["SI_S_abs_minmax_sign"].isnull(), "SI_S_abs_minmax_sign"
] = 0
profiles_researchers_df.loc[
    profiles_researchers_df["SI_N_minmax"].isnull(), "SI_N_minmax"
] = 0
profiles_researchers_df.loc[
    profiles_researchers_df["SI_I_minmax"].isnull(), "SI_I_minmax"
] = 0

# ----------------------------------
# remove influencers without twitter timelines from profiles
# ----------------------------------

# now that the social impact calculation is completed for each researcher, we
# can safely remove the influencers without twitter timelines and/or without
# mastodon timelines from the twitter profiles. for more details, see section
# "remove profiles with missing twitter timelines". In essence, for these
# people, we do not know the true activity, so they cannot be used for the
# dependent variable (migration). They can only be used in their role as
# influenceres for social impact calculation. So the zero activity they have at
# the moment cannot be "trusted".
# NOTE: after the prepostsplit, we have already removed people without valid
# profile description AND without posts, but here we also remove people WITH
# profile description but without posts.
profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_influencers_without_ttimelines(
        profiles_researchers_df
    )
)
profiles_researchers_df = (
    main_processing.remove_some_tprofiles.remove_influencers_without_mtimelines(
        profiles_researchers_df
    )
)

# ----------------------------------
# calculate final social impact score
# ----------------------------------

# calculate social impact as product of the three processed components
profiles_researchers_df["social_impact"] = (
    profiles_researchers_df["SI_S_abs_minmax_sign"]
    * profiles_researchers_df["SI_N_minmax"]
    * profiles_researchers_df["SI_I_minmax"]
)

# save profiles_researchers_df
path_profiles_researchers_df = utils.get_path(
    cfg,
    "processed",
    "social_impact",
    "profiles_researchers_combined_handles_updated_prepost_si.json",
)
profiles_researchers_df.to_json(
    path_profiles_researchers_df, orient="records", lines=True
)
len(profiles_researchers_df)
# ====================================================================
# determine open science endorsement
# ====================================================================

# load profiles from previous step (fast access)
profiles_researchers_df = data_loaders.load_tprofiles_prepost_si_main(cfg)

# flag open science endorsement based on pattern matching of open science terms
# in profile description
profiles_researchers_df = (
    main_processing.detect_open_science_endorsement.flag_open_science_endorsement(
        cfg, profiles_researchers_df
    )
)

# ====================================================================
# detect persons who returned to twitter by April 2023
# ====================================================================

# flag who among migrating researchers returned to twitter by April 2023
profiles_researchers_df = main_processing.flag_return_to_twitter.flag_return_to_twitter(
    cfg,
    profiles_researchers_df,
    start_date_apr,
    end_date_apr,
    common_timezone,
)

# ====================================================================
# save data for statistical analysis
# ====================================================================

# some final cleaning of the profiles researchers df: renaming columns,
# retaining only relevant variables
profiles_researchers_df = (
    main_processing.clean_final_processed_data.clean_final_processed_data(
        cfg, profiles_researchers_df, start_date_nov, common_timezone
    )
)

# save profiles researchers df for statistical analysis
path_profiles_processed = utils.get_path(
    cfg,
    "processed",
    "final_processed",
    "final_processed_data.json",
)
profiles_researchers_df.to_json(path_profiles_processed, orient="records", lines=True)

# ====================================================================
# ====================================================================
# 5. analysis
# ====================================================================
# ====================================================================

# the statistical/ML analysis was done in R, see
# statistical_analysis -> analysis.R
