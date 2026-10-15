from utils.utils import (
    get_path,
    check_json_format,
    check_json_dtypes,
    check_df_dtypes,
    unnest_column,
)

import pandas as pd
from tqdm import tqdm
import json
import numpy as np


def load_hashtags_df(cfg):
    """
    Load all posts with hashtags related to twitter migration chunk by chunk,
    returning a pandas DataFrame. Performing sanity checks for correct dtypes.
    """

    path_data_hashtags = get_path(
        cfg, "processed", "twitter", "setup", "hashtag_queries_combined.json"
    )

    # sanity check: json format
    check_json_format(path_data_hashtags)

    # sanity check: IDs should be strings
    check_json_dtypes(path_data_hashtags)

    # use iterator to load data combined hashtag queries chunk by chunk
    hashtags_df = pd.DataFrame()
    for chunk in tqdm(
        pd.read_json(
            path_data_hashtags,
            orient="records",
            lines=True,
            chunksize=100000,
            dtype={"author_id": str, "conversation_id": str, "id": str},
        )
    ):
        hashtags_df = pd.concat([hashtags_df, chunk], ignore_index=True)

    # drop columns that are not needed
    hashtags_df.drop(
        columns=[
            "geo",
            "withheld",
            "attachments",
            "possibly_sensitive",
            "edit_history_tweet_ids",
        ],
        inplace=True,
    )

    # sanity check: all IDs in df are strings
    check_df_dtypes(
        hashtags_df, columns_to_check=["author_id", "conversation_id", "id"]
    )

    return hashtags_df


def load_top100_eval_merged_evaluated(cfg):
    """
    Load the top 100 influencers with manual evaluation as to whether they are
    indeed researchers/influencers. Note that this is the first (old) version,
    which we add some missing people to.
    """

    path_top100_eval_merged_evaluated = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "Top100_influencers_manual_eval_new_evaluated_gs.csv",
    )
    top100_eval_merged_evaluated = pd.read_csv(path_top100_eval_merged_evaluated)

    return top100_eval_merged_evaluated


def load_top100_eval_merged_evaluated_v2(cfg):
    """
    Load the top 100 influencers with manual evaluation as to whether they are
    indeed researchers/influencers. Note that this is the updated version.
    """

    # load evaluation df
    path_top100_eval_merged_evaluated_v2 = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        # "Top100_influencers_manual_eval_new_evaluated.csv",
        "Top100_influencers_manual_eval_new_v2_evaluated.csv",
    )
    top100_eval_merged_evaluated_df_v2 = pd.read_csv(
        path_top100_eval_merged_evaluated_v2
    )

    return top100_eval_merged_evaluated_df_v2


def load_influencer_tprofiles_intial_check(cfg):
    """
    Load old version of influencer profiles for comparison with new updated
    version for influencer identification. NOTE: dtype not correct here.
    """

    path_influencer_profiles = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "influencer_profiles.json",
    )
    profiles_influencers_df_old = pd.read_json(
        path_influencer_profiles, orient="records", lines=True
    )

    return profiles_influencers_df_old


def load_tprofiles_initial(cfg):
    """
    Load twitter profiles for initial processing (e.g. extracting mastodon handles).
    NOTE: By mistake, the user IDs are not specified as strings; this is handled
    later, see load_tprofiles_main.
    """
    # read profiles researchers data
    path_profiles_researchers = get_path(
        cfg, "processed", "twitter", "setup", "profiles_researchers_combined.json"
    )
    profiles_researchers_df = pd.read_json(
        path_profiles_researchers, orient="records", lines=True
    )

    return profiles_researchers_df


def load_tprofiles_check_initial(cfg):
    """
    Load twitter profiles with correctly specified dtypes. Used for check in
    extracting mastodon handles. Also used for influencer identification
    function after correction of misspecified dtype.
    """
    # read profiles researchers data
    path_profiles_researchers = get_path(
        cfg, "processed", "twitter", "setup", "profiles_researchers_combined.json"
    )

    # sanity check: json format
    check_json_format(path_profiles_researchers)

    # sanity check: IDs should be strings
    check_json_dtypes(path_profiles_researchers)

    profiles_researchers_df_check = pd.read_json(
        path_profiles_researchers, orient="records", lines=True, dtype={"id": str}
    )

    # sanity check: all IDs in df are strings
    check_df_dtypes(profiles_researchers_df_check, columns_to_check=["id"])

    return profiles_researchers_df_check


def load_influencer_profiles_v2_initial(cfg):
    """
    Load final processed influencer profiles with correctly specified dtypes for
    manual stance detection.
    """
    # load influencer profiles
    path_influencer_profiles = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        "influencer_profiles_v2.json",
    )
    influencer_profiles_df = pd.read_json(
        path_influencer_profiles, orient="records", lines=True, dtype={"id": str}
    )

    return influencer_profiles_df


def load_opencheck_initial(cfg):
    """
    Load OpenCheck list where people openly shared their mastodon handles and
    dicisplines.
    """
    path_OpenCheck = get_path(
        cfg, "raw", "open_datasets", "opencheck", "All_disciplines.csv"
    )
    OpenCheck_df = pd.read_csv(path_OpenCheck)

    return OpenCheck_df


def load_academics_on_mastodon_initial(cfg):
    """
    Load Academics on Mastodon list where people openly shared their mastodon
    handles and disciplines.
    """

    path_Academics = get_path(
        cfg,
        "raw",
        "open_datasets",
        "academics_on_mastodon",
        "Academics_on_Mastodon.CSV",
    )
    Academics_df = pd.read_csv(
        path_Academics,
        sep=";",
        encoding="cp1252",
    )

    return Academics_df


def load_minstances_ranking(cfg):
    """
    Load Mastodon instances ranking with manual evaluation of TOS (is it allowed
    to collect data?) and account credentials that are later used to
    automatically collect data.
    """

    # read old ranking file
    path_evaluated = get_path(
        cfg,
        "processed",
        "mastodon",
        "instances_identification",
        # "instances_users_check_TOS_evaluated.csv",
        # "instances_users_check_TOS_evaluated_updated.csv",
        "instances_users_check_TOS_evaluated_updated_v2.csv",  # contains forgotten instances
    )
    evaluated_df = pd.read_csv(path_evaluated)

    return evaluated_df


def load_unnest_tprofiles_main(cfg):
    """
    Load twitter profiles with extracted mastodon handles for main processing.
    Fixing IDs. Unnesting column with public metrics, so that the df is ready
    for main processing.
    """

    print("Loading Twitter profiles for main processing...")

    # read twitter profiles with mastodon handles
    path_profiles_researchers = get_path(
        cfg,
        "processed",
        "twitter",
        "extract_handles",
        # "profiles_researchers_combined_handles.json",
        "profiles_researchers_combined_handles_updated.json",  # new version with deduplicated handles
    )
    profiles_researchers_df = pd.read_json(
        path_profiles_researchers, orient="records", lines=True
    )

    # bug fix: assign correctly represented string IDs to profiles_researchers_df
    # using original, unprocessed profiles with correctly specified dtype
    path_profiles_researchers_original = get_path(
        cfg,
        "processed",
        "twitter",
        "setup",
        "profiles_researchers_combined.json",
    )
    profiles_researchers_df_original = pd.read_json(
        path_profiles_researchers_original,
        orient="records",
        lines=True,
        dtype={"id": str},
    )
    profiles_researchers_df_original.drop_duplicates(
        subset=["description", "id", "username", "description"],
        inplace=True,
        ignore_index=True,
    )
    if not profiles_researchers_df_original.username.equals(
        profiles_researchers_df.username
    ):
        raise ValueError("Usernames are not identical in both DataFrames.")
    profiles_researchers_df["id"] = profiles_researchers_df_original["id"]
    if profiles_researchers_df["id"].duplicated().any():
        raise ValueError("ID column contains duplicate IDs.")

    # unnest column
    nested_columns = ["public_metrics"]
    unnested_columns = pd.concat(
        [unnest_column(profiles_researchers_df, col) for col in nested_columns], axis=1
    )
    if not profiles_researchers_df.index.is_unique:
        raise ValueError("The DataFrame index is not unique")
    if not unnested_columns.index.equals(profiles_researchers_df.index):
        raise ValueError("Index in unnested_columns is not identical to df.")
    profiles_researchers_df = profiles_researchers_df.join(unnested_columns)
    profiles_researchers_df = profiles_researchers_df.drop(nested_columns, axis=1)

    return profiles_researchers_df


def load_ttimelines_main(cfg):

    print("Loading Twitter timelines for main processing...")

    # path to file
    path_twitter_timelines = get_path(
        cfg,
        "processed",
        "twitter",
        "setup",
        "timelines_combined_final.json",
    )

    # use iterator to load data chunk by chunk
    twitter_timelines_df = pd.DataFrame()
    for chunk in tqdm(
        pd.read_json(
            path_twitter_timelines,
            lines=True,
            orient="records",
            chunksize=100000,
            dtype={"author_id": str, "conversation_id": str, "id": str},
        )
    ):
        twitter_timelines_df = pd.concat(
            [twitter_timelines_df, chunk], ignore_index=True
        )

    # # sanity check: all ids in json file should be strings
    # check_json_dtypes(
    #     path_twitter_timelines,
    #     fields_to_check=[
    #         "id",
    #         "author_id",
    #         "conversation_id",
    #     ],
    #     error=False,
    # )

    # # sanity check: all ids in pandas dataframe should be strings
    # check_df_dtypes(
    #     twitter_timelines_df,
    #     columns_to_check=["id", "author_id", "conversation_id"],
    #     error=False,
    # )

    return twitter_timelines_df


def load_influencer_tprofiles_main(cfg):

    # load influencer profiles with weighted influence score (based on stance
    # detection)
    print("Loading influencer Twitter profiles for main processing...")

    # load influencer profiles
    path_influencer_profiles_weighted = get_path(
        cfg,
        "processed",
        "twitter",
        "influencer_identification",
        # "influencer_profiles.json",
        "influencer_profiles_v2_weighted.json",
    )
    influencer_profiles_weighted_df = pd.read_json(
        path_influencer_profiles_weighted,
        orient="records",
        lines=True,
        dtype={"id": str},
    )

    return influencer_profiles_weighted_df


def load_influencer_followers_initial(cfg):
    """
    Load old version of influencer followers, to see how many IDs were already
    collected after update.
    """

    path_influencer_followers = get_path(
        cfg,
        "processed",
        "twitter",
        "setup",
        "influencers_followers_combined_updated.json",
    )
    check_json_format(path_influencer_followers)
    influencer_followers_df = pd.read_json(
        path_influencer_followers, orient="records", dtype={"to_id": str}
    )

    return influencer_followers_df


def load_influencer_followers_main(cfg):

    # load influencer followers
    path_influencer_followers = get_path(
        cfg,
        "processed",
        "twitter",
        "setup",
        # "influencers_followers_combined_updated.json",
        "influencers_followers_combined_updated_v2.json",
    )
    # influencer_followers_df = pd.read_json(path_influencer_followers, orient="records")
    influencer_followers_df = pd.read_json(
        path_influencer_followers, orient="records", dtype={"to_id": str}
    )

    return influencer_followers_df


def load_researchers_followed_influencer_IDs(cfg):

    path_researchers_followed_influencer_IDs = get_path(
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

    return researchers_followed_influencers_df


def load_posts_prepost_main(cfg):

    path_posts_pre_post_split = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split.json"
    )
    posts_pre_post_split = pd.read_json(
        path_posts_pre_post_split, orient="records", lines=True, dtype={"id": str}
    )
    return posts_pre_post_split


def load_tprofiles_prepost_main(cfg):

    path_profiles_researchers_df = get_path(
        cfg,
        "processed",
        "social_impact",
        "profiles_researchers_combined_handles_updated_prepost.json",
    )
    profiles_researchers_df = pd.read_json(
        path_profiles_researchers_df, orient="records", lines=True, dtype={"id": str}
    )

    return profiles_researchers_df


def load_posts_research_aggregated_main(cfg):

    path_posts_research_aggregated = get_path(
        cfg, "processed", "social_impact", "posts_research_aggregated.json"
    )
    posts_research_aggregated = pd.read_json(
        path_posts_research_aggregated, orient="records", lines=True, dtype={"id": str}
    )
    return posts_research_aggregated


def load_posts_research_aggregated_probs_main(cfg):

    path_posts_research_aggregated_probs = get_path(
        cfg, "processed", "social_impact", "posts_research_aggregated_probs.json"
    )
    posts_research_aggregated = pd.read_json(
        path_posts_research_aggregated_probs,
        orient="records",
        lines=True,
        dtype={"id": str},
    )
    return posts_research_aggregated


def load_tprofiles_prepost_si_main(cfg):

    path_profiles_researchers_df = get_path(
        cfg,
        "processed",
        "social_impact",
        "profiles_researchers_combined_handles_updated_prepost_si.json",
    )
    profiles_researchers_df = pd.read_json(
        path_profiles_researchers_df, orient="records", lines=True, dtype={"id": str}
    )

    return profiles_researchers_df


# paths for immediacy
def load_posts_pre_post_split_exploded_list(cfg):

    path_posts_pre_post_split_exploded_list = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_exploded_list.json"
    )
    with open(path_posts_pre_post_split_exploded_list, "r") as file:
        docs = json.load(file)

    return docs


def load_posts_pre_post_split_embeddings(cfg):

    path_docs_embeddings = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_embeddings.npy"
    )
    docs_embeddings = np.load(path_docs_embeddings)

    return docs_embeddings


def load_openalex_discipline_labels(cfg):

    path_zeroshot_topics = get_path(
        cfg, "processed", "social_impact", "micro_cluster.tsv"
    )
    zeroshot_topics_df = pd.read_csv(path_zeroshot_topics, sep="\t", encoding="latin1")

    return zeroshot_topics_df


def load_posts_pre_post_split_(cfg):

    path_posts_pre_post_split_ = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_.json"
    )
    posts_pre_post_split = pd.read_json(
        path_posts_pre_post_split_, orient="records", lines=True, dtype={"id": str}
    )

    return posts_pre_post_split


def load_posts_pre_post_split_exploded(cfg):

    path_posts_pre_post_split_exploded = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_exploded.json"
    )
    posts_pre_post_split_exploded = pd.read_json(
        path_posts_pre_post_split_exploded,
        orient="records",
        lines=True,
        dtype={"id": str},
    )

    return posts_pre_post_split_exploded


def load_doc_text_to_disciplines_text_df_50(cfg):

    path_doc_text_to_disciplines_text_df = get_path(
        cfg, "processed", "social_impact", "doc_text_to_disciplines_text_df_50.json"
    )
    doc_text_to_disciplines_text_df = pd.read_json(
        path_doc_text_to_disciplines_text_df, orient="records", lines=True
    )

    return doc_text_to_disciplines_text_df


def load_openalex_discipline_labels_embeddings(cfg):

    path_embeddings = get_path(
        cfg, "processed", "social_impact", "micro_cluster_embeddings_long.npy"
    )
    zeroshot_topics_list_embeddings = np.load(path_embeddings)

    return zeroshot_topics_list_embeddings
